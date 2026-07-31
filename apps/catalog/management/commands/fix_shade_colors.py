"""Recompute swatch colours so each shade dot matches its own product image."""

from django.core.management.base import BaseCommand

from apps.catalog.models import ProductVariant
from apps.catalog.shade_colors import resolve_shade_color


class Command(BaseCommand):
    help = "Recalculate ProductVariant.color_hex from each shade image"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report changes without saving")
        parser.add_argument("--product", default="", help="Only variants whose product name contains this text")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        variants = ProductVariant.objects.select_related("product").order_by("product__name", "id")
        if options["product"]:
            variants = variants.filter(product__name__icontains=options["product"])

        changed = 0
        from_image = 0
        for variant in variants:
            resolved = resolve_shade_color(variant.name, variant.image or None)
            if variant.image:
                from_image += 1
            if resolved == variant.color_hex:
                continue
            self.stdout.write(f"{variant.product.name} — {variant.name}: {variant.color_hex or '·'} -> {resolved}")
            changed += 1
            if not dry_run:
                variant.color_hex = resolved
                variant.save(update_fields=["color_hex"])

        summary = f"{changed} of {variants.count()} swatches updated ({from_image} sampled from shade images)."
        self.stdout.write(self.style.SUCCESS(f"[dry run] {summary}" if dry_run else summary))
