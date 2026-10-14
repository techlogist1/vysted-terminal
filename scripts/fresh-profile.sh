#!/usr/bin/env bash
# Reproducible never-run profiles for a release Vysted Terminal .app (macOS).
#
#   fresh-profile.sh launch <path-to-.app> [profile-dir]  create/reuse a profile dir, launch the
#                                                         binary directly with VYSTED_DATA_DIR
#   fresh-profile.sh wipe <profile-dir>                   delete the dir + its namespaced keychain items
#   fresh-profile.sh service <profile-dir>                print the profile's keychain service
#
# The service derivation matches `service_for` in src-tauri/src/keychain.rs (a test asserts it):
# "vysted-terminal.profile." + first 12 hex of sha256(canonical absolute dir). The default
# service "vysted-terminal" (the operator's real profile) is never touched.
set -euo pipefail

die() {
  echo "fresh-profile: $*" >&2
  exit 1
}

usage() {
  sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

# Canonical absolute path of a dir (created if missing), symlinks resolved like Rust's canonicalize.
canonical_dir() {
  mkdir -p "$1"
  (cd "$1" && pwd -P)
}

service_name() {
  local dir hex
  dir=$(canonical_dir "$1")
  hex=$(printf '%s' "$dir" | shasum -a 256 | cut -c1-12)
  printf 'vysted-terminal.profile.%s\n' "$hex"
}

cmd=${1:-}
case "$cmd" in
  service)
    [ $# -eq 2 ] || usage
    service_name "$2"
    ;;
  launch)
    [ $# -ge 2 ] && [ $# -le 3 ] || usage
    app=${2%/}
    bin="$app/Contents/MacOS/vysted-terminal"
    [ -x "$bin" ] || die "no executable at $bin"
    if [ $# -eq 3 ]; then
      dir=$(canonical_dir "$3")
    else
      dir=$(canonical_dir "$(mktemp -d "${TMPDIR:-/tmp}/vysted-profile.XXXXXX")")
    fi
    # Launched directly, not via `open`, which drops the environment.
    VYSTED_DATA_DIR="$dir" nohup "$bin" >"$dir/launch.log" 2>&1 &
    pid=$!
    echo "profile_dir=$dir"
    echo "service=$(service_name "$dir")"
    echo "pid=$pid"
    echo "log=$dir/launch.log"
    ;;
  wipe)
    [ $# -eq 2 ] || usage
    [ -d "$2" ] || die "no such profile dir: $2"
    service=$(service_name "$2")
    case "$service" in
      vysted-terminal.profile.????????????) ;;
      *) die "refusing to wipe unexpected service '$service'" ;;
    esac
    deleted=0
    while security delete-generic-password -s "$service" >/dev/null 2>&1; do
      deleted=$((deleted + 1))
      [ "$deleted" -lt 1000 ] || die "keychain delete loop did not terminate"
    done
    rm -rf "$(canonical_dir "$2")"
    echo "wiped $2 ($deleted keychain item(s) from $service)"
    ;;
  *)
    usage
    ;;
esac
