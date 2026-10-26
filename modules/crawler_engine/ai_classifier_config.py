"""
modules/crawler_engine/ai_classifier_config.py
==============================================
Central configuration for AI-Powered Official Website Discovery, Page Classification,
and Source Verification.

All AI API details, rate limits, models, token limits, thresholds, and operational flags
are centrally managed here outside the scraper code. Never hardcode credentials.
"""

import os
from pathlib import Path
from typing import Dict, Any

# ------------------------------------------------------------------------------
# 1. PROVIDER & MODEL CONFIGURATION
# ------------------------------------------------------------------------------
# Try loading environment variables from .env file if available
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# Primary provider (Gemini official API free tier)
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini").lower().strip()

# Fallback provider (Grok xAI - strict zero-cost policy only)
AI_FALLBACK_PROVIDER: str = os.getenv("AI_FALLBACK_PROVIDER", "grok").lower().strip()
AI_FALLBACK_ENABLED: bool = os.getenv("AI_FALLBACK_ENABLED", "true").lower() in ("true", "1", "yes")

# --- Google Gemini Configuration (Official Free Tier Only) ---
GEMINI_FREE_TIER_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b",
)
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
GEMINI_API_KEY_ENV: str = os.getenv("GEMINI_API_KEY_ENV", "GEMINI_API_KEY").strip()
GEMINI_BASE_URL: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").strip()

def is_gemini_free_tier_model(model_name: str) -> bool:
    """Verifies whether the given model name belongs to Google's official API free tier."""
    name = (model_name or "").lower().strip()
    if name.startswith("models/"):
        name = name[7:]
    return any(name == ft or name.startswith(ft) for ft in GEMINI_FREE_TIER_MODELS)

# --- Grok (xAI) Fallback Configuration (Strict Zero-Cost Requirement) ---
GROK_MODEL: str = os.getenv("GROK_MODEL", "grok-2-latest").strip()
GROK_API_KEY_ENV: str = os.getenv("GROK_API_KEY_ENV", "GROK_API_KEY").strip()
GROK_BASE_URL: str = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1").strip()

# Zero-cost policy: NEVER allow billable API calls under any circumstances
GROK_ZERO_COST_ONLY: bool = True
# Only enable Grok fallback if xAI account has confirmed, usable API credits that cover calls at zero cost
GROK_FREE_CREDITS_CONFIRMED: bool = os.getenv("GROK_FREE_CREDITS_CONFIRMED", "false").lower() in ("true", "1", "yes")
# Explicit warning: Web/app accounts (e.g. X Premium) do NOT grant free API credits on api.x.ai
GROK_WEB_ACCOUNT_DISCLAIMER: str = (
    "Free Grok web/app accounts do NOT provide free API usage. "
    "xAI developer API requires confirmed, non-billable promotional/grant credits to operate at zero cost."
)

# --- OpenRouter Configuration (Extensible / Legacy Alternative) ---
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
OPENROUTER_API_KEY_ENV: str = os.getenv("OPENROUTER_API_KEY_ENV", "OPENROUTER_API_KEY").strip()
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_REFERER: str = os.getenv("OPENROUTER_REFERER", "http://localhost:8000").strip()
OPENROUTER_TITLE: str = os.getenv("OPENROUTER_TITLE", "CSR & Job Intelligence Platform").strip()

# Default fallback values when database is unavailable
DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower().strip()
DEFAULT_AI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
DEFAULT_FALLBACK_PROVIDER = os.getenv("AI_FALLBACK_PROVIDER", "grok").lower().strip()
DEFAULT_FALLBACK_MODEL = os.getenv("GROK_MODEL", "grok-2-latest").strip()
DEFAULT_FALLBACK_ENABLED = os.getenv("AI_FALLBACK_ENABLED", "true").lower() in ("true", "1", "yes")

# Dynamic active provider model and endpoint assignment helpers
def get_active_provider() -> str:
    """Returns the centrally configured active AI provider."""
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        return get_active_ai_config().get("primary_provider", DEFAULT_AI_PROVIDER)
    except Exception:
        return DEFAULT_AI_PROVIDER

def get_active_model() -> str:
    """Returns the centrally configured active AI model."""
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        return get_active_ai_config().get("primary_model", DEFAULT_AI_MODEL)
    except Exception:
        return DEFAULT_AI_MODEL

def get_active_fallback_provider() -> str:
    """Returns the centrally configured fallback AI provider."""
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        return get_active_ai_config().get("fallback_provider", DEFAULT_FALLBACK_PROVIDER)
    except Exception:
        return DEFAULT_FALLBACK_PROVIDER

