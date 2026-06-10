#!/bin/bash
# Cargo RUNNER for macOS dev builds: sign-then-exec.
#
# `tauri dev` launches the debug binary via `cargo run`, and cargo hands the
# freshly built executable to this runner BEFORE it ever runs. That is the only
# reliable signing point: once the process is running, `codesign --force` on
# its file fails (text file busy), which is why the old package.json mtime
# watcher silently never signed anything — every dev session ran ad-hoc and the
# keychain ACL re-prompted on each rebuild.
#
# Signing here gives every dev binary the SAME designated requirement
# (identifier com.vysted.terminal + the "Vysted Terminal Dev Signing" cert), so
# one "Always Allow" keychain grant and one TCC/automation grant persist across
# rebuilds forever. Wired via src-tauri/.cargo/config.toml [target.*.runner].
#
# Pass-through behavior (never breaks a build):
#   - identity missing (CI, fresh machine)  -> exec unsigned
#   - VYSTED_SKIP_DEV_SIGN=1                -> exec unsigned
#   - codesign fails for any reason         -> exec anyway (warn on stderr)
#   - cargo test binaries also come through -> signed the same way (harmless)
set -u

IDENTITY="Vysted Terminal Dev Signing"
BIN="${1:-}"

if [ -n "$BIN" ] && [ -x "$BIN" ] && [ -z "${VYSTED_SKIP_DEV_SIGN:-}" ]; then
  if security find-identity -v -p codesigning 2>/dev/null | grep -q "$IDENTITY"; then
    if ! codesign --force --sign "$IDENTITY" --identifier com.vysted.terminal "$BIN" 2>/dev/null; then
      echo "[dev-sign] codesign failed for $BIN — running unsigned" >&2
    fi
  fi
fi

exec "$@"
