---
status: accepted
date: 2026-08-31
decision-makers: Kate Kruger
---

# Accept the plugin validator's root-`CLAUDE.md` warning instead of moving repo instructions into a skill

## Context and Problem Statement

This repo is both a Claude Code plugin (installed by users) and a project
(worked in by contributors). Contributor-facing instructions live in
`AGENTS.md`, with `CLAUDE.md` a one-line `@AGENTS.md` pointer so an agent
session started with either file loads the same content.

`claude plugin validate --strict` warns that a `CLAUDE.md` at the plugin root
is not loaded as project context when the plugin is installed, and suggests
shipping a skill instead. Held to `--strict` uncritically, that warning fails
CI. The question is whether to silence it by moving the pointer, or to keep
`scripts/validate-plugin.sh`'s existing carve-out that accepts this one
specific warning and fails the build on any other.

## Considered Options

* Accept the warning explicitly, as `scripts/validate-plugin.sh` already does
* Move the `@AGENTS.md` pointer (or the instructions themselves) into a skill
  under `skills/`, so the validator has nothing to warn about
* Drop `--strict` entirely for `plugin.json` and lose the gate's teeth

## Decision Outcome

Chosen option: "Accept the warning explicitly." `scripts/validate-plugin.sh`
holds an `ACCEPTED` allowlist of exactly this warning string, runs
`claude plugin validate .claude-plugin/plugin.json` without `--strict`, greps
its output, and fails the build on any warning that is not this one. The
marketplace manifest has no accepted warnings and is still held to `--strict`
directly, so the carve-out is scoped to the one manifest where it applies.

### Consequences

* Good, because a skill exists to be *selected at a moment the plugin decides
  is relevant*, and would ship repo-maintenance guidance (version bumping,
  test conventions, the write-tool guard rules) to every installer of the
  plugin, with no way to suppress it for users who are not contributors.
* Good, because the gate still fails on any warning this repo has not
  consciously reviewed — the allowlist is a single exact string, not a
  category.
* Bad, because a future, unrelated validator warning added to `plugin.json`
  checks would need `scripts/validate-plugin.sh` to be re-read carefully: the
  grep only excludes the one accepted line, so a second warning would
  correctly fail the build, but a maintainer skimming a red CI run needs to
  open the script to understand why one specific warning is fine and the rest
  are not.
* Neutral, because this decision is specific to the `plugin.json` validation
  step; it says nothing about whether some other repo in the portfolio should
  make the same call for its own root `CLAUDE.md` (most others simply do not
  ship one with content — see `AGENTS.md`'s Python-floor and dependency-file
  notes for other repo-specific choices).
