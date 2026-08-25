"""The send-ready rule is the single most consequential piece of logic here:
it decides whether a human being receives a cold email. These tests pin it down.
"""
from gtm_mcp.core import classify_email


def test_only_verified_states_are_send_ready():
    assert classify_email("a@corp.com", "verified")["send_ready"] is True
    assert classify_email("a@corp.com", "verified:commit")["send_ready"] is True


def test_every_uncertain_state_is_quarantined():
    for status in ("inferred", "catch-all", "risky", "personal", "unresolved"):
        result = classify_email("a@corp.com", status)
        assert result["send_ready"] is False, f"{status} must not be send-ready"
        assert result["status"] == status


def test_unknown_status_degrades_to_unresolved_not_to_verified():
    # A typo or a new upstream vocabulary must never fail open.
    assert classify_email("a@corp.com", "definitely-fine")["status"] == "unresolved"
    assert classify_email("a@corp.com", "definitely-fine")["send_ready"] is False


def test_missing_address_is_never_send_ready_even_when_verified():
    assert classify_email(None, "verified")["send_ready"] is False
    assert classify_email("", "verified")["send_ready"] is False


def test_status_is_case_and_whitespace_insensitive():
    assert classify_email("a@corp.com", "  VERIFIED  ")["send_ready"] is True
