#!/bin/sh
# Install the vysted-head-guard reference-transaction hook into this clone's
# .git/hooks, and arm it for the current branch. Idempotent. Run once per clone
# (and re-run if you switch the branch you want pinned):
#   sh scripts/install-head-guard.sh [protected-branch]
#
# It pins the MAIN worktree's HEAD to the protected branch so a stray teammate
# git op (running in the shared checkout because the agent shell's cwd resets)
# cannot flip it onto a stale branch. See scripts/git-hooks/reference-transaction.
set -e
common_dir=$(git rev-parse --git-common-dir)
prot=${1:-$(git rev-parse --abbrev-ref HEAD)}
src=$(CDPATH= cd "$(dirname "$0")" && pwd)/git-hooks/reference-transaction
mkdir -p "$common_dir/hooks"
cp "$src" "$common_dir/hooks/reference-transaction"
chmod +x "$common_dir/hooks/reference-transaction"
printf '%s' "$prot" > "$common_dir/vysted-protected-branch"
echo "vysted-head-guard installed → $common_dir/hooks/reference-transaction"
echo "main worktree HEAD pinned to: $prot"
