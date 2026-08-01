"""End-to-end smoke: public pages, cart, checkout gate, auth walls."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Product

c = Client(enforce_csrf_checks=False)
failed = False


def check(label, ok, detail=""):
    global failed
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        failed = True


# --- Public pages ---
urls = [
    "/",
    "/shop/",
    "/shop/bundles/",
    "/shop/ritual/",
    "/about/",
    "/faq/",
    "/contact/",
    "/blog/",
    "/gift-cards/",
    "/pages/shipping/",
    "/pages/returns/",
    "/pages/privacy/",
    "/pages/terms/",
    "/cart/",
    "/orders/track/",
    "/orders/checkout/",
    "/accounts/login/",
    "/accounts/register/",
    "/robots.txt",
    "/.well-known/security.txt",
    "/sitemap.xml",
    "/manage/",
    "/admin/",
]
product = Product.objects.filter(is_active=True).first()
if product:
    urls.append(product.get_absolute_url())

for url in urls:
    response = c.get(url, follow=False)
    # checkout with empty cart redirects; manage/admin redirect to login
    if url in {"/orders/checkout/", "/manage/", "/admin/"}:
        check(f"GET {url}", response.status_code in {200, 302}, f"status={response.status_code}")
    else:
        check(f"GET {url}", response.status_code < 400, f"status={response.status_code}")

# --- Cart add + cart page ---
if product:
    response = c.post("/cart/add/", {"product_id": product.id, "quantity": 1, "next": "/cart/"})
    check("POST /cart/add/", response.status_code == 302, f"status={response.status_code}")
    response = c.get("/cart/")
    check(
        "GET /cart/ with item",
        response.status_code == 200 and b"Cart" in response.content and b"checkout" in response.content.lower(),
    )

    # Open redirect must be blocked
    response = c.post(
        "/cart/add/",
        {"product_id": product.id, "quantity": 1, "next": "https://evil.example/"},
    )
    check("block external next", response.status_code == 302 and response.url == "/cart/")

    response = c.get("/orders/checkout/")
    check("GET /orders/checkout/ with cart", response.status_code == 200)

# --- Auth walls ---
response = c.get("/accounts/profile/")
check("profile requires login", response.status_code == 302)
response = c.get("/manage/")
check("manage requires login", response.status_code == 302)
response = c.get("/accounts/logout/")
check("logout rejects GET", response.status_code == 405)

# --- Staff desk ---
staff = User.objects.filter(is_superuser=True).first()
if staff:
    staff_client = Client()
    staff_client.force_login(staff)
    response = staff_client.get("/manage/")
    check("staff /manage/", response.status_code == 200)
    response = staff_client.get("/admin/")
    check("staff /admin/", response.status_code == 200)
    response = staff_client.get("/manage/products/")
    check("staff /manage/products/", response.status_code == 200)
    response = staff_client.get("/manage/orders/")
    check("staff /manage/orders/", response.status_code == 200)
    response = staff_client.get("/manage/content/")
    check("staff /manage/content/", response.status_code == 200)
    response = staff_client.get("/manage/messages/")
    check("staff /manage/messages/", response.status_code == 200)

# --- Order confirmation IDOR ---
from apps.orders.models import Order

order = Order.objects.first()
if order:
    stranger = Client()
    response = stranger.get(f"/orders/confirmation/{order.order_number}/")
    check(
        "confirmation IDOR blocked",
        response.status_code == 302 and "/orders/track" in (response.url or ""),
    )

if failed:
    raise SystemExit(1)
print("SMOKE OK")
