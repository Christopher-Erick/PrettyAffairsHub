"""Safe HTTP helpers shared across apps."""

from __future__ import annotations

from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_url(request, target: str | None, fallback: str = "/") -> str:
    """Return target only when it stays on this host; otherwise fallback."""
    if target and url_has_allowed_host_and_scheme(
        url=target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return fallback


def safe_redirect(request, target: str | None, fallback: str = "/") -> HttpResponseRedirect:
    return redirect(safe_redirect_url(request, target, fallback))