def get_active_fallback_model() -> str:
    """Returns the centrally configured fallback AI model."""
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        return get_active_ai_config().get("fallback_model", DEFAULT_FALLBACK_MODEL)
    except Exception:
        return DEFAULT_FALLBACK_MODEL

def is_fallback_enabled() -> bool:
    """Returns whether automatic failover is enabled."""
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        return get_active_ai_config().get("fallback_enabled", DEFAULT_FALLBACK_ENABLED)
    except Exception:
        return DEFAULT_FALLBACK_ENABLED

def is_free_tier_only_enforced() -> bool:
    """Returns whether cost protection / free-tier-only mode is active."""
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        return get_active_ai_config().get("free_tier_only", True)
    except Exception:
        return True


def __getattr__(name: str) -> Any:
    """
    PEP 562 dynamic module attribute lookup.
    Enables code accessing cfg.AI_MODEL, cfg.AI_PROVIDER, etc. to automatically
    receive the active configuration from the database without application restarts.
    """
    if name == "AI_PROVIDER":
        return get_active_provider()
    elif name == "AI_MODEL":
        return get_active_model()
    elif name == "GEMINI_MODEL":
        return get_active_model() if get_active_provider() == "gemini" else os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    elif name == "AI_FALLBACK_PROVIDER":
        return get_active_fallback_provider()
    elif name == "AI_FALLBACK_ENABLED":
        return is_fallback_enabled()
    elif name == "GROK_MODEL":
        return get_active_fallback_model()
    elif name == "REQUEST_TIMEOUT":
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            return get_active_ai_config().get("request_timeout", int(os.getenv("AI_REQUEST_TIMEOUT", "30")))
        except Exception:
            return int(os.getenv("AI_REQUEST_TIMEOUT", "30"))
    elif name == "MAX_RETRIES":
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            return get_active_ai_config().get("max_retries", int(os.getenv("AI_MAX_RETRIES", "3")))
        except Exception:
            return int(os.getenv("AI_MAX_RETRIES", "3"))
    elif name == "MAX_API_CALLS_PER_RUN":
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            return get_active_ai_config().get("max_api_calls_per_run", int(os.getenv("MAX_API_CALLS_PER_RUN", "50")))
        except Exception:
            return int(os.getenv("MAX_API_CALLS_PER_RUN", "50"))
    elif name == "AI_API_KEY_ENV":
        prov = get_active_provider()
        if prov == "gemini":
            return GEMINI_API_KEY_ENV
        elif prov == "grok":
            return GROK_API_KEY_ENV
        elif prov == "openrouter":
            return OPENROUTER_API_KEY_ENV
        return "AI_API_KEY"
    elif name == "AI_BASE_URL":
        prov = get_active_provider()
        if prov == "gemini":
            return GEMINI_BASE_URL
        elif prov == "grok":
            return GROK_BASE_URL
        elif prov == "openrouter":
            return OPENROUTER_BASE_URL
        return ""
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Unset static module-level variables so PEP 562 __getattr__ intercepts them dynamically at runtime
for _dynamic_attr in (
    "AI_PROVIDER",
    "AI_MODEL",
    "GEMINI_MODEL",
    "AI_FALLBACK_PROVIDER",
    "AI_FALLBACK_ENABLED",
    "GROK_MODEL",
    "AI_API_KEY_ENV",
    "AI_BASE_URL",
):
    if _dynamic_attr in globals():
        del globals()[_dynamic_attr]

# Prompt versioning for cache invalidation when prompt definitions change
PROMPT_VERSION: str = os.getenv("AI_PROMPT_VERSION", "v1.0").strip()
SUPPORTED_PROVIDERS = ("gemini", "grok", "openrouter", "mock")

# ------------------------------------------------------------------------------
# 2. OPERATIONAL & RUNTIME TOGGLES
# ------------------------------------------------------------------------------
# Master switch for AI classification. When False, uses deterministic rule-based fallback
AI_CLASSIFICATION_ENABLED: bool = os.getenv("AI_CLASSIFICATION_ENABLED", "true").lower() in ("true", "1", "yes")

# Dry run mode: if True, generates classifications & audit previews without modifying database
AI_DRY_RUN: bool = os.getenv("AI_DRY_RUN", "true").lower() in ("true", "1", "yes")

# Request caching to avoid redundant API calls and protect quota
AI_CACHE_ENABLED: bool = os.getenv("AI_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")

