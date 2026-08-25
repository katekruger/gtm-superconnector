# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-08-25

First public release. Renamed, documented, and tested; tool behavior is unchanged.

### Fixed

- **The MCP server could not start from a built plugin.** `server.py` imports
  `python-dotenv`, but `build-plugin.sh` installed only `fastmcp`, `httpx`, and
  `requests`. The sealed runtime was missing a required dependency, which
  surfaced as an opaque MCP handshake failure. The build now installs from
  `requirements.txt` and verifies every dependency imports before packaging.
- **`clay_list_approved_functions` referenced a file that was not in the repo.**
  Added [`config/clay-functions.example.json`](config/clay-functions.example.json).
- **`gtm_resolve_contact_email` defaulted to a path outside the plugin**, so
  resolution failed whenever `.mcp.json` did not override it. The default is now
  the bundled `servers/` directory.
- **`build-plugin.sh` hardcoded a single Homebrew interpreter path** and failed
  on any other layout. It now discovers a 3.12+ interpreter and accepts
  `PYTHON_SOURCE`.
- **`run-gtm-server.sh` required a built runtime**, so it could not run from a
  clone. It now falls back to `.venv/` and accepts a `GTM_PYTHON` override, with
  an actionable error when nothing is found.

### Changed

- **Renamed throughout.** `servers/gtm_mcp/` → `servers/gtm_mcp/`;
  `run-gtm-server.sh` → `run-gtm-server.sh`; MCP server keys `gtm` → `gtm`
  and `crm` → `crm`; plugin name → `gtm-superconnector`.
- **`CONTACT_TIERS_PATH` → `CONTACT_TIERS_PATH`.**
- **Account input field `product_users` → `product_users`.** The `user_count`
  alias is unchanged, so callers already using it are unaffected.
- **The SMTP probe identity is configurable** via `SMTP_PROBE_DOMAIN` instead of
  hardcoded, defaulting to the reserved `example.com`. Probing with a domain you
  do not control is impolite and affects sending reputation.
- Package and module docstrings no longer reference files from an unrelated
  repository.
- Removed three dead imports in `contact_tiers` flagged by the new lint step.

### Added

- MIT [LICENSE](LICENSE) — the repository was public with no license, so nothing
  in it was legally reusable.
- Full documentation set: [architecture](docs/architecture.md),
  [tools](docs/tools.md), [configuration](docs/configuration.md),
  [skills](docs/skills.md), [development](docs/development.md).
- `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml` — dependencies
  previously existed only as arguments inside the build script.
- [`.env.example`](.env.example) documenting all nine environment variables,
  their cost implications, and their default-off behavior.
- 23 tests covering the send-ready rule, scoring determinism, and the
  preview-only invariants.
- GitHub Actions CI: lint, import check, manifest validation, shell syntax, tests.
- [CONTRIBUTING.md](CONTRIBUTING.md).

### Removed

- The README's download link to a `v0.1.0` release in a different GitHub
  organization, which 404s for every visitor.

## [0.1.0]

Initial internal release.

[Unreleased]: https://github.com/katekruger/gtmplugin/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/katekruger/gtmplugin/releases/tag/v0.2.0
