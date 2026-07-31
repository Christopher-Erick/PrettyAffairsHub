import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.test import Client

from apps.catalog.models import Product

c = Client()
urls = [
    "/",
    "/shop/",
    "/shop/bundles/",
    "/about/",
    "/faq/",
    "/contact/",
    "/blog/",
    "/gift-cards/",
    "/cart/",
    "/orders/track/",
    "/accounts/login/",
    "/accounts/register/",
    "/robots.txt",
    "/sitemap.xml",
]
product = Product.objects.filter(is_active=True).first()
if product:
    urls.append(product.get_absolute_url())

failed = False
for url in urls:
    response = c.get(url)
    print(url, response.status_code)
    if response.status_code >= 400:
        failed = True

if failed:
    raise SystemExit(1)
print("SMOKE OK")