# Free quota exhaustion action: 'pause_and_save' (saves checkpoint and stops safely)
AI_QUOTA_EXHAUSTION_ACTION: str = os.getenv("AI_QUOTA_EXHAUSTION_ACTION", "pause_and_save").lower().strip()

# ------------------------------------------------------------------------------
# 3. RATE LIMITING, TIMEOUTS & QUOTA SAFEGUARDS
# ------------------------------------------------------------------------------
REQUEST_TIMEOUT: int = int(os.getenv("AI_REQUEST_TIMEOUT", "30"))
MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "3"))
BACKOFF_DELAY: float = float(os.getenv("AI_BACKOFF_DELAY", "2.0"))

# Enforce a maximum of 50 API requests per run by default, with a configurable hard limit
MAX_API_CALLS_PER_RUN: int = int(os.getenv("MAX_API_CALLS_PER_RUN", os.getenv("AI_MAX_API_CALLS_PER_RUN", "50")))


# Max tokens / bounded input sizing per request
MAX_INPUT_CHARS: int = int(os.getenv("AI_MAX_INPUT_CHARS", "14000"))
MAX_OUTPUT_TOKENS: int = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "4096"))

# Concurrency limits (1-3 recommended for free-tier quotas)
GLOBAL_CONCURRENCY: int = int(os.getenv("AI_CONCURRENCY", "2"))

# ------------------------------------------------------------------------------
# 4. BATCHING & PER-COMPANY BUDGETS
# ------------------------------------------------------------------------------
# Batch size for stage-one link name classification (compact JSON array)
LINK_BATCH_SIZE: int = int(os.getenv("AI_LINK_BATCH_SIZE", "10"))

# Maximum candidate links to collect per company during sitemap/DOM exploration
MAX_LINKS_PER_COMPANY: int = int(os.getenv("AI_MAX_LINKS_PER_COMPANY", "60"))
CANDIDATE_MAX_CAP: int = int(os.getenv("CANDIDATE_MAX_CAP", "50"))

# Crawler dynamic execution and probe parameters
PLAYWRIGHT_FALLBACK_LINK_THRESHOLD: int = int(os.getenv("PLAYWRIGHT_FALLBACK_LINK_THRESHOLD", "15"))
BROWSER_FINGERPRINT: str = os.getenv("CRAWLER_BROWSER_FINGERPRINT", "chrome124")
PROBE_RATE_LIMIT_DELAY: float = float(os.getenv("PROBE_RATE_LIMIT_DELAY", "0.2"))

# Maximum candidate pages to fetch and evaluate in Stage 2 per company
MAX_PAGES_PER_COMPANY: int = int(os.getenv("AI_MAX_PAGES_PER_COMPANY", "10"))

# ------------------------------------------------------------------------------
# 5. CLASSIFICATION LABELS & CONFIDENCE THRESHOLDS
# ------------------------------------------------------------------------------
# Stage 1: Discovered Link Categories
STAGE_1_BROAD_CATEGORIES = [
    "CAREERS_RECRUITMENT",
    "CSR_SOCIAL_IMPACT",
    "SUSTAINABILITY_ESG",
    "REPORTS_PUBLICATIONS",
    "OTHER_COMPANY_INFORMATION",
    "UNRELATED",
    "AMBIGUOUS"
]

STAGE_1_CANDIDATE_CATEGORIES = [
    "CAREERS_LANDING_CANDIDATE",
    "JOBS_LISTING_CANDIDATE",
    "INDIVIDUAL_JOB_CANDIDATE",
    "JOB_APPLICATION_CANDIDATE",
    "HR_INFORMATION_CANDIDATE",
    "CSR_OVERVIEW_CANDIDATE",
    "CSR_PROJECT_DISCLOSURE_CANDIDATE",
    "CSR_PARTNERSHIP_RFP_CANDIDATE",
    "SUSTAINABILITY_REPORT_CANDIDATE",
    "ANNUAL_REPORT_CANDIDATE",
    "CSR_REPORT_CANDIDATE",
    "UNKNOWN_REQUIRES_REVIEW"
]

