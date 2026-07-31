from pathlib import Path

from django.conf import settings


def _asset_version():
    """Cache-busting stamp: newest asset mtime in DEBUG, release stamp otherwise."""
    if not settings.DEBUG:
        return getattr(settings, "ASSET_VERSION", "1")
    newest = 0
    for directory in settings.STATICFILES_DIRS:
        for path in Path(directory).rglob("*"):
            if path.suffix in {".css", ".js"}:
                newest = max(newest, int(path.stat().st_mtime))
    return str(newest or "1")


def site_settings(request):
    return {
        "ASSET_VERSION": _asset_version(),
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_CURRENCY": settings.SITE_CURRENCY,
        "SITE_CURRENCY_SYMBOL": settings.SITE_CURRENCY_SYMBOL,
        "WHATSAPP_NUMBER": settings.WHATSAPP_NUMBER,
        "ANNOUNCEMENT_TEXT": "Free delivery on orders over KSh 5,000 · New season essentials",
    }
