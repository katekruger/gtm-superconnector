#!/bin/bash
# Build a distributable .plugin archive with a sealed Python runtime.
#
# Requires Python 3.12+. Set PYTHON_SOURCE to override interpreter discovery.
# Output: dist/gtm-superconnector.plugin
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Discover a suitable interpreter instead of hardcoding one install layout.
find_python() {
  if [[ -n "${PYTHON_SOURCE:-}" ]]; then
    echo "$PYTHON_SOURCE"
    return
  fi
  for name in python3.13 python3.12 python3; do
    local path
    path="$(command -v "$name" 2>/dev/null || true)"
    if [[ -n "$path" ]] && "$path" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
      echo "$path"
      return
    fi
  done
}

PYTHON_SOURCE="$(find_python)"

if [[ -z "$PYTHON_SOURCE" ]]; then
  echo "Python 3.12 or newer is required but was not found on PATH." >&2
  echo "Install it (e.g. 'brew install python@3.12') or set PYTHON_SOURCE to its path." >&2
  exit 1
fi

echo "Building with $PYTHON_SOURCE ($("$PYTHON_SOURCE" --version))"

"$PYTHON_SOURCE" -m venv --clear "$PLUGIN_ROOT/runtime"
"$PLUGIN_ROOT/runtime/bin/pip" install --quiet --upgrade pip
"$PLUGIN_ROOT/runtime/bin/pip" install --quiet -r "$PLUGIN_ROOT/requirements.txt"

# Fail loudly here rather than at MCP handshake time inside Claude.
"$PLUGIN_ROOT/runtime/bin/python" - <<'CHECK'
import importlib
for module in ("fastmcp", "httpx", "requests", "dotenv"):
    importlib.import_module(module)
print("runtime dependency check passed")
CHECK

PYTHONPATH="$PLUGIN_ROOT/servers" "$PLUGIN_ROOT/runtime/bin/python" -c 'import gtm_mcp.server; print("server imports cleanly")'

mkdir -p "$PLUGIN_ROOT/dist"
PLUGIN_ROOT="$PLUGIN_ROOT" "$PYTHON_SOURCE" <<'PY'
import os
import stat
import zipfile
from pathlib import Path

root = Path(os.environ["PLUGIN_ROOT"])
output = root / "dist" / "gtm-superconnector.plugin"
skip_dirs = {".git", ".github", ".venv", "dist", "docs", "tests", "__pycache__", ".pytest_cache", ".ruff_cache"}

with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in skip_dirs for part in relative.parts):
            continue
        if path.name == ".DS_Store" or path.suffix in {".pyc", ".plugin"} or path.is_dir():
            continue
        archive.write(path, relative)

with zipfile.ZipFile(output) as archive:
    links = [item.filename for item in archive.infolist() if stat.S_ISLNK(item.external_attr >> 16)]
    broken = archive.testzip()
if links or broken:
    raise SystemExit(f"Invalid archive: symbolic_links={links}, broken={broken}")
print(f"{output} ({output.stat().st_size // 1024} KB)")
PY
