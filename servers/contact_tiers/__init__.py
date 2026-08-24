"""Shared contact-resolution tiers for every contact-tiers scraping flow.

One implementation, used by `find_contacts.py`, the `Raw B2B Company Targets/`
pipeline, and `build1000/`. Lives at the repo root and depends only on stdlib +
requests (+ devpost_enrich, lazily, for the GitHub token) — deliberately NOT on
`reuse` or `find_contacts`, since `reuse` imports `find_contacts` and any such
dependency would be a circular import.

Typical use:

    import contact_tiers as ct

    ct.set_cache(my_fetcher)                    # optional: share a cache
    ctx = ct.email_context(domain, org)         # once per company
    email, status, li = ct.resolve_email(name, domain, ctx, login=gh_login)

See `resolve.resolve_email` for the status vocabulary — it is deliberately
honest about the difference between a real address, an inferred one, and a guess.
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
