"""Tier 2 — learn a company's email format, then apply it.

The old flow guessed `first@domain` for everyone and verified nothing, so a
single naive pattern was applied to 100% of rows regardless of what the company
actually uses. This module inverts that: take the *real* addresses we already
hold for a domain (commit authors, mailto: links, SEC contacts), work out which
format they follow, and apply that one format to the people we only have names
for.

One confirmed address at a domain is worth more than any number of guesses,
because it turns every other name at that company from a 1-in-4 coin flip into
a derivation. Inference needs >=2 agreeing examples (or 1 with no dissent) —
below that we report no pattern rather than launder a guess as knowledge.

Pure functions over data the caller supplies; no network, no cache needed.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Dict, List, Optional, Tuple


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def name_parts(name: str) -> Optional[Tuple[str, str]]:
    """(first, last) lowercased ascii, or None if `name` isn't a usable person.

    Punctuation inside a token is stripped rather than disqualifying it, so
    "Paul D'Ambra" -> (paul, dambra) and "sana-faraz" -> (sana, faraz). Real
    commit authors are full of both, and rejecting them silently threw away
    the very examples we learn formats from.
    """
    toks = [re.sub(r"[^a-z]", "", t) for t in re.split(r"[\s._-]+", _ascii(name).lower())]
    toks = [t for t in toks if t]
    if len(toks) < 2:
        return None
    return toks[0], toks[-1]


# Every format we can both recognise and generate. Order matters only for
# tie-breaking readability; scoring decides the winner.
PATTERNS: Dict[str, callable] = {
    "first":       lambda f, l: f,
    "first.last":  lambda f, l: f"{f}.{l}",
    "firstlast":   lambda f, l: f"{f}{l}",
    "flast":       lambda f, l: f"{f[0]}{l}",
    "f.last":      lambda f, l: f"{f[0]}.{l}",
    "first.l":     lambda f, l: f"{f}.{l[0]}",
    "firstl":      lambda f, l: f"{f}{l[0]}",
    "first_last":  lambda f, l: f"{f}_{l}",
    "last":        lambda f, l: l,
    "lastf":       lambda f, l: f"{l}{f[0]}",
}

# Companies that hand out `first@` commonly fall back to a disambiguated form
# when two people share a first name (PostHog: pawel.l@ alongside pawel.c@).
# So a dominant pattern's natural partner is worth trying before generic ones.
_COLLISION_FALLBACK = {
    "first": "first.l",
    "first.l": "first",
    "first.last": "flast",
    "flast": "first.last",
}


def render(pattern: str, name: str, domain: str) -> str:
    """Build the address `pattern` implies for `name` at `domain`."""
    parts = name_parts(name)
    fn = PATTERNS.get(pattern)
    if not parts or not fn or not domain:
        return ""
    return f"{fn(*parts)}@{domain.lower()}"


def match_pattern(name: str, email: str) -> List[str]:
    """Which patterns are consistent with this (name, email) pair."""
    parts = name_parts(name)
    if not parts or "@" not in (email or ""):
        return []
    local = email.split("@")[0].strip().lower()
    return [p for p, fn in PATTERNS.items() if fn(*parts) == local]


def infer(pairs: List[Tuple[str, str]], domain: str) -> Dict:
    """Infer the dominant format from known (name, email) pairs at `domain`.

    Returns {pattern, confidence, support, dissent, samples}:
      pattern    — best format, or "" when the evidence is too thin
      confidence — high / med / low
      support    — how many pairs the winning pattern explains
      dissent    — on-domain pairs it does NOT explain (a real signal that the
                   company mixes formats, e.g. after an acquisition)
    """
    domain = (domain or "").lower()
    on_domain = [(n, e) for n, e in pairs
                 if e and "@" in e and e.split("@")[-1].lower() == domain and name_parts(n)]
    empty = {"pattern": "", "confidence": "low", "support": 0,
             "dissent": 0, "samples": len(on_domain)}
    if not on_domain:
        return empty

    votes: Counter = Counter()
    for n, e in on_domain:
        for p in match_pattern(n, e):
            votes[p] += 1
    if not votes:
        return empty

    pattern, support = votes.most_common(1)[0]
    explained = {e for n, e in on_domain if pattern in match_pattern(n, e)}
    dissent = len(on_domain) - len(explained)
    samples = len(on_domain)
    share = support / samples if samples else 0.0

    # Score on the winner's *share*, not on absolute dissent. Every real company
    # has some off-format addresses (nicknames, legacy accounts, contractors);
    # demanding zero dissent scored obviously-correct formats as 'low' and meant
    # this tier never fired on live data. A clearly dominant format is usable
    # even with holdouts — the verifier and fallbacks catch the rest.
    if support >= 3 and share >= 0.7:
        confidence = "high"
    elif support >= 3 and share >= 0.5:
        confidence = "med"
    elif support >= 2 and dissent == 0:
        confidence = "high"
    elif support >= 2 and share >= 0.5:
        confidence = "med"
    elif support >= 1 and dissent == 0:
        confidence = "med"   # single example: suggestive, never authoritative
    else:
        confidence = "low"

    runner_up = ""
    for p, c in votes.most_common(3)[1:]:
        if c >= 2:
            runner_up = p
            break

    return {"pattern": pattern, "confidence": confidence, "support": support,
            "dissent": dissent, "samples": samples,
            "share": round(share, 2), "runner_up": runner_up}


def candidates_for(name: str, domain: str, inferred: Optional[Dict] = None) -> List[Tuple[str, str]]:
    """[(pattern, email)] to try for `name`, best-first.

    With a learned pattern that format leads; the common fallbacks follow so a
    verifier can still rescue the row. Without one this degrades to the old
    frequency-ordered guess list — no worse than before, just honest about it.
    """
    parts = name_parts(name)
    if not parts or not domain:
        return []
    generic = ["first", "first.last", "flast", "firstlast", "f.last", "first.l", "firstl"]
    if inferred and inferred.get("pattern"):
        p = inferred["pattern"]
        # Learned format first, then this company's *own* observed second format
        # (a mixed shop like HashiCorp runs first.last + flast side by side),
        # then its collision fallback, then the generic frequency order.
        lead = [p, inferred.get("runner_up", ""), _COLLISION_FALLBACK.get(p, "")]
        order = [o for o in lead if o] + [o for o in generic if o not in lead]
    else:
        order = generic
    out, seen = [], set()
    for p in order:
        addr = render(p, name, domain)
        if addr and addr not in seen:
            seen.add(addr)
            out.append((p, addr))
    return out
