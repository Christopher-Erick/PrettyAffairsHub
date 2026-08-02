"""Base settings shared by all environments."""

from pathlib import Path
from urllib.parse import unquote, urlparse

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_POSTGRES=(bool, False),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-change-me-pretty-affairs-hub")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

SITE_NAME = "Pretty Affairs Hub"
SITE_TAGLINE = "Your One Stop Beauty Destination"
SITE_CURRENCY = env("SITE_CURRENCY", default="KES")
SITE_CURRENCY_SYMBOL = env("SITE_CURRENCY_SYMBOL", default="KSh")
# Digits only with country code, e.g. 2547XXXXXXXX — enables the floating WhatsApp button.
WHATSAPP_NUMBER = env("WHATSAPP_NUMBER", default="")
SITE_PHONE = env("SITE_PHONE", default="")
SITE_EMAIL = env("SITE_EMAIL", default="")
SITE_INSTAGRAM = env("SITE_INSTAGRAM", default="")  # handle without @
SITE_TIKTOK = env("SITE_TIKTOK", default="")  # handle without @
SITE_CITY = env("SITE_CITY", default="Nairobi, Kenya")
SECURITY_CONTACT_EMAIL = env("SECURITY_CONTACT_EMAIL", default=SITE_EMAIL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "apps.core",
    "apps.catalog",
    "apps.content",
    "apps.accounts.apps.AccountsConfig",
    "apps.cart",
    "apps.orders",
    "apps.discounts",
    "apps.reviews",
    "apps.desk",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.accounts.middleware.ClientSessionPolicyMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "apps.core.middleware.CloudflareCacheMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
                "apps.accounts.context_processors.account_session",
                "apps.cart.context_processors.cart_context",
            ],
        },
    },
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:shop"
LOGOUT_REDIRECT_URL = "content:home"

WSGI_APPLICATION = "config.wsgi.application"


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    port = str(parsed.port or 5432)
    # Transaction pooler (Supabase :6543) must not hold persistent connections.
    conn_max_age = 0 if port == "6543" else 60
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (parsed.path.lstrip("/") or "postgres"),
        "USER": unquote(parsed.username or "postgres"),
        # Passwords in DATABASE_URL are percent-encoded when they contain @, !, %, etc.
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": port,
        "CONN_MAX_AGE": conn_max_age,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", default="require")},
    }


# Prefer Supabase / DATABASE_URL. Fall back to discrete POSTGRES_* or local SQLite.
DATABASE_URL = env("DATABASE_URL", default="")
SUPABASE_DB_URL = env("SUPABASE_DB_URL", default="")
if DATABASE_URL or SUPABASE_DB_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL or SUPABASE_DB_URL)}
elif env("USE_POSTGRES"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default="pretty_affairs_hub"),
            "USER": env("POSTGRES_USER", default="postgres"),
            "PASSWORD": env("POSTGRES_PASSWORD", default=""),
            "HOST": env("POSTGRES_HOST", default="localhost"),
            "PORT": env("POSTGRES_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", default="prefer")},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Africa/Nairobi")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Smart cache: Redis in production when REDIS_URL is set; LocMem for local.
# Catalogue entries live until writes invalidate them (see apps.core.smart_cache).
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": None,
            "KEY_PREFIX": "pah",
            # Fail fast instead of stalling a request when Redis is unreachable.
            "OPTIONS": {
                "socket_connect_timeout": 2,
                "socket_timeout": 2,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "pretty-affairs-hub",
            "TIMEOUT": None,
        }
    }

# Bust static/media browser caches on each Render deploy when available.
ASSET_VERSION = env("RENDER_GIT_COMMIT", default=env("ASSET_VERSION", default="1"))[:12]

# Read sessions through the cache, but always persist them in Postgres so a
# cache outage cannot break sign-in. See apps.core.sessions.
SESSION_ENGINE = "apps.core.sessions"
SESSION_CACHE_ALIAS = "default"
SESSION_SAVE_EVERY_REQUEST = False
# Client shoppers only — admins are exempt (see apps.accounts.session_policy).
CLIENT_IDLE_TIMEOUT_SECONDS = env.int("CLIENT_IDLE_TIMEOUT_SECONDS", default=20 * 60)

# Supabase project metadata (DB connection uses DATABASE_URL / SUPABASE_DB_URL above)
SUPABASE_URL = env("SUPABASE_URL", default="")
SUPABASE_ANON_KEY = env("SUPABASE_ANON_KEY", default="")

# Cloudflare — edge cache purge after catalogue writes
CLOUDFLARE_ACCOUNT_ID = env("CLOUDFLARE_ACCOUNT_ID", default="")
CLOUDFLARE_ZONE_ID = env("CLOUDFLARE_ZONE_ID", default="")
CLOUDFLARE_API_TOKEN = env("CLOUDFLARE_API_TOKEN", default="")
CLOUDFLARE_R2_BUCKET = env("CLOUDFLARE_R2_BUCKET", default="")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "strict-origin-when-cross-origin"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="Pretty Affairs Hub <onboarding@resend.dev>",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
# Resend HTTPS API (works on Render free tier). SMTP ports 25/465/587 are blocked
# on free web services, so prefer API whenever a Resend key is present.
RESEND_API_KEY = env("RESEND_API_KEY", default="") or EMAIL_HOST_PASSWORD
if RESEND_API_KEY and env("EMAIL_BACKEND", default="") == "":
    EMAIL_BACKEND = "apps.core.resend_backend.ResendAPIEmailBackend"
elif EMAIL_HOST and env("EMAIL_BACKEND", default="") == "":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Tax rate percent (0 = disabled / inclusive pricing)
TAX_RATE_PERCENT = env("TAX_RATE_PERCENT", default="0")
