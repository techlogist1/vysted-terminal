#!/usr/bin/env bash
# Reproducible never-run profiles for a release Vysted Terminal .app (macOS).
#
#   fresh-profile.sh launch <path-to-.app> [profile-dir]  create/reuse a profile dir, launch the
#                                                         binary directly with VYSTED_DATA_DIR
#   fresh-profile.sh wipe <profile-dir>                   delete a launch-created dir (marker-checked)
#                                                         + its namespaced keychain items
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
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

# Canonical absolute path of a dir (created if missing), symlinks resolved like Rust's canonicalize.
canonical_dir() {
  mkdir -p "$1"
  (cd "$1" && pwd -P)
}

MARKER=.vysted-fresh-profile

# Regex-escape a path for pkill -f.
re_escape() {
  printf '%s' "$1" | sed 's/[][\.*^$+?(){}|/]/\\&/g'
}

# wipe's guard: refuse anything that is not a plain, marker-carrying profile dir that launch created.
assert_wipeable() {
  local raw=${1%/} dir home real
  [ -n "$raw" ] || raw=/
  [ -L "$raw" ] && die "refusing to wipe a symlink: $1"
  dir=$(canonical_dir "$raw")
  home=$(cd "$HOME" && pwd -P)
  real="$home/Library/Application Support/com.vysted.terminal"
  [ "$dir" != "/" ] || die "refusing to wipe /"
  [ "$dir" != "$home" ] || die "refusing to wipe \$HOME"
  case "$home/" in "$dir"/*) die "refusing to wipe an ancestor of \$HOME: $dir" ;; esac
  case "$real/" in "$dir"/*) die "refusing to wipe the real app data dir (or a parent): $dir" ;; esac
  case "$dir/" in "$real"/*) die "refusing to wipe inside the real app data dir: $dir" ;; esac
  [ -f "$dir/$MARKER" ] || die "refusing to wipe $dir: no $MARKER marker (not created by 'launch')"
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
      created=0
      [ -e "$3" ] || created=1
      dir=$(canonical_dir "$3")
    else
      created=1
      dir=$(canonical_dir "$(mktemp -d "${TMPDIR:-/tmp}/vysted-profile.XXXXXX")")
    fi
    # Only a dir this script created is wipeable; a reused pre-existing dir stays unmarked.
    if [ "$created" -eq 1 ]; then : >"$dir/$MARKER"; fi
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
    assert_wipeable "$2"
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
    dir=$(canonical_dir "$2")
    # Quit the app first (kill the printed PID); a SIGTERM'd app leaves its sidecars running,
    # so stop any process still bound to this profile dir.
    # llama-server has no --data-dir; it is started with -m <profile>/models/..., so match the path.
    esc=$(re_escape "$dir")
    pkill -f -- "--data-dir $esc( |\$)" 2>/dev/null || true
    pkill -f -- "llama-server.* $esc/" 2>/dev/null || true
    rm -rf "$dir"
    echo "wiped $2 ($deleted keychain item(s) from $service)"
    ;;
  *)
    usage
    ;;
esac
