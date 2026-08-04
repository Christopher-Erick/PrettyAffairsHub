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
    "catalog:bundles:active",
    "content:home:page",
    "content:testimonials:featured",
    "content:homepage_sections",
    "content:flash_sales:live",
    "content:blog_posts:home",
    "content:faqs:active",
)


def _cache_get(key: str) -> Any:
    """Read from cache, treating an unreachable backend as a miss.

    A dead or over-quota cache must never take the shop down; the database
    can still answer every read.
    """
    try:
        return cache.get(key)
    except Exception:
        logger.warning("Cache read failed for %s; falling back to the database", key)
        return None


def _cache_set(key: str, value: Any, timeout: int | None) -> None:
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning("Cache write failed for %s", key)


def catalog_version() -> int:
    value = _cache_get(VERSION_KEY)
    if value is None:
        _cache_set(VERSION_KEY, 1, CACHE_TIMEOUT)
        return 1
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1


def versioned_key(namespace: str, *parts: Any) -> str:
    digest_parts = [str(part) for part in parts if part is not None and part != ""]
    suffix = hashlib.md5("|".join(digest_parts).encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:v{catalog_version()}:{suffix}"


def get_or_set(key: str, producer: Callable[[], T], timeout: int | None = CACHE_TIMEOUT) -> T:
    cached = _cache_get(key)
    if cached is not None:
        return cached
    value = producer()
    _cache_set(key, value, timeout)
    return value


def invalidate_catalog_cache(*, reason: str = "") -> None:
    """Bump the catalog generation and drop fixed keys.

    Call this after products, categories, collections, images, or variants change.
    """
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        _cache_set(VERSION_KEY, catalog_version() + 1, CACHE_TIMEOUT)
    except Exception:
        logger.warning("Cache version bump failed; skipping invalidation")
        return

    try:
        cache.delete_many(list(FIXED_KEYS))
    except Exception:
        logger.warning("Cache key eviction failed")
    if reason:
        logger.info("Catalog cache invalidated: %s (version=%s)", reason, catalog_version())

    # Never block the request on Cloudflare's HTTP API.
    try:
        from django.db import transaction

        transaction.on_commit(_schedule_cloudflare_purge)
    except Exception:
        _schedule_cloudflare_purge()


def _schedule_cloudflare_purge() -> None:
    """Debounce and fire Cloudflare purge off the request thread."""
    import threading
    import time

    lock_key = "smart:cf_purge_scheduled"
    try:
        # Only one purge every 30s across workers that share cache.
        if not cache.add(lock_key, time.time(), timeout=30):
            return
    except Exception:
        pass

    thread = threading.Thread(target=purge_cloudflare_cache, daemon=True)
    thread.start()


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
        with urlopen(request, timeout=5) as response:
            response.read()
        logger.info("Cloudflare edge cache purged for zone %s", zone)
    except Exception:
        logger.exception("Cloudflare cache purge failed")
