#!/bin/bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$PLUGIN_ROOT/runtime/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "GTM plugin runtime is missing. Reinstall the complete .plugin package." >&2
  exit 1
fi

export PYTHONPATH="$PLUGIN_ROOT/servers"
exec "$PYTHON_BIN" -m gtm_mcp.server
