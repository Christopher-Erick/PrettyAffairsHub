"""HTTP middlewares for security headers and Cloudflare edge caching."""

from __future__ import annotations


class SecurityHeadersMiddleware:
    """Attach baseline security headers not covered by Django defaults."""

    # Allow Google Fonts + self. Inline script is limited to the theme boot snippet
    # in base.html (localStorage theme). Tighten further when third-party tags arrive.
    CSP = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self' https://wa.me; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "upgrade-insecure-requests"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", self.CSP)
        return response


# Never edge-cache these (auth, cart, checkout, admin).
PRIVATE_PREFIXES = (
    "/admin/",
    "/manage/",
    "/accounts/",
    "/cart/",
    "/orders/",
)


class CloudflareCacheMiddleware:
    """Keep HTML private at the CDN; speed comes from Redis + static/media.

    Every storefront page embeds a CSRF token (footer newsletter and shop forms).
    Caching that HTML at Cloudflare would serve Visitor A's token to Visitor B and
    break add-to-cart / newsletter posts. Catalogue speed is handled by
    apps.core.smart_cache; Cloudflare should cache /static/ and /media/ only.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != "GET":
            return response
        if response.status_code != 200:
            return response

        content_type = (response.get("Content-Type") or "").lower()
        if content_type.startswith("text/html") or self._is_private(request):
            response["Cache-Control"] = "private, no-store"
            response["CDN-Cache-Control"] = "private, no-store"
            return response

        # Non-HTML public responses (robots, sitemap XML) may be shared briefly.
        response["Cache-Control"] = "public, max-age=300"
        response["Vary"] = "Accept-Encoding"
        return response

    def _is_private(self, request) -> bool:
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            return True
        path = request.path
        if any(path.startswith(prefix) for prefix in PRIVATE_PREFIXES):
            return True
        session = getattr(request, "session", None)
        if session is not None:
            session_key = getattr(session, "session_key", None)
            get = getattr(session, "get", None)
            if session_key and callable(get):
                if get("_auth_user_id") or (get("cart_item_count") or 0) > 0:
                    return True
        return False
