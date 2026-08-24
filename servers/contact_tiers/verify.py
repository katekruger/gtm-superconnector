"""Tier 3 — validated email status. The fix for the "~99% falsely-verified" problem.

Two independent signals, combined:
  1. Hunter (EMAIL_VERIFY_KEY) — we read its `accept_all` flag, which is what was
     missing: a "deliverable" on a catch-all domain is NOT a confirmed mailbox.
  2. Self-hosted SMTP probe — MX lookup + RCPT TO, plus a random-mailbox probe to
     detect catch-all domains directly. Free, no per-lookup cost.

Returns an honest status: verified | catch-all | risky | invalid | unknown.
Everything is cached (per email + per domain) so re-runs never re-probe.
Degrades gracefully: if port 25 is blocked (common on residential ISPs) the SMTP
signal is 'unknown' and we fall back to Hunter / the learned pattern.

Moved here from `Raw B2B Company Targets/enrich/email_verify.py` so that every
flow can use it: it previously imported `reuse`, which imports `find_contacts`,
which made it unusable from `find_contacts.py` itself.
"""

from __future__ import annotations

import random
import re
import smtplib
import socket
from typing import Dict, Optional

import requests

from .cache import env as _env, get_cache as _cache
from . import patterns as _pat

_SENDER = "research@example.com"   # neutral MAIL FROM for the probe
_SMTP_TIMEOUT = 8


def _hunter_key() -> str:
    return _env("EMAIL_VERIFY_KEY")


def _smtp_enabled() -> bool:
    return (_env("EMAIL_SMTP_VERIFY") or "1") not in ("0", "false", "no")


# ---------------------------------------------------------------------------
# MX
# ---------------------------------------------------------------------------
def mx_hosts(domain: str) -> list:
    f = _cache()
    key = "mx:" + domain
    hit = f.cache_get(key)
    if hit is not None:
        return hit.get("mx", [])
    hosts = []
    try:
        import dns.resolver
        ans = dns.resolver.resolve(domain, "MX", lifetime=6)
        hosts = [str(r.exchange).rstrip(".") for r in sorted(ans, key=lambda x: x.preference)]
    except Exception:
        hosts = []
    f.cache_put(key, {"mx": hosts})
    return hosts


# ---------------------------------------------------------------------------
# SMTP probe (real address + random address for catch-all)
# ---------------------------------------------------------------------------
def _smtp_probe(domain: str, address: str) -> Dict:
    """{rcpt_ok, catch_all, blocked}. One session probes both the real address
    and a random one, so catch-all is detected directly rather than assumed."""
    out = {"rcpt_ok": None, "catch_all": None, "blocked": False}
    hosts = mx_hosts(domain)
    if not hosts:
        out["rcpt_ok"] = False   # no MX at all -> no mailbox
        return out
    rand = f"nx-{random.randint(10**7, 10**8)}@{domain}"  # noqa: S311 (not security)
    for host in hosts[:2]:
        try:
            srv = smtplib.SMTP(timeout=_SMTP_TIMEOUT)
            srv.connect(host, 25)
            srv.helo("example.com")
            srv.mail(_SENDER)
            code_real, _ = srv.rcpt(address)
            code_rand, _ = srv.rcpt(rand)
            try:
                srv.quit()
            except Exception:
                pass
            out["rcpt_ok"] = code_real in (250, 251)
            out["catch_all"] = code_rand in (250, 251)
            return out
        except (socket.timeout, ConnectionRefusedError, OSError, smtplib.SMTPException):
            continue
    out["blocked"] = True
    return out


# ---------------------------------------------------------------------------
# Hunter (full response, incl. accept_all)
# ---------------------------------------------------------------------------
def _hunter(email: str) -> Optional[Dict]:
    key_ = _hunter_key()
    if not key_:
        return None
    f = _cache()
    ck = "hunterfull:" + email
    hit = f.cache_get(ck)
    if hit is not None:
        return hit.get("data")
    data = None
    try:
        r = requests.get("https://api.hunter.io/v2/email-verifier",
                         params={"email": email, "api_key": key_}, timeout=15)
        d = (r.json() or {}).get("data", {})
        data = {"result": d.get("result"), "accept_all": bool(d.get("accept_all")),
                "score": d.get("score"), "status": d.get("status")}
    except Exception:
        data = None
    f.cache_put(ck, {"data": data})
    return data


# ---------------------------------------------------------------------------
# Combined classification
# ---------------------------------------------------------------------------
def classify(email: str) -> str:
    """verified | catch-all | risky | invalid | unknown."""
    email = (email or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "invalid"
    domain = email.split("@")[1]
    f = _cache()
    ck = "emailstatus:" + email
    hit = f.cache_get(ck)
    if hit is not None:
        return hit.get("status", "unknown")

    h = _hunter(email)
    smtp = _smtp_probe(domain, email) if _smtp_enabled() else {"blocked": True}

    status = "unknown"
    # SMTP is the strongest direct signal when it works.
    if smtp and not smtp.get("blocked"):
        if smtp.get("catch_all"):
            status = "catch-all"
        elif smtp.get("rcpt_ok"):
            status = "verified"
        elif smtp.get("rcpt_ok") is False:
            status = "invalid"
    # Hunter corroborates / fills gaps, and its accept_all overrides a naive verified.
    if h:
        if h.get("accept_all") and status in ("verified", "unknown"):
            status = "catch-all"
        elif status == "unknown":
            r = h.get("result")
            status = {"deliverable": "verified", "undeliverable": "invalid",
                      "risky": "risky"}.get(r, "unknown")
            if status == "verified" and h.get("accept_all"):
                status = "catch-all"

    f.cache_put(ck, {"status": status})
    return status


# usable-for-outreach ranking: lower = better
RANK = {"verified": 0, "catch-all": 1, "risky": 2, "unknown": 3,
        "pattern-guessed": 3, "invalid": 9}
_RANK = RANK   # back-compat alias for existing callers


def best_email(name: str, domain: str) -> tuple:
    """Pick the best guessed address by validated status. Returns (email, status)
    where status honestly reflects the winner: verified / catch-all / risky /
    pattern-guessed (SMTP couldn't determine) / invalid (all guesses rejected) /
    not found. Never launders an invalid guess as 'pattern-guessed'.

    Kept for callers that have no company context. Prefer `resolve.resolve_email`,
    which learns the company's format first instead of guessing blind.
    """
    # Capped at 3 to match the old fc.email_guesses() behaviour: each candidate
    # costs a Hunter lookup, and the wider generic list would silently more than
    # double the credit burn of every existing caller.
    guesses = _pat.candidates_for(name, domain, None)[:3]
    if not guesses:
        return "", "not found"
    ranked = []
    for _p, addr in guesses:
        st = classify(addr)
        if st == "verified":
            return addr, "verified"     # confirmed mailbox — done
        ranked.append((addr, st))
    ranked.sort(key=lambda x: RANK.get(x[1], 3))
    addr, st = ranked[0]
    if st == "invalid":
        return addr, "invalid"
    return addr, ("pattern-guessed" if st == "unknown" else st)
