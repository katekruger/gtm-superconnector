# Instructions for agents working on this repository

This file is for an agent modifying **this repo**. It is not documentation for
users of the plugin — that is [README.md](README.md) and [docs/](docs/).

`CLAUDE.md` is a one-line pointer (`@AGENTS.md`) to this file, not a second
copy. If you find yourself editing `CLAUDE.md` to explain something, put the
explanation here instead.

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
| `docs/` | Reference documentation for plugin users |
| `docs/decisions/` | ADRs (MADR 4.0.0). Permanent, numbered, never renumbered |
| `tests/` | Mirrors `servers/gtm_mcp/core.py` |

New code goes in the module that matches its I/O shape, not wherever is
convenient: pure logic into `core.py` ([Rule 1](#rules-that-are-not-negotiable)),
anything that talks to n8n into `n8n.py`, anything that talks to Clay or the CRM
stays behind their MCP connectors (this repo never calls those APIs directly —
see [`servers/` in detail](#servers-in-detail)), and a new email-resolution
strategy into its own module under `servers/contact_tiers/`, one tier lower than
whatever it depends on.

## Commands

```bash
pytest -q                                 # tests
ruff check servers tests                  # lint
python scripts/check-skills.py            # skill frontmatter rules
./scripts/bump-version.sh --check         # version agreement
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
./scripts/validate-plugin.sh              # runs both validate calls above with the one accepted warning
```

Requires Python 3.12+. `scripts/run-gtm-server.sh` picks up `.venv/bin/python`
automatically; override with `GTM_PYTHON`.

Every command above was re-run from a clean clone against Python 3.12.14 while
writing this file (`pytest`: 23 passed; `ruff`: all checks passed;
`check-skills.py`: 5 skills conform; `bump-version.sh --check`: all 4 files
agree; both `plugin validate --strict` calls: pass, with the one warning
documented in [ADR 0001](docs/decisions/0001-accept-the-root-claude-md-warning.md)).
`claude plugin validate --strict` requires a current `@anthropic-ai/claude-code`
CLI (`npm install -g @anthropic-ai/claude-code`) — an older locally-installed
`claude` binary may lack `--strict` entirely or reject `displayName` as
unrecognized; that is a stale-CLI problem, not a manifest problem. CI always
installs fresh, so it never hits this.

### Dependencies: `requirements*.txt` is authoritative, `pyproject.toml` mirrors it

This repo declares dependencies in two places and they must agree, but they do
not serve the same purpose:

- **`requirements.txt` / `requirements-dev.txt` are authoritative.** CI
  installs from `requirements-dev.txt` (`.github/workflows/ci.yml`), the local
  setup in [`docs/development.md`](docs/development.md) and
  [`contributing.md`](contributing.md) installs from it, and
  `scripts/build-plugin.sh` installs the sealed runtime from
  `requirements.txt`. If you change a runtime dependency, change it here
  first.
- **`pyproject.toml`'s `dependencies` and `[project.optional-dependencies]
  dev` exist for packaging metadata** — `[build-system]` / `[tool.setuptools]`
  make the package `pip install`-able by name, and `[tool.pytest.ini_options]`
  / `[tool.ruff]` configure those tools. Nothing in this repo's CI or docs runs
  `pip install .`; the version ranges under `dependencies` must simply be kept
  identical to `requirements.txt` by hand. There is no automated check for
  this — when you touch one, check the other.

## Servers, in detail

Two independent Python packages live under `servers/`, and neither imports
the other:

- **`servers/gtm_mcp/`** is the MCP server itself: `server.py` (thin — tool
  registration and argument marshalling only), `core.py` (every pure
  function — see [Rule 1](#rules-that-are-not-negotiable)), and `n8n.py`
  (`N8nOps`, the only module that performs an authenticated write and the
  only place the allowlist is enforced). It is launched by
  `scripts/run-gtm-server.sh` as the `gtm` entry in `.mcp.json`, over stdio.
  It only runs where a local plugin MCP server can run — see
  [`docs/architecture.md`](docs/architecture.md)'s availability boundary.
- **`servers/contact_tiers/`** is a standalone four-tier email resolver
  (`git_emails.py` → `patterns.py` → `verify.py` → `pdl.py`, in that cost
  order) with no dependency on `gtm_mcp` beyond the standard library plus
  `requests`. `gtm_mcp/server.py` imports it via `CONTACT_TIERS_PATH`; nothing
  else does. It is written to be liftable into another pipeline without
  dragging the MCP server along — keep it that way.

Registration is entirely in `.mcp.json`: `clay` and `crm` are remote HTTP
connectors (`crm`'s URL is the user-supplied `${user_config.crm_mcp_url}`,
absent by default), `gtm` is the local one, launched via
`${CLAUDE_PLUGIN_ROOT}/scripts/run-gtm-server.sh` with `CONTACT_TIERS_PATH`,
`CLAY_FUNCTION_POLICY_PATH`, and `N8N_BASE_URL` passed as env. A new local
server would be a fourth entry here, its own launcher script, and its own
package under `servers/` — this repo has never needed more than one local
server and there is no shared harness to plug into; write the launcher by
hand.

## Skills, in detail

Each `skills/<name>/SKILL.md` is a procedure — an ordered list of tool calls
with explicit stopping points, not a prompt. `scripts/check-skills.py` (run in
CI) is the authority on frontmatter shape; the rules below are why it checks
what it checks:

- Frontmatter is `description` (required) and `name` (optional). The
  published skill spec treats the **directory name** as the invocation name —
  `name`, where present, must match the directory exactly, but do not add
  `name` to a skill that lacks it and do not remove it from one that has it.
- `description` **must open with "Use when"**, stay third person, and list the
  actual phrasings a user types — never a summary of the procedure. A
  description that summarizes the workflow gets followed *instead of* the
  skill body; `check-skills.py` calls this "the most damaging skill defect"
  and it is the reason the check exists.
- Body under 500 words, numbered imperative steps. Heavier material — scoring
  criteria, approval-gate tables — goes in `references/<topic>.md`, linked
  from the body, and every such relative link must resolve (also checked).
- **A skill that can cause a write makes the approval gate its own numbered
  step.** Every existing skill does this; see
  [`skills/outreach-builder/references/approval-gates.md`](skills/outreach-builder/references/approval-gates.md)
  for the canonical example.
- **Renaming a skill's directory is a breaking change** — it changes the
  invocation name. Avoid it; if unavoidable, say so in `CHANGELOG.md`.

Adding a skill: create the directory, write `SKILL.md`, run
`python scripts/check-skills.py`, then add it to the table in `README.md` and
a section in `docs/skills.md`. Nothing auto-discovers skills into those two
docs — do both by hand or the skill is invisible to a plugin user reading
either.

## Config, in detail

`config/` holds **example** policy, not runtime config: `clay-functions.example.json`
is the only tracked file, documenting the shape `clay_list_approved_functions`
expects. The real file, `config/clay-functions.json`, is gitignored — it is
organization-specific approval/cost policy (which Clay Functions may run,
their row caps, their credit cost) and must never be committed. `.env` is the
other gitignored, must-never-commit file; both are listed in `.gitignore`
under "Secrets and local config". If `config/clay-functions.json` is absent,
the tool reports `configured: false` rather than treating absence as blanket
approval — do not change that fallback to anything more permissive.

## Relationship to the rest of the portfolio

This plugin does not depend on or share code with any other MCP server in the
portfolio (e.g. `segment-mcp`). The `clay` and `crm` MCP connectors it talks to
are external services reached over HTTP, not other repos in this account. The
only portfolio-wide conventions this repo follows are the ones in this file and
in CI (Conventional Commits, ADRs in `docs/decisions/`, SHA-pinned Actions);
its Python floor (3.12) and its use of `requirements*.txt` alongside
`pyproject.toml` are both deliberately *not* aligned with sibling repos — see
[Python floor](#python-floor) below.

## What this repo deliberately does not do

- **No PyPI package, no `pip install gtm-superconnector`.** Distribution is a
  Claude Code plugin only, installed via the self-marketplace
  (`.claude-plugin/marketplace.json`, `"source": "./"`) or a built
  `dist/gtm-superconnector.plugin` archive attached to a GitHub Release. There
  is no Trusted Publishing setup, no PyPI environment, and none is planned —
  do not add release automation that assumes one.
- **No default CRM endpoint.** `crm_mcp_url` is always user-supplied
  `userConfig`; the plugin ships with no maintainer-controlled host anywhere.
- **No tool executes a Clay Function.** `clay_list_approved_functions` reads
  and reports local policy only; execution goes through the official Clay MCP
  connector, never through this repo's code.
- **No write path without both guards.** See
  [Rule 4](#rules-that-are-not-negotiable) — there is deliberately no
  "trusted caller" bypass.
- **No auto-discovery of skills or tools into documentation.** `README.md`'s
  skill table and `docs/skills.md` / `docs/tools.md` are hand-maintained; nothing
  generates them from `skills/` or `server.py`.

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

**6. Uncertainty survives the return trip.** Report missing fields as missing.
Do not let a tool return a confident-looking value it cannot support.

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
entry. CI fails if they disagree. `pyproject.toml`'s version field is included
in that list — bumping it there does not make it the source of truth for
dependencies (see [Dependencies](#dependencies-requirementstxt-is-authoritative-pyprojecttoml-mirrors-it)
above), only for the release number.

## Adding a tool

1. Write the logic as a pure function in `servers/gtm_mcp/core.py`
2. Test it
3. Wrap it in `server.py` with the right annotation — `readOnlyHint` for reads,
   `destructiveHint` for anything that can mutate a remote system
4. If it can write: `confirm: bool = False`, return a preview with
   `write_performed: False` when unconfirmed, and enforce an allowlist
5. Document it in `docs/tools.md`

## Release process

1. `./scripts/bump-version.sh <semver>` — updates all four version-carrying
   files in one step; never edit them by hand
2. Add a `CHANGELOG.md` entry under a new version heading
3. `./scripts/build-plugin.sh` — builds the sealed runtime and
   `dist/gtm-superconnector.plugin`, failing loudly on any missing runtime
   dependency rather than deferring the failure to an MCP handshake inside
   Claude
4. `git tag v<semver> && git push --tags`
5. Attach `dist/gtm-superconnector.plugin` to the GitHub Release

There is no PyPI publish step and no MCP Registry publish step — see
[What this repo deliberately does not do](#what-this-repo-deliberately-does-not-do).

## Before opening a PR

- [ ] `pytest -q`, `ruff check servers tests`, `python scripts/check-skills.py`,
      and `./scripts/bump-version.sh --check` all pass locally
- [ ] `./scripts/validate-plugin.sh` passes (needs a current `claude` CLI —
      see [Commands](#commands))
- [ ] A touched safety rule has a new or updated test ([Rule 2](#rules-that-are-not-negotiable))
- [ ] `docs/tools.md` updated if a tool signature or behavior changed
- [ ] `CHANGELOG.md` has an entry under `Unreleased`
- [ ] One concern per PR; say what you changed and why, and note anything you
      deliberately did not do

## What gets rejected

- Direct commits to `main` — branch and open a PR, even for a typo
- A write tool with only one of the two guards in [Rule 4](#rules-that-are-not-negotiable)
- A safety rule changed without a corresponding test ([Rule 2](#rules-that-are-not-negotiable))
- `core.py` gaining any I/O, filesystem access, or un-parameterized wall-clock read
- A hardcoded personal endpoint, credential, or default CRM host
- A skill description that summarizes the procedure instead of stating triggers
- Renaming a skill directory without flagging it as breaking in `CHANGELOG.md`
- Reformatting unrelated code

## Conventions

Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`,
`test:`). Small, reviewable commits. Never push to `main` — branch and open a PR.

---

`AGENTS.md` is a real file, not a symlink to something else, because symlinks
break when a plugin is installed into a different directory. `CLAUDE.md`
carries the one-line pointer `@AGENTS.md` instead.
