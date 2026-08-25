"""Shared contact-resolution tiers.

A single four-tier email resolver, ordered by certainty and cost — free and
factual first, paid guesswork last. Each tier only handles what the one above
it could not resolve:

  1. git_emails  — the real address a person publishes in their own commits
  2. patterns    — the company's address format, learned from tier 1's real
                   addresses, applied to people we only have a name for
  3. verify      — MX/SMTP/Hunter confirm or reject
  4. pdl         — paid lookup for the remainder; also the only linkedin_url source

Depends only on the standard library plus `requests`. Tier 4 (`pdl`) and the
paid side of tier 3 are opt-in and stay disabled unless explicitly enabled.

Typical use:

    import contact_tiers as ct

    ct.set_cache(my_fetcher)                    # optional: share a cache
    ctx = ct.email_context(domain, org)         # once per company
    email, status, li = ct.resolve_email(name, domain, ctx, login=gh_login)

See `resolve.resolve_email` for the status vocabulary — it is deliberately
honest about the difference between a real address, an inferred one, and a
guess. Only `verified` and `verified:commit` are ever send-ready.
"""

from .cache import DiskCache, env, get_cache, set_cache
from .git_emails import corporate_pairs, email_for_person, org_commit_emails
from .github_org import find_org, org_matches
from .patterns import PATTERNS, candidates_for, infer, match_pattern, name_parts, render
from .pdl import budget_remaining, calls_made, enrich_person
from .resolve import email_context, resolve_email
from .verify import RANK, best_email, classify, mx_hosts

__all__ = [
    # cache / env. NB: the accessor is `get_cache`, not `cache` — exporting a
    # function named `cache` here would shadow the `contact_tiers.cache`
    # submodule and break `from . import cache` inside the package.
    "DiskCache", "get_cache", "set_cache", "env",
    # tier 1
    "org_commit_emails", "corporate_pairs", "email_for_person",
    "find_org", "org_matches",
    # tier 2
    "PATTERNS", "infer", "render", "match_pattern", "candidates_for", "name_parts",
    # tier 3
    "classify", "best_email", "mx_hosts", "RANK",
    # tier 4
    "enrich_person", "budget_remaining", "calls_made",
    # orchestration
    "email_context", "resolve_email",
]
