"""Smart catalog cache — long-lived, invalidated only when catalogue data changes.

Reads hit the cache. The database is queried on a miss, which should only
happen after a write bumps the catalog version (or after a cold start).
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Persist until explicitly invalidated. LocMem / Redis both honour None.
CACHE_TIMEOUT = None
VERSION_KEY = "smart:catalog:version"

# Fixed keys cleared on every catalogue write (in addition to version bump).
FIXED_KEYS = (
    "catalog:category_tree",
    "catalog:categories_active",
    "catalog:collections_active",
    "catalog:shop:discovery",
    "catalog:shop:shade_studio",
    "catalog:home:rails",
    "catalog:top_seller",
    "content:testimonials:featured",
    "content:homepage_sections",
    "content:flash_sales:live",
    "content:blog_posts:home",
)


def catalog_version() -> int:
    value = cache.get(VERSION_KEY)
    if value is None:
        cache.set(VERSION_KEY, 1, timeout=CACHE_TIMEOUT)
        return 1
    return int(value)


def versioned_key(namespace: str, *parts: Any) -> str:
    digest_parts = [str(part) for part in parts if part is not None and part != ""]
    suffix = hashlib.md5("|".join(digest_parts).encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:v{catalog_version()}:{suffix}"


def get_or_set(key: str, producer: Callable[[], T], timeout: int | None = CACHE_TIMEOUT) -> T:
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = producer()
    cache.set(key, value, timeout=timeout)
    return value


def invalidate_catalog_cache(*, reason: str = "") -> None:
    """Bump the catalog generation and drop fixed keys.

    Call this after products, categories, collections, images, or variants change.
    """
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, catalog_version() + 1, timeout=CACHE_TIMEOUT)

    cache.delete_many(list(FIXED_KEYS))
    if reason:
        logger.info("Catalog cache invalidated: %s (version=%s)", reason, catalog_version())

    purge_cloudflare_cache()


def purge_cloudflare_cache() -> None:
    """Ask Cloudflare to purge cached HTML when credentials are configured."""
    zone = getattr(settings, "CLOUDFLARE_ZONE_ID", "") or ""
    token = getattr(settings, "CLOUDFLARE_API_TOKEN", "") or ""
    if not zone or not token:
        return
    try:
        from urllib.request import Request, urlopen
        import json

        payload = json.dumps({"purge_everything": True}).encode("utf-8")
        request = Request(
            f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            response.read()
        logger.info("Cloudflare edge cache purged for zone %s", zone)
    except Exception:
        logger.exception("Cloudflare cache purge failed")
