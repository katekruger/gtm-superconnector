"""The four-tier email resolver.

Ordered by certainty and cost — free and factual first, paid guesswork last.
Each tier only handles what the one above it couldn't:

  1. git_emails  — the real address a person publishes in their own commits
  2. patterns    — the company's format, learned from Tier 1's real addresses,
                   applied to people we only have a name for
  3. verify      — MX/SMTP/Hunter confirm or reject
  4. pdl         — paid lookup for the remainder; also the only linkedin_url source

The status vocabulary is deliberately narrow about what we actually know.
Nothing here is allowed to round a guess up into a fact.
"""

from __future__ import annotations

from typing import Dict, Optional

from . import git_emails as _ge
from . import patterns as _pat
from . import pdl as _pdl
from . import verify as _ev


def email_context(domain: str, org: str = "") -> Dict:
    """Per-company email intelligence, computed once and reused for every person
    at that company: the org's real commit authors, and the address format
    inferred from the ones on the company domain.

    Cheap to call repeatedly — git_emails caches per org.
    """
    authors = _ge.org_commit_emails(org, domain) if org else []
    pairs = _ge.corporate_pairs(org, domain) if org else []
    return {"org": org, "domain": domain, "authors": authors,
            "pattern": _pat.infer(pairs, domain)}


def resolve_email(name: str, domain: str, ctx: Optional[Dict] = None,
                  login: str = "", company: str = "", use_pdl: bool = True,
                  use_verify: bool = True) -> tuple:
    """Return (email, status, linkedin_url).

    `use_verify=False` skips Tier 3 (Hunter costs a credit per candidate); Tiers
    1 and 2 are free and still run, so callers that never verified before don't
    silently acquire a per-row bill. `use_pdl=False` likewise skips Tier 4.

    Status meanings:
      verified:commit          — the work address this person publishes in commits
      verified                 — a mailbox SMTP/Hunter confirmed exists
      inferred:<fmt>           — derived from a format learned from real addresses
                                 at this domain; unconfirmed but evidence-backed
      verified:commit:personal — a real address, but their personal one; no work
                                 address could be derived
      catch-all / risky        — domain accepts everything / provider flagged it
      pattern-guessed          — nothing learned, nothing confirmed. A guess.
      pdl                      — supplied by PeopleDataLabs
      not found                — no usable address
    """
    ctx = ctx or {"org": "", "authors": [], "pattern": {}}

    # Tier 1 — a real address, no inference involved.
    try:
        real, real_is_corp = _ge.email_for_person(name, ctx.get("org", ""), domain, login)
    except Exception:
        real, real_is_corp = "", False
    if real and real_is_corp:
        return real, "verified:commit", ""
    # A personal address (their Gmail) is real but is the wrong channel for B2B
    # outreach, so it waits below in case we can derive their work address.

    # Tiers 2+3 — try the learned format first, let the verifier confirm.
    inferred = ctx.get("pattern") or {}
    try:
        cands = _pat.candidates_for(name, domain, inferred)
    except Exception:
        cands = []
    if not cands:
        return (real, "verified:commit:personal", "") if real else ("", "not found", "")

    ranked = []
    for pat, addr in cands:
        st = "unknown"
        if use_verify:
            try:
                st = _ev.classify(addr)
            except Exception:
                st = "unknown"
            if st == "verified":
                return addr, "verified", ""
        ranked.append((pat, addr, st))

    # SMTP is usually blocked on residential ISPs, so 'unknown' is the common
    # case. A pattern we learned from real addresses is still a strong bet —
    # say so explicitly rather than hiding it behind a generic guess label.
    if inferred.get("pattern") and inferred.get("confidence") in ("high", "med"):
        addr = _pat.render(inferred["pattern"], name, domain)
        if addr and not any(a == addr and s == "invalid" for _p, a, s in ranked):
            return addr, f"inferred:{inferred['pattern']}", ""

    # A real personal address now beats an unconfirmed catch-all/risky work
    # guess: at this point we have no evidence for the work address at all.
    if real:
        return real, "verified:commit:personal", ""

    usable = [(p, a, s) for p, a, s in ranked if s != "invalid"]
    if usable:
        usable.sort(key=lambda x: _ev.RANK.get(x[2], 3))
        pat, addr, st = usable[0]
        if st in ("catch-all", "risky"):
            return addr, st, ""

    # Tier 4 — paid, and only for rows nothing free could resolve.
    person = {}
    if use_pdl:
        try:
            person = _pdl.enrich_person(name, domain, company)
        except Exception:
            person = {}
    if person.get("email"):
        return person["email"], "pdl", person.get("linkedin_url", "")
    li = person.get("linkedin_url", "")

    if usable:
        pat, addr, st = usable[0]
        return addr, ("pattern-guessed" if st == "unknown" else st), li
    return "", "not found", li
