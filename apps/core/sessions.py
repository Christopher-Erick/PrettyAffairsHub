"""Session store that reads through the cache but survives a failing cache.

Sessions are persisted in Postgres, with the cache as a read-through
accelerator. Pure cache sessions returned 500 on sign-in whenever Redis was
unreachable or over quota, because creating a session probes the cache for key
collisions and any backend error propagated to the request.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.sessions.backends.cached_db import SessionStore as CachedDBStore
from django.core.cache import caches

logger = logging.getLogger(__name__)


class _ForgivingCache:
    """Cache proxy that degrades to a miss instead of raising."""

    def __init__(self, cache):
        self._cache = cache

    def get(self, key, default=None):
        try:
            return self._cache.get(key, default)
        except Exception:
            logger.warning("Session cache read failed; using the database")
            return default

    def set(self, key, value, timeout=None):
        try:
            self._cache.set(key, value, timeout)
        except Exception:
            logger.warning("Session cache write failed; session is stored in the database")

    def delete(self, key):
        try:
            self._cache.delete(key)
        except Exception:
            logger.warning("Session cache delete failed")

    def has_key(self, key):
        try:
            return self._cache.has_key(key)
        except Exception:
            return False

    def __contains__(self, key):
        return self.has_key(key)


class SessionStore(CachedDBStore):
    def __init__(self, session_key=None):
        super().__init__(session_key)
        self._cache = _ForgivingCache(caches[settings.SESSION_CACHE_ALIAS])
