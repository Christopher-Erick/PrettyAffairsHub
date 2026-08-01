"""Lightweight request rate limiting backed by the Django cache."""

from __future__ import annotations

import hashlib

from django.core.cache import cache
from django.http import HttpResponse


def client_ip(request) -> str:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR") or "unknown"


def rate_limit_exceeded(request, *, scope: str, limit: int, window_seconds: int) -> bool:
    """Return True when this client has exceeded `limit` hits in the window."""
    raw = f"{scope}:{client_ip(request)}"
    key = "rl:" + hashlib.sha256(raw.encode()).hexdigest()[:40]
    try:
        count = cache.get(key)
        if count is None:
            cache.set(key, 1, window_seconds)
            return False
        if int(count) >= limit:
            return True
        cache.incr(key)
        return False
    except Exception:
        # Cache outage must never block legitimate shoppers.
        return False


def too_many_requests(message: str = "Too many attempts. Please wait a moment and try again.") -> HttpResponse:
    return HttpResponse(message, status=429, content_type="text/plain; charset=utf-8")
