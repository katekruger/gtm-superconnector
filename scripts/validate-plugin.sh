#!/bin/bash
# Validate both plugin manifests, failing on any error and on any warning we
# have not consciously accepted.
#
# Why not just `--strict`: this repo is both a plugin (installed by users) and a
# project (worked in by contributors). CLAUDE.md serves the second role, but the
# validator only knows about the first, and warns that a root CLAUDE.md ships
# inside the plugin without being loaded as plugin context. That warning is
# correct and we are accepting it deliberately — moving the instructions into a
# skill would ship repo-maintenance guidance to every user of the plugin, which
# is worse.
#
# Any OTHER warning still fails the build, so the gate keeps its teeth.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ACCEPTED="CLAUDE.md at the plugin root is not loaded as project context"
status=0

# The marketplace manifest has no accepted warnings — hold it to --strict.
echo "==> marketplace.json (--strict)"
claude plugin validate .claude-plugin/marketplace.json --strict

echo "==> plugin.json"
output="$(claude plugin validate .claude-plugin/plugin.json 2>&1)" || status=$?
echo "$output"

if [[ $status -ne 0 ]]; then
  echo "FAIL: plugin.json has validation errors." >&2
  exit 1
fi

unexpected="$(echo "$output" | grep -E '^\s+❯' | grep -vF "$ACCEPTED" || true)"
if [[ -n "$unexpected" ]]; then
  echo "FAIL: unaccepted warning(s):" >&2
  echo "$unexpected" >&2
  exit 1
fi

echo "OK: both manifests valid; only the accepted CLAUDE.md warning present."
