# GTM Superconnector

A [Claude Code](https://claude.com/claude-code) plugin for go-to-market work that refuses to guess.

It bundles five GTM skills with a local MCP server providing deterministic scoring, contact resolution, and guarded automation — wired to Clay and a CRM. The organizing principle: **evidence or silence.** An inferred email address is never reported as a real one, absence of evidence is never converted into a negative claim, and no tool sends, uploads, or launches anything without a separate explicit approval.

[![CI](https://github.com/katekruger/gtmplugin/actions/workflows/ci.yml/badge.svg)](https://github.com/katekruger/gtmplugin/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

---

## Why this exists

Most GTM automation optimizes for volume and treats data quality as a rounding error. That is how a pattern-guessed address ends up in a send queue labelled "verified."

This plugin inverts the default. Email addresses carry a status vocabulary that distinguishes *confirmed*, *inferred*, and *guessed* — and only two of seven states are ever send-ready. Reconciliation stops at a dry run. Campaign builds come back paused. The one tool that can write to a remote system requires both an allowlist and a confirmation flag.

If you want a tool that will blast 10,000 guessed addresses, this is the wrong repo.

## What's inside

```
gtmplugin/
├── skills/           # 5 Claude skills — the workflows an agent follows
├── servers/
│   ├── gtm_mcp/      # MCP server: scoring, reconciliation, previews, n8n ops
│   └── contact_tiers/# 4-tier email resolver, ordered by certainty and cost
├── config/           # Clay Function approval + cost policy
├── scripts/          # Build and launch
├── tests/            # Safety invariants and scoring determinism
└── docs/             # Full reference documentation
```

## Quick start

Requires **Python 3.12+**.

```bash
git clone https://github.com/katekruger/gtmplugin.git
cd gtmplugin
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # optional — see Configuration
```

Then add the plugin to Claude Code:

```bash
claude plugin install .
```

The scoring, ranking, reconciliation, and preview tools work immediately with no credentials. API keys only unlock the n8n and paid-enrichment tiers.

Verify the install:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'servers'); import gtm_mcp.server; print('ok')"
```

## The five skills

Each skill is a procedure Claude follows, not a prompt template. They live in [`skills/`](skills/) and every one ends at a stop-and-approve gate.

| Skill | Use when you want to | Stops at |
|---|---|---|
| [researching-accounts](skills/researching-accounts/SKILL.md) | Research an account, source ICP companies, rank targets, find the best contact | A ranked summary with explicit missing fields |
| [building-outreach-campaigns](skills/building-outreach-campaigns/SKILL.md) | Build a campaign, verify a contact, prepare design-partner outreach | A paused campaign preview |
| [reconciling-clay-snapshots](skills/reconciling-clay-snapshots/SKILL.md) | Diff a user snapshot against Clay, check schema drift | A dry run |
| [reviewing-activation-dropoff](skills/reviewing-activation-dropoff/SKILL.md) | Find activation drop-off and missing proof moments | Cohort counts and recommendations |
| [debugging-n8n-workflows](skills/debugging-n8n-workflows/SKILL.md) | Debug a workflow failure, dry-run, retry an execution | A retry preview |

## The three connectors

| Connector | Type | Purpose |
|---|---|---|
| `clay` | Remote HTTP MCP | Discovery, enrichment, and enabled Clay Functions |
| `crm` | Remote HTTP MCP | CRM records and audited activity |
| `gtm` | Local stdio MCP | Everything deterministic — scoring, reconciliation, previews, n8n |

The two remote connectors work anywhere Claude runs. **The local `gtm` connector requires a desktop Claude Code session** — it is a local process, so it is unavailable when the desktop app is closed or when an administrator disables local plugin MCP servers. See [docs/architecture.md](docs/architecture.md#availability-boundary).

## Tool reference

Eighteen tools. Seventeen are annotated read-only; exactly one can write.

**Scoring and ranking** — `gtm_score_icp_accounts`, `gtm_rank_team_adoption`, `gtm_rank_best_contact`

**Contact resolution** — `gtm_resolve_contact_email`, `gtm_classify_email_readiness`, `gtm_build_enrichment_provenance`

**Data operations** — `gtm_reconcile_clay_snapshot`, `gtm_detect_activation_dropoff`, `gtm_preview_campaign_build`, `clay_list_approved_functions`

**n8n** — `n8n_health`, `n8n_list_approved_workflows`, `n8n_validate_workflow`, `n8n_preview_workflow_input`, `n8n_list_executions`, `n8n_inspect_execution`, `n8n_last_known_good`, `n8n_retry_execution` ⚠️

Full signatures, arguments, and return shapes: **[docs/tools.md](docs/tools.md)**.

## The email status vocabulary

This is the core safety property, so it is worth stating on the front page:

| Status | Meaning | Send-ready |
|---|---|---|
| `verified` | Confirmed by a verification provider | ✅ |
| `verified:commit` | Published by the person in their own git commits | ✅ |
| `inferred` | Matches the company's known address pattern | ❌ |
| `catch-all` | Domain accepts everything; proves nothing | ❌ |
| `risky` | Provider flagged it | ❌ |
| `personal` | Not a corporate address | ❌ |
| `unresolved` | We do not know | ❌ |

An unrecognized status **degrades to `unresolved`**, never to `verified`. It fails closed. See [`tests/test_email_classification.py`](tests/test_email_classification.py) — the rule is pinned by tests.

## Configuration

Every variable is optional. Copy [`.env.example`](.env.example) to `.env` and fill in only what you need.

| Variable | Unlocks | Cost |
|---|---|---|
| `N8N_API_KEY` | All n8n tools | Free |
| `N8N_APPROVED_WORKFLOW_IDS` | n8n **retries** — disabled entirely without it | Free |
| `EMAIL_VERIFY_KEY` | Tier-3 email verification (Hunter) | 💰 Paid |
| `PEOPLEDATALABS_API_KEY` | Tier-4 enrichment + LinkedIn URLs | 💰 Paid |
| `GITHUB_TOKEN` | Tier-1 commit-email harvesting | Free |
| `SMTP_PROBE_DOMAIN` | Identity for SMTP probes — set to a domain you own | Free |

Both paid tiers are **opt-in per call** (`allow_paid_verification`, `allow_pdl`) in addition to needing a key. Full details: [docs/configuration.md](docs/configuration.md).

## Building a distributable plugin

```bash
./scripts/build-plugin.sh
```

Discovers a Python 3.12+ interpreter, builds a sealed runtime, verifies every dependency imports, confirms the server starts, and writes `dist/gtm-superconnector.plugin`. The archive is rejected if it contains symlinks or corrupt entries. Runtimes and built packages are gitignored.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q            # 23 tests
ruff check servers tests
```

See [docs/development.md](docs/development.md) for architecture notes and the contribution workflow, or [CONTRIBUTING.md](CONTRIBUTING.md) to submit a change.

## Documentation

- **[docs/architecture.md](docs/architecture.md)** — how the pieces fit, and where the local connector stops working
- **[docs/tools.md](docs/tools.md)** — complete MCP tool reference with arguments and return shapes
- **[docs/configuration.md](docs/configuration.md)** — every environment variable, cost implications, safety controls
- **[docs/skills.md](docs/skills.md)** — what each skill does and the approval gates it enforces
- **[docs/development.md](docs/development.md)** — local setup, testing, releasing
- **[CHANGELOG.md](CHANGELOG.md)** — version history

## License

MIT — see [LICENSE](LICENSE).
