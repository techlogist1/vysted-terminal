# Keychain Dev Signing — Runbook

**Status (2026-06-11): SOLVED by the dev-keystore — dev builds no longer touch the macOS
keychain, so there are ZERO dialogs of any kind on rebuild.** The long saga (stable
signing → keychain ACL grants → partition-list wildcard) is closed; every approach short
of leaving the keychain failed to remove the per-cdhash SecurityAgent dialog. The fix:
in DEBUG builds, `keychain_set/get/delete` route to a git-ignored local file
(`<app-data-dir>/dev-keystore.json`, `0600`) instead of the OS keychain. A one-time
migration copies existing secrets keychain→file on first dev boot (one final dialog, then
never again). Release builds are unchanged (OS keychain, bit-for-bit). See
**DEV KEYSTORE — THE FIX (verified)** below. The chapters under it are the historical
record of why everything else was insufficient.

---

## DEV KEYSTORE — THE FIX (2026-06-11, implemented + verified on screen)

`src-tauri/src/keychain.rs` now has two backends chosen at BUILD time:

- **Release** (`cfg(not(debug_assertions))`): the OS keychain via `keyring`, exactly as
  before — service `vysted-terminal`, the same accounts, no behaviour change. A test,
  `release_never_uses_dev_keystore` (run under `cargo test --release`), asserts the dev
  file path can never be reached in a release build; the `dev_keystore` module is
  `#[cfg(debug_assertions)]`, so its code does not even exist in a release binary.
- **Dev** (`cfg(debug_assertions)`): a JSON file at **`<app-data-dir>/dev-keystore.json`**
  (on this Mac: `~/Library/Application Support/com.vysted.terminal/dev-keystore.json`),
  perms `0600`, git-ignored (`.gitignore`: `dev-keystore.json`, `**/dev-keystore.json`).
  `keychain_set/get/delete` read and write this file — the OS keychain is never touched,
  so a fresh dev cdhash raises no SecurityAgent evaluation.

**Audit (every keychain call site):** the ONLY code that touches the OS keychain is
`keychain.rs` (the three commands + the migration). The renderer reaches it solely through
`src/lib/keychain.ts`; the Python sidecars NEVER read the keychain (zero `keyring`
imports — they receive secrets in request headers). So redirecting `keychain.rs` covers
100% of dev key/meta reads and writes, from both the app and the sidecars.

**One-time migration (`keychain_migrate`, dev-only; renderer calls it once at boot via
`migrateDevKeystore()`):** copies the candidate accounts from the OS keychain into the
file, idempotent via a `migrated` flag (the guard is checked BEFORE any keychain read, so
every boot after the first does ZERO keychain reads — the bug that re-raised the dialog on
each boot until it was moved ahead of the reads). Values are copied keychain→file entirely
in Rust, never returned to JS. The migration uses a **read → idle ~140s → re-read** pass:
the first read of an existing item triggers the one cdhash ACL evaluation, which only
self-dismisses-as-allow while the app is IDLE on the keychain, after which the re-read
returns the value. If it fails (the operator denies it, or the keychain stays hostile),
the keystore is left empty and the user re-adds keys via Settings — `migrated` is still
set, so the keychain is never retried.

**Verified on screen (2026-06-11):**

- One migration boot: the four existing items (`llm-provider:deepseek`,
  `llm-provider:openrouter`, `broker:_meta:first-launch-tos`,
  `app-meta:onboarding-complete`) copied into the file; this is the ONE final dialog.
- **THREE consecutive from-scratch rebuilds** (app + all sidecars force-rebuilt, each a
  genuinely new cdhash: `932790c9…`, `3c0bec1d…`, `0aca12ec…`), each booted and exercised
  with a live chat call (SPY $728.34 / QQQ / NVDA $202.40 — real tool-backed answers):
  a continuous 0.5s SecurityAgent watcher logged **0 dialogs** across all three, and the
  migration command did **0 keychain reads** per boot.
