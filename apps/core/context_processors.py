import time
from pathlib import Path

from django.conf import settings

_ASSET_VERSION_CACHE = {"value": "1", "expires": 0.0}


def _asset_version():
    """Cache-busting stamp: newest asset mtime in DEBUG, release stamp otherwise."""
    if not settings.DEBUG:
        return getattr(settings, "ASSET_VERSION", "1")
    now = time.monotonic()
    if now < _ASSET_VERSION_CACHE["expires"]:
        return _ASSET_VERSION_CACHE["value"]
    newest = 0
    for directory in settings.STATICFILES_DIRS:
        for path in Path(directory).rglob("*"):
            if path.suffix in {".css", ".js"}:
                newest = max(newest, int(path.stat().st_mtime))
    value = str(newest or "1")
    _ASSET_VERSION_CACHE["value"] = value
    _ASSET_VERSION_CACHE["expires"] = now + 5.0
    return value


def _nav_active(request):
    """Which primary nav item matches the current page (for tracking bar)."""
    match = getattr(request, "resolver_match", None)
    if not match:
        return {}
    ns = match.namespace or ""
    name = match.url_name or ""
    flag = request.GET.get("flag", "")
    return {
        "home": ns == "content" and name == "home",
        "shop": ns == "catalog"
        and (
            (name == "shop" and flag not in {"new", "bestsellers"})
            or name in {"product_detail", "category", "collection"}
        ),
        "new": ns == "catalog" and name == "shop" and flag == "new",
        "bestsellers": ns == "catalog" and name == "shop" and flag == "bestsellers",
        "bundles": ns == "catalog" and name in {"bundles", "bundle_detail"},
        "ritual": ns == "catalog" and name == "ritual_builder",
        "gifts": ns == "content" and name == "gift_cards",
        "journal": ns == "content" and name in {"blog", "blog_detail"},
        "about": ns == "content" and name == "about",
        "contact": ns == "content" and name == "contact",
        "account": ns == "accounts"
        and name
        in {
            "profile",
            "login",
            "register",
            "wishlist",
            "address_create",
            "password_reset",
            "password_reset_done",
            "password_reset_confirm",
            "password_reset_complete",
        },
    }


def site_settings(request):
    return {
        "ASSET_VERSION": _asset_version(),
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_CURRENCY": settings.SITE_CURRENCY,
        "SITE_CURRENCY_SYMBOL": settings.SITE_CURRENCY_SYMBOL,
        "WHATSAPP_NUMBER": settings.WHATSAPP_NUMBER,
        "SITE_PHONE": getattr(settings, "SITE_PHONE", ""),
        "SITE_EMAIL": getattr(settings, "SITE_EMAIL", ""),
        "SITE_INSTAGRAM": getattr(settings, "SITE_INSTAGRAM", ""),
        "SITE_TIKTOK": getattr(settings, "SITE_TIKTOK", ""),
        "SITE_CITY": getattr(settings, "SITE_CITY", ""),
        "ANNOUNCEMENT_TEXT": (
            "Free delivery on orders over KSh 5,000 · Easy returns on sealed items · Chat on WhatsApp"
        ),
        "NAV_ACTIVE": _nav_active(request),
    }
