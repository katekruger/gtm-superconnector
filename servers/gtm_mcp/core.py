from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SEND_READY = {"verified", "verified:commit"}


def _number(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = row.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return 0.0


def rank_team_adoption(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for row in accounts[:500]:
        users = _number(row, "product_users", "user_count")
        repos = _number(row, "active_repositories", "active_repo_count")
        agents = _number(row, "coding_agent_usage", "ai_job_count")
        verified = _number(row, "verified_corporate_emails", "verified_email_count")
        concentration = min(_number(row, "team_concentration"), 1.0)
        sponsor = min(_number(row, "sponsor_potential"), 1.0)
        score = min(100.0, users * 12 + repos * 5 + min(agents, 20) * 1.5 + verified * 4 + concentration * 15 + sponsor * 10)
        evidence = [name for name, value in (("multiple_users", users >= 2), ("active_repositories", repos > 0), ("coding_agent_usage", agents > 0), ("verified_contacts", verified > 0), ("concentrated_team", concentration >= .5)) if value]
        ranked.append({**row, "team_adoption_score": round(score, 1), "ranking_evidence": evidence})
    return sorted(ranked, key=lambda x: x["team_adoption_score"], reverse=True)


def score_icp_accounts(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in accounts[:500]:
        size = _number(row, "team_size", "employee_count")
        size_fit = 1.0 if 2 <= size <= 15 else (0.4 if 1 <= size <= 30 else 0.0)
        evidence = {
            "team_size_2_15": size_fit == 1,
            "claude_code_or_codex": bool(row.get("coding_agent_evidence") or row.get("claude_code_evidence") or row.get("codex_evidence")),
            "open_source": bool(row.get("open_source_evidence")),
            "ai_tooling": bool(row.get("ai_tooling_evidence")),
            "developer_workflow": bool(row.get("developer_workflow_evidence")),
        }
        score = size_fit * 30 + evidence["claude_code_or_codex"] * 30 + evidence["open_source"] * 15 + evidence["ai_tooling"] * 15 + evidence["developer_workflow"] * 10
        output.append({**row, "icp_score": round(score, 1), "icp_evidence": evidence})
    return sorted(output, key=lambda x: x["icp_score"], reverse=True)


TITLE_PRIORITY = (
    (100, ("cto", "chief technology officer", "technical cofounder", "technical co-founder")),
    (92, ("founder", "cofounder", "co-founder")),
    (85, ("vp engineering", "head of engineering", "engineering director")),
    (78, ("developer productivity", "developer experience", "devex", "platform engineering")),
    (70, ("founding engineer", "staff engineer", "principal engineer", "engineering manager")),
)


def rank_contacts(contacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for row in contacts[:200]:
        title = str(row.get("title") or "").lower()
        title_score = next((score for score, phrases in TITLE_PRIORITY if any(p in title for p in phrases)), 20)
        status = str(row.get("email_verification_status") or "unresolved").lower()
        corporate = bool(row.get("email")) and not bool(row.get("personal_email"))
        score = title_score + (12 if status in SEND_READY else 0) + (5 if corporate else 0) + (5 if row.get("source_url") else 0)
        ranked.append({**row, "contact_score": score, "send_ready": status in SEND_READY, "selection_evidence": {"title_score": title_score, "verification_status": status, "corporate_email": corporate, "source_present": bool(row.get("source_url"))}})
    return sorted(ranked, key=lambda x: x["contact_score"], reverse=True)


def classify_email(email: str | None, status: str | None) -> dict[str, Any]:
    normalized = (status or "unresolved").strip().lower()
    allowed = {"verified", "verified:commit", "inferred", "catch-all", "risky", "personal", "unresolved"}
    if normalized not in allowed:
        normalized = "unresolved"
    return {"email": email, "status": normalized, "send_ready": bool(email) and normalized in SEND_READY, "rule": "Only verified or verified:commit is send-ready."}


def bundle_provenance(fields: list[dict[str, Any]]) -> dict[str, Any]:
    bundled: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []
    required = {"field", "value", "source", "collected_at", "confidence", "verification_method"}
    invalid = []
    for index, item in enumerate(fields[:1000]):
        missing = sorted(required - set(item))
        if missing:
            invalid.append({"index": index, "missing": missing})
            continue
        name = str(item["field"])
        entry = {key: item.get(key) for key in ("value", "source", "collected_at", "confidence", "verification_method")}
        previous = bundled.get(name)
        if previous and previous["value"] != entry["value"]:
            conflicts.append({"field": name, "values": [previous, entry]})
        if not previous or float(entry.get("confidence") or 0) > float(previous.get("confidence") or 0):
            bundled[name] = entry
    return {"fields": bundled, "conflicts": conflicts, "invalid_inputs": invalid, "complete": not invalid}


def reconcile_snapshots(current: list[dict[str, Any]], incoming: list[dict[str, Any]], key: str = "user_id") -> dict[str, Any]:
    if len(current) > 10000 or len(incoming) > 10000:
        raise ValueError("Snapshot reconciliation is capped at 10,000 rows per side.")
    old = {str(row[key]): row for row in current if row.get(key) not in (None, "")}
    new = {str(row[key]): row for row in incoming if row.get(key) not in (None, "")}
    inserts = [new[k] for k in new.keys() - old.keys()]
    missing = [old[k] for k in old.keys() - new.keys()]
    updates, unchanged = [], []
    for item_key in new.keys() & old.keys():
        changes = {field: {"before": old[item_key].get(field), "after": new[item_key].get(field)} for field in set(old[item_key]) | set(new[item_key]) if old[item_key].get(field) != new[item_key].get(field)}
        (updates if changes else unchanged).append({key: item_key, **({"changes": changes} if changes else {})})
    old_schema = set().union(*(row.keys() for row in current)) if current else set()
    new_schema = set().union(*(row.keys() for row in incoming)) if incoming else set()
    return {"key": key, "inserts": inserts, "updates": updates, "unchanged": unchanged, "missing_from_incoming": missing, "missing_key_rows": {"current": sum(not row.get(key) for row in current), "incoming": sum(not row.get(key) for row in incoming)}, "schema_drift": {"added": sorted(new_schema - old_schema), "removed": sorted(old_schema - new_schema)}, "write_performed": False}


def detect_activation_dropoff(users: list[dict[str, Any]], inactive_days: int = 14, as_of: str | None = None) -> list[dict[str, Any]]:
    now = datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else datetime.now(timezone.utc)
    results = []
    for row in users[:10000]:
        reasons = []
        installed = bool(row.get("installed") or row.get("onboarding_completed_at"))
        repos = _number(row, "repo_count", "active_repo_count", "distinct_repos_worked")
        history = _number(row, "prompt_count", "ai_job_count", "chat_session_count")
        if installed and repos == 0:
            reasons.append("installed_without_repository")
        if history > 0:
            last = row.get("last_active_at") or row.get("last_active")
            if last:
                parsed = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                if (now - parsed).days >= inactive_days:
                    reasons.append("created_history_then_inactive")
        if installed and history == 0:
            reasons.append("no_meaningful_proof_moment")
        if reasons:
            results.append({**row, "dropoff_reasons": reasons})
    return results


def preview_campaign_build(
    name: str,
    subject: str,
    body: str,
    timezone_name: str = "America/New_York",
    sender_accounts: list[str] | None = None,
    tags: list[str] | None = None,
    lead_list_id: str | None = None,
) -> dict[str, Any]:
    """Return a portable, zero-write campaign plan. Never touches the network."""
    return {
        "campaign": {
            "name": name,
            "status": "paused",
            "schedule": {"timezone": timezone_name, "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "from": "09:00", "to": "17:00"},
            "sequences": [{"steps": [{"type": "email", "delay_days": 0, "variants": [{"subject": subject, "body": body}]}]}],
            "sender_accounts": sender_accounts or [],
            "tags": tags or [],
            "lead_list_id": lead_list_id,
        },
        "warnings": [message for condition, message in ((not sender_accounts, "No sender allocation supplied."), (not lead_list_id, "No lead list mapped.")) if condition],
        "write_performed": False,
        "next_step": "Review this plan, then use the Instantly connector separately if creation is approved.",
    }