- Settings reads the migrated key live (DeepSeek shows "✓ Key configured" from the
  keystore); the "Add key" dialog opens dialog-free and validates input (a dummy Groq key
  was correctly rejected as unauthorized). `keychain_set/get/delete` against the file are
  unit-pinned (`roundtrip_set_get_delete_against_the_file`), plus the once-only guard
  (`migrate_collecting_reads_keychain_zero_times_once_migrated`) and the 0600-perms and
  no-clobber tests. ci-local green; PyInstaller builds and boots (smoke incl. ICONIKSPEV).

**Caveat (harness, not the product):** the migration read self-dismisses-as-allow only
when nothing polls the window list / screenshots during the dialog — the verification's
own watcher initially CANCELED the read ("User canceled the operation."), which is why the
migration runs a patient idle re-read and falls back to Settings if it still can't read.
On a normal interactive boot the one migration dialog allows and the keys carry over.

---

## WILDCARD EXPERIMENT — VERIFIED FAILED (2026-06-11, operator-run + measured)

The operator ran the partition-list wildcard one-liner from a plain Terminal against all
four items: `security set-generic-password-partition-list -S
"apple:,apple-tool:,codesign:,cdhash:" -s vysted-terminal -a <acct> -k <pw>` (four `ok`
lines returned). It did NOT eliminate the per-cdhash transient dialog.

**Method:** a continuous Quartz watcher (0.5s cadence) logged every visible SecurityAgent
window across two from-scratch rebuild+boot rounds, each forcing a GENUINELY NEW cdhash
(a throwaway comment in `src-tauri/src/main.rs` → real recompile → fresh signature,
reverted after). Each round booted and exercised a real key-reading flow (one chat call).

**Result — both fresh cdhashes still flashed; the key read succeeded each time:**

| Round | cdhash      | dialog first → last seen                       | duration                         | chat answered? |
| ----- | ----------- | ---------------------------------------------- | -------------------------------- | -------------- |
| A     | `c52d0890…` | 18:28:15.985 → 18:29:33.049 (gone by 18:30:13) | **~77–117s** (past the 60s line) | yes            |
| B     | `3a94b5f9…` | 18:32:03.222 → 18:32:20.302                    | ~17s                             | yes            |

The dialog still self-dismisses as ALLOW (the cert-based trusted-app entry validates; both
chats answered with live data), but **persistence is variable and at least once exceeded
the 60-second "regression" threshold** — so "ignore it, it vanishes in ~10–50s" no longer
holds as a guarantee. The bare `cdhash:` prefix is NOT honored as a wildcard: a self-signed
identity has no Apple Team ID, so the item's `partition_id` cannot express "any cdhash
under team X," and securityd runs one evaluation pass per never-before-seen cdhash. The
prior FINAL VERDICT's "optional experiment may remove even the transient" is now resolved:
**it does not.** Note the running dev binary confirms the cause — `codesign -dvvv`:
`Authority=Vysted Terminal Dev Signing`, `TeamIdentifier=not set`.

## NEXT STEP (now done) — the dev-keystore approach

This section recommended the dev-keystore (option 1 below); it was IMPLEMENTED this session
— see **DEV KEYSTORE — THE FIX** at the top. Option 2 remains the only way to also get
zero dialogs in RELEASE-signed local runs, if ever needed.

1. **Dev-only file keystore (DONE).** `keychain.rs` stores dev secrets in a `0600`
   git-ignored file gated behind `cfg(debug_assertions)`; no per-app/per-cdhash ACL, so no
   SecurityAgent evaluation, zero dialogs. Release keeps the OS keychain unchanged.
2. **Apple Developer ID Application certificate (not needed for dev).** A Team ID would let
   the `partition_id` grant the whole team so every cdhash validates without a per-build
   evaluation — the only path to zero dialogs for a RELEASE-signed binary read locally.
   Irrelevant to `tauri dev` now that the dev keystore bypasses the keychain entirely.

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
  'vysted-terminal' in your keychain"_. The prompt was left unanswered (autonomous run — the
  password cannot be typed by automation) and timed out; a timed-out prompt records nothing.