# Stage 2: Verified Page Content Categories
STAGE_2_PAGE_CATEGORIES = [
    # Careers & Jobs
    "CAREERS_LANDING_PAGE",
    "JOBS_LISTING_PAGE",
    "INDIVIDUAL_JOB_PAGE",
    "JOB_APPLICATION_PAGE",
    "HR_INFORMATION_PAGE",
    # CSR
    "CSR_OVERVIEW_PAGE",
    "CSR_PROJECT_DISCLOSURE",
    "CSR_PARTNERSHIP_OR_RFP",
    # Reports
    "SUSTAINABILITY_OR_ESG_REPORT",
    "ANNUAL_REPORT_WITH_CSR_EVIDENCE",
    "CSR_REPORT",
    # Other
    "UNRELATED_PAGE",
    "INACCESSIBLE_PAGE",
    "INSUFFICIENT_CONTENT",
    "UNKNOWN_REQUIRES_REVIEW"
]

# Acceptance confidence thresholds by target page category
CLASSIFICATION_THRESHOLDS: Dict[str, float] = {
    "CAREERS_LANDING_PAGE": 0.70,
    "JOBS_LISTING_PAGE": 0.75,
    "INDIVIDUAL_JOB_PAGE": 0.75,
    "JOB_APPLICATION_PAGE": 0.80,
    "HR_INFORMATION_PAGE": 0.65,
    "CSR_OVERVIEW_PAGE": 0.70,
    "CSR_PROJECT_DISCLOSURE": 0.75,
    "CSR_PARTNERSHIP_OR_RFP": 0.85,
    "SUSTAINABILITY_OR_ESG_REPORT": 0.70,
    "ANNUAL_REPORT_WITH_CSR_EVIDENCE": 0.75,
    "CSR_REPORT": 0.70,
    "DEFAULT": 0.70
}

# Minimum margin of separation between the top predicted label and competing labels
MIN_LABEL_SEPARATION: float = float(os.getenv("AI_MIN_LABEL_SEPARATION", "0.15"))

# ------------------------------------------------------------------------------
# 6. CACHING & RESUME PATHS
# ------------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
CACHE_DIR: Path = BASE_DIR / ".cache" / "ai_classifier"
CHECKPOINT_DIR: Path = BASE_DIR / ".checkpoints"
REPORTS_DIR: Path = BASE_DIR / "reports" / "ai_discovery"
REPORT_DIR: Path = REPORTS_DIR


CACHE_EXPIRATION_HOURS: int = int(os.getenv("AI_CACHE_EXPIRATION_HOURS", "168"))  # 7 days

def get_config_summary() -> Dict[str, Any]:
    """Returns a non-secret summary of active AI classification configuration."""
    api_key_val = os.environ.get(AI_API_KEY_ENV, "")
    api_key_present = bool(api_key_val)
    grok_key_present = bool(os.environ.get(GROK_API_KEY_ENV) or os.environ.get("XAI_API_KEY"))
    return {
        "primary_provider": AI_PROVIDER,
        "primary_model": AI_MODEL,
        "gemini_model": GEMINI_MODEL,
        "primary_api_key_configured": api_key_present,
        "primary_api_key_env_var": AI_API_KEY_ENV,
        "primary_api_key_length": len(api_key_val) if api_key_present else 0,
        "is_primary_model_free_tier": is_gemini_free_tier_model(AI_MODEL) if AI_PROVIDER == "gemini" else True,
        "fallback_provider": AI_FALLBACK_PROVIDER,
        "fallback_enabled": AI_FALLBACK_ENABLED,
        "fallback_model": GROK_MODEL,
        "grok_zero_cost_only": GROK_ZERO_COST_ONLY,
        "grok_free_credits_confirmed": GROK_FREE_CREDITS_CONFIRMED,
        "grok_api_key_configured": grok_key_present,
        "grok_web_account_disclaimer": GROK_WEB_ACCOUNT_DISCLAIMER,
        "classification_enabled": AI_CLASSIFICATION_ENABLED,
        "dry_run": AI_DRY_RUN,
        "cache_enabled": AI_CACHE_ENABLED,
        "max_api_calls_per_run": MAX_API_CALLS_PER_RUN,
        "link_batch_size": LINK_BATCH_SIZE,
        "max_links_per_company": MAX_LINKS_PER_COMPANY,
        "max_pages_per_company": MAX_PAGES_PER_COMPANY,
        "candidate_max_cap": CANDIDATE_MAX_CAP,
        "playwright_fallback_link_threshold": PLAYWRIGHT_FALLBACK_LINK_THRESHOLD,
        "browser_fingerprint": BROWSER_FINGERPRINT,
        "probe_rate_limit_delay": PROBE_RATE_LIMIT_DELAY,
        "cache_dir": str(CACHE_DIR),
        "checkpoint_dir": str(CHECKPOINT_DIR),
    }
