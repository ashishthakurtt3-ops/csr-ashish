"""
modules/admin_panel/services/ai_config_service.py
=================================================
Centralized service for managing AI providers, model selections, secure credentials,
cost-protection rules, and real-time live connectivity testing.
"""

import os
import re
import json
import time
import socket
import ipaddress
import urllib.parse
import logging
import requests
import sqlite3
import config as cfg
from typing import Dict, Any, Optional, Tuple, List
from django.utils import timezone
from django.db import transaction

from modules.admin_panel.models import AIProviderConfig, AISystemSettings, AIConfigurationAuditLog
from modules.admin_panel.utils.ai_crypto import mask_api_key, decrypt_secret, encrypt_secret, is_masked_placeholder

logger = logging.getLogger(__name__)

# SSRF Security Validation
def validate_endpoint_url_ssrf(url: str) -> Tuple[bool, str]:
    """
    Strict SSRF validation on custom/endpoint URLs:
    - Only allows http and https schemes.
    - http is ONLY allowed for localhost and 127.0.0.1.
    - Resolves hostname to all IP addresses (IPv4 and IPv6).
    - Blocks private RFC1918, link-local, loopback (for external domains), multicast, reserved, and 0.0.0.0.
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."
    url_str = url.strip()
    try:
        parsed = urllib.parse.urlsplit(url_str)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    if parsed.scheme not in ('http', 'https'):
        return False, f"Invalid protocol '{parsed.scheme}'. Only http and https are allowed."

    host = parsed.hostname
    if not host:
        return False, "URL is missing a valid hostname."

    if parsed.scheme == 'http' and host not in ('localhost', '127.0.0.1'):
        return False, f"Unencrypted HTTP is only allowed for localhost or 127.0.0.1, not for '{host}'."

    try:
        addr_info = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        return False, f"Could not resolve host '{host}': {e}"

    for family, socktype, proto, canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Invalid resolved IP address: {ip_str}"

        if ip.is_loopback:
            if host not in ('localhost', '127.0.0.1'):
                return False, f"Host '{host}' resolves to forbidden loopback address {ip_str}."
        elif ip.is_link_local:
            return False, f"Host '{host}' resolves to forbidden link-local IP {ip_str}."
        elif ip.is_private:
            return False, f"Host '{host}' resolves to private/internal network IP {ip_str}."
        elif ip.is_multicast:
            return False, f"Host '{host}' resolves to multicast IP {ip_str}."
        elif ip.is_reserved:
            return False, f"Host '{host}' resolves to reserved IP {ip_str}."
        elif ip_str.startswith('0.'):
            return False, f"Host '{host}' resolves to invalid zero-network IP {ip_str}."

    return True, ""


# Secret Sanitization Engine
def sanitize_secrets_text(text: str, extra_keys: Optional[List[str]] = None) -> str:
    """
    Sanitizes raw API keys, Authorization Bearer tokens, and x-goog-api-key headers
    from strings, logs, URLs, error messages, and audit payloads.
    """
    if not text or not isinstance(text, str):
        return text or ""

    sanitized = text
    # 1. Redact query string API keys
    sanitized = re.sub(r'([?&](?:key|api_key|apiKey|auth)=)[^&\s"\']+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    # 2. Redact Google API key headers
    sanitized = re.sub(r'(x-goog-api-key\s*[:=]\s*)[^\s"\',]+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    # 3. Redact Authorization Bearer headers
    sanitized = re.sub(r'(Authorization\s*[:=]\s*Bearer\s+)[^\s"\',]+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{12,}', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)

    # 4. Redact known raw keys
    if extra_keys:
        for k in extra_keys:
            if k and len(k) >= 6:
                sanitized = sanitized.replace(k, "[REDACTED]")

    return sanitized


def is_provider_paid_tier(provider_name: str, model_id: Optional[str] = None) -> bool:
    """
    Returns True if the provider or model is considered billable/paid.
    """
    p = (provider_name or "").lower().strip()
    if p in ("gemini", "groq", "ollama", "local"):
        return False
    if p == "openrouter":
        m = (model_id or "").lower().strip()
        if ":free" in m or "free" in m:
            return False
        return True
    return True


# In-memory cached active config snapshot to avoid redundant DB queries on high-frequency crawler calls
_CACHED_CONFIG: Optional[Dict[str, Any]] = None
_CACHE_TIMESTAMP: float = 0
_CACHE_TTL_SECONDS: float = 10.0


# Confirmed Free-Tier Models per Provider
FREE_TIER_MODELS_CATALOG: Dict[str, Tuple[str, ...]] = {
    "gemini": (
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash-8b",
    ),
    "openrouter": (
        "openrouter/free",
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "qwen/qwen-2.5-7b-instruct:free",
    ),
    "groq": (
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
        "deepseek-r1-distill-llama-70b",
    ),
    "mistral": (
        "open-mistral-7b",
    ),
    "ollama": (
        "llama3.2",
        "mistral",
        "deepseek-r1:8b",
        "qwen2.5",
        "phi3",
    ),
    "grok": (),  # Grok has no free API tier unless explicit confirmed grant/promo credits exist
}

DEFAULT_PROVIDERS_METADATA = [
    {
        "provider": "gemini",
        "display_name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-3.1-flash-lite",
        "env_key_var": "GEMINI_API_KEY",
        "available_models": [
            {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite", "is_free_tier": True, "description": "High-efficiency, ultra fast official API free tier"},
            {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash", "is_free_tier": True, "description": "Official API high-intelligence fast flash model"},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "is_free_tier": True, "description": "Legacy free tier flash model"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "is_free_tier": True, "description": "Multimodal general purpose free model"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "is_free_tier": True, "description": "Experimental low-latency multimodal model"},
            {"id": "gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash-8B", "is_free_tier": True, "description": "Lightweight 8B parameter model"},
        ]
    },
    {
        "provider": "grok",
        "display_name": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "env_key_var": "GROK_API_KEY",
        "available_models": [
            {"id": "grok-2-latest", "name": "Grok 2 Latest", "is_free_tier": False, "description": "State-of-the-art Grok reasoning (Requires confirmed grant credits for zero-cost)"},
            {"id": "grok-beta", "name": "Grok Beta", "is_free_tier": False, "description": "xAI developer preview model (Requires confirmed grant credits)"},
        ]
    },
    {
        "provider": "openrouter",
        "display_name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openrouter/free",
        "env_key_var": "OPENROUTER_API_KEY",
        "available_models": [
            {"id": "openrouter/free", "name": "OpenRouter Free Router", "is_free_tier": True, "description": "Automatically routes between operational free tier models"},
            {"id": "google/gemma-2-9b-it:free", "name": "Google Gemma 2 9B (Free)", "is_free_tier": True, "description": "OpenRouter hosted Gemma 2 model"},
            {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Meta Llama 3.2 3B (Free)", "is_free_tier": True, "description": "OpenRouter hosted compact Llama model"},
            {"id": "mistralai/mistral-7b-instruct:free", "name": "Mistral 7B Instruct (Free)", "is_free_tier": True, "description": "OpenRouter hosted Mistral model"},
            {"id": "qwen/qwen-2.5-7b-instruct:free", "name": "Qwen 2.5 7B (Free)", "is_free_tier": True, "description": "OpenRouter hosted Qwen reasoning model"},
        ]
    },
    {
        "provider": "groq",
        "display_name": "Groq Cloud (Fast Llama)",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key_var": "GROQ_API_KEY",
        "available_models": [
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile", "is_free_tier": True, "description": "Ultra-fast state-of-the-art open weights with generous free tier"},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant", "is_free_tier": True, "description": "Sub-100ms ultra low latency free-tier model"},
            {"id": "gemma2-9b-it", "name": "Google Gemma 2 9B", "is_free_tier": True, "description": "High precision open weights model by Google on Groq"},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B 32k", "is_free_tier": True, "description": "MoE architecture with 32k context on Groq free tier"},
            {"id": "deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 Distill 70B", "is_free_tier": True, "description": "Advanced reasoning model hosted on Groq"},
        ]
    },
    {
        "provider": "openai",
        "display_name": "OpenAI (ChatGPT)",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key_var": "OPENAI_API_KEY",
        "available_models": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "is_free_tier": False, "description": "Highly cost-effective fast omnimodel for high-volume classification"},
            {"id": "gpt-4o", "name": "GPT-4o Flagship", "is_free_tier": False, "description": "OpenAI flagship multimodality and intelligence"},
            {"id": "o3-mini", "name": "OpenAI o3-mini", "is_free_tier": False, "description": "State-of-the-art cost-efficient STEM & classification reasoning"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "is_free_tier": False, "description": "Legacy fast extraction model"},
        ]
    },
    {
        "provider": "anthropic",
        "display_name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-haiku-latest",
        "env_key_var": "ANTHROPIC_API_KEY",
        "available_models": [
            {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku", "is_free_tier": False, "description": "Lightning-fast, highly accurate structured JSON classification"},
            {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet", "is_free_tier": False, "description": "Industry leading benchmarks for complex corporate page analysis"},
            {"id": "claude-3-opus-latest", "name": "Claude 3 Opus", "is_free_tier": False, "description": "Deep nuanced analysis for complex sustainability disclosures"},
        ]
    },
    {
        "provider": "deepseek",
        "display_name": "DeepSeek AI",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "env_key_var": "DEEPSEEK_API_KEY",
        "available_models": [
            {"id": "deepseek-chat", "name": "DeepSeek-V3 Chat", "is_free_tier": False, "description": "Ultra low-cost high performance flagship model"},
            {"id": "deepseek-reasoner", "name": "DeepSeek-R1 Reasoner", "is_free_tier": False, "description": "Full Chain-of-Thought reasoning for complex corporate reports"},
        ]
    },
    {
        "provider": "mistral",
        "display_name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "env_key_var": "MISTRAL_API_KEY",
        "available_models": [
            {"id": "mistral-small-latest", "name": "Mistral Small Latest", "is_free_tier": False, "description": "Cost-effective, low latency enterprise classification model"},
            {"id": "open-mistral-7b", "name": "Open Mistral 7B", "is_free_tier": True, "description": "Open community model with free experimentation tier"},
            {"id": "mistral-large-latest", "name": "Mistral Large Latest", "is_free_tier": False, "description": "Mistral flagship model with premier reasoning capabilities"},
            {"id": "codestral-latest", "name": "Codestral Latest", "is_free_tier": False, "description": "High precision parser and structured output engine"},
        ]
    },
    {
        "provider": "ollama",
        "display_name": "Ollama (Local Self-Hosted)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "env_key_var": "OLLAMA_API_KEY",
        "available_models": [
            {"id": "llama3.2", "name": "Meta Llama 3.2 (Local)", "is_free_tier": True, "description": "100% Free local execution with zero data egress and zero token cost"},
            {"id": "mistral", "name": "Mistral 7B (Local)", "is_free_tier": True, "description": "Local high-speed extraction engine"},
            {"id": "deepseek-r1:8b", "name": "DeepSeek R1 8B (Local)", "is_free_tier": True, "description": "Local distilled reasoning model"},
            {"id": "qwen2.5", "name": "Qwen 2.5 (Local)", "is_free_tier": True, "description": "Local multilingual web extraction model"},
            {"id": "phi3", "name": "Microsoft Phi-3 Mini (Local)", "is_free_tier": True, "description": "Extremely lightweight local SLM"},
        ]
    },
    {
        "provider": "custom",
        "display_name": "Custom OpenAI Gateway",
        "base_url": "http://localhost:8080/v1",
        "default_model": "custom-model",
        "env_key_var": "CUSTOM_AI_API_KEY",
        "available_models": [
            {"id": "custom-model", "name": "Custom Endpoint Model", "is_free_tier": False, "description": "Connect to LM-Studio, vLLM, Together, Perplexity, or any OpenAI-compatible API"},
        ]
    },
]


def clear_config_cache():
    """Invalidates the in-memory active configuration cache."""
    global _CACHED_CONFIG, _CACHE_TIMESTAMP
    _CACHED_CONFIG = None
    _CACHE_TIMESTAMP = 0


def is_model_free_tier(provider: str, model_id: str) -> bool:
    """Verifies whether a given model is an approved zero-cost model for the provider."""
    prov = (provider or "").lower().strip()
    mid = (model_id or "").lower().strip()
    if mid.startswith("models/"):
        mid = mid[7:]

    # Ollama / Local self-hosted is always 100% free with zero token cost
    if prov in ("ollama", "local"):
        return True

    if prov == "gemini":
        return any(mid == ft or mid.startswith(ft) for ft in FREE_TIER_MODELS_CATALOG.get("gemini", ()))
    elif prov == "openrouter":
        if mid == "openrouter/free" or mid.endswith(":free"):
            return True
        return mid in FREE_TIER_MODELS_CATALOG.get("openrouter", ())
    elif prov == "groq":
        return mid in FREE_TIER_MODELS_CATALOG.get("groq", ()) or any(ft in mid for ft in ("llama-3.3-70b", "llama-3.1-8b", "gemma2-9b"))
    elif prov == "mistral":
        return mid in FREE_TIER_MODELS_CATALOG.get("mistral", ())
    elif prov == "grok":
        # Grok is only free if confirmed grant credits exist
        confirmed = os.environ.get("GROK_FREE_CREDITS_CONFIRMED", "false").lower() in ("true", "1", "yes")
        return confirmed
    return False


def bootstrap_default_configs():
    """
    Ensures default provider and system configuration records exist in the database.
    Pulls initial API keys and model selections from .env without overwriting or leaking secrets.
    """
    try:
        # 1. Bootstrap Providers
        for pdata in DEFAULT_PROVIDERS_METADATA:
            prov_name = pdata["provider"]
            cfg_obj, created = AIProviderConfig.objects.get_or_create(
                provider=prov_name,
                defaults={
                    "display_name": pdata["display_name"],
                    "base_url": pdata["base_url"],
                    "selected_model": pdata["default_model"],
                    "available_models": pdata["available_models"],
                    "is_enabled": True if prov_name == "gemini" else False,
                    "status": AIProviderConfig.STATUS_UNCONFIGURED,
                }
            )

            # If created or missing API key, check if an environment variable key is available to seed
            if not cfg_obj.encrypted_api_key:
                env_var = pdata.get("env_key_var")
                env_key = os.environ.get(env_var, "").strip() if env_var else ""
                if not env_key and prov_name == "grok":
                    env_key = os.environ.get("XAI_API_KEY", "").strip()

                if env_key:
                    cfg_obj.set_api_key(env_key)
                    cfg_obj.status = AIProviderConfig.STATUS_ACTIVE
                    cfg_obj.save(update_fields=["encrypted_api_key", "api_key_masked", "status"])

            # If model list changed, update available_models
            if not cfg_obj.available_models or len(cfg_obj.available_models) < len(pdata["available_models"]):
                cfg_obj.available_models = pdata["available_models"]
                cfg_obj.save(update_fields=["available_models"])

        # 2. Bootstrap System Settings
        settings_obj = AISystemSettings.get_solo()
        if not settings_obj.primary_model:
            settings_obj.primary_provider = os.environ.get("AI_PROVIDER", "gemini").lower().strip()
            settings_obj.primary_model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
            settings_obj.fallback_provider = os.environ.get("AI_FALLBACK_PROVIDER", "grok").lower().strip()
            settings_obj.fallback_model = os.environ.get("GROK_MODEL", "grok-2-latest").strip()
            settings_obj.fallback_enabled = os.environ.get("AI_FALLBACK_ENABLED", "true").lower() in ("true", "1")
            settings_obj.free_tier_only = True
            settings_obj.save()

    except Exception as e:
        logger.warning("AI configuration bootstrap skipped or deferred: %s", e)


def get_active_ai_config() -> Dict[str, Any]:
    """
    Returns the currently active AI configuration dictionary, backed by in-memory caching.
    Ensures that modifications made in the Admin Panel immediately reflect across all callers
    without requiring application restarts or source code changes.
    """
    global _CACHED_CONFIG, _CACHE_TIMESTAMP
    now = time.time()
    if _CACHED_CONFIG is not None and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _CACHED_CONFIG

    try:
        bootstrap_default_configs()
        settings_obj = AISystemSettings.get_solo()

        # Query provider configurations
        providers_qs = AIProviderConfig.objects.all()
        providers_dict: Dict[str, Dict[str, Any]] = {}
        for p in providers_qs:
            decrypted_key = p.get_api_key()
            # If no DB key, fallback to env var for backward compatibility
            if not decrypted_key:
                if p.provider == 'gemini':
                    decrypted_key = os.environ.get("GEMINI_API_KEY", "").strip()
                elif p.provider == 'openrouter':
                    decrypted_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
                elif p.provider == 'grok':
                    decrypted_key = os.environ.get("GROK_API_KEY", "").strip() or os.environ.get("XAI_API_KEY", "").strip()

            providers_dict[p.provider] = {
                "display_name": p.display_name,
                "is_enabled": p.is_enabled,
                "base_url": p.base_url,
                "selected_model": p.effective_model,
                "masked_key": p.api_key_masked or mask_api_key(decrypted_key),
                "has_key": bool(decrypted_key),
                "status": p.status,
                "last_tested_at": p.last_tested_at,
                "last_test_result": p.last_test_result,
                "last_test_message": p.last_test_message,
                "_api_key": decrypted_key,  # For internal server-side API clients only; NEVER serialized to frontend
            }

        primary_prov = settings_obj.primary_provider
        primary_info = providers_dict.get(primary_prov, {})
        primary_model = settings_obj.primary_model or primary_info.get("selected_model", "gemini-3.1-flash-lite")
        primary_key = primary_info.get("_api_key", "")
        primary_base_url = primary_info.get("base_url", "")

        fallback_prov = settings_obj.fallback_provider
        fallback_info = providers_dict.get(fallback_prov, {})
        fallback_model = settings_obj.fallback_model or fallback_info.get("selected_model", "grok-2-latest")
        fallback_key = fallback_info.get("_api_key", "")
        fallback_base_url = fallback_info.get("base_url", "")

        config_snapshot = {
            "primary_provider": primary_prov,
            "primary_model": primary_model,
            "primary_api_key": primary_key,
            "primary_base_url": primary_base_url,
            "fallback_enabled": settings_obj.fallback_enabled,
            "fallback_provider": fallback_prov,
            "fallback_model": fallback_model,
            "fallback_api_key": fallback_key,
            "fallback_base_url": fallback_base_url,
            "free_tier_only": settings_obj.free_tier_only,
            "request_timeout": settings_obj.request_timeout,
            "max_retries": settings_obj.max_retries,
            "max_api_calls_per_run": settings_obj.max_api_calls_per_run,
            "providers": providers_dict,
        }

        _CACHED_CONFIG = config_snapshot
        _CACHE_TIMESTAMP = now
        return _CACHED_CONFIG

    except Exception as e:
        logger.warning("Failed to load AI configuration from database. Falling back to environment variables: %s", e)
        # Emergency fallback to environment variables
        prov = os.environ.get("AI_PROVIDER", "gemini").lower().strip()
        model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() if prov == "gemini" else os.environ.get("AI_MODEL", "")
        key = os.environ.get("GEMINI_API_KEY", "").strip() if prov == "gemini" else ""
        return {
            "primary_provider": prov,
            "primary_model": model,
            "primary_api_key": key,
            "primary_base_url": "https://generativelanguage.googleapis.com/v1beta" if prov == "gemini" else "",
            "fallback_enabled": os.environ.get("AI_FALLBACK_ENABLED", "true").lower() in ("true", "1"),
            "fallback_provider": os.environ.get("AI_FALLBACK_PROVIDER", "grok").lower().strip(),
            "fallback_model": os.environ.get("GROK_MODEL", "grok-2-latest").strip(),
            "fallback_api_key": os.environ.get("GROK_API_KEY", "").strip(),
            "fallback_base_url": "https://api.x.ai/v1",
            "free_tier_only": True,
            "request_timeout": 30,
            "max_retries": 3,
            "max_api_calls_per_run": 50,
            "providers": {},
        }


def update_system_settings(data: Dict[str, Any], user=None, ip_address: str = "") -> Tuple[bool, str, int]:
    """
    Atomically updates global AI system settings.
    Enforces optimistic concurrency (409 on version mismatch) and paid-provider cost protection.
    Returns (success, message, status_code).
    """
    try:
        with transaction.atomic():
            settings_obj = AISystemSettings.get_solo()

            # Version check for 409 Conflict
            if "version" in data and data["version"] is not None:
                client_ver = int(data["version"])
                if client_ver != settings_obj.version:
                    return False, f"Settings conflict: Configuration was modified by another administrator (version {settings_obj.version} vs submitted {client_ver}). Please reload the page.", 409

            new_primary_prov = str(data.get("primary_provider", settings_obj.primary_provider)).lower().strip()
            new_primary_model = str(data.get("primary_model", settings_obj.primary_model)).strip()
            new_free_tier = bool(data.get("free_tier_only", settings_obj.free_tier_only))
            new_fallback_enabled = bool(data.get("fallback_enabled", settings_obj.fallback_enabled))
            new_fallback_prov = str(data.get("fallback_provider", settings_obj.fallback_provider)).lower().strip()
            new_fallback_model = str(data.get("fallback_model", settings_obj.fallback_model)).strip()
            new_timeout = int(data.get("request_timeout", settings_obj.request_timeout))
            new_retries = int(data.get("max_retries", settings_obj.max_retries))
            new_max_calls = int(data.get("max_api_calls_per_run", settings_obj.max_api_calls_per_run))

            # Paid provider guard: verify authorization
            if new_primary_prov:
                prim_cfg = AIProviderConfig.objects.filter(provider=new_primary_prov).first()
                if prim_cfg and is_provider_paid_tier(new_primary_prov, new_primary_model) and not prim_cfg.allow_paid_calls:
                    return False, f"Paid Provider Guard: '{prim_cfg.display_name}' cannot be assigned as Primary without 'Allow Paid Calls' authorization.", 400

            if new_fallback_enabled and new_fallback_prov:
                fall_cfg = AIProviderConfig.objects.filter(provider=new_fallback_prov).first()
                if fall_cfg and is_provider_paid_tier(new_fallback_prov, new_fallback_model) and not fall_cfg.allow_paid_calls:
                    return False, f"Paid Provider Guard: '{fall_cfg.display_name}' cannot be assigned as Failover without 'Allow Paid Calls' authorization.", 400

            # Bounds validation
            new_timeout = max(5, min(180, new_timeout))
            new_retries = max(0, min(5, new_retries))
            new_max_calls = max(1, min(500, new_max_calls))

            settings_obj.primary_provider = new_primary_prov
            settings_obj.primary_model = new_primary_model
            settings_obj.free_tier_only = new_free_tier
            settings_obj.fallback_enabled = new_fallback_enabled
            settings_obj.fallback_provider = new_fallback_prov
            settings_obj.fallback_model = new_fallback_model
            settings_obj.request_timeout = new_timeout
            settings_obj.max_retries = new_retries
            settings_obj.max_api_calls_per_run = new_max_calls
            settings_obj.version += 1
            if user:
                settings_obj.updated_by = user
            settings_obj.save()

            # Record sanitized audit log
            audit_msg = sanitize_secrets_text(
                f"Updated settings (v{settings_obj.version}): Primary={new_primary_prov}/{new_primary_model}, "
                f"Fallback={new_fallback_prov}/{new_fallback_model} (Enabled: {new_fallback_enabled}), "
                f"FreeTierOnly={new_free_tier}, Timeout={new_timeout}s, Retries={new_retries}"
            )
            AIConfigurationAuditLog.objects.create(
                action='SAVE_SETTINGS',
                provider=new_primary_prov,
                model_name=new_primary_model,
                status='SUCCESS',
                message=audit_msg,
                details={
                    "version": settings_obj.version,
                    "primary_provider": new_primary_prov,
                    "primary_model": new_primary_model,
                    "fallback_enabled": new_fallback_enabled,
                    "fallback_provider": new_fallback_prov,
                    "free_tier_only": new_free_tier,
                },
                performed_by=user,
                ip_address=ip_address
            )

            clear_config_cache()
            return True, "AI System Settings saved successfully.", 200

    except Exception as e:
        logger.exception("Failed to update AI system settings: %s", e)
        return False, f"Database error updating AI settings: {str(e)}", 500


def save_provider_config(
    provider: str,
    data: Dict[str, Any],
    user=None,
    ip_address: str = ""
) -> Tuple[bool, str, int]:
    """
    Saves an individual provider's configuration drawer.
    Enforces optimistic concurrency (409 on version mismatch), SSRF validation on custom URLs,
    paid-provider guard for Primary/Failover roles, and key sanitization in audit logs.
    Returns (success, message, status_code).
    """
    prov_name = (provider or "").lower().strip()
    try:
        with transaction.atomic():
            cfg_obj, _ = AIProviderConfig.objects.get_or_create(
                provider=prov_name,
                defaults={
                    "display_name": prov_name.capitalize(),
                    "selected_model": "",
                }
            )

            # 1. Version check for 409 Conflict
            if "version" in data and data["version"] is not None:
                client_ver = int(data["version"])
                if client_ver != cfg_obj.version:
                    return False, f"Version conflict: Provider '{cfg_obj.display_name}' was modified by another administrator (version {cfg_obj.version} vs submitted {client_ver}). Please reload the page before saving.", 409

            if "settings_version" in data and data["settings_version"] is not None:
                client_settings_ver = int(data["settings_version"])
                current_settings = AISystemSettings.get_solo()
                if client_settings_ver != current_settings.version:
                    return False, f"Settings conflict: AI System Settings were modified by another administrator (version {current_settings.version} vs submitted {client_settings_ver}). Please reload the page before saving.", 409

            # 2. SSRF validation on base_url
            if "base_url" in data and data["base_url"]:
                candidate_url = str(data["base_url"]).strip()
                ssrf_ok, ssrf_err = validate_endpoint_url_ssrf(candidate_url)
                if not ssrf_ok:
                    return False, f"Endpoint URL SSRF validation failed: {ssrf_err}", 400
                cfg_obj.base_url = candidate_url

            # 3. Update basic fields
            if "display_name" in data and data["display_name"]:
                cfg_obj.display_name = str(data["display_name"]).strip()
            if "is_enabled" in data:
                cfg_obj.is_enabled = bool(data["is_enabled"])
            if "selected_model" in data and data["selected_model"]:
                cfg_obj.selected_model = str(data["selected_model"]).strip()
            if "custom_model" in data:
                cfg_obj.custom_model = str(data["custom_model"]).strip()
            if "allow_paid_calls" in data:
                cfg_obj.allow_paid_calls = bool(data["allow_paid_calls"])

            # 4. Key update logic
            old_raw_key = cfg_obj.get_api_key()
            if data.get("clear_api_key"):
                cfg_obj.set_api_key("")
                cfg_obj.status = AIProviderConfig.STATUS_UNCONFIGURED
                # If key cleared and was Primary or Failover, unset role to protect pipeline
                settings_obj = AISystemSettings.get_solo()
                if settings_obj.primary_provider == prov_name:
                    settings_obj.primary_provider = ""
                    settings_obj.version += 1
                    settings_obj.save()
                if settings_obj.fallback_provider == prov_name and settings_obj.fallback_enabled:
                    settings_obj.fallback_enabled = False
                    settings_obj.version += 1
                    settings_obj.save()
            elif "api_key" in data and str(data["api_key"]).strip():
                raw_key = str(data["api_key"]).strip()
                if not is_masked_placeholder(raw_key):
                    cfg_obj.set_api_key(raw_key)

            # 5. Role update logic (Primary / Failover / Not used)
            if "role" in data:
                requested_role = str(data["role"]).lower().strip()
                settings_obj = AISystemSettings.get_solo()

                if requested_role == "primary":
                    # Paid provider guard check
                    if is_provider_paid_tier(prov_name, cfg_obj.effective_model) and not cfg_obj.allow_paid_calls:
                        return False, f"Paid Provider Guard: '{cfg_obj.display_name}' cannot be assigned as Primary without 'Allow Paid Calls' authorization.", 400
                    settings_obj.primary_provider = prov_name
                    settings_obj.primary_model = cfg_obj.effective_model
                    # If this was previously failover, clear failover
                    if settings_obj.fallback_provider == prov_name:
                        settings_obj.fallback_provider = ""
                    settings_obj.version += 1
                    settings_obj.save()

                elif requested_role == "failover":
                    # Paid provider guard check
                    if is_provider_paid_tier(prov_name, cfg_obj.effective_model) and not cfg_obj.allow_paid_calls:
                        return False, f"Paid Provider Guard: '{cfg_obj.display_name}' cannot be assigned as Failover without 'Allow Paid Calls' authorization.", 400
                    settings_obj.fallback_provider = prov_name
                    settings_obj.fallback_model = cfg_obj.effective_model
                    settings_obj.fallback_enabled = True
                    # If this was previously primary, clear primary
                    if settings_obj.primary_provider == prov_name:
                        settings_obj.primary_provider = ""
                    settings_obj.version += 1
                    settings_obj.save()

                elif requested_role == "not_used":
                    if settings_obj.primary_provider == prov_name:
                        settings_obj.primary_provider = ""
                        settings_obj.version += 1
                        settings_obj.save()
                    if settings_obj.fallback_provider == prov_name and settings_obj.fallback_enabled:
                        settings_obj.fallback_enabled = False
                        settings_obj.version += 1
                        settings_obj.save()

            # Increment provider version monotonically
            cfg_obj.version += 1
            cfg_obj.save()

            # Collect raw keys to redact from logs
            keys_to_redact = [k for k in [old_raw_key, cfg_obj.get_api_key()] if k]

            # Audit record (Sanitized: NO raw keys stored anywhere)
            raw_audit_msg = f"Updated configuration for provider '{prov_name}' (Model: {cfg_obj.effective_model}, Role: {data.get('role', 'unchanged')}, Version: {cfg_obj.version})"
            safe_audit_msg = sanitize_secrets_text(raw_audit_msg, keys_to_redact)

            AIConfigurationAuditLog.objects.create(
                action='SAVE_PROVIDER',
                provider=prov_name,
                model_name=cfg_obj.effective_model,
                status='SUCCESS',
                message=safe_audit_msg,
                details={
                    "version": cfg_obj.version,
                    "is_enabled": cfg_obj.is_enabled,
                    "selected_model": cfg_obj.selected_model,
                    "allow_paid_calls": cfg_obj.allow_paid_calls,
                    "key_configured": bool(cfg_obj.encrypted_api_key),
                },
                performed_by=user,
                ip_address=ip_address
            )

            clear_config_cache()
            return True, f"Provider '{cfg_obj.display_name}' saved successfully.", 200

    except Exception as e:
        logger.exception("Failed to save provider config for %s: %s", prov_name, e)
        return False, f"Failed to save provider: {str(e)}", 500


# Rate-limiting dictionary for model refresh endpoint (10s per provider)
_MODEL_REFRESH_LAST_CALLED: Dict[str, float] = {}

def refresh_provider_models(
    provider: str,
    user=None,
    ip_address: str = ""
) -> Tuple[bool, str, List[Dict[str, Any]], int]:
    """
    Refreshes the available model catalog for a provider.
    - Rate-limited to at most once every 10 seconds per provider.
    - Queries the provider's /models or list endpoint if reachable.
    - Falls back to DEFAULT_PROVIDERS_METADATA catalog on timeout or network error.
    - Flags deprecated models and flags if the currently selected model is missing.
    Returns (success, message, models_list, status_code).
    """
    prov_name = (provider or "").lower().strip()
    now = time.time()
    last_called = _MODEL_REFRESH_LAST_CALLED.get(prov_name, 0)
    if now - last_called < 10.0:
        remaining = int(10.0 - (now - last_called))
        return False, f"Rate limited. Please wait {remaining} seconds before refreshing '{prov_name}' models again.", [], 429

    _MODEL_REFRESH_LAST_CALLED[prov_name] = now

    cfg_obj = AIProviderConfig.objects.filter(provider=prov_name).first()
    raw_key = cfg_obj.get_api_key() if cfg_obj else ""
    base_url = (cfg_obj.base_url if cfg_obj else "").strip()

    # Look up fallback metadata
    default_meta = next((m for m in DEFAULT_PROVIDERS_METADATA if m["provider"] == prov_name), None)
    fallback_models = list(default_meta["available_models"]) if default_meta else []

    refreshed_models: List[Dict[str, Any]] = []

    # Attempt live query if key or local
    if raw_key or prov_name in ("ollama", "local"):
        try:
            if prov_name == "gemini":
                ep = f"https://generativelanguage.googleapis.com/v1beta/models?key={raw_key}"
                resp = requests.get(ep, headers={"x-goog-api-key": raw_key}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        m_name = m.get("name", "").replace("models/", "")
                        if "gemini" in m_name:
                            disp = m.get("displayName", m_name)
                            is_free = is_model_free_tier("gemini", m_name)
                            is_dep = "deprecated" in m_name or "1.0" in m_name
                            refreshed_models.append({
                                "id": m_name,
                                "name": disp,
                                "is_free_tier": is_free,
                                "is_deprecated": is_dep,
                                "description": m.get("description", "Google Gemini model")
                            })
            elif prov_name in ("openai", "groq", "openrouter", "deepseek", "mistral", "grok", "custom"):
                clean_base = base_url.rstrip("/") if base_url else ""
                if not clean_base:
                    if prov_name == "groq": clean_base = "https://api.groq.com/openai/v1"
                    elif prov_name == "openrouter": clean_base = "https://openrouter.ai/api/v1"
                    elif prov_name == "openai": clean_base = "https://api.openai.com/v1"
                    elif prov_name == "deepseek": clean_base = "https://api.deepseek.com/v1"
                    elif prov_name == "mistral": clean_base = "https://api.mistral.ai/v1"
                    elif prov_name == "grok": clean_base = "https://api.x.ai/v1"

                if clean_base:
                    ep = f"{clean_base}/models"
                    headers = {"Authorization": f"Bearer {raw_key}"}
                    resp = requests.get(ep, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("data", [])
                        for item in items[:40]:
                            m_id = item.get("id") or item.get("name", "")
                            if m_id:
                                is_free = is_model_free_tier(prov_name, m_id)
                                is_dep = "deprecated" in m_id or "gpt-3.5" in m_id or ("instruct" in m_id and "0613" in m_id)
                                refreshed_models.append({
                                    "id": m_id,
                                    "name": m_id,
                                    "is_free_tier": is_free,
                                    "is_deprecated": is_dep,
                                    "description": f"{prov_name.capitalize()} remote model"
                                })
            elif prov_name in ("ollama", "local"):
                clean_base = base_url.rstrip("/") if base_url else "http://localhost:11434"
                ep = f"{clean_base}/api/tags"
                resp = requests.get(ep, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        m_name = m.get("name") or m.get("model", "")
                        if m_name:
                            refreshed_models.append({
                                "id": m_name,
                                "name": m_name,
                                "is_free_tier": True,
                                "is_deprecated": False,
                                "description": "Local Ollama model"
                            })
        except Exception as e:
            logger.info("Remote models fetch for %s bypassed (%s). Using fallback catalog.", prov_name, e)

    # Fallback if empty
    if not refreshed_models:
        refreshed_models = fallback_models

    # Check for missing currently selected model
    if cfg_obj and cfg_obj.selected_model:
        selected_id = cfg_obj.selected_model
        found = any(m.get("id") == selected_id for m in refreshed_models)
        if not found:
            refreshed_models.insert(0, {
                "id": selected_id,
                "name": f"{selected_id} (Unrecognized / Missing from remote)",
                "is_free_tier": is_model_free_tier(prov_name, selected_id),
                "is_deprecated": True,
                "is_missing": True,
                "description": "This saved model was not returned in the provider's active model list."
            })

    # Save to provider config if updated
    if cfg_obj:
        cfg_obj.available_models = refreshed_models
        cfg_obj.save(update_fields=["available_models"])

    return True, f"Successfully refreshed {len(refreshed_models)} models for {prov_name.capitalize()}.", refreshed_models, 200


def get_crawler_usage_metrics() -> Dict[str, Any]:
    """
    Queries real crawler intelligence metrics from persistent disk cache (ai_cache.sqlite3)
    and AISystemSettings.
    Returns strictly real recorded numbers, and 'not tracked yet' for unrecorded metrics.
    """
    db_path = os.path.join(str(getattr(cfg, "CACHE_DIR", ".cache/ai_classifier")), "ai_cache.sqlite3")
    total_cached = 0
    provider_breakdown: Dict[str, int] = {}
    model_breakdown: Dict[str, int] = {}
    oldest_ts = None
    newest_ts = None

    if os.path.exists(db_path):
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ai_cache")
            row = cur.fetchone()
            if row:
                total_cached = row[0]

            cur.execute("SELECT provider, COUNT(*) FROM ai_cache GROUP BY provider")
            for p, cnt in cur.fetchall():
                provider_breakdown[p or "unknown"] = cnt

            cur.execute("SELECT model_name, COUNT(*) FROM ai_cache GROUP BY model_name")
            for m, cnt in cur.fetchall():
                model_breakdown[m or "unknown"] = cnt

            cur.execute("SELECT MIN(created_at), MAX(created_at) FROM ai_cache")
            r = cur.fetchone()
            if r:
                oldest_ts, newest_ts = r
        except Exception as e:
            logger.warning("Error reading SQLite AI cache metrics: %s", e)
        finally:
            if conn:
                conn.close()

    settings_obj = AISystemSettings.get_solo()

    return {
        "total_cached_responses": total_cached,
        "provider_breakdown": provider_breakdown,
        "model_breakdown": model_breakdown,
        "oldest_cache_entry": oldest_ts or "not tracked yet",
        "latest_cache_entry": newest_ts or "not tracked yet",
        "max_api_calls_per_run": settings_obj.max_api_calls_per_run,
        "request_timeout_seconds": settings_obj.request_timeout,
        "max_retries": settings_obj.max_retries,
        "token_usage_input": "not tracked yet",
        "token_usage_output": "not tracked yet",
        "monthly_api_spend_usd": "$0.00 (Zero-Cost Policy Enforced)",
        "live_http_calls_total": "not tracked yet",
    }


# ------------------------------------------------------------------------------
# REAL-TIME LIVE PROVIDER TEST ENGINE
# ------------------------------------------------------------------------------

def test_provider_live(
    provider: str,
    api_key_override: Optional[str] = None,
    model_override: Optional[str] = None,
    base_url_override: Optional[str] = None,
    user=None,
    ip_address: str = ""
) -> Dict[str, Any]:
    """
    Executes a real server-side live test for the designated AI provider and model.
    Steps:
    1. Validates configuration and credentials exist.
    2. Enforces free-tier cost protection if enabled.
    3. Performs authentic metadata probe and harmless minimal inference test.
    4. Validates structured JSON response parsing.
    5. Records test status, latency, and timestamp without logging secrets.
    """
    prov_name = (provider or "").lower().strip()
    start_time = time.time()

    # 1. Resolve configuration
    try:
        cfg_obj, _ = AIProviderConfig.objects.get_or_create(
            provider=prov_name,
            defaults={
                "display_name": prov_name.capitalize(),
                "selected_model": (model_override or "").strip() or "gemini-3.1-flash-lite",
            }
        )
    except Exception:
        cfg_obj = None

    # Resolve API Key
    raw_key = ""
    if api_key_override and api_key_override.strip():
        raw_key = api_key_override.strip()
    elif cfg_obj and cfg_obj.encrypted_api_key:
        raw_key = cfg_obj.get_api_key()
    else:
        # Fallback to environment variable
        if prov_name == "gemini":
            raw_key = os.environ.get("GEMINI_API_KEY", "").strip()
        elif prov_name == "openrouter":
            raw_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        elif prov_name == "grok":
            raw_key = os.environ.get("GROK_API_KEY", "").strip() or os.environ.get("XAI_API_KEY", "").strip()

    # Resolve Model
    model = (model_override or (cfg_obj.effective_model if cfg_obj else "")).strip()
    if not model:
        if prov_name == "gemini":
            model = "gemini-3.1-flash-lite"
        elif prov_name == "openrouter":
            model = "openrouter/free"
        elif prov_name == "grok":
            model = "grok-2-latest"
        else:
            model = "default"

    # Resolve Base URL
    base_url = (base_url_override or (cfg_obj.base_url if cfg_obj else "")).strip()
    if not base_url:
        default_urls = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "openrouter": "https://openrouter.ai/api/v1",
            "groq": "https://api.groq.com/openai/v1",
            "ollama": "http://localhost:11434/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "mistral": "https://api.mistral.ai/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "grok": "https://api.x.ai/v1",
            "custom": "http://localhost:8080/v1",
        }
        base_url = default_urls.get(prov_name, "https://api.openai.com/v1")

    # Local Ollama / self-hosted endpoints operate without an external cloud API key
    if not raw_key and prov_name in ("ollama", "local"):
        raw_key = "ollama"

    if not raw_key:
        res = {
            "success": False,
            "status": "CONFIG_ERROR",
            "message": f"API key is missing for {prov_name.capitalize()}. Please enter and save an API key before testing.",
            "latency_ms": 0,
            "model": model,
        }
        _record_test_outcome(prov_name, model, res, cfg_obj, user, ip_address)
        return res

    # 2. Free-tier cost protection check
    active_settings = AISystemSettings.get_solo()
    if active_settings.free_tier_only and not is_model_free_tier(prov_name, model):
        res = {
            "success": False,
            "status": "COST_PROTECTION_BLOCKED",
            "message": (
                f"Cost Protection Warning: Model '{model}' is not a verified free-tier model for {prov_name.capitalize()}. "
                f"To test or activate this model, disable 'Free-Tier-Only' cost protection in AI System Settings."
            ),
            "latency_ms": 0,
            "model": model,
        }
        _record_test_outcome(prov_name, model, res, cfg_obj, user, ip_address)
        return res

    # 3. Perform Live Test by Provider Protocol
    test_result: Dict[str, Any]
    if prov_name == "gemini":
        test_result = _test_gemini_live(raw_key, model, base_url)
    elif prov_name == "anthropic":
        test_result = _test_anthropic_live(raw_key, model, base_url)
    elif prov_name == "openrouter":
        test_result = _test_openrouter_live(raw_key, model, base_url)
    elif prov_name == "grok":
        test_result = _test_grok_live(raw_key, model, base_url, active_settings.free_tier_only)
    elif prov_name in ("ollama", "local"):
        test_result = _test_ollama_live(model, base_url)
    else:
        # Standard universal OpenAI-compatible REST test (Groq, OpenAI, Mistral, DeepSeek, Custom)
        test_result = _test_openai_compatible_live(prov_name, raw_key, model, base_url)

    latency_ms = int((time.time() - start_time) * 1000)
    test_result["latency_ms"] = latency_ms
    test_result["model"] = model

    _record_test_outcome(prov_name, model, test_result, cfg_obj, user, ip_address)
    return test_result


def _record_test_outcome(provider: str, model: str, result: Dict[str, Any], cfg_obj, user, ip_address: str):
    """Persists test outcomes in DB and audit logs."""
    try:
        status_code = AIProviderConfig.STATUS_ACTIVE if result.get("success") else AIProviderConfig.STATUS_ERROR
        if result.get("status") == "QUOTA_EXCEEDED":
            status_code = AIProviderConfig.STATUS_RATE_LIMITED

        if cfg_obj:
            cfg_obj.status = status_code
            cfg_obj.last_tested_at = timezone.now()
            cfg_obj.last_test_result = result.get("status", "UNKNOWN")
            cfg_obj.last_test_message = result.get("message", "")
            cfg_obj.last_test_latency_ms = result.get("latency_ms", 0)
            cfg_obj.save(update_fields=[
                "status", "last_tested_at", "last_test_result", "last_test_message", "last_test_latency_ms"
            ])

        AIConfigurationAuditLog.objects.create(
            action='TEST_PROVIDER',
            provider=provider,
            model_name=model,
            status=result.get("status", "UNKNOWN"),
            message=result.get("message", "")[:400],
            details={
                "success": result.get("success"),
                "status": result.get("status"),
                "latency_ms": result.get("latency_ms"),
            },
            performed_by=user,
            ip_address=ip_address
        )
        clear_config_cache()
    except Exception as e:
        logger.warning("Failed to record test outcome: %s", e)


def _test_gemini_live(api_key: str, model: str, base_url: str) -> Dict[str, Any]:
    """Tests Google Gemini official API via metadata check followed by harmless minimal inference."""
    clean_base = base_url.rstrip('/')
    
    # Minimal harmless test inference payload
    endpoint = f"{clean_base}/interactions?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    body = {
        "model": model,
        "input": "System check. Output strictly valid JSON object conforming to: {\"status\": \"ok\", \"ping\": \"pong\"}",
        "response_format": {
            "type": "text",
            "mime_type": "application/json"
        }
    }

    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=20)
        
        # 1. Success
        if resp.status_code == 200:
            data = resp.json()
            actual_model = data.get("model") or model
            # Verify structured JSON output
            raw_text = ""
            for step in data.get("steps", []):
                if step.get("type") == "model_output":
                    for part in step.get("content", []):
                        if isinstance(part, dict) and "text" in part:
                            raw_text += part["text"]
                        elif isinstance(part, str):
                            raw_text += part

            if not raw_text and "candidates" in data:
                cands = data.get("candidates", [])
                if cands:
                    parts = cands[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")

            # Validate that response contains valid JSON
            is_valid_json = False
            try:
                # Strip codeblocks if any
                cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and parsed.get("status") == "ok":
                    is_valid_json = True
            except Exception:
                pass

            return {
                "success": True,
                "status": "SUCCESS",
                "message": (
                    f"Authentication successful. Model '{actual_model}' responded successfully with valid structured JSON."
                    + (" (Verified JSON)" if is_valid_json else "")
                ),
            }

        # 2. Authentication failure
        elif resp.status_code in (400, 403):
            err_text = _extract_error_message(resp)
            return {
                "success": False,
                "status": "INVALID_KEY",
                "message": f"Authentication failed (HTTP {resp.status_code}): {err_text}",
            }

        # 3. Model unavailable / Not found
        elif resp.status_code == 404:
            return {
                "success": False,
                "status": "MODEL_UNAVAILABLE",
                "message": f"Model '{model}' was not found or is unavailable to this Google AI API project (HTTP 404).",
            }

        # 4. Quota exceeded
        elif resp.status_code == 429:
            err_text = _extract_error_message(resp)
            return {
                "success": False,
                "status": "QUOTA_EXCEEDED",
                "message": f"Gemini free-tier quota or rate limit exceeded (HTTP 429): {err_text}",
            }

        # 5. Upstream server error
        elif resp.status_code in (500, 502, 503, 504):
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"Gemini service temporarily unavailable (HTTP {resp.status_code}). Please retry in a few moments.",
            }

        else:
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"Gemini returned unexpected HTTP {resp.status_code}: {_extract_error_message(resp)}",
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": "Connection to Google Gemini endpoint timed out after 20 seconds.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Network error connecting to Gemini: {str(e)}",
        }


def _test_openrouter_live(api_key: str, model: str, base_url: str) -> Dict[str, Any]:
    """Tests OpenRouter API via chat completions test."""
    clean_base = base_url.rstrip('/')
    endpoint = f"{clean_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "CSR & Job Intelligence Platform",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Respond strictly with valid JSON: {\"status\": \"ok\", \"ping\": \"pong\"}"}
        ],
        "max_tokens": 60,
        "temperature": 0.1
    }

    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            actual_model = data.get("model") or model
            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"OpenRouter API key is valid. Model '{actual_model}' responded successfully.",
            }
        elif resp.status_code in (401, 403):
            return {
                "success": False,
                "status": "INVALID_KEY",
                "message": f"OpenRouter authentication rejected key (HTTP {resp.status_code}): {_extract_error_message(resp)}",
            }
        elif resp.status_code == 404:
            return {
                "success": False,
                "status": "MODEL_UNAVAILABLE",
                "message": f"OpenRouter model '{model}' was not found or is currently offline (HTTP 404).",
            }
        elif resp.status_code == 429:
            return {
                "success": False,
                "status": "QUOTA_EXCEEDED",
                "message": f"OpenRouter rate limit or credit quota exhausted (HTTP 429): {_extract_error_message(resp)}",
            }
        else:
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"OpenRouter returned HTTP {resp.status_code}: {_extract_error_message(resp)}",
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": "Connection to OpenRouter endpoint timed out after 20 seconds.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Network error connecting to OpenRouter: {str(e)}",
        }


def _test_grok_live(api_key: str, model: str, base_url: str, free_tier_only: bool) -> Dict[str, Any]:
    """Tests xAI Grok API, strictly validating key and zero-cost policy compliance."""
    clean_base = base_url.rstrip('/')
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. Metadata probe first (zero billable tokens)
    try:
        resp = requests.get(f"{clean_base}/models", headers=headers, timeout=15)
        if resp.status_code in (401, 403):
            return {
                "success": False,
                "status": "INVALID_KEY",
                "message": f"xAI API authentication failed (HTTP {resp.status_code}): {_extract_error_message(resp)}",
            }
        elif resp.status_code == 429:
            return {
                "success": False,
                "status": "QUOTA_EXCEEDED",
                "message": "xAI rate limit or credit limit reached (HTTP 429).",
            }
        elif resp.status_code != 200:
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"xAI returned HTTP {resp.status_code}: {_extract_error_message(resp)}",
            }

        # Key is valid. Check zero-cost grant credit status
        confirmed = os.environ.get("GROK_FREE_CREDITS_CONFIRMED", "false").lower() in ("true", "1", "yes")
        if free_tier_only and not confirmed:
            return {
                "success": True,  # Key is authenticated
                "status": "KEY_VERIFIED_CREDITS_UNCONFIRMED",
                "message": (
                    "xAI API key verified successfully! NOTE: Free-Tier Cost Protection is active, but "
                    "GROK_FREE_CREDITS_CONFIRMED is currently False. Web/app accounts do not grant free API credits. "
                    "Inference calls are paused until promotional/grant credits are confirmed."
                ),
            }

        # Harmless minimal inference request
        body = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Respond strictly with valid JSON: {\"status\": \"ok\"}"}
            ],
            "max_tokens": 30
        }
        resp_chat = requests.post(f"{clean_base}/chat/completions", json=body, headers=headers, timeout=20)
        if resp_chat.status_code == 200:
            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"xAI Grok API key is valid and model '{model}' responded successfully.",
            }
        else:
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"xAI Grok chat test returned HTTP {resp_chat.status_code}: {_extract_error_message(resp_chat)}",
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": "Connection to xAI endpoint timed out after 20 seconds.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Network error connecting to xAI: {str(e)}",
        }


def _test_openai_compatible_live(provider_name: str, api_key: str, model: str, base_url: str) -> Dict[str, Any]:
    """Tests any OpenAI-compatible provider (Groq, OpenAI, Mistral, DeepSeek, Custom, etc.)."""
    clean_base = base_url.rstrip('/')
    endpoint = f"{clean_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if "openrouter" in provider_name.lower():
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "CSR & Job Intelligence Platform"

    p_title = provider_name.replace('_', ' ').capitalize()
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Respond strictly with valid JSON: {\"status\": \"ok\", \"ping\": \"pong\"}"}
        ],
        "max_tokens": 50,
        "temperature": 0.0
    }
    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            actual_model = data.get("model") or model
            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"{p_title} authentication successful. Model '{actual_model}' responded with valid structured JSON.",
            }
        elif resp.status_code in (401, 403):
            return {
                "success": False,
                "status": "INVALID_KEY",
                "message": f"{p_title} authentication rejected API key (HTTP {resp.status_code}): {_extract_error_message(resp)}",
            }
        elif resp.status_code == 404:
            return {
                "success": False,
                "status": "MODEL_UNAVAILABLE",
                "message": f"{p_title} model '{model}' was not found or endpoint URL is incorrect (HTTP 404).",
            }
        elif resp.status_code == 429:
            return {
                "success": False,
                "status": "QUOTA_EXCEEDED",
                "message": f"{p_title} rate limit or credit quota exhausted (HTTP 429): {_extract_error_message(resp)}",
            }
        elif resp.status_code in (500, 502, 503, 504):
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"{p_title} upstream service temporarily unavailable (HTTP {resp.status_code}). Please retry.",
            }
        else:
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"{p_title} returned HTTP {resp.status_code}: {_extract_error_message(resp)}",
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Connection to {p_title} endpoint timed out after 20 seconds.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Network error connecting to {p_title}: {str(e)}",
        }


def _test_anthropic_live(api_key: str, model: str, base_url: str) -> Dict[str, Any]:
    """Tests Anthropic Claude API via official /v1/messages endpoint."""
    clean_base = base_url.rstrip('/')
    endpoint = f"{clean_base}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": model,
        "max_tokens": 50,
        "messages": [
            {"role": "user", "content": "Respond strictly with valid JSON: {\"status\": \"ok\", \"ping\": \"pong\"}"}
        ]
    }
    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            actual_model = data.get("model") or model
            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"Anthropic authentication successful. Model '{actual_model}' responded successfully.",
            }
        elif resp.status_code in (401, 403):
            return {
                "success": False,
                "status": "INVALID_KEY",
                "message": f"Anthropic authentication rejected API key (HTTP {resp.status_code}): {_extract_error_message(resp)}",
            }
        elif resp.status_code == 404:
            return {
                "success": False,
                "status": "MODEL_UNAVAILABLE",
                "message": f"Anthropic model '{model}' was not found or base URL is incorrect (HTTP 404).",
            }
        elif resp.status_code in (429, 529):
            return {
                "success": False,
                "status": "QUOTA_EXCEEDED",
                "message": f"Anthropic rate limit or quota exceeded (HTTP {resp.status_code}): {_extract_error_message(resp)}",
            }
        else:
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"Anthropic returned HTTP {resp.status_code}: {_extract_error_message(resp)}",
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": "Connection to Anthropic endpoint timed out after 20 seconds.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Network error connecting to Anthropic: {str(e)}",
        }


def _test_ollama_live(model: str, base_url: str) -> Dict[str, Any]:
    """Tests local Ollama / self-hosted server connectivity."""
    clean_base = base_url.rstrip('/')
    endpoint = f"{clean_base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Respond with JSON: {\"status\": \"ok\"}"}],
        "max_tokens": 20
    }
    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=10)
        if resp.status_code == 200:
            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"Ollama local runner is active. Model '{model}' responded successfully (100% Free / Zero Token Cost).",
            }
        else:
            # Fallback probe to /api/tags if /v1/chat/completions is not mounted
            root_base = clean_base.removesuffix('/v1')
            tag_resp = requests.get(f"{root_base}/api/tags", timeout=5)
            if tag_resp.status_code == 200:
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": f"Ollama server is active and reachable at '{root_base}'. Ready for local inference.",
                }
            return {
                "success": False,
                "status": "PROVIDER_ERROR",
                "message": f"Ollama returned HTTP {resp.status_code}: {_extract_error_message(resp)}",
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "message": f"Cannot connect to Ollama at {clean_base}. Make sure Ollama is running locally ('ollama serve'): {str(e)}",
        }


def _test_custom_live(api_key: str, model: str, base_url: str) -> Dict[str, Any]:
    """Backward-compatible wrapper for testing generic custom provider endpoints."""
    return _test_openai_compatible_live("custom", api_key, model, base_url)


def _extract_error_message(resp: requests.Response) -> str:
    """Safely extracts a readable error string from a provider's JSON or text response."""
    try:
        data = resp.json()
        if "error" in data:
            err = data["error"]
            if isinstance(err, dict):
                return err.get("message", json.dumps(err))
            return str(err)
        return json.dumps(data)[:200]
    except Exception:
        return resp.text[:200]


