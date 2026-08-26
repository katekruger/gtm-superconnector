## What changed

## Why

## How it was tested
<!-- Paste actual command output, not a description of it. -->

```
```

## Checklist

- [ ] `pytest -q` passes
- [ ] `ruff check servers tests` passes
- [ ] `python scripts/check-skills.py` passes
- [ ] `./scripts/bump-version.sh --check` passes
- [ ] `claude plugin validate .claude-plugin/plugin.json --strict` passes
- [ ] Docs updated (`docs/tools.md` if a tool signature changed)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Version bumped if this is a release
- [ ] If a safety rule changed, a test pins the new behavior
- [ ] If a skill was renamed, it is flagged as a breaking change
