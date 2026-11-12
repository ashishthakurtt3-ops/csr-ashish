"""
Django settings for CSR & Job Intelligence Platform.
"""
import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

from django.core.exceptions import ImproperlyConfigured


def _require_env(name):
    """Secrets are never hard-coded: a missing value stops the server with a clear message."""
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(
            f"Environment variable {name} is required (copy .env.example to .env and fill it in)."
        )
    return value


DEBUG = os.environ.get('DEBUG', 'False').strip().lower() in ('true', '1', 'yes')
SECRET_KEY = _require_env('SECRET_KEY')

_hosts = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]
if not DEBUG and '*' in _hosts:
    raise ImproperlyConfigured("ALLOWED_HOSTS must not contain '*' when DEBUG is off.")
if any('test' in arg.lower() for arg in sys.argv):
    if 'testserver' not in _hosts:
        _hosts.append('testserver')
ALLOWED_HOSTS = _hosts

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Project modular applications
    'modules.admin_panel.apps.AdminPanelConfig',
    'modules.website.apps.WebsiteConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'modules.website.middleware.StaticCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'modules.admin_panel.middleware.AdminRoleMiddleware',
    'modules.website.middleware.StrictSubscriptionEnforcementMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'modules.website.context_processors.global_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# MySQL is the ONLY database. Persistent connections with health checks.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": _require_env("MYSQL_DB"),
        "USER": _require_env("MYSQL_USER"),
        "PASSWORD": _require_env("MYSQL_PASSWORD"),
        "HOST": os.environ.get("MYSQL_HOST", "localhost"),
        "PORT": os.environ.get("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Session engine: cached_db for ultra-fast session reads backed by DB persistence
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# High-performance caching: Redis if REDIS_URL provided, else LocMemCache (per-process)
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL'),
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'impactbridge-locmem-cache',
            'TIMEOUT': 300,
        }
    }

# Logging configuration: turn off verbose SQL queries in normal/production operation
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Legacy (read-only) business database kept for one-time gap-fill imports.
# It is NEVER used as the application database.
LEGACY_MYSQL = {
    "HOST": os.environ.get("LEGACY_MYSQL_HOST", os.environ.get("MYSQL_HOST", "localhost")),
    "PORT": os.environ.get("LEGACY_MYSQL_PORT", os.environ.get("MYSQL_PORT", "3306")),
    "USER": os.environ.get("LEGACY_MYSQL_USER", os.environ.get("MYSQL_USER", "")),
    "PASSWORD": os.environ.get("LEGACY_MYSQL_PASSWORD", os.environ.get("MYSQL_PASSWORD", "")),
    "NAME": os.environ.get("LEGACY_MYSQL_DB", "csr_intelligence"),
}

# Custom User Model
AUTH_USER_MODEL = 'admin_panel.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = []
if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS.append(BASE_DIR / 'static')
if (BASE_DIR / 'static_admin').exists():
    STATICFILES_DIRS.append(BASE_DIR / 'static_admin')

STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_VERSION = '4.3.0'

# Media / Uploaded files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Email System Configuration
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'ImpactBridge <noreply@impactbridge.org>'
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Safety Guard: Global background crawler lock.
# Allowed for selectable 50-company batch crawling
ALLOW_GLOBAL_SYNC = True

# Phase 1 Safety Guard: Freeze all job deletion and expiration transitions until explicitly approved.
FREEZE_JOB_EXPIRY_AND_DELETION = True

# Step 0 Exact-Match Standard: Reconciliation freshness window (hours)
RECONCILE_MAX_AGE_HOURS = int(os.environ.get('RECONCILE_MAX_AGE_HOURS', 72))
ENFORCE_RECONCILE_FRESHNESS = os.environ.get('ENFORCE_RECONCILE_FRESHNESS', 'False').lower() in ('true', '1')


# ── Subscription and Payment Gateway Security Guards ──────────────────────────
ALLOW_PROTOTYPE_PAYMENTS = os.environ.get('ALLOW_PROTOTYPE_PAYMENTS', 'True' if DEBUG else 'False').strip().lower() in ('true', '1', 'yes')
ALLOW_DEMO_AUTH_FALLBACK = os.environ.get('ALLOW_DEMO_AUTH_FALLBACK', 'True' if DEBUG else 'False').strip().lower() in ('true', '1', 'yes')

# ── Browser and Transport Security Headers ────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False').lower() in ('true', '1')
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 0))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_SUBDOMAINS', 'False').lower() in ('true', '1')
    SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'False').lower() in ('true', '1')
