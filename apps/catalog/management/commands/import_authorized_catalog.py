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

from django.core.cache import cache
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
from apps.catalog.shade_colors import resolve_shade_color


LIP_TRIBE_FEED = "https://theliptribe.co.ke/products.json?limit=250"
LINTONS_SHOP = "https://www.lintonsbeauty.com/shopall"
USER_AGENT = "PrettyAffairsHub/1.0 authorized catalogue importer"

CATEGORY_RULES = {
    "Lip Oil": (
        "lip oil",
        "lip serum",
        "oil balm",
        "lip glowy balm",
        "lip sleeping mask",
        "lip mask",
        "lip balm",
        "lip treatment",
        "lip ointment",
        "lip repair",
        "lip protectant",
        "super balm",
        "lip butter",
        "lip therapy",
        "lip scrub",
        "lip lightening",
        "pout preserve",
        "overnight lip",
    ),
    "Lip Gloss": ("lip gloss", "gloss bomb", "lip luminizer", "lifter gloss", "glossy lip"),
    "Lipstick": (
        "lipstick",
        "lip tint",
        "matte ink",
        "lip pencil",
        "lip liner",
        "glow tint",
        "superstay matte",
        "superstay glow",
    ),
    "Lashes": ("lashes", "false lash", "falsies", "mascara"),
    "Pocket Mirrors": ("pocket mirror", "compact mirror"),
    "Cleansing Brushes": ("cleansing brush", "facial brush"),
    "Sunglasses": ("sunglasses", "sun glasses"),
    "Face Masks": ("face mask", "sheet mask", "clay mask"),
    "Jewellery Boxes": ("jewellery box", "jewelry box"),
    "Boob Tape": ("boob tape", "breast tape"),
    "Acrylic Bangles": ("acrylic bangle", "acrylic bracelet"),
    "Perfumes": (
        "eau de parfum",
        " edp",
        "parfum",
        "perfume",
        "euphoria",
        "good girl",
        "scandal",
        "gucci bloom",
        "divine couture",
        "jasmin secret",
        "rose envoutante",
    ),
    "Body Splash": ("body splash", "body mist", "body lotion", "hand cream"),
    "Cologne": ("cologne", "eau de toilette", " edt", " for him", " him "),
}

LIP_TRIBE_CATEGORIES = {
    "Lip Oil",
    "Lip Gloss",
    "Lipstick",
    "Pocket Mirrors",
    "Lashes",
    "Face Masks",
}
LINTONS_CATEGORIES = {
    "Lip Gloss",
    "Lipstick",
    "Lip Oil",
    "Perfumes",
    "Cologne",
    "Lashes",
    "Body Splash",
}

LINTONS_FRAGRANCE_HINTS = (
    "calvin klein",
    "carolina herrera",
    "jean paul",
    "gucci",
    "chanel",
    "dior",
    "versace",
    "yves saint",
    "armeani",
    "armani",
    "hugo boss",
    "montblanc",
    "mugler",
    "paco rabanne",
    "tom ford",
    "burberry",
    "prada",
    "jeanne en provence",
)

