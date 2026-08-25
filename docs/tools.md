# Tool reference

Eighteen tools on the local `gtm` connector. Seventeen are annotated `readOnlyHint`; `n8n_retry_execution` is annotated `destructiveHint` and is the only tool that can write to a remote system.

Every tool that could imply a write returns `write_performed: false` explicitly, so a caller never has to infer it.

---

## Scoring and ranking

### `gtm_score_icp_accounts(accounts) -> list`

Scores accounts against a 2–15-person software-team ICP using explicit evidence fields. Returns the input rows plus `icp_score` (0–100) and `icp_evidence`, sorted descending. Caps at 500 accounts.

| Input field | Contributes |
|---|---|
| `team_size` or `employee_count` | 30 at 2–15 people; 12 at 1–30; 0 otherwise |
| `coding_agent_evidence` / `claude_code_evidence` / `codex_evidence` | 30 |
| `open_source_evidence` | 15 |
| `ai_tooling_evidence` | 15 |
| `developer_workflow_evidence` | 10 |

Evidence fields are truthiness-checked, so pass a source URL rather than `true` — the skills require one.

An account with no evidence scores `0.0`. That means *no evidence found*, not *evidence of absence*; `icp_evidence` reports each flag separately so the distinction survives.

### `gtm_rank_team_adoption(accounts) -> list`

Ranks accounts by observed product adoption. Returns rows plus `team_adoption_score` (capped at 100) and `ranking_evidence`. Caps at 500 accounts.

| Input field | Weight |
|---|---|
| `product_users` or `user_count` | ×12 |
| `active_repositories` or `active_repo_count` | ×5 |
| `coding_agent_usage` or `ai_job_count` | ×1.5, contribution capped at 20 |
| `verified_corporate_emails` or `verified_email_count` | ×4 |
| `team_concentration` (0–1) | ×15 |
| `sponsor_potential` (0–1) | ×10 |

Use this only when real product-usage fields exist. Without them it degrades to ranking everything at zero.

### `gtm_rank_best_contact(contacts) -> list`

Ranks people by decision-making authority and reachability. Returns rows plus `contact_score`, `send_ready`, and `selection_evidence`. Caps at 200 contacts.

Title priority, matched as a substring against `title`:

| Score | Titles |
|---|---|
| 100 | CTO, chief technology officer, technical (co)founder |
| 92 | founder, cofounder, co-founder |
| 85 | VP engineering, head of engineering, engineering director |
| 78 | developer productivity, developer experience, DevEx, platform engineering |
| 70 | founding engineer, staff engineer, principal engineer, engineering manager |
| 20 | anything else |

Bonuses: `+12` send-ready verification status, `+5` corporate address, `+5` a `source_url` is present.

`send_ready` here is derived from `email_verification_status` alone. A high-ranked contact with an unverified address is still not send-ready.

---

## Contact resolution

### `gtm_classify_email_readiness(email=None, verification_status=None) -> dict`

Normalizes any status into the seven-state vocabulary and decides send-readiness. This is the safety-critical function in the package.

Returns `{email, status, send_ready, rule}`.

- Only `verified` and `verified:commit` produce `send_ready: true`
- An empty or missing address is never send-ready, whatever the status says
- An unrecognized status degrades to `unresolved` — it fails closed
- Input is lowercased and stripped before matching

### `gtm_resolve_contact_email(name, domain, github_org="", github_login="", company="", allow_paid_verification=False, allow_pdl=False) -> dict`