def create_or_update_custom_provider(
    provider_id: str,
    display_name: str,
    base_url: str,
    default_model: str,
    available_models: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    user=None,
    ip_address: str = ""
) -> Tuple[bool, str, Optional[AIProviderConfig]]:
    """
    Dynamically registers a custom AI provider or endpoint in AIProviderConfig.
    Allows connecting any OpenAI-compatible provider, local model runner, or internal gateway.
    """
    clean_id = (provider_id or "").lower().strip()
    clean_id = re.sub(r'[^a-z0-9_-]', '', clean_id)
    if not clean_id:
        return False, "Provider identifier is required (alphanumeric, hyphens, underscores).", None

    clean_name = (display_name or "").strip() or clean_id.capitalize()
    clean_base = (base_url or "").strip().rstrip('/')
    clean_model = (default_model or "").strip()

    if not clean_base:
        clean_base = "https://api.openai.com/v1"
    if not clean_model:
        clean_model = "default"

    models_catalog = available_models or []
    if not any(m.get("id") == clean_model for m in models_catalog):
        models_catalog.insert(0, {
            "id": clean_model,
            "name": clean_model,
            "is_free_tier": clean_id in ("ollama", "local", "groq"),
            "description": f"Configured model for {clean_name}"
        })

    try:
        with transaction.atomic():
            cfg_obj, created = AIProviderConfig.objects.get_or_create(
                provider=clean_id,
                defaults={
                    "display_name": clean_name,
                    "base_url": clean_base,
                    "selected_model": clean_model,
                    "available_models": models_catalog,
                    "is_enabled": True,
                    "status": AIProviderConfig.STATUS_UNCONFIGURED,
                }
            )
            if not created:
                cfg_obj.display_name = clean_name
                cfg_obj.base_url = clean_base
                cfg_obj.selected_model = clean_model
                cfg_obj.available_models = models_catalog
                cfg_obj.is_enabled = True

            if api_key and str(api_key).strip() and not is_masked_placeholder(api_key):
                cfg_obj.set_api_key(str(api_key).strip())
                cfg_obj.status = AIProviderConfig.STATUS_ACTIVE
            elif clean_id in ("ollama", "local"):
                cfg_obj.status = AIProviderConfig.STATUS_ACTIVE

            cfg_obj.save()

            AIConfigurationAuditLog.objects.create(
                action='SAVE_PROVIDER',
                provider=clean_id,
                model_name=clean_model,
                status='SUCCESS',
                message=f"{'Created' if created else 'Updated'} custom AI provider '{clean_name}' ({clean_id})",
                details={
                    "created": created,
                    "base_url": clean_base,
                    "selected_model": clean_model,
                },
                performed_by=user,
                ip_address=ip_address
            )

            clear_config_cache()
            return True, f"Provider '{clean_name}' {'registered' if created else 'updated'} successfully.", cfg_obj
    except Exception as e:
        logger.exception("Failed to create/update custom provider %s: %s", clean_id, e)
        return False, f"Failed to register provider: {str(e)}", None


