"""Resolve a company's GitHub org login — the key that unlocks Tiers 1 and 2.

Ported verbatim from `Raw B2B Company Targets/enrich/github_signals.py` (which
now delegates here) so that flows without their own org resolution — notably
`find_contacts.py` — can reach commit emails too. It lives in this package
rather than there because `github_signals` imports `reuse`, which imports
`find_contacts`: a circular import for any root-level caller.

The verification in `org_matches` is the load-bearing part and must not be
loosened: a login that merely equals the domain label silently attaches an
unrelated org's repos, headcount, and — now — its employees' email addresses to
the wrong company. Name similarity alone matched 'Ramp' to 'FedRAMP'; substring
matching on hosts matched ramp.com inside liveramp.com. Both are guarded here.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import quote, urlparse

from .cache import env as _env, get_cache as _cache

GH = "https://api.github.com"


def _de():
    import devpost_enrich as de
    return de


def _reserved() -> set:
    de = _de()
    return set(getattr(de, "GH_RESERVED", ())) | {
        "sponsors", "enterprise", "readme", "topics", "search", "orgs", "collections",
        "about", "site", "marketplace", "pricing", "security", "login", "join",
        "settings", "notifications", "new", "organizations", "explore", "trending",
        "customer-stories", "team", "blog", "watch", "stars",
    }


def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def org_matches(login: str, domain: str, name: str = "") -> bool:
    """Confirm a candidate org actually belongs to this company: its profile
    website or public org email points back at the company domain.

    Name similarity is deliberately NOT accepted — it matched 'Ramp' to the
    unrelated 'FedRAMP' org. Hosts are parsed and compared, not substring-matched,
    because plain `in` matched ramp.com inside liveramp.com.
    """
    try:
        u = _de().gh_user(login) or {}
    except Exception:
        return False
    if u.get("type") != "Organization":
        return False
    dom = (domain or "").lower().replace("www.", "").strip("/")
    if not dom:
        return False
    blog = (u.get("blog") or "").strip().lower()
    if blog:
        host = urlparse(blog if "//" in blog else "//" + blog).netloc.replace("www.", "")
        if host == dom or host.endswith("." + dom):
            return True
    email = (u.get("email") or "").strip().lower()
    if "@" in email:
        edom = email.rsplit("@", 1)[-1].replace("www.", "")
        if edom == dom or edom.endswith("." + dom):
            return True
    return False


def find_org(domain: str, name: str = "", org_hint: str = "") -> str:
    """Best-effort GitHub org login for a company, or "". Cached per domain.

    Every candidate must pass `org_matches` — an unverified org is worse than
    none, since it would poison the learned email pattern for the company.
    """
    domain = (domain or "").strip().lower()
    if not domain:
        return ""
    f = _cache()
    key = f"ghorg/v1:{domain}|{(name or '').lower()}|{(org_hint or '').lower()}"
    hit = f.cache_get(key)
    if hit is not None:
        return hit.get("org", "")

    reserved = _reserved()
    org = ""
    # 1. an org linked from the homepage — still verified: a page's GitHub links
    #    are often the site's VENDORS (wix, newrelic), not the company's own org.
    if org_hint and org_hint.lower() not in reserved and org_matches(org_hint, domain, name):
        org = org_hint
    if not org:
        # 2. guess login = domain label or compact name (cheap: core API).
        label = domain.split(".")[0]
        for guess in {label, _compact(name)}:
            if guess and guess.lower() not in reserved and org_matches(guess, domain, name):
                org = guess
                break
    if not org and name:
        # 3. org search by name (expensive: 30/min), same verification.
        try:
            data = _de().gh_get(f"{GH}/search/users?q={quote(name + ' type:org')}&per_page=5") or {}
        except Exception:
            data = {}
        for item in (data.get("items") or []):
            login = item.get("login", "")
            if login and org_matches(login, domain, name):
                org = login
                break

    f.cache_put(key, {"org": org})
    return org
