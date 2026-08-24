"""Tier 4 — paid person lookup, spent only on what Tiers 1-3 couldn't resolve.

The repo already calls PDL's *company* endpoint for firmographics
(`enrichcli/sources/paid_peopledatalabs.py`); this is the *person* endpoint,
which returns work emails and a LinkedIn profile URL. It is the only source in
the stack that yields a LinkedIn URL without touching LinkedIn, so it is also
how `linkedin_url` gets populated.

Credits are the constraint, so this is deliberately last: by the time a row
reaches here, commit mining, pattern inference and SMTP verification have all
declined to produce a usable address. Enforces a per-process credit ceiling and
caches every lookup (including misses) so re-runs never re-spend.

No key -> every call returns {} and the pipeline carries on.
"""

from __future__ import annotations

import threading
from typing import Dict

import requests

from .cache import env as _env, get_cache as _cache

URL = "https://api.peopledatalabs.com/v5/person/enrich"
_TIMEOUT = 20

_calls = [0]
_lock = threading.Lock()


def _max_calls() -> int:
    try:
        return int(_env("PDL_MAX_CALLS") or "250")
    except ValueError:
        return 250


def budget_remaining() -> int:
    with _lock:
        return max(0, _max_calls() - _calls[0])


def calls_made() -> int:
    with _lock:
        return _calls[0]


def _spend() -> bool:
    """Reserve one credit. False when the ceiling is hit."""
    with _lock:
        if _calls[0] >= _max_calls():
            return False
        _calls[0] += 1
        return True


def enrich_person(name: str, domain: str, company: str = "",
                  min_likelihood: int = 6) -> Dict:
    """{email, linkedin_url, title, source} for a person at a company, or {}.

    `min_likelihood` is PDL's own match-confidence gate (1-10). 6 is the
    documented "probably the right human" threshold; below that PDL will happily
    return a same-named stranger, which is worse than no record at all.
    """
    name, domain = (name or "").strip(), (domain or "").strip().lower()
    if not _env("PEOPLEDATALABS_API_KEY") or not name or not domain:
        return {}

    f = _cache()
    key = f"pdlperson/v1:{name.lower()}|{domain}"
    cached = f.cache_get(key)
    if cached is not None:
        return cached.get("person", {})

    if not _spend():
        return {}   # budget exhausted — not cached, so a later run can retry

    out: Dict = {}
    try:
        r = requests.get(URL, params={
            "api_key": _env("PEOPLEDATALABS_API_KEY"),
            "name": name,
            "company": company or domain,
            "min_likelihood": min_likelihood,
        }, timeout=_TIMEOUT)
        if r.status_code == 200:
            d = (r.json() or {}).get("data") or {}
            email = (d.get("work_email") or "").strip().lower()
            if not email:
                for rec in (d.get("emails") or []):
                    if isinstance(rec, dict) and "professional" in (rec.get("type") or ""):
                        email = (rec.get("address") or "").strip().lower()
                        break
            li = (d.get("linkedin_url") or "").strip()
            out = {
                "email": email,
                "linkedin_url": ("https://" + li) if li and not li.startswith("http") else li,
                "title": (d.get("job_title") or "").strip(),
                "source": "pdl_person",
            }
        elif r.status_code == 404:
            out = {}          # genuine miss — cache it so we never re-spend
        else:
            return {}         # rate-limited / server error: don't cache
    except Exception:
        return {}             # transient: don't cache, allow a retry

    f.cache_put(key, {"person": out})
    return out