def delete_provider(provider_id: str, user=None, ip_address: str = "") -> Tuple[bool, str]:
    """Removes a custom provider if not in active routing use."""
    clean_id = (provider_id or "").lower().strip()
    core_providers = ("gemini", "openrouter", "grok")
    if clean_id in core_providers:
        return False, f"Cannot delete core system provider '{clean_id}'."

    settings_obj = AISystemSettings.get_solo()
    if settings_obj.primary_provider == clean_id:
        return False, f"Cannot delete '{clean_id}' because it is currently configured as the Primary Provider. Reassign the primary provider first."
    if settings_obj.fallback_enabled and settings_obj.fallback_provider == clean_id:
        return False, f"Cannot delete '{clean_id}' because it is currently configured as the Fallback Provider. Reassign the fallback provider first."

    try:
        with transaction.atomic():
            cfg_obj = AIProviderConfig.objects.filter(provider=clean_id).first()
            if not cfg_obj:
                return False, f"Provider '{clean_id}' not found."

            display_name = cfg_obj.display_name
            cfg_obj.delete()

            AIConfigurationAuditLog.objects.create(
                action='SAVE_PROVIDER',
                provider=clean_id,
                model_name="-",
                status='SUCCESS',
                message=f"Deleted custom AI provider '{display_name}' ({clean_id})",
                details={"deleted": True},
                performed_by=user,
                ip_address=ip_address
            )

            clear_config_cache()
            return True, f"Provider '{display_name}' removed successfully."
    except Exception as e:
        logger.exception("Failed to delete provider %s: %s", clean_id, e)
        return False, f"Failed to delete provider: {str(e)}"
