# Instructions for agents working on this repository

This file is for an agent modifying **this repo**. It is not documentation for
users of the plugin — that is [README.md](README.md) and [docs/](docs/).

## What this repo is

A Claude Code plugin, `gtm-superconnector`. The repo root **is** the plugin: the
manifest is at `.claude-plugin/plugin.json` and the marketplace entry at
`.claude-plugin/marketplace.json` uses `"source": "./"`.

## Layout

| Path | What it is |
|---|---|
| `.claude-plugin/` | `plugin.json` (manifest) and `marketplace.json` (self-marketplace) |
| `.mcp.json` | Three MCP connectors: `clay`, `crm`, `gtm` |
| `skills/<name>/SKILL.md` | One directory per skill, canonical path |
| `servers/gtm_mcp/` | The local MCP server |
| `servers/contact_tiers/` | Standalone four-tier email resolver |
| `config/` | Example policy files; the real ones are gitignored |
| `scripts/` | Build, launch, version bump, skill check |
| `docs/` | Reference documentation |
| `tests/` | Mirrors `servers/gtm_mcp/core.py` |

## Commands

```bash
pytest -q                                 # tests
ruff check servers tests                  # lint
python scripts/check-skills.py            # skill frontmatter rules
./scripts/bump-version.sh --check         # version agreement
./scripts/bump-version.sh 0.3.0           # set every version field
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
```

Requires Python 3.12+. `scripts/run-gtm-server.sh` picks up `.venv/bin/python`
automatically; override with `GTM_PYTHON`.

## Rules that are not negotiable

**1. `core.py` stays pure.** No network, no filesystem, no wall-clock reads
without an `as_of` parameter. This is what makes the safety properties testable.

**2. A skill change requires a corresponding test.** If you touch a safety rule —
send-readiness, an approval gate, a bound — pin the new behavior in `tests/`.
A rule documented in prose is a suggestion.

**3. Nothing fails open.** Unknown input degrades to the most conservative state.
`classify_email` treats an unrecognized status as `unresolved`, never `verified`.

**4. Write tools need two independent guards.** A `confirm` flag *and* a
configuration-level allowlist.

**5. Never hardcode a personal endpoint.** Anything user-specific goes in
`userConfig` and is referenced as `${user_config.key}`. Bundled paths use
`${CLAUDE_PLUGIN_ROOT}`.

## Naming policy

The repo and the plugin share one name: `gtm-superconnector`.

Use it verbatim in prose, headings, install commands, and URLs
(`github.com/katekruger/gtm-superconnector`). There is nothing to disambiguate.

## Python floor

**3.12 minimum, and do not lower it.** `servers/gtm_mcp/server.py` uses PEP 604
unions (`str | None`) in tool signatures, and FastMCP resolves those annotations
at runtime to build the MCP tool schemas. On 3.11 or earlier that raises at
import. The floor is a hard technical constraint, not a preference, and it is
deliberately not aligned with the other plugin repos.

## Skill frontmatter rules

Enforced by `scripts/check-skills.py` in CI:

```yaml
---
name: <optional; if present, must match the directory name exactly>
description: >
  Use when the user asks to "...", "...", or ... .
---
```

- `description` is **required**. `name` is **optional** — the published spec
  treats the directory name as authoritative. Where `name` exists it must match
  the directory. Do not add it where absent; do not strip it where present.
- `description` must open with **"Use when"**, be third person, and stay under
  1024 characters
- The description states **triggers, never the procedure**. A description that
  summarizes the workflow gets followed *instead of* the skill body — this is the
  most damaging skill defect and the reason the check exists
- Body under 500 words. Heavier material goes in `references/` and is linked
- **Renaming a skill is a breaking change.** The directory name is the
  invocation name. Avoid it; if unavoidable, flag it in `CHANGELOG.md`

## Version bumping

The version lives in four files, listed in `.version-bump.json`. Never edit them
by hand — run `./scripts/bump-version.sh <semver>`, then add a `CHANGELOG.md`
entry. CI fails if they disagree.

## Adding a tool

1. Write the logic as a pure function in `servers/gtm_mcp/core.py`
2. Test it
3. Wrap it in `server.py` with the right annotation — `readOnlyHint` for reads,
   `destructiveHint` for anything that can mutate a remote system
4. If it can write: `confirm: bool = False`, return a preview with
   `write_performed: False` when unconfirmed, and enforce an allowlist
5. Document it in `docs/tools.md`

## Conventions

Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`,
`test:`). Small, reviewable commits. Never push to `main` — branch and open a PR.
