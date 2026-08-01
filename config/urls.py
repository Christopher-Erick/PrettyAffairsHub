from django.contrib import admin
from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_control
from django.views.static import serve

from apps.core.sitemaps import sitemaps


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /manage/",
        "Disallow: /accounts/",
        "Disallow: /cart/",
        "Disallow: /orders/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def security_txt(request):
    contact = getattr(settings, "SECURITY_CONTACT_EMAIL", "") or getattr(settings, "SITE_EMAIL", "")
    lines = [
        f"Contact: mailto:{contact}" if contact else "Contact: https://prettyaffairshub.onrender.com/contact/",
        "Preferred-Languages: en",
        "Canonical: https://prettyaffairshub.onrender.com/.well-known/security.txt",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


# Product photos live under MEDIA_ROOT. Long browser cache so repeat visits skip re-download.
# WhiteNoise only serves STATIC; this serves /media/ on Render until R2 is wired.
cached_media_serve = cache_control(public=True, max_age=60 * 60 * 24 * 30, immutable=True)(serve)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("manage/", include("apps.desk.urls")),
    path("", include("apps.content.urls")),
    path("shop/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path(".well-known/security.txt", security_txt, name="security_txt"),
]

urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        cached_media_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