DEFAULT_COPY = (
    "A carefully selected beauty essential curated for the Pretty Affairs Hub edit.",
    "Curated quality\nEveryday wear\nGiftable finish",
    "Use as directed on the product packaging. Patch-test if you have sensitive skin.",
)

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
    "Lashes": (
        "A lash essential selected for lift, definition, and polished eye drama.",
        "Defined lashes\nBuildable effect\nEveryday to evening",
        "Apply from the base of the lashes outward. Remove gently at the end of the day.",
    ),
    "Pocket Mirrors": (
        "A compact beauty companion designed for quick touch-ups wherever the day takes you.",
        "Travel-friendly\nEasy touch-ups\nGiftable design",
        "Keep in your handbag or beauty pouch for on-the-go touch-ups.",
    ),
    "Face Masks": (
        "A face treatment selected for a refreshed, cared-for finish.",
        "Skin-loving care\nAt-home ritual\nVisible refresh",
        "Apply to clean skin as directed. Rinse or remove after the recommended time.",
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
    "Body Splash": (
        "A body care essential selected for a soft finish and everyday freshness.",
        "Soft finish\nEveryday freshness\nLayerable scent",
        "Apply to clean skin and allow to absorb. Reapply as desired.",
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


def lintons_category(title: str) -> str | None:
    matched = category_for(title, LINTONS_CATEGORIES)
    if matched:
        return matched
    lowered = title.lower()
    makeup_blockers = (
        "mascara",
        "concealer",
        "foundation",
        "primer",
        "sunkisser",
        "gloss",
        "lipstick",
        "tint",
        "balm",
    )
    if any(blocker in lowered for blocker in makeup_blockers):
        return None
    if any(hint in lowered for hint in LINTONS_FRAGRANCE_HINTS):
        return "Perfumes"
    if re.search(r"\b\d+\s*ml\b", lowered) and "spf" not in lowered:
        return "Perfumes"
    return None


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


def fetch_lip_tribe_products() -> list[dict]:
    products: list[dict] = []
    for page in range(1, 6):
        payload = json.loads(fetch(f"{LIP_TRIBE_FEED}&page={page}").decode("utf-8"))
        batch = payload.get("products") or []
        if not batch:
            break
        products.extend(batch)
        if len(batch) < 250:
            break
    return products


class Command(BaseCommand):
    help = "Import a curated authorized catalogue with locally stored images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit-per-category",
            type=int,
            default=25,
            help="Max products to import per category (ignored with --full-import)",
        )
        parser.add_argument(
            "--full-import",
            action="store_true",
            help="Import every matched product from authorized sources (no per-category cap)",
        )
        parser.add_argument("--refresh", action="store_true", help="Replace images and variants for imported products")

    def handle(self, *args, **options):
        full_import = options["full_import"]
        limit = None if full_import else max(1, min(options["limit_per_category"], 100))
        refresh = options["refresh"]
        try:
            lip_products = fetch_lip_tribe_products()
            lintons_cards = parse_lintons_cards(fetch(LINTONS_SHOP).decode("utf-8", errors="replace"))
        except Exception as exc:
            raise CommandError(f"Could not retrieve authorized product sources: {exc}") from exc

        candidates: dict[str, list[dict]] = defaultdict(list)
        for raw in lip_products:
            category = category_for(raw.get("title", ""), LIP_TRIBE_CATEGORIES)
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
            category = lintons_category(raw["name"])
            if not category:
                continue
            raw.update({"variants": [], "vendor": raw["name"].split()[0], "source": "Lintons Beauty"})
            candidates[category].append(raw)

        imported = defaultdict(int)
        missing = []
        available = sum(len(items) for items in candidates.values())
        self.stdout.write(
            f"Matched {available} source products across {len(candidates)} categories "
            f"(limit={'full' if full_import else limit})."
        )
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
                if limit is not None and len(selected) >= limit:
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
            cache.delete_many(
                [
                    "catalog:category_tree",
                    "catalog:categories_active",
                    "catalog:collections_active",
                ]
            )

        self.stdout.write(self.style.SUCCESS(f"Imported {imported_total} authorized products."))
        for category in Category.objects.filter(is_active=True, parent__isnull=False).order_by(
            "parent__sort_order", "sort_order"
        ):
            self.stdout.write(f"  {category.name}: {imported.get(category.name, 0)}")
        if missing:
            self.stdout.write(self.style.WARNING(f"Missing categories skipped: {', '.join(missing)}"))

    @transaction.atomic
    def import_product(self, data: dict, category: Category, index: int, refresh: bool):
        description, benefits, directions = COPY.get(category.name, DEFAULT_COPY)
        brand, _ = Brand.objects.get_or_create(name=data["vendor"][:120])
        source_url = data["url"][:500]
        product = Product.objects.filter(source_url=source_url).first()
        if not product:
            product = Product.objects.filter(name=data["name"]).first() or Product()
        product.name = data["name"][:200]
        product.brand = brand
        product.short_description = description[:255]
        # Sourcing stays in source_name/source_url for staff; shopper copy never names it.
        product.description = f"{description} Curated for the Pretty Affairs Hub edit."
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

            item.color_hex = resolve_shade_color(title, item.image or None)
            item.save(update_fields=["color_hex"])