Runs the full four-tier waterfall (see [architecture](architecture.md#serverscontact_tiers)).

Both paid tiers are **off by default** and require a key *and* the corresponding flag. Returns the classification plus `raw_status`, `linkedin_url`, `cost_controls`, and `provenance`.

Raises `ValueError` if the `contact_tiers` package cannot be imported from `CONTACT_TIERS_PATH`.

### `gtm_build_enrichment_provenance(fields) -> dict`

Bundles enriched fields with their sourcing metadata before any CRM write-back is proposed. Caps at 1,000 fields.

Each item **must** carry all six of `field`, `value`, `source`, `collected_at`, `confidence`, `verification_method`. Items missing any key are rejected into `invalid_inputs` rather than being partially accepted.

Returns `{fields, conflicts, invalid_inputs, complete}`. When two sources disagree, the higher `confidence` wins **and the conflict is still reported** — disagreement is never silently resolved.

---

## Data operations

### `gtm_reconcile_clay_snapshot(current_rows, incoming_rows, key="user_id") -> dict`

Diffs two complete snapshots. Preview only; `write_performed` is always `false`.

Returns `inserts`, `updates` (with field-level `before`/`after`), `unchanged`, `missing_from_incoming`, `missing_key_rows`, and `schema_drift`.

**Raises `ValueError` above 10,000 rows per side** rather than truncating — a truncated diff would misreport real rows as missing.

Rows absent from the incoming snapshot land in `missing_from_incoming`, never in a delete list. Deciding whether a missing row means "deleted" or "not exported" is the operator's call.

### `gtm_detect_activation_dropoff(users, inactive_days=14, as_of=None) -> list`

Finds three drop-off cohorts, returning only users with at least one reason. Caps at 10,000 users.

| Reason | Condition |
|---|---|
| `installed_without_repository` | Installed but `repo_count` is 0 |
| `created_history_then_inactive` | Has usage history, but `last_active_at` is at least `inactive_days` old |
| `no_meaningful_proof_moment` | Installed but zero usage history |

Pass `as_of` (ISO 8601) to evaluate against a fixed clock — required for reproducible analysis and used by the tests.

### `gtm_preview_campaign_build(name, subject, body, timezone_name="America/New_York", sender_accounts=None, tags=None, lead_list_id=None) -> dict`

Builds a campaign plan. **Zero network calls, zero writes.** The campaign always comes back `status: "paused"`, and `warnings` flags an unmapped sender allocation or lead list.

Creation and launch happen through a separate connector, after approval.

### `clay_list_approved_functions() -> dict`

Reads the local approval and cost contract from `CLAY_FUNCTION_POLICY_PATH`. Executes nothing — Clay Functions run through the official Clay MCP connector.

If the file is absent, returns `configured: false` plus the required schema, so a missing policy is visible rather than silently permissive. Start from [`config/clay-functions.example.json`](../config/clay-functions.example.json).

---

## n8n operations

All n8n tools require `N8N_API_KEY`; without it they raise. Tools taking a `workflow_id` enforce `N8N_APPROVED_WORKFLOW_IDS` when it is set.

| Tool | Arguments | Notes |
|---|---|---|
| `n8n_health()` | — | Reachability plus whether the key and allowlist are configured. Call this first. |
| `n8n_list_approved_workflows(limit=100)` | limit 1–250 | Filters to the allowlist; reports `allowlist_enforced` |
| `n8n_validate_workflow(workflow_id)` | | Structural check only. Reports missing, unnamed, and disabled nodes. Never executes. |
| `n8n_preview_workflow_input(workflow_id, input_payload)` | | Dry run. Validates payload size (256 KB cap) and lists trigger nodes. Never invokes. |
| `n8n_list_executions(workflow_id, status=None, limit=50)` | limit 1–100 | |
| `n8n_inspect_execution(execution_id)` | | Full run data for diagnosis |
| `n8n_last_known_good(workflow_id)` | | Newest successful execution, for diffing against a failure |
| `n8n_retry_execution(...)` | ⚠️ see below | The only write |

### `n8n_retry_execution(execution_id, workflow_id, load_latest_workflow=False, confirm=False) -> dict` ⚠️

The only tool in the package that mutates a remote system. Two independent guards:

1. **`confirm=false` (the default)** returns a preview with `write_performed: false`. Nothing is sent.
2. **The allowlist must be non-empty.** With `N8N_APPROVED_WORKFLOW_IDS` unset, a confirmed retry still raises: *"Retries are disabled until N8N_APPROVED_WORKFLOW_IDS is configured."*

So an unconfigured install cannot retry anything, and a configured install cannot retry by accident.
