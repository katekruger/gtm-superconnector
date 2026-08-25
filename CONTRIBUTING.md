# Contributing

Thanks for taking a look. This is a small, opinionated codebase — the constraints below are what keep it honest.

## Before you start

Open an issue for anything beyond a bug fix or docs correction. The plugin has a deliberate stance on data quality and approval gates, and a change that loosens one is a design conversation, not a patch.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

Full detail in [docs/development.md](docs/development.md).

## The rules that matter

**1. `core.py` stays pure.** No network, no filesystem, no wall-clock reads without an `as_of` parameter. This is what makes the safety properties testable.

**2. A new safety rule needs a test.** If your change adds or modifies a guarantee — send-readiness, an approval gate, a bound — pin it in `tests/`.

**3. Nothing fails open.** Unknown input degrades to the most conservative state. `classify_email` treats an unrecognized status as `unresolved`, never `verified`. Preserve that shape.

**4. Write tools need two independent guards.** A `confirm` flag and a configuration-level allowlist. One is not enough.

**5. Uncertainty survives the return trip.** Report missing fields as missing. Do not let a tool return a confident-looking value it cannot support.

## Pull requests

- One concern per PR
- `ruff check servers tests` and `pytest -q` pass
- Update [docs/tools.md](docs/tools.md) if you changed a tool signature or behavior
- Add a `CHANGELOG.md` entry under `Unreleased`
- Say what you changed and why; note anything you deliberately did not do

## Reporting bugs

Include the Python version, whether you are running from a clone or a built `.plugin`, the tool involved, and what you expected versus what happened. Redact keys.

For anything security-sensitive — a credential leak path, a way to bypass an approval gate — please open a private advisory rather than a public issue.