- **Rebuild round 3**: DR again byte-identical (`codesign -d -r-` → `identifier
"com.vysted.terminal" and certificate leaf = H"c0d31e56…"`), and the same prompt
  reappeared — confirming the loop: until the grant is actually GIVEN once, every fresh
  binary prompts. The grant is the one and only missing piece; the signing side is proven
  stable.
- **TCC**: a trusted CGEvent click + a System Events AppleScript query against the freshly
  rebuilt binary raised no new automation/accessibility dialog — grants persisted across the
  rebuild (consistent with ~8 rebuilds across the R8 run, zero TCC dialogs).

## FINAL VERDICT — post-grant verification (2026-06-11, attended grants given)

**The disease (interactive prompts requiring your password) is CURED. A transient,
self-dismissing dialog remains once per fresh binary — it needs NO interaction and stalls
nothing.** Evidence from the verification run:

1. **Item census:** the app reads exactly FOUR keychain items at boot (service
   `vysted-terminal`, accounts `llm-provider:deepseek`, `llm-provider:openrouter`,
   `broker:_meta:first-launch-tos`, `app-meta:onboarding-complete`). Your "~4 prompts per
   launch" was one per item; "× 3 rebuilds ≈ 12" matched one grant round per fresh binary
   before the grants stuck.
2. **ACL state after your grants:** every item carried ONE valid `(OK)` trusted-application
   entry with the stable requirement (`identifier "com.vysted.terminal" and certificate leaf
= H"c0d31e56…"`) — plus 29–48 DEAD entries each (~165 total), one for every past
   Always-Allow on an ad-hoc build. That scar tissue has been PRUNED: the signed app itself
   rewrote all four items in place (get → delete → set through its own IPC; values verified
   in-process, never exposed). All four items now read: `apps=1, stable-OK=1, dead=0`.
3. **Fresh-rebuild proofs:** after pruning, two more full rebuild+boot rounds (new binaries,
   runner-signed, sidecar rebuilt and auto-signed as `com.vysted.sidecar`) booted and read
   ALL keys with ZERO human input — chat on DeepSeek worked unattended.
4. **The residual, precisely:** on the FIRST key read of a never-executed binary, macOS
   shows the keychain dialog for ~10–50s and then SELF-DISMISSES AS ALLOW (the cert-based
   ACL entry validates; the read succeeds; boot continues). Root cause: the item's
   `partition_id` ACL entry pins specific **cdhashes** (verified in the dump:
   `cdhash:1d73de…, cdhash:28621a…, …`), and a self-signed identity has no Apple team id
   the partition list could express — so each new cdhash triggers one securityd evaluation
   pass. This is structural to self-signed identities on the file keychain. A pre-exec
   `codesign --verify` in the runner was tested and did NOT shorten it (reverted).

**What this means for you:** IGNORE these dialogs — do not type your password; they vanish
on their own and the keys are read. Only a prompt that survives >60s would indicate a real
regression (then re-check this doc's ACL inspection commands). Unattended overnight driving
works: the only cost is a one-time ~10–50s delay on the first key read per rebuild.

**Optional experiment — status: NOT RUN** (offered at session close-out 2026-06-11; the
attended password entry did not happen, and the partition lists were verified still
cdhash-pinned afterwards). The transient self-dismissing flash therefore remains expected
behavior per the FINAL VERDICT above. The one-liner below stays available if you ever want
to try it (one password entry, may remove even the transient — unverified, harmless if it
fails): the partition list may accept a bare-prefix wildcard. Per item:

```bash
security set-generic-password-partition-list \
  -S "apple:,apple-tool:,codesign:,cdhash:" \
  -s vysted-terminal -a "llm-provider:deepseek" \
  -k "YOUR_LOGIN_PASSWORD" ~/Library/Keychains/login.keychain-db
# repeat for: llm-provider:openrouter, broker:_meta:first-launch-tos,
#             app-meta:onboarding-complete
```

Then rebuild + relaunch; if the transient dialog is gone, it worked. Note: any future
"Always Allow" click re-pins a cdhash — harmless, but unnecessary.

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
