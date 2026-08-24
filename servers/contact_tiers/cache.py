"""Shared disk cache + env access for the contact tiers.

Deliberately dependency-free. The tier modules are imported by BOTH
`find_contacts.py` (repo root) and the `Raw B2B Company Targets/` pipeline, and
`reuse.py` imports `find_contacts` — so anything the tiers import from `reuse`
or `find_contacts` would be a circular import. Hence a self-contained cache
here rather than reaching for `find_contacts.Fetcher`.

Key hashing and the cache directory match `find_contacts.Fetcher` exactly, so
every flow shares one cache and a lookup paid for by one pipeline is free for
the next. Callers with their own fetcher can inject it via `set_cache()`; it
only needs `cache_get(key)` / `cache_put(key, record)`.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")

_injected = None
_lock = threading.Lock()
_env_loaded = False


class DiskCache:
    """Same layout as find_contacts.Fetcher's cache: cache/<sha1(key)>.json."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, hashlib.sha1(key.encode()).hexdigest() + ".json")

    def cache_get(self, key: str) -> Optional[dict]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def cache_put(self, key: str, record: dict) -> None:
        record["cached_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            with open(self._path(key), "w", encoding="utf-8") as f:
                json.dump(record, f)
        except Exception:
            pass  # a cache write failure must never break a run


def set_cache(obj) -> None:
    """Inject a cache (e.g. an existing Fetcher) shared with the caller."""
    global _injected
    with _lock:
        _injected = obj


def get_cache():
    global _injected
    with _lock:
        if _injected is None:
            _injected = DiskCache()
        return _injected


def env(key: str, default: str = "") -> str:
    """Read a key from the environment, loading the repo .env once on demand.

    Read lazily rather than at import so that whichever entry point loads .env
    first (reuse.py does; find_contacts.py doesn't) still ends up with values.
    """
    global _env_loaded
    if not _env_loaded:
        with _lock:
            if not _env_loaded:
                try:
                    from dotenv import load_dotenv
                    load_dotenv(os.path.join(BASE_DIR, ".env"))
                except Exception:
                    pass
                _env_loaded = True
    return (os.environ.get(key) or default).strip()
