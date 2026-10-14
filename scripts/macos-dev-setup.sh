#!/usr/bin/env bash
# scripts/macos-dev-setup.sh
#
# Idempotent verification and guidance for macOS dev code-signing setup.
# Checks that the stable self-signed dev signing identity is present and the
# partition list is configured. Prints clear remediation steps if not.
#
# Run once per machine after creating the certificate:
#   bash scripts/macos-dev-setup.sh
#
# Non-Darwin systems exit cleanly — this script is macOS-only.
# See docs/redesign/KEYCHAIN_DEV_SIGNING.md for the full runbook.

set -euo pipefail

DEV_IDENTITY="Vysted Terminal Dev Signing"

# ── Platform guard ───────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macos-dev-setup: non-Darwin platform detected — nothing to do."
  exit 0
fi

echo ""
echo "=== Vysted Terminal — macOS dev signing setup check ==="
echo ""

ERRORS=0

# ── 1. Check codesign is available ───────────────────────────────────────────
if ! command -v codesign &>/dev/null; then
  echo "[FAIL] codesign not found. Install Xcode Command Line Tools:"
  echo "       xcode-select --install"
  ERRORS=$((ERRORS + 1))
else
  echo "[OK]   codesign is available."
fi

# ── 2. Check the dev signing identity exists ─────────────────────────────────
IDENTITY_LINE=""
if command -v security &>/dev/null; then
  IDENTITY_LINE=$(security find-identity -v -p codesigning 2>/dev/null \
    | grep "$DEV_IDENTITY" || true)
fi

if [[ -z "$IDENTITY_LINE" ]]; then
  echo "[FAIL] Signing identity not found: '$DEV_IDENTITY'"
  echo ""
  echo "       Run the certificate creation steps from the runbook:"
  echo "       docs/redesign/KEYCHAIN_DEV_SIGNING.md  (Phase 1 -> Step 1)"
  echo ""
  echo "       Quick summary:"
  echo "         Open Keychain Access -> Certificate Assistant -> Create a Certificate"
  echo "         Name: '$DEV_IDENTITY'"
  echo "         Identity Type: Self Signed Root"
  echo "         Certificate Type: Code Signing"
  echo "         Validity: 1825 days"
  echo ""
  ERRORS=$((ERRORS + 1))
else
  echo "[OK]   Signing identity found: $IDENTITY_LINE"
fi

# ── 3. Smoke-test: attempt a codesign without user interaction ────────────────
# We sign a trivial temp binary. If the partition list is NOT configured the
# codesign call will hang waiting for a GUI password prompt. We time-box it with
# a 3-second timeout (signing itself is instant when the ACL is set).
# Only run this check if the identity was found.
if [[ -n "$IDENTITY_LINE" ]] && command -v codesign &>/dev/null; then
  TMPBIN=$(mktemp)
  # Write a minimal Mach-O: copy the shell binary as a proxy test target.
  cp /bin/sh "$TMPBIN"
  chmod +x "$TMPBIN"

  SIGN_RESULT=0
  # timeout is a GNU coreutils command; macOS ships gtimeout via brew or uses
  # perl/python. Fall back gracefully if not available.
  if command -v gtimeout &>/dev/null; then
    gtimeout 5 codesign --force --sign "$DEV_IDENTITY" "$TMPBIN" \
      --identifier "com.vysted.terminal" 2>/dev/null \
      && SIGN_RESULT=0 || SIGN_RESULT=$?
  else
    # No gtimeout — run codesign with a background kill.
    codesign --force --sign "$DEV_IDENTITY" "$TMPBIN" \
      --identifier "com.vysted.terminal" 2>/dev/null &
    SIGN_PID=$!
    # Wait up to 5s for the codesign to finish.
    for i in $(seq 1 10); do
      sleep 0.5
      if ! kill -0 "$SIGN_PID" 2>/dev/null; then
        break
      fi
    done
    # If still running, it's blocked on a password prompt.
    if kill -0 "$SIGN_PID" 2>/dev/null; then
      kill "$SIGN_PID" 2>/dev/null || true
      SIGN_RESULT=124  # timeout-like exit code
    else
      wait "$SIGN_PID" && SIGN_RESULT=0 || SIGN_RESULT=$?
    fi
  fi
  rm -f "$TMPBIN"

  if [[ $SIGN_RESULT -eq 0 ]]; then
    echo "[OK]   codesign with '$DEV_IDENTITY' succeeds without prompting."
  elif [[ $SIGN_RESULT -eq 124 ]]; then
    echo "[WARN] codesign timed out (>5s) — this usually means the partition list"
    echo "       is not configured. The binary signing will block on a GUI prompt"
    echo "       during 'pnpm tauri:dev'."
    echo ""
    echo "       Run the one-time partition-list command (requires your login password):"
    echo "         security set-key-partition-list \\"
    echo "           -S apple-tool:,apple:,codesign: \\"
    echo "           -s \\"
    echo "           -k YOUR_LOGIN_PASSWORD \\"
    echo "           -t private \\"
    echo "           ~/Library/Keychains/login.keychain-db"
    echo ""
    echo "       See Phase 1 -> Step 3 in docs/redesign/KEYCHAIN_DEV_SIGNING.md"
    ERRORS=$((ERRORS + 1))
  else
    echo "[WARN] codesign exited with code $SIGN_RESULT — check identity trust."
    echo "       Open Keychain Access, find '$DEV_IDENTITY', double-click,"
    echo "       expand Trust, set 'Code Signing' to 'Always Trust'."
    ERRORS=$((ERRORS + 1))
  fi
fi

# ── 4. Verify APPLE_SIGNING_IDENTITY would resolve (env advisory) ─────────────
echo ""
if [[ "${APPLE_SIGNING_IDENTITY:-}" == "$DEV_IDENTITY" ]]; then
  echo "[OK]   APPLE_SIGNING_IDENTITY is set to '$DEV_IDENTITY'."
else
  echo "[INFO] APPLE_SIGNING_IDENTITY is not set in this shell."
  echo "       'pnpm tauri:dev' sets it automatically on Darwin."
  echo "       For tauri build / CI, set it explicitly before building."
fi

# ── Result ────────────────────────────────────────────────────────────────────
echo ""
if [[ $ERRORS -eq 0 ]]; then
  echo "All checks passed. Run 'pnpm tauri:dev' to start the dev server with"
  echo "stable code signing. After the first 'Always Allow' click on a keychain"
  echo "item, subsequent dev rebuilds will not re-prompt."
else
  echo "$ERRORS check(s) failed. Complete the steps above, then re-run:"
  echo "  bash scripts/macos-dev-setup.sh"
  exit 1
fi
