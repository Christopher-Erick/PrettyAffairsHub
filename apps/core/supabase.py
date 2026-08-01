"""Supabase connection helpers.

Pretty Affairs Hub keeps Django models and admin. Supabase is the managed
PostgreSQL host (and optional Storage later) — not a Firebase-style rewrite.
"""

from __future__ import annotations

from django.conf import settings


def supabase_configured() -> bool:
    return bool(getattr(settings, "SUPABASE_URL", "") or getattr(settings, "DATABASE_URL", ""))


def supabase_project_url() -> str:
    return getattr(settings, "SUPABASE_URL", "") or ""


def database_backend_label() -> str:
    """Human-readable label for ops docs / health checks."""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgresql" in engine:
        host = settings.DATABASES["default"].get("HOST", "")
        if "supabase" in host or getattr(settings, "SUPABASE_URL", ""):
            return "Supabase PostgreSQL"
        return "PostgreSQL"
    if "sqlite" in engine:
        return "SQLite (local)"
    return engine
