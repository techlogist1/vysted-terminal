#!/bin/sh
# Self-check for scripts/git-hooks/pre-push (vysted-pushguard).
#
# Builds a throwaway repo + bare remote under a temp dir, installs the hook, and
# asserts what it must let through and what it must refuse. Touches nothing in
# this clone and never contacts a network remote. Exits non-zero on any failure.
#
#   sh scripts/git-hooks/test-pre-push.sh
set -u
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
hook=$here/pre-push
registrar=$(CDPATH= cd "$here/../rig" && pwd)/register_capture.py

tmp=$(mktemp -d "${TMPDIR:-/tmp}/pushguard-test.XXXXXX")
trap 'rm -rf "$tmp"' EXIT INT TERM

rc=0
ok() { echo "PASS  $1"; }
no() {
  echo "FAIL  $1"
  rc=1
}

git init --quiet --bare "$tmp/remote.git"
git init --quiet "$tmp/work"
cd "$tmp/work" || exit 2
git config user.email pushguard@test.invalid
git config user.name "pushguard test"
git config commit.gpgsign false
git config core.hooksPath .git/hooks
git config advice.defaultBranchName false
git remote add proofremote "$tmp/remote.git"
cp "$hook" .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# The repo under test carries the hook source and the registrar, so a green run
# also proves the patterns do not match their own definitions.
mkdir -p scripts/git-hooks scripts/rig docs/redesign/verification/r15/stage0
cp "$hook" scripts/git-hooks/pre-push
cp "$registrar" scripts/rig/register_capture.py
: >docs/redesign/verification/r15/CAPTURES.jsonl
echo "baseline" >README.md
git add -A
git commit --quiet -m "baseline"
branch=$(git rev-parse --abbrev-ref HEAD)

try() { # try <label> <expect: allow|block> [grep-for]
  label=$1
  expect=$2
  want=${3:-}
  out=$(git push proofremote "$branch" 2>&1)
  code=$?
  if [ "$expect" = allow ] && [ $code -ne 0 ]; then
    no "$label (expected allow, got block)"
    echo "$out" | sed 's/^/        /'
    return
  fi
  if [ "$expect" = block ] && [ $code -eq 0 ]; then
    no "$label (expected block, push succeeded)"
    return
  fi
  if [ -n "$want" ] && ! echo "$out" | grep -q "$want"; then
    no "$label (blocked, but output lacks '$want')"
    echo "$out" | sed 's/^/        /'
    return
  fi
  ok "$label"
}

# 1. Baseline: hook source + registrar + clean text push cleanly.
try "clean baseline push (no self-trip on the pattern table)" allow

# 2. A planted fake key blocks. Built at runtime so no key-shaped literal ever
#    lands in the real repo.
fake="sk-or-v1-$(python3 -c 'print("0123456789abcdef" * 4)')"
printf 'OPENROUTER_KEY = "%s"\n' "$fake" >sidecar_config.py
git add sidecar_config.py
git commit --quiet -m "plant fake key"
try "planted fake OpenRouter key is refused" block openrouter-key

# 2b. The hook must not echo the secret it found.
out=$(git push proofremote "$branch" 2>&1)
if echo "$out" | grep -q "$fake"; then
  no "hook printed the matched secret value"
else
  ok "hook never prints the matched value"
fi
git reset --quiet --hard HEAD~1

# 3. The allow-marker exempts a deliberate fixture line.
printf 'FIXTURE = "%s"  # pushguard:allow\n' "$fake" >fixture.py
git add fixture.py
git commit --quiet -m "allow-markered fixture"
try "allow-marker exempts a fixture line" allow

# 4. A secret-bearing filename blocks even with harmless content.
mkdir -p keys
echo "placeholder" >keys/server.pem
git add keys/server.pem
git commit --quiet -m "add pem"
try "added *.pem is refused" block secret-bearing-filename
git reset --quiet --hard HEAD~1

# 5. An unregistered r15 capture blocks and is named.
shot=docs/redesign/verification/r15/stage0/shot.png
printf 'fake-png-bytes-for-test\n' >"$shot"
git add "$shot"
git commit --quiet -m "add capture"
try "unregistered r15 capture is refused" block "stage0/shot.png"

# 6. Registering it unblocks the same push.
python3 scripts/rig/register_capture.py "$shot" --tool test-harness \
  --frontmost-app vysted-terminal --window-owner vysted-terminal >/dev/null
git add docs/redesign/verification/r15/CAPTURES.jsonl
git commit --quiet -m "register capture"
try "registered r15 capture is allowed" allow

# 7. Registering the same bytes twice adds no second ledger line.
before=$(wc -l <docs/redesign/verification/r15/CAPTURES.jsonl)
python3 scripts/rig/register_capture.py "$shot" --tool test-harness >/dev/null
after=$(wc -l <docs/redesign/verification/r15/CAPTURES.jsonl)
if [ "$before" = "$after" ]; then ok "register_capture is idempotent"; else no "register_capture duplicated an entry"; fi

# 8. An image OUTSIDE the r15 tree is not gated (history already has many).
mkdir -p docs/screenshots
printf 'fake-png\n' >docs/screenshots/other.png
git add docs/screenshots/other.png
git commit --quiet -m "unrelated image"
try "image outside r15 is not gated" allow

if [ $rc -eq 0 ]; then echo "pushguard: all checks passed"; else echo "pushguard: FAILURES"; fi
exit $rc
