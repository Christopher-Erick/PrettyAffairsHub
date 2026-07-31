"""Import an authorized, curated catalogue from the two approved source stores.

This command intentionally imports only factual product data and locally stores
authorized images. Descriptions are rewritten for Pretty Affairs Hub.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import (
    Brand,
    Category,
    Collection,
    Product,
    ProductImage,
    ProductVariant,
)


LIP_TRIBE_FEED = "https://theliptribe.co.ke/products.json?limit=250"
LINTONS_SHOP = "https://www.lintonsbeauty.com/shopall"
USER_AGENT = "PrettyAffairsHub/1.0 authorized catalogue importer"

CATEGORY_RULES = {
    "Lip Oil": ("lip oil", "lip serum", "oil balm"),
    "Lip Gloss": ("lip gloss", "gloss bomb", "lip luminizer"),
    "Lipstick": ("lipstick", "lip tint", "matte ink"),
    "Lashes": ("lashes", "false lash", "falsies"),
    "Pocket Mirrors": ("pocket mirror", "compact mirror"),
    "Cleansing Brushes": ("cleansing brush", "facial brush"),
    "Sunglasses": ("sunglasses", "sun glasses"),
    "Face Masks": ("face mask", "sheet mask", "clay mask"),
    "Jewellery Boxes": ("jewellery box", "jewelry box"),
    "Boob Tape": ("boob tape", "breast tape"),
    "Acrylic Bangles": ("acrylic bangle", "acrylic bracelet"),
    "Perfumes": ("eau de parfum", " edp", "parfum"),
    "Body Splash": ("body splash", "body mist"),
    "Cologne": ("cologne", "eau de toilette", " edt"),
}

SHADE_COLORS = {
    "clear": "#E8DAD3",
    "transparent": "#E8DAD3",
    "pink": "#D86C91",
    "rose": "#A94F5C",
    "berry": "#8D294C",
    "cherry": "#A71930",
    "red": "#B8222E",
    "crimson": "#991E32",
    "coral": "#E96F62",
    "peach": "#E99B7B",
    "orange": "#D86C31",
    "nude": "#B98269",
    "beige": "#B99A83",
    "sand": "#B99A83",
    "tan": "#9A674F",
    "caramel": "#9A6042",
    "maple": "#8D503D",
    "toast": "#8A5648",
    "brown": "#6F4336",
    "cocoa": "#694037",
    "plum": "#713B5B",
    "purple": "#714B76",
    "wine": "#711F3A",
    "burgundy": "#711F3A",
    "black": "#2A2320",
    "gold": "#C29A52",
    "honey": "#C7954F",
    "green": "#5A865F",
    "blue": "#4F6F91",
}

COPY = {
    "Lip Oil": (
        "A cushiony lip oil selected for shine, comfort, and effortless everyday wear.",
        "Comforting moisture\nGlossy finish\nEasy everyday application",
        "Glide over bare lips or layer over lip colour. Reapply whenever lips need shine.",
    ),
    "Lip Gloss": (
        "A polished lip gloss selected for dimensional shine and comfortable wear.",
        "High-shine finish\nComfortable texture\nLayers beautifully",
        "Apply directly to lips or layer over liner and lipstick for extra dimension.",
    ),
    "Lipstick": (
        "A statement lip colour selected for rich payoff and a refined finish.",
        "Buildable colour\nComfortable wear\nDefined finish",
        "Apply from the centre outward. Pair with liner for a more sculpted look.",
    ),
    "Pocket Mirrors": (
        "A compact beauty companion designed for quick touch-ups wherever the day takes you.",
        "Travel-friendly\nEasy touch-ups\nGiftable design",
        "Keep in your handbag or beauty pouch for on-the-go touch-ups.",
    ),
    "Perfumes": (
        "A memorable fragrance selected to bring polish, character, and lasting presence.",
        "Signature scent\nLayerable fragrance\nElegant finishing touch",
        "Mist onto pulse points from a short distance. Avoid rubbing into the skin.",
    ),
    "Cologne": (
        "A fresh, confident fragrance selected for an easy and distinctive daily signature.",
        "Fresh scent profile\nEveryday versatility\nRefined finish",
        "Spray lightly onto pulse points and clothing from a safe distance.",
    ),
}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=90) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.replace("\ufffd", "-")
    return re.sub(r"\s+", " ", value).strip()


def category_for(title: str, allowed: set[str] | None = None) -> str | None:
    haystack = f" {title.lower()}"
    for category, keywords in CATEGORY_RULES.items():
        if allowed and category not in allowed:
            continue
        if any(keyword in haystack for keyword in keywords):
            return category
    return None


def shade_color(name: str) -> str:
    lowered = name.lower()
    for keyword, color in SHADE_COLORS.items():
        if keyword in lowered:
            return color
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    hue = int(digest[:2], 16)
    saturation = 38 + int(digest[2:4], 16) % 35
    lightness = 38 + int(digest[4:6], 16) % 28
    # HSL is useful in CSS, but the model stores hex. Convert a stable HSL here.
    import colorsys

    red, green, blue = colorsys.hls_to_rgb(hue / 255, lightness / 100, saturation / 100)
    return f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"


def image_filename(url: str, prefix: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{slugify(prefix)[:60]}-{digest}{suffix}"


def parse_lintons_cards(raw_html: str) -> list[dict]:
    marker = re.compile(r'<div[^>]+data-hook="product-item-root"[^>]*>', re.I)
    matches = list(marker.finditer(raw_html))
    cards = []
    for index, match in enumerate(matches):
        opening = match.group(0)
        chunk = raw_html[match.start() : matches[index + 1].start() if index + 1 < len(matches) else len(raw_html)]
        name_match = re.search(r'aria-label="([^"]+?) gallery"', opening, re.I)
        slug_match = re.search(r'data-slug="([^"]+)"', opening, re.I)
        image_match = re.search(r'data-image-info="([^"]+)"', chunk, re.I)
        href_match = re.search(r'href="(https://www\.lintonsbeauty\.com/product-page/[^"]+)"', chunk, re.I)
        text = clean_text(re.sub(r"<[^>]+>", " ", chunk[:20000]))
        price_match = re.search(r"Ksh\D*([\d,]+\.\d{2})", text, re.I)
        if not (name_match and slug_match and image_match and price_match):
            continue
        try:
            image_info = json.loads(html.unescape(image_match.group(1)))
            image_uri = image_info.get("imageData", {}).get("uri", "")
        except (TypeError, ValueError):
            image_uri = ""
        if not image_uri:
            continue
        cards.append(
            {
                "name": clean_text(name_match.group(1)),
                "slug": slug_match.group(1),
                "url": href_match.group(1) if href_match else f"https://www.lintonsbeauty.com/product-page/{slug_match.group(1)}",
                "price": Decimal(price_match.group(1).replace(",", "")),
                "image_urls": [f"https://static.wixstatic.com/media/{image_uri}"],
                "available": "Sold Out" not in text,
            }
        )
    return cards


class Command(BaseCommand):
    help = "Import a curated authorized catalogue with locally stored images"

    def add_arguments(self, parser):
        parser.add_argument("--limit-per-category", type=int, default=5)
        parser.add_argument("--refresh", action="store_true", help="Replace images and variants for imported products")

    def handle(self, *args, **options):
        limit = max(1, min(options["limit_per_category"], 20))
        refresh = options["refresh"]
        try:
            lip_products = json.loads(fetch(LIP_TRIBE_FEED).decode("utf-8"))["products"]
            lintons_cards = parse_lintons_cards(fetch(LINTONS_SHOP).decode("utf-8", errors="replace"))
        except Exception as exc:
            raise CommandError(f"Could not retrieve authorized product sources: {exc}") from exc

        candidates: dict[str, list[dict]] = defaultdict(list)
        for raw in lip_products:
            category = category_for(raw.get("title", ""), {"Lip Oil", "Lip Gloss", "Lipstick", "Pocket Mirrors"})
            if not category:
                continue
            variants = raw.get("variants", [])
            prices = [Decimal(v["price"]) for v in variants if v.get("price")]
            if not prices:
                continue
            candidates[category].append(
                {
                    "name": clean_text(raw["title"]),
                    "url": f"https://theliptribe.co.ke/products/{raw['handle']}",
                    "price": min(prices),
                    "compare_at_price": max(
                        [Decimal(v["compare_at_price"]) for v in variants if v.get("compare_at_price")] or [Decimal("0")]
                    )
                    or None,
                    "image_urls": [img["src"] for img in raw.get("images", [])[:3] if img.get("src")],
                    "variants": variants,
                    "vendor": clean_text(raw.get("vendor", "")) or "The Lip Tribe Edit",
                    "source": "The Lip Tribe",
                    "available": any(v.get("available", True) for v in variants),
                }
            )

        for raw in lintons_cards:
            category = category_for(raw["name"], {"Lip Gloss", "Lipstick", "Perfumes", "Cologne"})
            if not category:
                continue
            raw.update({"variants": [], "vendor": raw["name"].split()[0], "source": "Lintons Beauty"})
            candidates[category].append(raw)

        imported = defaultdict(int)
        missing = []
        target_categories = list(CATEGORY_RULES)
        for category_name in target_categories:
            category = Category.objects.filter(name=category_name, is_active=True).first()
            if not category:
                missing.append(category_name)
                continue
            seen_names = set()
            selected = []
            for candidate in candidates[category_name]:
                key = candidate["name"].lower()
                if key in seen_names:
                    continue
                seen_names.add(key)
                selected.append(candidate)
                if len(selected) >= limit:
                    break
            for index, data in enumerate(selected):
                self.import_product(data, category, index, refresh)
                imported[category_name] += 1

        imported_total = sum(imported.values())
        if imported_total:
            Product.objects.filter(
                name__in=[
                    "Velvet Rose Lipstick",
                    "Crimson Muse",
                    "Silk Nude Gloss",
                    "Soft Sand Gloss",
                    "Amber Glow Lip Oil",
                    "Berry Bloom Oil",
                ],
                source_name="",
            ).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(f"Imported {imported_total} authorized products."))
        for category in Category.objects.filter(is_active=True, parent__isnull=False).order_by(
            "parent__sort_order", "sort_order"
        ):
            self.stdout.write(f"  {category.name}: {imported.get(category.name, 0)}")

    @transaction.atomic
    def import_product(self, data: dict, category: Category, index: int, refresh: bool):
        description, benefits, directions = COPY[category.name]
        brand, _ = Brand.objects.get_or_create(name=data["vendor"][:120])
        source_url = data["url"][:500]
        product = Product.objects.filter(source_url=source_url).first()
        if not product:
            product = Product.objects.filter(name=data["name"]).first() or Product()
        product.name = data["name"][:200]
        product.brand = brand
        product.short_description = description[:255]
        product.description = (
            f"{description} Selected from {data['source']} for the Pretty Affairs Hub edit."
        )
        product.benefits = benefits
        product.directions = directions
        product.price = data["price"]
        compare = data.get("compare_at_price")
        product.compare_at_price = compare if compare and compare > data["price"] else None
        product.sku = f"PAH-{slugify(category.name)[:6].upper()}-{hashlib.md5(source_url.encode()).hexdigest()[:7].upper()}"
        product.source_name = data["source"]
        product.source_url = source_url
        product.stock = 12 if data.get("available", True) else 0
        product.is_active = bool(data.get("available", True))
        product.is_featured = index == 0
        product.is_bestseller = index == 1
        product.is_new = index >= 2
        product.is_trending = index == 0
        product.save()
        product.categories.set([category])

        everyday = Collection.objects.filter(slug="everyday-essentials").first()
        night = Collection.objects.filter(slug="night-out").first()
        collections = [c for c in [everyday, night if category.name in {"Lipstick", "Perfumes", "Cologne"} else None] if c]
        product.collections.set(collections)

        if refresh:
            product.images.all().delete()
            product.variants.all().delete()
        if not product.images.exists():
            for position, url in enumerate(data.get("image_urls", [])):
                try:
                    content = fetch(url)
                    image = ProductImage(product=product, alt_text=f"{product.name} product image", sort_order=position)
                    image.image.save(image_filename(url, product.name), ContentFile(content), save=True)
                except Exception as exc:
                    self.stderr.write(f"Image skipped for {product.name}: {exc}")

        raw_variants = data.get("variants", [])
        useful_variants = [
            variant
            for variant in raw_variants
            if clean_text(variant.get("title", "")).lower() not in {"", "default title"}
        ]
        if useful_variants:
            product.stock = 0
            product.save(update_fields=["stock"])
        for variant in useful_variants[:12]:
            title = clean_text(variant.get("title", "Shade"))
            item, _ = ProductVariant.objects.update_or_create(
                product=product,
                name=title[:120],
                defaults={
                    "sku": clean_text(variant.get("sku", ""))[:64],
                    "price_override": Decimal(variant["price"]) if variant.get("price") else None,
                    "stock": 8 if variant.get("available", True) else 0,
                    "is_active": True,
                    "color_hex": shade_color(title),
                },
            )
            featured = variant.get("featured_image") or {}
            image_url = featured.get("src") if isinstance(featured, dict) else ""
            if image_url and (refresh or not item.image):
                try:
                    item.image.save(
                        image_filename(image_url, f"{product.name}-{title}"),
                        ContentFile(fetch(image_url)),
                        save=True,
                    )
                except Exception as exc:
                    self.stderr.write(f"Variant image skipped for {product.name}/{title}: {exc}")
