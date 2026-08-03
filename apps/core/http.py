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


def is_same_origin_request(request) -> bool:
    """Reject cross-site browser requests for sensitive JSON actions.

    Prefers Sec-Fetch-Site when present; falls back to Origin / Referer host checks.
    """
    fetch_site = (request.headers.get("Sec-Fetch-Site") or "").lower()
    if fetch_site == "cross-site":
        return False

    host = request.get_host()
    require_https = request.is_secure()

    origin = (request.headers.get("Origin") or "").strip()
    if origin:
        return url_has_allowed_host_and_scheme(
            url=origin,
            allowed_hosts={host},
            require_https=require_https,
        )

    referer = (request.headers.get("Referer") or "").strip()
    if referer:
        return url_has_allowed_host_and_scheme(
            url=referer,
            allowed_hosts={host},
            require_https=require_https,
        )

    # Some privacy browsers omit Origin/Referer on same-site XHR.
    return fetch_site in {"", "same-origin", "same-site", "none"}
