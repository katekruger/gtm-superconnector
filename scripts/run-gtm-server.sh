#!/bin/bash
# Launch the bundled GTM MCP server.
#
# Resolution order for the interpreter:
#   1. $GTM_PYTHON, if set        — explicit override
#   2. <plugin>/runtime/bin/python — the sealed runtime built by build-plugin.sh
#   3. <plugin>/.venv/bin/python   — a local development virtualenv
#
# A packaged .plugin always ships (2). Running from a git clone normally uses (3).
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for candidate in "${GTM_PYTHON:-}" "$PLUGIN_ROOT/runtime/bin/python" "$PLUGIN_ROOT/.venv/bin/python"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "${PYTHON_BIN:-}" ]]; then
  cat >&2 <<'MSG'
No Python runtime found for the GTM MCP server.

If you installed the packaged plugin, the bundled runtime is missing or
corrupt — reinstall the complete .plugin file.

If you are running from a git clone, create a development environment first:

    python3.12 -m venv .venv
    .venv/bin/pip install -r requirements.txt

Or point GTM_PYTHON at an interpreter that already has the dependencies.
MSG
  exit 1
fi

export PYTHONPATH="$PLUGIN_ROOT/servers${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN" -m gtm_mcp.server
