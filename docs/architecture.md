# Architecture

## The shape of it

```
Claude (skills)  ──▶  three MCP connectors  ──▶  data + automation
                        │
        ┌───────────────┼────────────────┐
        │               │                │
     clay            crm               gtm
   (remote)        (remote)          (LOCAL)
   Clay API       CRM records     deterministic logic
```

Skills are procedures, not prompts. Each one names the tools to call, the order to call them in, and the point at which it must stop and ask. The connectors supply capability; the skills supply judgment and restraint.

## Why the local connector exists

Clay and the CRM are remote HTTP MCP servers — they work anywhere Claude runs. The CRM
endpoint is not bundled: it is a `userConfig` value (`crm_mcp_url`) that you point at your
own server. Left blank, the CRM connector is simply absent and the skills that would have
used it label their results partial rather than substituting another source.

So why bundle a local Python server at all?

Because three categories of work should not be delegated to a language model:

1. **Scoring.** An LLM asked to "rank these accounts" produces plausible, unstable, unauditable rankings. `gtm_score_icp_accounts` produces the same output for the same input, forever, and returns the evidence flags that produced the number.
2. **Diffing.** Snapshot reconciliation is exact set arithmetic. A model summarizing a diff will miss rows.
3. **Safety gates.** A rule enforced in prose is a suggestion. A rule enforced in `classify_email` is a rule.

The local server is the part of the system that cannot be talked out of its answer.

## Availability boundary

This is the main operational constraint, and it is worth understanding before you build on it.

| Surface | Skills | `clay` / `crm` | `gtm` (local) |
|---|---|---|---|
| Claude Code, desktop | ✅ | ✅ | ✅ |
| Web chat | ✅ | ✅ | ❌ |
| Remote / headless sessions | ✅ | ✅ | ❌ |

The `gtm` connector is a local stdio process launched by `scripts/run-gtm-server.sh`. It requires a desktop session, and an administrator can disable local plugin MCP servers entirely.

When the local connector is unavailable, the skills still run and the remote connectors still work — but the deterministic tools are missing, and a skill that depends on `gtm_classify_email_readiness` will say so rather than improvising. To use these tools in remote sessions you would need to deploy the server behind public HTTPS and register it as a remote MCP endpoint.

## Package layout

### `servers/gtm_mcp/`

| Module | Responsibility |
|---|---|
| `server.py` | MCP tool definitions and annotations. Thin — argument handling and delegation only. |
| `core.py` | Every pure function: scoring, ranking, classification, reconciliation, provenance, previews. No I/O, no network, no clock except through an injected `as_of`. |
| `n8n.py` | `N8nOps` — the only module that performs authenticated writes, and the only place the allowlist is enforced. |

`core.py` is pure by design. That is what makes the test suite meaningful and the scoring reproducible.

### `servers/contact_tiers/`

A four-tier email resolver, ordered by certainty and cost. Each tier handles only what the tier above could not:

| Tier | Module | Method | Cost | Best status it can produce |
|---|---|---|---|---|
| 1 | `git_emails` | Addresses people publish in their own commits | Free | `verified:commit` |
| 2 | `patterns` | Company address format learned from tier 1, applied to new names | Free | `inferred` |
| 3 | `verify` | MX / SMTP probe, optional Hunter lookup | Free / 💰 | `verified` |
| 4 | `pdl` | People Data Labs lookup; the only source of LinkedIn URLs | 💰 | `inferred` |

Tier 1 is first because it is the only tier that observes an address the person actually chose to publish. Tiers 3 and 4 are cost-bearing and stay off unless enabled by both a key and a per-call flag.

The package depends only on the standard library plus `requests`, so it can be lifted into other pipelines without dragging the MCP server along.

## Safety model

Three layers, in order of strength:

**1. Type-level.** Seventeen of eighteen tools carry `readOnlyHint`. `n8n_retry_execution` carries `destructiveHint` — the client can surface this before a call happens.

**2. Runtime.** The write path requires *both* `confirm=true` *and* a non-empty `N8N_APPROVED_WORKFLOW_IDS`. With the allowlist unset, retries raise rather than proceed. Called with `confirm=false`, the tool returns a preview and `write_performed: False`.

**3. Procedural.** Every skill ends at an approval gate, and [`skills/outreach-builder/references/approval-gates.md`](../skills/outreach-builder/references/approval-gates.md) enumerates them.

The layers are ordered deliberately: a failure at the procedural layer is caught by the runtime layer.

## Bounds

Every batch tool caps its input rather than accepting unbounded work:

| Tool | Cap | On exceed |
|---|---|---|
| `gtm_score_icp_accounts`, `gtm_rank_team_adoption` | 500 accounts | Silently truncates |
| `gtm_rank_best_contact` | 200 contacts | Silently truncates |
| `gtm_build_enrichment_provenance` | 1,000 fields | Silently truncates |
| `gtm_detect_activation_dropoff` | 10,000 users | Silently truncates |
| `gtm_reconcile_clay_snapshot` | 10,000 rows per side | **Raises `ValueError`** |
| `n8n_preview_workflow_input` | 256 KB payload | Reports an issue, stays valid=false |

Reconciliation raises rather than truncating because a silently truncated diff would report real rows as missing — a wrong answer is worse than an error.
