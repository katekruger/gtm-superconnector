#!/bin/bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_SOURCE="${PYTHON_SOURCE:-/opt/homebrew/bin/python3.12}"

if [[ ! -x "$PYTHON_SOURCE" ]]; then
  echo "Python 3.12 is required. Set PYTHON_SOURCE to its executable path." >&2
  exit 1
fi

"$PYTHON_SOURCE" -m venv --clear "$PLUGIN_ROOT/runtime"
"$PLUGIN_ROOT/runtime/bin/pip" install \
  'fastmcp>=2.12,<3' \
  'httpx>=0.27,<1' \
  'requests>=2.31,<3'

mkdir -p "$PLUGIN_ROOT/dist"
PLUGIN_ROOT="$PLUGIN_ROOT" "$PYTHON_SOURCE" <<'PY'
import os
import stat
import zipfile
from pathlib import Path

root = Path(os.environ["PLUGIN_ROOT"])
output = root / "dist" / "gtm-superconnector.plugin"
skip_dirs = {".git", "dist", "__pycache__", ".pytest_cache"}

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
print(output)
PY
