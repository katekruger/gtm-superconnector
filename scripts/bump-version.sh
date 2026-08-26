#!/bin/bash
# Read .version-bump.json and set every listed version field to the same value.
#
#   scripts/bump-version.sh 0.3.0     set all versions to 0.3.0
#   scripts/bump-version.sh --check   verify they already agree (used by CI)
#
# Fails loudly if a listed path is missing, rather than silently skipping it —
# a version field that quietly stops being updated is the whole failure mode
# this script exists to prevent.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <semver|--check>" >&2
  exit 2
fi

exec python3 - "$1" <<'PY'
import json, re, sys
from pathlib import Path

arg = sys.argv[1]
check = arg == "--check"
if not check and not re.fullmatch(r"\d+\.\d+\.\d+", arg):
    sys.exit(f"not a semver: {arg}")

spec = json.loads(Path(".version-bump.json").read_text())
found, missing = {}, []

def read_json(path, field):
    data = json.loads(path.read_text())
    node = data
    for part in field.split("."):
        node = node[int(part)] if part.isdigit() else node[part]
    return node

def write_json(path, field, value):
    data = json.loads(path.read_text())
    node = data
    parts = field.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if part.isdigit() else node[part]
    last = parts[-1]
    node[int(last) if last.isdigit() else last] = value
    path.write_text(json.dumps(data, indent=2) + "\n")

for entry in spec["files"]:
    path, field = Path(entry["path"]), entry["field"]
    if not path.exists():
        missing.append(str(path))
        continue
    if path.suffix == ".json":
        found[str(path)] = read_json(path, field)
        if not check:
            write_json(path, field, arg)
    else:
        text = path.read_text()
        pattern = {
            ".toml": rf'(?m)^(\s*{re.escape(field.split(".")[-1])}\s*=\s*")([^"]+)(")',
            ".py":   rf'(?m)^(\s*{re.escape(field)}\s*=\s*")([^"]+)(")',
        }[path.suffix]
        match = re.search(pattern, text)
        if not match:
            missing.append(f"{path} (field {field})")
            continue
        found[str(path)] = match.group(2)
        if not check:
            path.write_text(re.sub(pattern, rf"\g<1>{arg}\g<3>", text, count=1))

if missing:
    sys.exit("version-bump: listed but not found:\n  " + "\n  ".join(missing))

if check:
    distinct = set(found.values())
    for path, value in sorted(found.items()):
        print(f"  {value:10} {path}")
    if len(distinct) != 1:
        sys.exit(f"version-bump: versions disagree: {sorted(distinct)}")
    print(f"version-bump: all {len(found)} files agree at {distinct.pop()}")
else:
    print(f"version-bump: set {len(found)} files to {arg}")
PY
