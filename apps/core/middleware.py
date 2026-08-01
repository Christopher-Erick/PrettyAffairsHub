"""HTTP middlewares for security headers and Cloudflare edge caching."""

from __future__ import annotations


class SecurityHeadersMiddleware:
    """Attach baseline security headers not covered by Django defaults."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response


# Paths that are safe to cache at the edge for anonymous visitors.
PUBLIC_PREFIXES = (
    "/",
    "/shop/",
    "/about/",
    "/faq/",
    "/blog/",
    "/contact/",
)

# Never edge-cache these (auth, cart, checkout, admin).
PRIVATE_PREFIXES = (
    "/admin/",
    "/manage/",
    "/accounts/",
    "/cart/",
    "/checkout/",
    "/orders/",
    "/wishlist/",
)


class CloudflareCacheMiddleware:
    """Set Cache-Control so Cloudflare's edge can hold public HTML.

    Authenticated or cart-bearing sessions stay private. Catalogue writes
    bump the app cache and optionally purge Cloudflare (see smart_cache).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != "GET":
            return response
        if response.status_code != 200:
            return response
        if self._is_private(request):
            response["Cache-Control"] = "private, no-store"
            return response
        if not self._is_public_path(request.path):
            return response

        # Browser: short. Cloudflare edge (s-maxage / CDN-Cache-Control): long.
        # Edge is purged when catalogue data changes (if API token is set).
        response["Cache-Control"] = (
            "public, max-age=60, s-maxage=86400, stale-while-revalidate=600"
        )
        response["CDN-Cache-Control"] = "public, max-age=86400"
        response["Vary"] = "Accept-Encoding, Cookie"
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
                if get("cart_id") or get("_auth_user_id"):
                    return True
        return False

    def _is_public_path(self, path: str) -> bool:
        if path in {"/", ""}:
            return True
        return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES if prefix != "/")
