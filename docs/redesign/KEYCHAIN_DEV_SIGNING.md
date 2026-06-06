# Keychain Dev Signing — Runbook

**Status: NEEDS-MANUAL-CHECK** — The one-time cert creation and ACL step must be performed by the operator on the target machine. Automation cannot substitute for the attended prompt.

---

## Root Cause

`tauri dev` does NOT code-sign the macOS binary it produces. The compiled binary at
`src-tauri/target/debug/vysted-terminal` is either:

- ad-hoc signed by the OS (ARM Macs require some signature to execute), or
- left unsigned

Either way, the code signature changes on every recompile because the binary content changes
and there is no stable signing identity. The macOS keychain ACL tracks items by **designated
requirement (DR)** — a policy expression that includes the signer's certificate hash and the
app's bundle identifier. A stable DR requires a stable signing identity. Without one, every
`cargo` rebuild produces a binary whose DR differs from the one stored in the ACL → the ACL
cache is invalid → macOS prompts again.

The `keyring` v3 + `apple-native` integration in `src-tauri/src/keychain.rs` is correct. The
`Cargo.toml` features (`apple-native`, `windows-native`, `sync-secret-service`, `crypto-rust`)
are correct. The problem is purely at the signing layer of the dev binary.

**Note on `APPLE_SIGNING_IDENTITY`:** This env var applies only to `tauri build` (the bundler
path). It is **not** consumed by `tauri dev`. There is an open feature request
(tauri-apps/tauri#7930) to support dev signing, but it is not shipped as of Tauri v2.11.

---

## Fix Strategy

1. Create a stable self-signed code-signing certificate tied to the app's bundle identifier.
2. Import it into the login keychain and configure the ACL so `codesign` can access it
   without interactive prompts (`security set-key-partition-list`).
3. After each `cargo` recompile, re-sign the dev binary with this stable identity.
   The DR (cert hash + identifier) is the same every time → keychain ACL persists → no
   re-prompt after the first "Always Allow" click.

The wiring lives in `scripts/macos-dev-setup.sh` (one-time setup, idempotent) and the
`tauri:dev` script in `package.json` (re-signs the binary on each hot-reload cycle via a
background file-watch loop).

---

## Step-by-Step

### Phase 1 — One-Time Certificate Creation (OPERATOR-ATTENDED, run once per machine)

These steps open interactive Keychain Access UI or require your login keychain password.
They cannot be scripted fully non-interactively without storing the password in plaintext.

**Step 1: Create the self-signed code-signing certificate**

Open Keychain Access → Certificate Assistant → Create a Certificate:

| Field                    | Value                         |
| ------------------------ | ----------------------------- |
| Name                     | `Vysted Terminal Dev Signing` |
| Identity Type            | Self Signed Root              |
| Certificate Type         | Code Signing                  |
| Let me override defaults | checked                       |
| Validity period          | 1825 days (5 years)           |

Leave all other fields at defaults. Click Create. The cert and private key are added to your
login keychain.

Alternatively via command line (no Apple Developer account required):

```bash
# Create a Certificate Signing Request config
cat > /tmp/vysted-codesign.conf << 'EOF'
[ req ]
default_bits       = 4096
distinguished_name = dn
x509_extensions    = ext
prompt             = no

[ dn ]
CN = Vysted Terminal Dev Signing

[ ext ]
keyUsage           = critical,digitalSignature
extendedKeyUsage   = critical,codeSigning
basicConstraints   = critical,CA:false
subjectKeyIdentifier = hash
EOF

# Generate key + self-signed cert (5-year validity)
openssl req -x509 -config /tmp/vysted-codesign.conf \
  -days 1825 \
  -out /tmp/vysted-codesign.pem \
  -keyout /tmp/vysted-codesign.key \
  -newkey rsa:4096 -nodes

# Bundle as PKCS#12 for import
openssl pkcs12 -export \
  -out /tmp/vysted-codesign.p12 \
  -inkey /tmp/vysted-codesign.key \
  -in /tmp/vysted-codesign.pem \
  -passout pass:vysted-dev-cert

# Import into login keychain
security import /tmp/vysted-codesign.p12 \
  -k ~/Library/Keychains/login.keychain-db \
  -P vysted-dev-cert \
  -T /usr/bin/codesign \
  -T /usr/bin/security

# Clean up temp files
rm /tmp/vysted-codesign.conf /tmp/vysted-codesign.pem \
   /tmp/vysted-codesign.key /tmp/vysted-codesign.p12

echo "Certificate imported. Verify with:"
echo "  security find-identity -v -p codesigning | grep 'Vysted'"
```

**Step 2: Trust the certificate for code signing (OPERATOR-ATTENDED)**

Open Keychain Access. Find "Vysted Terminal Dev Signing" under My Certificates. Double-click
→ expand Trust → set "Code Signing" to "Always Trust". Close, enter your password when
prompted.

This marks the cert itself as trusted. Without this step, Gatekeeper and the keychain will
not accept signatures from it.

**Step 3: Set the partition list (OPERATOR-ATTENDED, run once)**

This is the critical step that tells the keychain to allow `codesign` to access the private
key without prompting on each use. You must supply your login keychain password:

```bash
# Replace YOUR_LOGIN_PASSWORD with your actual macOS login password.
# This is required by the security command — there is no workaround.
security set-key-partition-list \
  -S apple-tool:,apple:,codesign: \
  -s \
  -k "YOUR_LOGIN_PASSWORD" \
  -t private \
  ~/Library/Keychains/login.keychain-db
```

This sets the partition list on ALL private keys in your login keychain, giving `codesign`
access without interactive prompts. It is a one-time operation (survives reboots).

**Step 4: Run the idempotent setup script**

```bash
bash scripts/macos-dev-setup.sh
```

The script verifies the identity is present and reports if any step is missing.

---

### Phase 2 — Per-Session Wiring (AUTOMATED)

The `tauri:dev` script in `package.json` handles this. When you run:

```bash
pnpm tauri:dev
```

On Darwin, the script:

1. Starts `tauri dev --features dev-tools` in the foreground (which recompiles on source
   changes).
2. Launches a background loop that watches `src-tauri/target/debug/vysted-terminal` for
   modification and re-signs it with `APPLE_SIGNING_IDENTITY="Vysted Terminal Dev Signing"`
   whenever the binary changes.

The first time you access the keychain after setup, macOS will still prompt once for
"Always Allow" (because the keychain item's ACL for the vysted-terminal app is being set
for the first time). After clicking "Always Allow", the ACL stores the DR of the signed
binary. Because every subsequent dev binary is signed with the same identity, the DR is
stable → no further prompts.

On non-Darwin platforms, `pnpm tauri:dev` falls back to plain `tauri dev --features dev-tools`
with no signing wrapping.

---

## Verification Procedure

1. Complete Phase 1 steps on a clean machine.
2. Run `pnpm tauri:dev`.
3. Access a keychain secret (e.g. set an API key in Settings).
4. Click "Always Allow" when prompted.
5. Make a source change (e.g. change a string in `src/`). Wait for hot-reload.
6. Access the keychain again.
7. **Expected: no prompt appears.** The ACL recognizes the re-signed binary via its stable DR.
8. Rebuild from scratch (`cargo clean && pnpm tauri:dev`). Access the keychain again.
9. **Expected: no prompt.** The cert hash is stable regardless of binary content.

---

## Why `.cargo/config.toml` is Omitted

`src-tauri/.cargo/config.toml` with `[env] APPLE_SIGNING_IDENTITY = ...` propagates only to
Cargo compilation, not to the Tauri CLI's bundler or signing step. Since `tauri dev` ignores
`APPLE_SIGNING_IDENTITY` entirely (the bundler path that reads it never runs during `tauri dev`),
setting it in `.cargo/config.toml` provides no benefit. Signing must be done by a post-build
`codesign` invocation in the dev wrapper script, not by Tauri's own signing path. This file is
therefore NOT created — it would create a false impression that Cargo is handling the signing.

---

## Proposed CLAUDE.md Gotcha Addition

Add the following line to the **Gotchas > Frontend** section (or a new **Gotchas > Keychain &
signing** subsection) in `CLAUDE.md`. The lead should apply this after reviewing this runbook:

```
- **macOS keychain re-prompts on every `tauri dev` rebuild** because `tauri dev` never
  invokes the signing step — the dev binary is unsigned/ad-hoc each time. Fix: create a
  5-year self-signed cert ("Vysted Terminal Dev Signing"), run `scripts/macos-dev-setup.sh`
  once (sets the partition list), then use `pnpm tauri:dev` which re-signs the debug binary
  on each hot-reload via a background watcher. After one "Always Allow" click the ACL
  persists. See `docs/redesign/KEYCHAIN_DEV_SIGNING.md`.
```

---

## Summary: Automated vs Operator-Attended

| Step                                       | Who                        | Why                                                                                  |
| ------------------------------------------ | -------------------------- | ------------------------------------------------------------------------------------ |
| Create self-signed cert                    | **OPERATOR-ATTENDED**      | Requires Keychain Access UI or interactive shell with output inspection              |
| Trust cert in Keychain Access              | **OPERATOR-ATTENDED**      | GUI-only trust dialog                                                                |
| `security set-key-partition-list`          | **OPERATOR-ATTENDED**      | Requires login keychain password — cannot be stored/scripted without plaintext creds |
| First "Always Allow" keychain click        | **OPERATOR-ATTENDED**      | One-time per keychain item on a given machine                                        |
| `scripts/macos-dev-setup.sh`               | **AUTOMATED** (idempotent) | Verify cert exists, print instructions if missing                                    |
| `pnpm tauri:dev` re-sign watcher           | **AUTOMATED**              | Runs on every dev session, no interaction needed                                     |
| `pnpm tauri:dev` fallback on Linux/Windows | **AUTOMATED**              | Platform guard in package.json                                                       |
