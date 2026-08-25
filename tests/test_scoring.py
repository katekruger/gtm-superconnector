"""Scoring is deterministic and evidence-driven — same input, same rank, always."""
from gtm_mcp.core import rank_contacts, rank_team_adoption, score_icp_accounts


def test_icp_scoring_is_deterministic():
    accounts = [{"team_size": 8, "coding_agent_evidence": "url"}]
    assert score_icp_accounts(accounts) == score_icp_accounts(accounts)


def test_icp_prefers_target_team_size_band():
    ranked = score_icp_accounts([
        {"team_size": 8, "name": "in-band"},
        {"team_size": 25, "name": "wide-band"},
        {"team_size": 900, "name": "out-of-band"},
    ])
    assert [row["name"] for row in ranked] == ["in-band", "wide-band", "out-of-band"]
    assert ranked[-1]["icp_score"] == 0.0


def test_icp_evidence_flags_are_reported_alongside_the_score():
    row = score_icp_accounts([{"team_size": 5, "open_source_evidence": "https://example.com"}])[0]
    assert row["icp_evidence"]["open_source"] is True
    assert row["icp_evidence"]["claude_code_or_codex"] is False


def test_absent_evidence_never_becomes_negative_evidence():
    # An empty account scores zero, but no field is asserted as false-in-the-world.
    row = score_icp_accounts([{}])[0]
    assert row["icp_score"] == 0.0
    assert set(row["icp_evidence"]) == {
        "team_size_2_15", "claude_code_or_codex", "open_source", "ai_tooling", "developer_workflow",
    }


def test_contact_ranking_puts_technical_decision_makers_first():
    ranked = rank_contacts([
        {"title": "Marketing Intern", "name": "intern"},
        {"title": "CTO", "name": "cto"},
        {"title": "Founding Engineer", "name": "eng"},
    ])
    assert [row["name"] for row in ranked] == ["cto", "eng", "intern"]


def test_contact_ranking_marks_send_ready_from_verification_status_only():
    ranked = rank_contacts([{"title": "CTO", "email": "a@corp.com", "email_verification_status": "inferred"}])
    assert ranked[0]["send_ready"] is False


def test_team_adoption_score_is_bounded():
    row = rank_team_adoption([{
        "product_users": 9999, "active_repositories": 9999,
        "coding_agent_usage": 9999, "verified_corporate_emails": 9999,
    }])[0]
    assert row["team_adoption_score"] <= 100.0
