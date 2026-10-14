#!/bin/sh
# Install every vysted git hook into this clone's shared hook dir. Idempotent —
# run once per clone, and re-run after editing a hook:
#   sh scripts/install-git-hooks.sh [protected-branch]
#
#   reference-transaction  vysted-head-guard   (scripts/install-head-guard.sh)
#   pre-push               vysted-pushguard    (scripts/git-hooks/pre-push)
#
# The protected branch is only (re-)armed when it is not already set, or when
# given explicitly — so running this from a teammate worktree cannot re-pin the
# main worktree's HEAD onto the teammate's branch.
set -e
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
common_dir=$(git rev-parse --git-common-dir)

prot=${1:-$(cat "$common_dir/vysted-protected-branch" 2>/dev/null || true)}
if [ -n "$prot" ]; then
  sh "$here/install-head-guard.sh" "$prot"
else
  sh "$here/install-head-guard.sh"
fi

mkdir -p "$common_dir/hooks"
cp "$here/git-hooks/pre-push" "$common_dir/hooks/pre-push"
chmod +x "$common_dir/hooks/pre-push"
echo "vysted-pushguard installed → $common_dir/hooks/pre-push"
