# GTM Superconnector

A [Claude Code](https://claude.com/claude-code) plugin for go-to-market work that refuses to guess.

It bundles five GTM skills with a local MCP server providing deterministic scoring, contact resolution, and guarded automation — wired to Clay and to a CRM endpoint you supply. The organizing principle: **evidence or silence.** An inferred email address is never reported as a real one, absence of evidence is never converted into a negative claim, and no tool sends, uploads, or launches anything without a separate explicit approval.

[![CI](https://github.com/katekruger/gtm-superconnector/actions/workflows/ci.yml/badge.svg)](https://github.com/katekruger/gtm-superconnector/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

---

## Why this exists

Most GTM automation optimizes for volume and treats data quality as a rounding error. That is how a pattern-guessed address ends up in a send queue labelled "verified."

This plugin inverts the default. Email addresses carry a status vocabulary that distinguishes *confirmed*, *inferred*, and *guessed* — and only two of seven states are ever send-ready. Reconciliation stops at a dry run. Campaign builds come back paused. The one tool that can write to a remote system requires both an allowlist and a confirmation flag.

If you want a tool that will blast 10,000 guessed addresses, this is the wrong repo.

## What's inside

```
gtm-superconnector/                     # the repo root IS the plugin
├── .claude-plugin/
│   ├── plugin.json            # manifest, incl. userConfig
│   └── marketplace.json       # self-marketplace, source "./"
├── .mcp.json                  # 3 connectors: clay, crm, gtm
├── skills/                    # 5 skills — the workflows an agent follows
├── servers/
│   ├── gtm_mcp/               # MCP server: scoring, reconciliation, previews, n8n
│   └── contact_tiers/         # 4-tier email resolver, by certainty and cost
├── config/                    # Clay Function approval + cost policy (example)
├── scripts/                   # build, launch, version bump, skill check
├── tests/                     # safety invariants and scoring determinism
└── docs/                      # full reference documentation
```

## Requirements

- **Python 3.12+** — `servers/gtm_mcp/server.py` uses PEP 604 unions (`str | None`)
  in its tool signatures, and FastMCP resolves those annotations at runtime to build
  the MCP tool schemas. On 3.11 or earlier that raises at import. This is a hard
  constraint, not a preference.
- **Claude Code v2.1.x or newer** — for `userConfig` and marketplace install
- No API keys required to start. Credentials only unlock the n8n and paid-enrichment tiers.

## Install

### From the marketplace

```bash
/plugin marketplace add katekruger/gtm-superconnector
/plugin install gtm-superconnector@gtm-superconnector
```

### From a local clone

```bash
git clone https://github.com/katekruger/gtm-superconnector.git
cd gtm-superconnector
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
claude plugin marketplace add ./gtm-superconnector
claude plugin install gtm-superconnector@gtm-superconnector
```

`claude plugin install` resolves a plugin **name** from a configured marketplace —
it does not take a directory path. Adding the local directory as a marketplace
first is what makes the local install work.

### Configuration on install

Two optional settings are declared in the manifest and prompted for at install time:

| Option | What it does |
|---|---|
| `crm_mcp_url` | HTTPS URL of *your* CRM MCP server. Leave blank to run without the CRM connector. |
| `n8n_base_url` | Your n8n instance. Defaults to `http://127.0.0.1:5678`. |

Set them non-interactively with `--config`:

```bash
claude plugin install gtm-superconnector@gtm-superconnector --config n8n_base_url=http://127.0.0.1:5678
```

## Quick start

The deterministic tools work immediately, with no credentials and no network:

```
Score these accounts for ICP fit: Acme (8 engineers, uses Claude Code,
open source), Globex (900 employees, no signals).
```

Acme returns `icp_score: 60.0` with `claude_code_or_codex: true`; Globex returns
`0.0`. The zero means *no evidence found*, not *evidence of absence* — every
evidence flag is reported separately so the difference survives.

Verify the server itself loads:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'servers'); import gtm_mcp.server; print('ok')"
```

## The five skills

Each skill is a procedure Claude follows, not a prompt template. They live in [`skills/`](skills/) and every one ends at a stop-and-approve gate.

| Skill | Use when you want to | Stops at |
|---|---|---|
| [account-intelligence](skills/account-intelligence/SKILL.md) | Research an account, source ICP companies, rank targets, find the best contact | A ranked summary with explicit missing fields |
| [outreach-builder](skills/outreach-builder/SKILL.md) | Build a campaign, verify a contact, prepare design-partner outreach | A paused campaign preview |
| [clay-reconciliation](skills/clay-reconciliation/SKILL.md) | Diff a user snapshot against Clay, check schema drift | A dry run |
| [activation-review](skills/activation-review/SKILL.md) | Find activation drop-off and missing proof moments | Cohort counts and recommendations |
| [n8n-operations](skills/n8n-operations/SKILL.md) | Debug a workflow failure, dry-run, retry an execution | A retry preview |

## The three connectors

| Connector | Type | Purpose |
|---|---|---|
| `clay` | Remote HTTP MCP | Discovery, enrichment, and enabled Clay Functions |
| `crm` | Remote HTTP MCP | CRM records and audited activity. **User-supplied** — set `crm_mcp_url` to your own endpoint, or leave it blank and the skills degrade to partial results. |
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

## Safety and limits

What this plugin **will not** do, by construction rather than by convention:

- **Send, upload, or launch anything.** Every skill ends at a preview or a dry run.
  Campaign builds come back `status: "paused"`.
- **Treat an unverified address as send-ready.** Five of the seven email states are
  quarantined, and an unrecognized state degrades to `unresolved` rather than to
  `verified`. It fails closed.
- **Write to a remote system without two independent guards.** `n8n_retry_execution`
  needs `confirm=true` *and* a non-empty `N8N_APPROVED_WORKFLOW_IDS`. With the
  allowlist unset, retries raise rather than proceed.
- **Spend money implicitly.** Both paid enrichment tiers need an API key *and* a
  per-call flag, and the response echoes `cost_controls` so spend is visible.
- **Convert absent evidence into a negative claim.** A missing signal is reported as
  missing, not as false.
- **Contact an endpoint you did not configure.** The CRM connector is `userConfig`;
  there is no maintainer-controlled endpoint anywhere in the plugin.

Honest limits:

- **The local `gtm` connector needs a desktop session.** It is a local stdio process,
  so it is unavailable in web chat and remote sessions, and an administrator can
  disable local plugin MCP servers entirely. The skills and the two remote connectors
  still work; the deterministic tools do not. See
  [docs/architecture.md](docs/architecture.md#availability-boundary).
- **Scoring is deterministic, not correct.** It reproduces the same ranking for the
  same input. Whether the weights match *your* ICP is your call — they are documented
  in [docs/tools.md](docs/tools.md) so you can disagree with them specifically.
- **Batch tools cap their input.** Most truncate; reconciliation raises above 10,000
  rows per side, because a silently truncated diff misreports real rows as missing.
- **Windows is untested.** The launcher and build script are Bash.

## Building a distributable plugin

```bash
./scripts/build-plugin.sh
```

Discovers a Python 3.12+ interpreter, builds a sealed runtime, verifies every dependency imports, confirms the server starts, and writes `dist/gtm-superconnector.plugin`. The archive is rejected if it contains symlinks or corrupt entries. Runtimes and built packages are gitignored.

## Development

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

.venv/bin/pytest -q                        # 23 tests
.venv/bin/ruff check servers tests         # lint
python3 scripts/check-skills.py            # skill frontmatter rules
./scripts/bump-version.sh --check          # version agreement
```

See [docs/development.md](docs/development.md) for architecture notes and the contribution workflow, or [CONTRIBUTING.md](CONTRIBUTING.md) to submit a change.

## Documentation

- **[docs/architecture.md](docs/architecture.md)** — how the pieces fit, and where the local connector stops working
- **[docs/tools.md](docs/tools.md)** — complete MCP tool reference with arguments and return shapes
- **[docs/configuration.md](docs/configuration.md)** — every environment variable, cost implications, safety controls
- **[docs/skills.md](docs/skills.md)** — what each skill does and the approval gates it enforces
- **[docs/development.md](docs/development.md)** — local setup, testing, releasing
- **[CHANGELOG.md](CHANGELOG.md)** — version history

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for
setup, the commit convention, and how to add a skill. Participation is governed by
the [Code of Conduct](CODE_OF_CONDUCT.md).

Security issues go through
[private advisories](https://github.com/katekruger/gtm-superconnector/security/advisories/new),
not public issues. [SECURITY.md](SECURITY.md) documents exactly what data this
plugin sends where.

## See also

Every project here shares one idea: a GTM system should refuse to act on data it cannot verify.

[n8n-operator](https://github.com/katekruger/n8n-operator) — the governed control plane behind this plugin's n8n operations, usable on its own with a full audit trail.

[campaign-preflight](https://github.com/katekruger/campaign-preflight) — the same evidence-or-silence rule applied to outbound campaigns: 76 deterministic checks, and never a pass it could not verify.

## License

MIT — see [LICENSE](LICENSE).

No third-party assets are redistributed here. The plugin talks to Clay, n8n,
Hunter, and People Data Labs through their own APIs under your own credentials
and their respective terms.
