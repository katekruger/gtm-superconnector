"""Every tool in this package is preview-only. These tests assert the guarantee
rather than trusting the docstrings.
"""
import pytest

from gtm_mcp.core import bundle_provenance, detect_activation_dropoff, preview_campaign_build, reconcile_snapshots


def test_campaign_preview_starts_paused_and_writes_nothing():
    result = preview_campaign_build("Q3", "subject", "body")
    assert result["campaign"]["status"] == "paused"
    assert result["write_performed"] is False


def test_campaign_preview_warns_about_unmapped_senders_and_lists():
    warnings = preview_campaign_build("Q3", "s", "b")["warnings"]
    assert len(warnings) == 2


def test_reconciliation_reports_but_never_writes():
    result = reconcile_snapshots(
        [{"user_id": "1", "plan": "free"}],
        [{"user_id": "1", "plan": "pro"}, {"user_id": "2"}],
    )
    assert result["write_performed"] is False
    assert result["updates"][0]["changes"]["plan"] == {"before": "free", "after": "pro"}
    assert [row["user_id"] for row in result["inserts"]] == ["2"]


def test_reconciliation_separates_missing_rows_from_deletions():
    # A row absent from the incoming snapshot is "missing_from_incoming",
    # never silently treated as a delete.
    result = reconcile_snapshots([{"user_id": "1"}], [])
    assert len(result["missing_from_incoming"]) == 1
    assert result["inserts"] == []


def test_reconciliation_surfaces_schema_drift():
    result = reconcile_snapshots([{"user_id": "1", "old_col": 1}], [{"user_id": "1", "new_col": 2}])
    assert result["schema_drift"] == {"added": ["new_col"], "removed": ["old_col"]}


def test_reconciliation_refuses_oversized_snapshots():
    with pytest.raises(ValueError, match="10,000"):
        reconcile_snapshots([{"user_id": str(i)} for i in range(10_001)], [])


def test_provenance_rejects_fields_missing_their_source():
    result = bundle_provenance([{"field": "email", "value": "a@b.com"}])
    assert result["complete"] is False
    assert "source" in result["invalid_inputs"][0]["missing"]


def test_provenance_records_conflicts_instead_of_silently_picking_one():
    result = bundle_provenance([
        {"field": "title", "value": "CTO", "source": "a", "collected_at": "2026-01-01", "confidence": 0.9, "verification_method": "manual"},
        {"field": "title", "value": "VP Eng", "source": "b", "collected_at": "2026-01-02", "confidence": 0.5, "verification_method": "scrape"},
    ])
    assert len(result["conflicts"]) == 1
    assert result["fields"]["title"]["value"] == "CTO"  # higher confidence wins, conflict still reported


def test_activation_dropoff_flags_install_without_repository():
    rows = detect_activation_dropoff([{"installed": True, "repo_count": 0}])
    assert "installed_without_repository" in rows[0]["dropoff_reasons"]


def test_activation_dropoff_is_evaluated_against_a_fixed_clock():
    users = [{"installed": True, "repo_count": 2, "prompt_count": 5, "last_active_at": "2026-01-01T00:00:00Z"}]
    rows = detect_activation_dropoff(users, inactive_days=14, as_of="2026-03-01T00:00:00Z")
    assert "created_history_then_inactive" in rows[0]["dropoff_reasons"]


def test_healthy_users_are_not_flagged():
    users = [{"installed": True, "repo_count": 3, "prompt_count": 40, "last_active_at": "2026-02-28T00:00:00Z"}]
    assert detect_activation_dropoff(users, as_of="2026-03-01T00:00:00Z") == []
