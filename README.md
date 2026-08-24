# GTM plugin for Claude Cowork

[Download the private v0.1.0 release](https://github.com/katekruger/gtmplugin/releases/download/v0.1.0/gtm-superconnector.plugin)

This plugin bundles five GTM skills with three connectors:

- Official Clay remote MCP for discovery, enrichment, and enabled Clay Functions.
- CRM remote MCP for CRM records and audited activity.
- A bundled local GTM MCP for deterministic scoring, email policy, reconciliation, campaign previews, activation analysis, and guarded n8n operations.

## Install

Open Claude Desktop, switch to Cowork, go to **Customize → Plugins**, choose the option to upload a custom plugin, and select `gtm-superconnector.plugin`. Complete the Clay and CRM OAuth prompts.

The local GTM connector works in Cowork through Claude Desktop. It is unavailable when the desktop app is closed or when an administrator disables local plugin MCP servers.

## n8n configuration

The local connector defaults to `http://127.0.0.1:5678`. To enable n8n API operations, the desktop process must receive:

- `N8N_API_KEY`: a scoped n8n API key.
- `N8N_APPROVED_WORKFLOW_IDS`: comma-separated workflow IDs the connector may inspect or retry.

Retries are disabled without the allowlist and require `confirm=true` even when configured.

## Availability boundary

Plugin skills work in Cowork, web chat, and Claude Desktop. The bundled local MCP works only through Claude Desktop. A public HTTPS deployment is required for the same proprietary tools to work in remote Cowork sessions when the desktop app is unavailable.

## Build from source

Run `scripts/build-plugin.sh` on Apple Silicon macOS with Python 3.12. The script creates an isolated runtime, writes `dist/gtm-superconnector.plugin`, and rejects archives containing symbolic links or corrupted files. Generated runtimes and plugin packages are intentionally excluded from Git history.
