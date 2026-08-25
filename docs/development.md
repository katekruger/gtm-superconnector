# Development

## Setup

Requires **Python 3.12+**. The server uses PEP 604 union syntax (`str | None`) in signatures that FastMCP resolves at runtime to build tool schemas, so older interpreters will fail at import.

```bash
git clone https://github.com/katekruger/gtmplugin.git
cd gtmplugin
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

`scripts/run-gtm-server.sh` finds `.venv/bin/python` automatically. Override with `GTM_PYTHON` if your interpreter lives elsewhere.

## Testing

```bash
.venv/bin/pytest -q
```

`pyproject.toml` sets `pythonpath = ["servers"]`, so tests import `gtm_mcp` without an install step.

The suite covers `core.py` — the pure layer. That is deliberate: `core.py` has no I/O, no network, and no clock except an injected `as_of`, which makes every safety property directly assertable.

Three groups:

| File | Asserts |
|---|---|
| `test_email_classification.py` | The send-ready rule, including that unknown statuses fail closed |
| `test_scoring.py` | Determinism, ordering, and that absent evidence is not negative evidence |
| `test_safety_invariants.py` | `write_performed: false`, paused previews, bounds enforcement, conflict reporting |

**Adding a safety rule means adding a test.** A rule documented in prose is a suggestion; a rule pinned by a test is a rule.

## Linting

```bash
.venv/bin/ruff check servers tests
```

`line-length` is 200 with `E501` ignored. `core.py` favors dense single-expression returns, and reflowing them would hurt readability more than it helps.

## Architecture rules

Two conventions keep the codebase testable:

**1. `core.py` stays pure.** No network, no filesystem, no `datetime.now()` without an `as_of` escape hatch. Anything needing I/O goes in `n8n.py`, `server.py`, or `contact_tiers/`.

**2. `server.py` stays thin.** Tool definitions handle argument marshalling and delegate. Logic worth testing belongs in `core.py`, where it can be tested without an MCP client.

## Adding a tool

1. Write the logic as a pure function in `core.py`
2. Test it
3. Add the `@mcp.tool` wrapper in `server.py` with the correct annotation:
   - `annotations={"readOnlyHint": True}` — reads and computes only
   - `annotations={"destructiveHint": True}` — can mutate a remote system
4. If it can write: require `confirm: bool = False`, return a preview with `write_performed: False` when unconfirmed, and enforce an allowlist
5. Document it in [`docs/tools.md`](tools.md)

The annotation is not decoration — clients surface it before the call happens.

## Building a release

```bash
./scripts/build-plugin.sh
```

The script discovers a 3.12+ interpreter (override with `PYTHON_SOURCE`), builds a sealed venv at `runtime/`, installs from `requirements.txt`, verifies every dependency imports, confirms the server itself imports, then writes `dist/gtm-superconnector.plugin`.

The import checks exist because a missing runtime dependency otherwise surfaces as an opaque MCP handshake failure inside Claude. Failing at build time is considerably cheaper.

Excluded from the archive: `.git`, `.github`, `.venv`, `dist`, `docs`, `tests`, and every cache directory. The archive is rejected if it contains symlinks or corrupt entries.

## Releasing

1. Update `version` in `pyproject.toml` and `.claude-plugin/plugin.json`, and `__version__` in `servers/gtm_mcp/__init__.py` — keep all three in sync
2. Add a `CHANGELOG.md` entry
3. `./scripts/build-plugin.sh`
4. Tag and push: `git tag v0.2.0 && git push --tags`
5. Attach `dist/gtm-superconnector.plugin` to the GitHub release

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every push to `main` and every PR: lint, server import check, JSON manifest validation, shell syntax check, and the test suite.

The manifest validation matters more than it looks — a malformed `.mcp.json` breaks the plugin at load time with an error that is hard to trace back to a stray comma.
