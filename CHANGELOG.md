# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`.claude-plugin/marketplace.json`** — a self-marketplace, so the plugin can be
  installed at all. Without it there was no install route: `claude plugin
  marketplace add` resolves exactly this path, and `claude plugin install` only
  accepts a plugin name from an already-added marketplace. Verified `"source":
  "./"` against the CLI rather than assuming it, since the docs only show
  subdirectory sources.
- **`userConfig`** for `crm_mcp_url` and `n8n_base_url`, replacing a hardcoded
  personal endpoint. Both optional.
- `SECURITY.md`, including a table of exactly what data reaches which third party
  and under what conditions.
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).
- `CLAUDE.md` and `AGENTS.md` — instructions for agents working on this repo.
- `.github/` issue templates, PR checklist, and `dependabot.yml`.
- `.version-bump.json` and `scripts/bump-version.sh`; CI fails if the four
  version-carrying files disagree.
- `scripts/check-skills.py`, enforcing the skill frontmatter rules in CI.
- `.gitattributes`.
- README sections: Requirements, a real Quick start, and Safety and limits.

### Changed

- **BREAKING: all five skills renamed to verb-first form.** Invocation names change:
  `account-intelligence` → `researching-accounts`,
  `outreach-builder` → `building-outreach-campaigns`,
  `clay-reconciliation` → `reconciling-clay-snapshots`,
  `activation-review` → `reviewing-activation-dropoff`,
  `n8n-operations` → `debugging-n8n-workflows`.
  Anyone invoking these by their old name must update.
- Every skill description rewritten to open with "Use when" and lead with real
  user phrasings instead of `This skill should be used when...`.
- CI now runs `claude plugin validate --strict` on both manifests, the skill
  checker, the version-agreement check, and a gitleaks scan over full history.
- Manifest gains `displayName`.

### Fixed

- **The documented install command did not exist.** The README said `claude plugin
  install .`; that command takes a plugin name from a marketplace and has no path
  form. Replaced with the two routes that actually work.

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
