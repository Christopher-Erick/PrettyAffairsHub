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

        # Browser: 5 minutes for anonymous HTML. Edge (s-maxage): 1 day when Cloudflare proxies.
        response["Cache-Control"] = (
            "public, max-age=300, s-maxage=86400, stale-while-revalidate=600"
        )
        response["CDN-Cache-Control"] = "public, max-age=86400"
        # Only vary on encoding for anonymous HTML — Cookie would kill edge/browser reuse.
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

    def _is_public_path(self, path: str) -> bool:
        if path in {"/", ""}:
            return True
        return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES if prefix != "/")
