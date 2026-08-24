"""Tier 1 — real emails from public git commit metadata.

Every git commit carries the author's configured email. For an ICP of software
companies this is the highest-yield free contact source there is: no guessing,
no verification round-trip, and it doubles as the ground truth that lets
`patterns.infer` work out a company's address format.

Two complementary reads:
  * org repos  -> /repos/{org}/{repo}/commits gives every contributor's
    author.email in one pass (broad: covers people who haven't pushed lately).
  * a handle   -> devpost_enrich.gh_commit_email walks that user's recent
    PushEvents (narrow, but resolves a specific person we already named).

Only emails on the company's own domain count as corporate. Personal addresses
(Gmail etc.) are kept but flagged, because they're contactable yet useless for
pattern inference — and are the wrong channel for B2B outreach anyway.
Bot/noreply addresses are dropped.

Cached per org. Degrades to [] without a GitHub token.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .cache import env as _env, get_cache as _cache

_GH = "https://api.github.com"

# Addresses that are never a human we can contact.
_BOT_RE = re.compile(
    r"(noreply|no-reply|users\.noreply\.github\.com|actions@github|"
    r"dependabot|renovate|greenkeeper|snyk-bot|\[bot\]|github-actions)", re.I)

# Free-mail providers: real, contactable, but not corporate -> no pattern signal.
_PERSONAL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "me.com", "protonmail.com", "proton.me",
    "aol.com", "gmx.com", "mail.com", "yandex.ru", "qq.com", "163.com",
}

_MAX_REPOS = 5           # most-recently-pushed repos per org
_COMMITS_PER_REPO = 100  # one page each — plenty for pattern inference


def _de():
    """devpost_enrich lazily: it owns the GitHub token + rate-limited gh_get.

    Imported inside the call rather than at module scope so that importing this
    package never triggers devpost_enrich's module-level token lookup (which can
    shell out to the `gh` CLI) for callers that never touch GitHub.
    """
    import devpost_enrich as de
    return de


def gh_get(url: str):
    try:
        return _de().gh_get(url)
    except Exception:
        return None


def _looks_like_person(name: str) -> bool:
    """A git author.name that's plausibly a real full name."""
    name = (name or "").strip()
    toks = [t for t in name.split() if t]
    if not (2 <= len(toks) <= 4):
        return False
    if "@" in name or any(ch.isdigit() for ch in name):
        return False
    return all(len(t) >= 2 for t in toks)


def _org_repos(org: str) -> List[str]:
    """Most-recently-pushed public repo names for an org."""
    repos = gh_get(f"{_GH}/orgs/{org}/repos?per_page=30&sort=pushed&type=public")
    if not isinstance(repos, list):
        return []
    return [r["name"] for r in repos
            if isinstance(r, dict) and r.get("name") and not r.get("fork")][:_MAX_REPOS]


def _repo_commit_authors(org: str, repo: str) -> List[Dict]:
    """[{name, email, login}] from one repo's recent commits."""
    data = gh_get(f"{_GH}/repos/{org}/{repo}/commits?per_page={_COMMITS_PER_REPO}")
    if not isinstance(data, list):
        return []
    out: List[Dict] = []
    for c in data:
        if not isinstance(c, dict):
            continue
        author = ((c.get("commit") or {}).get("author") or {})
        email = (author.get("email") or "").strip().lower()
        name = (author.get("name") or "").strip()
        if not email or _BOT_RE.search(email) or "@" not in email:
            continue
        login = ((c.get("author") or {}) or {}).get("login") or ""
        out.append({"name": name, "email": email, "login": login})
    return out


def org_commit_emails(org: str, domain: str) -> List[Dict]:
    """Distinct commit authors for an org.

    Returns [{name, email, login, corporate, commits}] sorted by commit count
    (most-active first — a decent proxy for "actually works here"). `corporate`
    is True when the address is on the company's own domain, which is what
    `patterns.infer` learns from.
    """
    if not org:
        return []
    f = _cache()
    key = f"gitemails/v1:{org.lower()}|{(domain or '').lower()}"
    cached = f.cache_get(key)
    if cached is not None:
        return cached.get("authors", [])

    seen: Dict[str, Dict] = {}
    for repo in _org_repos(org):
        for rec in _repo_commit_authors(org, repo):
            email = rec["email"]
            edom = email.split("@")[-1]
            if edom in _PERSONAL_DOMAINS and not _looks_like_person(rec["name"]):
                continue  # anonymous personal address — no name, no value
            hit = seen.get(email)
            if hit:
                hit["commits"] += 1
                if not hit["name"] and rec["name"]:
                    hit["name"] = rec["name"]
                if not hit["login"] and rec["login"]:
                    hit["login"] = rec["login"]
                continue
            seen[email] = {
                "name": rec["name"],
                "email": email,
                "login": rec["login"],
                "corporate": bool(domain) and edom == domain.lower(),
                "commits": 1,
            }

    authors = sorted(seen.values(), key=lambda a: -a["commits"])
    f.cache_put(key, {"authors": authors})
    return authors


def corporate_pairs(org: str, domain: str) -> List[tuple]:
    """[(full_name, email)] on the company domain — the pattern-inference input."""
    return [(a["name"], a["email"]) for a in org_commit_emails(org, domain)
            if a["corporate"] and _looks_like_person(a["name"])]


def email_for_person(name: str, org: str, domain: str, login: str = "") -> tuple:
    """A *real* commit email for a specific person: (email, is_corporate).

    Tries the org's commit authors first (by name, then by login), then falls
    back to that user's own PushEvents via the existing devpost_enrich helper.

    Corporate and personal addresses are both returned but flagged, because the
    caller must treat them differently: a work address is the right channel for
    B2B outreach, whereas someone's Gmail is a personal inbox and should lose to
    an inferred work address even though it's the more "certain" of the two.
    """
    want = re.sub(r"[^a-z]", "", (name or "").lower())
    if not want:
        return "", False
    matches = []
    for a in org_commit_emails(org, domain):
        if re.sub(r"[^a-z]", "", a["name"].lower()) == want or \
           (login and a["login"].lower() == login.lower()):
            matches.append(a)
    if matches:
        matches.sort(key=lambda a: (not a["corporate"], -a["commits"]))
        return matches[0]["email"], matches[0]["corporate"]

    if login:
        try:
            email = _de().gh_commit_email(login, name) or ""
        except Exception:
            email = ""
        email = email.strip().lower()
        if email and not _BOT_RE.search(email) and "@" in email:
            return email, bool(domain) and email.split("@")[-1] == domain.lower()
    return "", False
