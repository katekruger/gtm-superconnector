from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from fastmcp import FastMCP
from dotenv import load_dotenv

from .core import bundle_provenance, classify_email, detect_activation_dropoff, preview_campaign_build, rank_contacts, rank_team_adoption, reconcile_snapshots, score_icp_accounts
from .n8n import N8nOps

load_dotenv(Path(__file__).parents[2] / ".env")

mcp = FastMCP("GTM Superconnector")


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_rank_team_adoption(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank candidate accounts using product users, repositories, coding-agent usage, verified corporate emails, sponsor potential, and team concentration."""
    return rank_team_adoption(accounts)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_score_icp_accounts(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score accounts already sourced by Clay for the 2-15-person software-team ICP using explicit evidence fields."""
    return score_icp_accounts(accounts)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_rank_best_contact(contacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank CTO, technical founder, engineering leader, DevEx leader, and founding-engineer candidates with evidence and email readiness."""
    return rank_contacts(contacts)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_classify_email_readiness(email: str | None = None, verification_status: str | None = None) -> dict[str, Any]:
    """Normalize email status to verified, verified:commit, inferred, catch-all, risky, personal, or unresolved. Only verified states are send-ready."""
    return classify_email(email, verification_status)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_resolve_contact_email(
    name: str,
    domain: str,
    github_org: str = "",
    github_login: str = "",
    company: str = "",
    allow_paid_verification: bool = False,
    allow_pdl: bool = False,
) -> dict[str, Any]:
    """Run the shared email waterfall. Paid Hunter/PDL tiers are opt-in; only verified results are send-ready."""
    outreach = Path(os.getenv("CONTACT_TIERS_PATH", Path(__file__).parents[3] / "contact-tiers"))
    if str(outreach) not in sys.path:
        sys.path.insert(0, str(outreach))
    try:
        import contact_tiers as ct
    except ImportError as exc:
        raise ValueError(f"Could not load the shared contact_tiers resolver from {outreach}: {exc}") from exc
    context = ct.email_context(domain, github_org)
    email, raw_status, linkedin_url = ct.resolve_email(
        name, domain, context, login=github_login, company=company,
        use_verify=allow_paid_verification, use_pdl=allow_pdl,
    )
    status = str(raw_status).lower()
    normalized = (
        status if status in {"verified", "verified:commit", "catch-all", "risky"}
        else "personal" if "personal" in status
        else "inferred" if status.startswith("inferred:") or status in {"pdl", "pattern-guessed"}
        else "unresolved"
    )
    return {
        **classify_email(email or None, normalized),
        "raw_status": raw_status,
        "linkedin_url": linkedin_url or None,
        "cost_controls": {"paid_verification_enabled": allow_paid_verification, "pdl_enabled": allow_pdl},
        "provenance": {"resolver": "contact_tiers", "github_org": github_org or None},
    }


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_build_enrichment_provenance(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Bundle enriched fields with source, collection date, confidence, verification method, and conflicting evidence."""
    return bundle_provenance(fields)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_reconcile_clay_snapshot(current_rows: list[dict[str, Any]], incoming_rows: list[dict[str, Any]], key: str = "user_id") -> dict[str, Any]:
    """Diff a complete current snapshot against incoming Clay rows: inserts, field updates, unchanged, missing IDs, and schema drift. Preview only."""
    return reconcile_snapshots(current_rows, incoming_rows, key)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_detect_activation_dropoff(users: list[dict[str, Any]], inactive_days: int = 14, as_of: str | None = None) -> list[dict[str, Any]]:
    """Find installed-without-repo, history-then-inactive, and no-proof-moment users from product fields."""
    return detect_activation_dropoff(users, inactive_days, as_of)


@mcp.tool(annotations={"readOnlyHint": True})
def gtm_preview_campaign_build(
    name: str,
    subject: str,
    body: str,
    timezone_name: str = "America/New_York",
    sender_accounts: list[str] | None = None,
    tags: list[str] | None = None,
    lead_list_id: str | None = None,
) -> dict[str, Any]:
    """Build a paused campaign preview for Cowork with zero external writes or HTTP calls."""
    return preview_campaign_build(name, subject, body, timezone_name, sender_accounts, tags, lead_list_id)


@mcp.tool(annotations={"readOnlyHint": True})
def clay_list_approved_functions() -> dict[str, Any]:
    """Show the local approval/cost contract for Clay Functions. Execute functions through the official Clay MCP connector."""
    path = Path(os.getenv("CLAY_FUNCTION_POLICY_PATH", Path(__file__).parents[2] / "config" / "clay-functions.example.json"))
    if not path.exists():
        return {"functions": [], "configured": False, "required": ["name", "expected_outputs", "max_rows", "estimated_credits_per_row", "permissions", "approved"]}
    data = json.loads(path.read_text())
    return {**data, "configured": True, "execution_connector": "Official Clay MCP: https://api.clay.com/v3/mcp"}


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_health() -> dict[str, Any]:
    """Check n8n reachability and whether API-key and workflow allowlist controls are configured."""
    return await N8nOps().health()


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_list_approved_workflows(limit: int = 100) -> dict[str, Any]:
    """List n8n workflows, filtering to the configured approved workflow IDs when an allowlist exists."""
    ops = N8nOps()
    data = await ops.request("GET", "/api/v1/workflows", params={"limit": min(max(limit, 1), 250)})
    rows = data.get("data", data if isinstance(data, list) else [])
    if ops.approved:
        rows = [row for row in rows if str(row.get("id")) in ops.approved]
    return {"workflows": rows, "allowlist_enforced": bool(ops.approved)}


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_validate_workflow(workflow_id: str) -> dict[str, Any]:
    """Structurally validate an approved workflow and report missing nodes, unnamed nodes, disabled nodes, and credential references. No execution."""
    ops = N8nOps()
    ops._check(workflow_id)
    workflow = await ops.request("GET", f"/api/v1/workflows/{workflow_id}")
    nodes = workflow.get("nodes", [])
    issues = []
    if not nodes:
        issues.append("workflow_has_no_nodes")
    for node in nodes:
        if not node.get("name"):
            issues.append(f"unnamed_node:{node.get('id', '?')}")
        if node.get("disabled"):
            issues.append(f"disabled_node:{node.get('name', node.get('id', '?'))}")
    return {"workflow_id": workflow_id, "name": workflow.get("name"), "node_count": len(nodes), "credential_reference_count": sum(bool(n.get("credentials")) for n in nodes), "issues": issues, "valid": not issues, "executed": False}


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_preview_workflow_input(workflow_id: str, input_payload: dict[str, Any]) -> dict[str, Any]:
    """Validate payload size and show the approved trigger nodes that could accept it. Dry run only; never invokes the workflow."""
    ops = N8nOps()
    ops._check(workflow_id)
    workflow = await ops.request("GET", f"/api/v1/workflows/{workflow_id}")
    encoded = json.dumps(input_payload)
    triggers = [
        {"id": node.get("id"), "name": node.get("name"), "type": node.get("type")}
        for node in workflow.get("nodes", [])
        if "trigger" in str(node.get("type", "")).lower() or "webhook" in str(node.get("type", "")).lower()
    ]
    issues = []
    if len(encoded.encode()) > 256_000:
        issues.append("payload_exceeds_256kb_connector_limit")
    if not triggers:
        issues.append("no_supported_trigger_detected")
    return {"workflow_id": workflow_id, "trigger_nodes": triggers, "payload_bytes": len(encoded.encode()), "input_keys": sorted(input_payload), "issues": issues, "valid": not issues, "executed": False}


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_list_executions(workflow_id: str, status: str | None = None, limit: int = 50) -> Any:
    """List recent executions for one approved n8n workflow."""
    ops = N8nOps()
    ops._check(workflow_id)
    params = {"workflowId": workflow_id, "limit": min(max(limit, 1), 100), "includeData": False}
    if status:
        params["status"] = status
    return await ops.request("GET", "/api/v1/executions", params=params)


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_inspect_execution(execution_id: str) -> Any:
    """Inspect one n8n execution with run data for failure diagnosis. Read-only."""
    return await N8nOps().request("GET", f"/api/v1/executions/{execution_id}", params={"includeData": True})


@mcp.tool(annotations={"readOnlyHint": True})
async def n8n_last_known_good(workflow_id: str) -> dict[str, Any]:
    """Return the newest successful execution for an approved workflow."""
    ops = N8nOps()
    ops._check(workflow_id)
    data = await ops.request("GET", "/api/v1/executions", params={"workflowId": workflow_id, "status": "success", "limit": 1, "includeData": True})
    rows = data.get("data", [])
    return {"workflow_id": workflow_id, "execution": rows[0] if rows else None}


@mcp.tool(annotations={"destructiveHint": True})
async def n8n_retry_execution(execution_id: str, workflow_id: str, load_latest_workflow: bool = False, confirm: bool = False) -> dict[str, Any]:
    """Preview or retry one failed execution. Requires confirm=true and an explicit workflow allowlist."""
    preview = {"action": "retry_execution", "execution_id": execution_id, "workflow_id": workflow_id, "load_latest_workflow": load_latest_workflow, "write_performed": False}
    if not confirm:
        return preview
    ops = N8nOps()
    ops._check(workflow_id, write=True)
    result = await ops.request("POST", f"/api/v1/executions/{execution_id}/retry", json={"loadWorkflow": load_latest_workflow})
    return {"write_performed": True, "result": result}


if __name__ == "__main__":
    mcp.run()
