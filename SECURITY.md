# Security policy

## Reporting a vulnerability

Report privately through
[GitHub Security Advisories](https://github.com/katekruger/gtm-superconnector/security/advisories/new).
Please do not open a public issue.

Expect an acknowledgement within 7 days and an assessment within 30.

## In scope

- A way to make a tool write, send, or upload without the documented confirmation
- A bypass of the n8n workflow allowlist
- An input that causes `gtm_classify_email_readiness` to report an unverified
  address as send-ready
- Credential leakage through logs, tool output, or error messages
- Anything that causes the plugin to contact an endpoint the user did not configure

## Out of scope

- Cost incurred by deliberately enabling the paid enrichment tiers
- Behavior of the third-party services this plugin talks to (Clay, n8n, Hunter,
  People Data Labs), except where this plugin sends them data it should not

## What data goes where

This matters more than usual here, because the plugin handles contact data.

| Destination | What is sent | When |
|---|---|---|
| Nothing — stays local | Scoring, ranking, classification, reconciliation, activation analysis, campaign previews | Always. These tools make no network calls at all. |
| Your n8n instance | Workflow and execution queries | Only when `N8N_API_KEY` is set |
| GitHub API | Public org and commit metadata | Tier-1 email resolution, only with `GITHUB_TOKEN` |
| Hunter.io | The email address being verified | Only with `EMAIL_VERIFY_KEY` **and** `allow_paid_verification=true` |
| People Data Labs | Name, domain, company | Only with `PEOPLEDATALABS_API_KEY` **and** `allow_pdl=true` |
| Mail servers on the target domain | An SMTP `RCPT` probe from `SMTP_PROBE_DOMAIN` | Tier-3 verification |
| Your configured CRM endpoint | Whatever the CRM connector is asked for | Only if you set `crm_mcp_url` |

Both paid tiers are off by default and require a key *and* a per-call flag. There
is no configuration in which this plugin sends contact data to an endpoint the
maintainer controls.

## Credentials

Never commit `.env` or `config/clay-functions.json`; both are gitignored. Sensitive
`userConfig` values are stored by Claude Code in the OS keychain, not in this repo.
