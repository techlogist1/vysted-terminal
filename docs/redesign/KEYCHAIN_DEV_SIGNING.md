# Keychain Dev Signing — Runbook

**Status (R8 hot patch, 2026-06-11): WIRED AND VERIFIED — one attended "Always Allow" remains.**
The certificate exists and is trusted, codesign runs prompt-free (partition list set), and
EVERY dev build now signs automatically before first launch. One keychain item still holds an
old build's designated requirement in its ACL — the next launch shows ONE password +
"Always Allow" prompt; granting it re-keys the item to the stable identity permanently.

---

## R8 hot patch — why the prompts survived the original wiring, and the real fix

**The original watcher could never work.** The `tauri:dev` wrapper re-signed
`src-tauri/target/debug/vysted-terminal` on an mtime watch — but `codesign --force` on a
RUNNING executable fails (text file busy), and by the time the watcher's first 1.5s tick
fired, `tauri dev` had already launched the binary. Every failure was swallowed by
`stdio:'ignore'` + try/catch, so every dev session silently ran AD-HOC signed (verified live:
the running R8 binary showed `Signature=adhoc, linker-signed`), the designated requirement
changed per rebuild, and the keychain ACL re-prompted — the ~20-prompts-per-session pain.

**The fix is a cargo RUNNER** (`src-tauri/.cargo/config.toml` →
`scripts/macos-dev-sign-run.sh`): cargo hands the freshly built executable to the runner
BEFORE first exec — the only moment signing can succeed — and the runner signs it with
"Vysted Terminal Dev Signing" (identifier `com.vysted.terminal`) and then `exec`s it. This
covers the initial launch AND every HMR rust-rebuild relaunch, deterministically. The broken
watcher is deleted from `package.json` (`tauri:dev` is now plain `tauri:mcp`).

Notes on the runner approach (distinct from the rejected `[env]` idea below):

- Cargo discovers `.cargo/config.toml` from the INVOCATION cwd. The Tauri CLI invokes cargo
  from `src-tauri/`, so the runner applies there and `../scripts/...` resolves. ci-local's
  `cargo test --manifest-path src-tauri/Cargo.toml` from the repo root never sees the config
  — CI and test runs are untouched.
- The runner passes through untouched (exec without signing) when the identity is missing
  (CI, fresh machines) or `VYSTED_SKIP_DEV_SIGN=1`. A codesign failure warns and runs anyway
  — it can never break a build.
- Release signing/notarization (`tauri build` + `APPLE_SIGNING_IDENTITY`) is untouched.

**Sidecar binaries are now signed too** (`scripts/macos-dev-sign.mjs`, called by all three
`ensure-*-sidecar.mjs` scripts after each PyInstaller build): `com.vysted.sidecar`,
`com.vysted.openbb-mcp-sidecar`, `com.vysted.sec-edgar-mcp-sidecar`, same identity. Sidecars
do not read the keychain (the renderer does), but stable identities keep every other
signature-keyed macOS permission (firewall accept-incoming, TCC pairings) from resetting per
rebuild. Same pass-through rules as the runner.

## R8 verification evidence (2026-06-11)

- `codesign --force --sign "Vysted Terminal Dev Signing" …` runs with NO password prompt
  (partition list confirmed set; identity `C0D31E56…` valid in the login keychain).
- **Rebuild round 1** (`touch src-tauri/src/main.rs` → `pnpm tauri:dev`): the binary the app
  ran was `Identifier=com.vysted.terminal / Authority=Vysted Terminal Dev Signing` (first
  dev session ever to run identity-signed from boot), ZERO prompt windows, provider key read
  succeeded (header connected on DeepSeek).
- **Rebuild round 2** (same procedure): binary again signed with the identical designated
  requirement — and ONE SecurityAgent prompt appeared: _"vysted-terminal wants to access key
  'vysted-terminal' in your keychain"_. That item's ACL still holds an old build's DR. This
  is THE one-time grant: password + "Always Allow" re-keys the ACL to the stable DR
  (cert hash + `com.vysted.terminal`), which no rebuild changes again.
- **TCC**: a trusted CGEvent click + a System Events AppleScript query against the freshly
  rebuilt binary raised no new automation/accessibility dialog — grants persisted across the
  rebuild (consistent with ~8 rebuilds across the R8 run, zero TCC dialogs).

## OPERATOR — the one remaining click (one-time-forever)

On the next launch (or the prompt already on screen): when macOS asks
_"vysted-terminal wants to access key 'vysted-terminal' in your keychain"_, enter your login
password and click **Always Allow** (not Allow). If a second prompt appears for another
stored key item (one per item whose ACL predates the stable identity), Always-Allow it the
same way. After that, rebuilds never re-prompt: every dev binary now carries the same
designated requirement by construction.

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

The wiring lives in `scripts/macos-dev-setup.sh` (one-time setup, idempotent) and — since
the R8 hot patch — the cargo runner (`src-tauri/.cargo/config.toml` →
`scripts/macos-dev-sign-run.sh`), which signs every freshly built dev binary before its
first exec. (The original package.json file-watch loop is gone: it re-signed AFTER launch,
which always fails on a running binary — see the R8 section at the top.)

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
