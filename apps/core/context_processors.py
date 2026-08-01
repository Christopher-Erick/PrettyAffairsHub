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
        "SITE_CITY": getattr(settings, "SITE_CITY", ""),
        "ANNOUNCEMENT_TEXT": (
            "Free delivery on orders over KSh 5,000 · Easy returns on sealed items · Chat on WhatsApp"
        ),
    }
