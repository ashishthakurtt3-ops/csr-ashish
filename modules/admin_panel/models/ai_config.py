"""
modules/admin_panel/models/ai_config.py
=======================================
Database models for Centralized AI Models & API Configuration.
Provides:
- AIProviderConfig: Configuration, encrypted credentials, model choices, and health status per provider.
- AISystemSettings: Singleton configuration for active primary/fallback selections and cost protection.
- AIConfigurationAuditLog: Tamper-evident audit trail of all AI configuration adjustments and tests.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from modules.admin_panel.utils.ai_crypto import encrypt_secret, decrypt_secret, mask_api_key


class AIProviderConfig(models.Model):
    """
    Configuration and state for an AI provider (Gemini, OpenRouter, Grok, Custom).
    Stores encrypted API credentials at rest and tracks health/testing diagnostics.
    """
    STATUS_UNCONFIGURED = 'UNCONFIGURED'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_ERROR = 'ERROR'
    STATUS_RATE_LIMITED = 'RATE_LIMITED'

    STATUS_CHOICES = [
        (STATUS_UNCONFIGURED, 'Unconfigured / Pending Setup'),
        (STATUS_ACTIVE, 'Active & Verified'),
        (STATUS_ERROR, 'Authentication / Network Error'),
        (STATUS_RATE_LIMITED, 'Rate Limited / Quota Exhausted'),
    ]

    provider = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique provider identifier (e.g. 'gemini', 'openrouter', 'grok', 'custom')"
    )
    display_name = models.CharField(max_length=100, help_text="Human-readable provider name")
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this provider is permitted for classification requests."
    )
    allow_paid_calls = models.BooleanField(
        default=False,
        help_text="Explicit administrator authorization permitting billable API calls to this paid provider."
    )
    version = models.IntegerField(
        default=1,
        help_text="Monotonically increasing version counter for optimistic concurrency locking."
    )
    encrypted_api_key = models.TextField(
        blank=True,
        default="",
        help_text="Encrypted API key ciphertext stored securely at rest."
    )
    api_key_masked = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Masked representation of API key safe for public admin display."
    )
    base_url = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Custom or default base URL endpoint."
    )
    selected_model = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Active selected model identifier."
    )
    custom_model = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional custom model ID override."
    )
    available_models = models.JSONField(
        default=list,
        blank=True,
        help_text="Catalog of known supported models with metadata."
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_UNCONFIGURED
    )
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_result = models.CharField(max_length=60, blank=True, default="")
    last_test_message = models.TextField(blank=True, default="")
    last_test_latency_ms = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_provider_config'
        ordering = ['provider']
        verbose_name = 'AI Provider Configuration'
        verbose_name_plural = 'AI Provider Configurations'

    def __str__(self):
        return f"{self.display_name} ({self.provider}) [{self.status}]"

    def set_api_key(self, raw_key: str):
        """Encrypts and sets the raw API key without storing plaintext."""
        clean = (raw_key or "").strip()
        if clean:
            self.encrypted_api_key = encrypt_secret(clean)
            self.api_key_masked = mask_api_key(clean)
        else:
            self.encrypted_api_key = ""
            self.api_key_masked = ""

    def get_api_key(self) -> str:
        """Decrypts and returns the raw API key for server-side outbound requests."""
        if not self.encrypted_api_key:
            return ""
        return decrypt_secret(self.encrypted_api_key)

    @property
    def key_last4(self) -> str:
        """Returns the trailing 4 characters of the decrypted key, or empty string."""
        raw = self.get_api_key()
        if not raw:
            return ""
        return raw[-4:] if len(raw) >= 4 else raw

    @property
    def effective_model(self) -> str:
        """Returns the custom model ID if defined, otherwise the selected model ID."""
        return (self.custom_model or self.selected_model or "").strip()


class AISystemSettings(models.Model):
    """
    Centralized singleton record managing active primary and fallback selections,
    strict cost-protection flags, and request quotas across the application.
    """
    primary_provider = models.CharField(
        max_length=50,
        default='gemini',
        help_text="Primary AI provider for classifications ('gemini', 'openrouter', 'grok')"
    )
    primary_model = models.CharField(
        max_length=100,
        default='gemini-3.1-flash-lite',
        help_text="Primary model identifier."
    )
    fallback_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic failover if primary provider is rate-limited or unavailable."
    )
    fallback_provider = models.CharField(
        max_length=50,
        default='grok',
        blank=True,
        help_text="Fallback AI provider name."
    )
    fallback_model = models.CharField(
        max_length=100,
        default='grok-2-latest',
        blank=True,
        help_text="Fallback model identifier."
    )
    free_tier_only = models.BooleanField(
        default=True,
        help_text="Strict cost protection: block paid models and unconfirmed credits."
    )
    request_timeout = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(180)],
        help_text="HTTP request timeout in seconds."
    )
    max_retries = models.IntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Maximum backoff retry attempts for transient errors."
    )
    max_api_calls_per_run = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text="Maximum AI requests permitted in a single pipeline run."
    )
    version = models.IntegerField(
        default=1,
        help_text="Monotonically increasing version counter for optimistic concurrency locking."
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'admin_panel.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ai_settings_updates'
    )

    class Meta:
        db_table = 'ai_system_settings'
        verbose_name = 'AI System Settings'
        verbose_name_plural = 'AI System Settings'

    def __str__(self):
        return f"AI System Settings: Primary={self.primary_provider}/{self.primary_model} (Free Tier Only: {self.free_tier_only})"

    @classmethod
    def get_solo(cls) -> 'AISystemSettings':
        """Singleton getter ensuring exactly one settings instance exists."""
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class AIConfigurationAuditLog(models.Model):
    """
    Immutable audit history recording all AI configuration changes and live tests.
    Strictly sanitizes details to NEVER record raw API keys or sensitive authorization headers.
    """
    ACTION_CHOICES = [
        ('SAVE_SETTINGS', 'Updated AI System Settings'),
        ('SAVE_PROVIDER', 'Updated Provider Configuration'),
        ('TEST_PROVIDER', 'Executed Live API & Model Test'),
        ('RESET_DEFAULTS', 'Reset AI Configuration to Defaults'),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    provider = models.CharField(max_length=50, blank=True, default="")
    model_name = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=50, blank=True, default="")
    message = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    performed_by = models.ForeignKey(
        'admin_panel.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ai_audit_logs'
    )
    ip_address = models.CharField(max_length=45, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_configuration_audit_log'
        ordering = ['-timestamp']
        verbose_name = 'AI Configuration Audit Log'
        verbose_name_plural = 'AI Configuration Audit Logs'

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.action} ({self.provider}) -> {self.status}"

    @property
    def latency_ms(self):
        if isinstance(self.details, dict):
            return self.details.get('latency_ms')
        return None
