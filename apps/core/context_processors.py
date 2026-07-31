from django.conf import settings


def site_settings(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_CURRENCY": settings.SITE_CURRENCY,
        "SITE_CURRENCY_SYMBOL": settings.SITE_CURRENCY_SYMBOL,
        "WHATSAPP_NUMBER": settings.WHATSAPP_NUMBER,
        "ANNOUNCEMENT_TEXT": "Free delivery on orders over KSh 5,000 · New season essentials",
    }
