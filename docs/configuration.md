# Configuration

Every variable is optional. With none of them set, the server starts and all deterministic tools — scoring, ranking, classification, reconciliation, activation analysis, campaign previews — work normally. Credentials unlock the n8n and paid-enrichment tiers only.

Copy [`.env.example`](../.env.example) to `.env` in the repo root. `.env` is gitignored.

```bash
cp .env.example .env
```

The server loads `.env` at startup via `python-dotenv`. Variables already present in the environment take precedence.

## userConfig (set at install time)

Declared in the manifest and prompted for by `/plugin configure`, or passed with
`claude plugin install --config KEY=VALUE`. Both are optional.

| Key | What it unlocks | Left blank |
|---|---|---|
| `crm_mcp_url` | The `crm` connector, pointed at **your own** CRM MCP server | The connector is absent. Skills that would use it say so and label results partial — they never substitute another source. |
| `n8n_base_url` | The n8n instance the local server talks to | Defaults to `http://127.0.0.1:5678` |

No CRM endpoint ships with this plugin. There is no default, and no
maintainer-controlled host anywhere in the configuration.

## Path variables

Normally set automatically by [`.mcp.json`](../.mcp.json) using `${CLAUDE_PLUGIN_ROOT}`. Override only for unusual layouts.

| Variable | Default | Purpose |
|---|---|---|
| `CONTACT_TIERS_PATH` | `servers/` | Where `gtm_resolve_contact_email` imports the resolver from |
| `CLAY_FUNCTION_POLICY_PATH` | `config/clay-functions.json` | Clay approval and cost contract |

## n8n

| Variable | Default | Effect |
|---|---|---|
| `N8N_BASE_URL` | `http://127.0.0.1:5678` | Instance URL |
| `N8N_API_KEY` | — | **Required by every n8n tool.** Unset, they raise `ValueError`. |
| `N8N_APPROVED_WORKFLOW_IDS` | — | Comma-separated allowlist |

`N8N_APPROVED_WORKFLOW_IDS` is a safety control, not a filter, and behaves differently for reads and writes:

- **Unset** — read tools work unfiltered; **retries are disabled entirely** and raise if attempted
- **Set** — every workflow ID is checked against it; anything else raises

Retries additionally require `confirm=true` on the call. Configuring the allowlist does not make retries automatic.

Use a scoped key. The connector needs read access to workflows and executions, plus retry permission only if you intend to retry.

## Contact resolution

All optional. Two are cost-bearing.

| Variable | Tier | Cost | Effect when unset |
|---|---|---|---|
| `GITHUB_TOKEN` | 1 | Free | Tier 1 skipped; resolution degrades to pattern inference and cannot produce `verified:commit` |
| `EMAIL_VERIFY_KEY` | 3 | 💰 Hunter credits | SMTP-only verification; no provider confirmation |
| `PEOPLEDATALABS_API_KEY` | 4 | 💰 PDL credits | Tier 4 skipped; no LinkedIn URLs |
| `SMTP_PROBE_DOMAIN` | 3 | Free | Falls back to `example.com` |

### Cost controls are two-layered

A key alone does not spend money. `gtm_resolve_contact_email` also requires a per-call flag:

```python
gtm_resolve_contact_email(name="...", domain="...")                          # free tiers only
gtm_resolve_contact_email(name="...", domain="...", allow_paid_verification=True)  # tier 3 paid
gtm_resolve_contact_email(name="...", domain="...", allow_pdl=True)               # tier 4 paid
```

Both default to `False`, and the response echoes `cost_controls` so spend is visible in the transcript. The [building-outreach-campaigns](../skills/building-outreach-campaigns/SKILL.md) skill keeps both disabled unless the user approves the cost.

### Set `SMTP_PROBE_DOMAIN` to a domain you own

Tier 3 opens an SMTP connection and issues `HELO` / `MAIL FROM` before a `RCPT` probe. Receiving mail servers log that identity. Probing with a domain you do not control is impolite, and doing it at volume from a domain you *do* control affects your sending reputation.

The default is `example.com` — reserved by [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606) and deliberately useless — so an unconfigured install cannot impersonate anyone.

## Clay Function policy

`clay_list_approved_functions` reads a local JSON contract describing which Clay Functions are approved and what they cost. It executes nothing; execution goes through the official Clay MCP connector.

```bash
cp config/clay-functions.example.json config/clay-functions.json
```

`config/clay-functions.json` is gitignored, since real policy tends to be organization-specific. Each entry requires `name`, `expected_outputs`, `max_rows`, `estimated_credits_per_row`, `permissions`, and `approved`.

If the file is missing, the tool returns `configured: false` along with the required schema — a missing policy is reported, never treated as blanket approval.

## Security notes

- **Never commit `.env` or `config/clay-functions.json`.** Both are gitignored; verify with `git check-ignore -v .env` before your first commit.
- **Scope your keys.** The n8n key needs workflow and execution read access, and retry permission only if you intend to retry.
- **Paid keys are rate-limited by cost, not by policy.** The per-call flags are the real budget control.
- **`GITHUB_TOKEN` needs no scopes** for public commit metadata. A default read-only token is sufficient.
