"""Production settings — Supabase PostgreSQL + Cloudflare-ready."""

from .base import *  # noqa: F401, F403
from .base import DATABASE_URL, SUPABASE_DB_URL, _database_from_url, env

DEBUG = False
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Production always uses Supabase / Postgres — never SQLite.
if not (DATABASE_URL or SUPABASE_DB_URL):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER"),
            "PASSWORD": env("POSTGRES_PASSWORD"),
            "HOST": env("POSTGRES_HOST"),
            "PORT": env("POSTGRES_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
            "DISABLE_SERVER_SIDE_CURSORS": True,
            "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", default="require")},
        }
    }
else:
    DATABASES = {"default": _database_from_url(DATABASE_URL or SUPABASE_DB_URL)}
