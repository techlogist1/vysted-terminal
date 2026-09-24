<!-- CRITIC of RELEASE_RUNBOOK.draft.md at f444479031d7d493b7955b9af041d18e7c7a40cc -->

# Critic — RELEASE_RUNBOOK.draft.md

Read cold as the lead cutting 0.9.0, every command and claim checked against the repo at
`f444479031d7d493b7955b9af041d18e7c7a40cc` (`git show <sha>:<path>`), `FACTS.md`, and the
local toolchain (`which`). Model: Fable 5.1. Label `stage-d-critic-runbook`.

## Verdict: REVISE

Findings 4 and 5 make a step fail or silently pass for the wrong reason; findings 1–3 and 6–7
mislead the reader about what the bump and build actually touch. Findings 8–11 are low.

## Findings

### 1. wrong — §1 bump list does not match FACTS `version_occurrences` (three manifest rows dropped, miscounted exclusions)

- Location: §1 "Version bump to 0.9.0", lines 30–44.
- Evidence: the draft says it lists "Every `[load_bearing]` occurrence" minus the exclusions it
  names, but `FACTS.md:75-77` carries three more `[load_bearing]` rows the draft neither lists
  nor excludes: `plugins/vysted-lenses/manifest.json:6`, `plugins/vysted-news/manifest.json:6`,
  `plugins/yfinance/manifest.json:6` (`"requiredHostVersion": "0.8.0"` at the sha). The
  semantics are a minimum-host pin: `src/lib/plugin-runtime.ts:374-375`
  `if (!hostSatisfies(this.context.hostVersion, manifest.requiredHostVersion)) return "plugin
  requires host version >= …"`, so 0.9.0 satisfies 0.8.0 and no bump is required — but the
  runbook has to say which. Also the parenthetical at lines 30–32 says "the two rows FACTS itself
  marks as unrelated" then lists 1 + "five unrelated-crate rows at 281/290/758/2426/2443/3351/3368"
  — that is seven rows (`git grep -n '0\.8\.0' <sha> -- src-tauri/Cargo.lock` → 281, 290, 758,
  2426, 2443, 3351, 3368, 5487).
- Fix: add a bullet "`plugins/{vysted-lenses,vysted-news,yfinance}/manifest.json:6`
  `requiredHostVersion: "0.8.0"` — a minimum-host pin (`plugin-runtime.ts:374`), NOT bumped;
  0.9.0 satisfies it" (or bump them deliberately and say why). Correct "two rows"/"five" to
  "one row"/"seven".

### 2. wrong — §1 presents arbitrary test literals as load-bearing bump targets, and lists two of eleven

- Location: §1 lines 42–44.
- Evidence: `src/components/SettingsPanel.test.tsx:831-845` — the fixture returns
  `{ version: "0.8.0", logTail: [...] }` and the assertions check
  `preview.textContent` contains the logTail line and `writeText` calls; nothing asserts the
  version string (`sed -n '831,875p' | grep expect` → only logTail/Copied/writeText). The
  characterisation "test fixture asserting the `/system/diagnostics` version echo" (inherited
  from `FACTS.md:94`) is wrong. `src/lib/plugin-runtime.test.ts` has `0.8.0` on lines 498, 508,
  517, 542, 545, 547, 550, 551, 552, 555, 556 (hostSatisfies semantics tests, e.g. :551
  `expect(hostSatisfies("0.8.0", "0.9.0")).toBe(false)`), plus `src/store/marketplace.test.ts:43`
  `new PluginRuntime({ hostVersion: "0.8.0" })`; the draft names only :498 and :508. Bumping two
  of eleven arbitrary literals is neither required nor consistent.
- Fix: split §1 into (a) the five must-bump sources — `package.json:3`, `src-tauri/Cargo.toml:3`,
  `src-tauri/tauri.conf.json:4`, `sidecar/app.py:327`, `src/lib/plugin-bootstrap.ts:37` — plus
  `Cargo.lock` via the `cargo update` line (CLAUDE.md:276-279 names exactly these five), and (b)
  "test fixtures that happen to use 0.8.0 as an arbitrary literal — not bump targets"
  (`SettingsPanel.test.tsx:831`, `plugin-runtime.test.ts:498-556`, `marketplace.test.ts:43`,
  `sidecar/tests/test_data_cache.py:131-150`).

### 3. wrong — §1 "expected output" of the stale-string grep does not match what the grep prints

- Location: §1 lines 59–69.
- Evidence: running the draft's exact command at the sha
  (`git grep -n '0\.8\.0' <sha> -- . ':!CHANGELOG.md' ':!docs/archive' ':!docs/redesign/verification' ':!docs/screenshots' ':!pnpm-lock.yaml' | wc -l`) → **92** lines: 55 prose
  (FACTS.md:18-72 — which also include `docs/research/phase-10/*`, not named in the draft) and 37
  in source/lock/test/manifest files. After the five-file bump the same grep still prints ~87
  lines (`package.json:76`, `Cargo.lock` ×7, `test_data_cache.py` ×5, three manifests,
  `plugin-runtime.test.ts` ×11, `marketplace.test.ts:43`, `workspace.test.ts:1488` (a doc
  comment "v0.8.0 rows"), `plugin-runtime.ts:115` (a doc comment), + 55 prose). "roughly 90
  `0.8.0` prose hits" is the wrong number and the wrong category, and "no hits against the
  load-bearing paths above" is not something the reader can eyeball out of 87 lines.
- Fix: either tighten the grep — add `':!docs' ':!*.test.ts' ':!*.test.tsx' ':!sidecar/tests'
  ':!src-tauri/Cargo.lock' ':!plugins/*/manifest.json'` — and state the expected residual as
  exactly `package.json:76` (prettier-plugin-tailwindcss pin), `src/lib/plugin-runtime.ts:115`
  and `src/lib/workspace.test.ts:1488` (doc comments); or keep the wide grep and print the
  expected residual list.

### 4. missing — §3 has no toolchain prerequisite; `pnpm ci-local` fails on this machine as written

- Location: §3 (and §2), lines 74–96.
- Evidence: `package.json:22` (`ci-local`) calls bare `python -m pip install ruff==0.15.12`,
  `ruff`, `pytest`, `cargo`. On this Mac: `which python python3 pytest ruff cargo node pnpm` →
  `python not found`, `/opt/homebrew/bin/python3`, `pytest not found`, ruff/cargo/node/pnpm found
  (node only after `export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:…`; the wave's own brief
  had to say so). The sidecar venv exists and is the intended interpreter:
  `sidecar/.venv/bin/python --version` → `Python 3.13.13` (FACTS "tools": venvs present). Without
  it active, step 3 dies at `python -m pip install ruff==0.15.12` (`zsh: command not found:
  python`) after already having spent the lint/typecheck minutes — and CI's workflows get their
  `python` from `actions/setup-python` `python-version: "3.13"` (`.github/workflows/test.yml:41`),
  which the local mirror does not.
- Fix: add a "Prerequisites (one shell, before §2)" block: `export
  PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`, `source
  sidecar/.venv/bin/activate` (so `python`/`pip`/`pytest`/`ruff` resolve to Python 3.13.13),
  `rustc -vV` (the ensure scripts read the target triple from it, `ensure-sidecar.mjs:30-35`),
  pnpm 10.32.1 (FACTS "tools"; `.github/workflows/*.yml` pin `version: 10.32.1`).

### 5. wrong — §7 "a fresh profile has no keychain entry for this namespace, so the dialog must show" is false for a release build

- Location: §7 lines 244–250 and 251–256.
- Evidence: the terms ack is persisted in the **OS keychain** — `src/store/safety.ts:4-5,17`
  (`FIRST_LAUNCH_TOS_ACCOUNT = KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")`,
  `src/lib/keychain.ts:42` → account `app-meta:first-launch-terms`), and the Rust side picks the
  backend at build time: `src-tauri/src/keychain.rs:6-10` release = `keyring` OS keychain,
  service `"vysted-terminal"` (`:38`); the file keystore `<app-data-dir>/dev-keystore.json` is
  `cfg(debug_assertions)` only (`:11-12`, `:20-23`, `:45 USE_DEV_KEYSTORE = cfg!(debug_assertions)`).
  So for the `pnpm tauri build` `.app` of §6, the ack does NOT live in the app-data directory; a
  "fresh app-data directory" leaves the lead's login-keychain item
  `vysted-terminal` / `app-meta:first-launch-terms` in place, the dialog does not show, and the
  check passes for the wrong reason (or fails with no explanation). The RC1 precedent the draft
  cites only worked because it launched a **`tauri build --debug`** bundle
  (`RC1_GATE_PLAN.md:21`), whose keystore is the file in the isolated `HOME`. The same applies to
  `app-meta:onboarding-complete` (`keychain.ts:101`) and to every BYOK key: the release `.app`
  reads the operator's real keys under the same service, so the §7 launch is not "keyless" unless
  those items are absent.
- Fix: rewrite §7's precondition: "The release build stores the ack in the login keychain
  (`keychain.rs:6-10`, service `vysted-terminal`). Before launch: `security
  find-generic-password -s vysted-terminal -a app-meta:first-launch-terms` (never `-w`, never
  print the value) — if present, either delete it (`security delete-generic-password -s
  vysted-terminal -a app-meta:first-launch-terms`, same for `app-meta:onboarding-complete`) or
  run the check as a separate macOS user. A fresh app-data dir alone does not reset it." Keep
  the RC1 reference but label it as the debug-build path.

### 6. missing — §4/§6 ship sidecar binaries signed with the lead's private self-signed dev identity unless `VYSTED_SKIP_DEV_SIGN=1` is set

- Location: §4 lines 139–178, §6 lines 217–219, §8 line 263.
- Evidence: every ensure script signs its output after the copy —
  `scripts/ensure-sidecar.mjs:207 signDevBinary(outPath, "com.vysted.sidecar")`,
  `ensure-openbb-mcp-sidecar.mjs:202`, `ensure-sec-edgar-mcp-sidecar.mjs:194`;
  `scripts/macos-dev-sign.mjs:17,42` runs `codesign --force --sign "Vysted Terminal Dev
  Signing" --identifier … <bin>` whenever that identity is in the login keychain (`:21-33`),
  and is skipped only by non-Darwin, a missing identity, or `VYSTED_SKIP_DEV_SIGN=1` (`:37-40`).
  `tauri.conf.json:10` `beforeBuildCommand: "node scripts/ensure-all-sidecars.mjs && pnpm
  build"` re-runs the ensure scripts inside `pnpm tauri build`, and the lead's Mac has the
  identity (CLAUDE.md "macOS keychain re-prompts…" gotcha; `scripts/macos-dev-setup.sh`). Net:
  the three `externalBin` payloads inside the unsigned release bundle carry a signature from a
  5-year self-signed cert named after the dev rig — never intended for shipping
  (`macos-dev-sign.mjs:12-13` "release signing is Tauri's job and untouched by this", but Tauri
  signs nothing here, §8).
- Fix: prefix §4 and §6 with `VYSTED_SKIP_DEV_SIGN=1` (`VYSTED_SKIP_DEV_SIGN=1 pnpm
  sidecars:build`, `VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build`), and add one line to §8: "inner
  sidecar binaries: ad-hoc/linker-signed only when built with `VYSTED_SKIP_DEV_SIGN=1`; otherwise
  they carry the local dev identity". Note the `[dev-sign] signed …` log line (`macos-dev-sign.mjs:45`)
  in §4's expected output as the symptom to watch for.

### 7. missing — no CHANGELOG / release-notes step; §9's GitHub Release has no body source

- Location: checklist lines 11–21; §9 lines 288–301.
- Evidence: `CHANGELOG.md` at the sha uses a per-release heading `## v0.7.0 — Completion +
  Polish + Parity (2026-05-17)` (`:401`), `## v0.6.5 — …` (`:649`); there is no `## v0.8.0`
  heading (`grep -n '^## v0\.8'` → none — v0.8.0 was tagged off a docs-only commit,
  `git log -1 v0.8.0` → `f45019f6 docs(release/v0.8.0/H2): …`), and nothing in the runbook adds a
  `## v0.9.0 — … (date)` heading. §9 writes the tag message but gives the operator no notes for
  the Release body; this wave produced
  `docs/redesign/verification/r15/stage-d/RELEASE_NOTES.draft.md` (line 3 `# Vysted Terminal
  0.9.0`) which the runbook never references.
- Fix: add step "1b. `CHANGELOG.md`: add `## v0.9.0 — <title> (<date>)` above the R15 Stage C
  headings, in the bump commit; promote `RELEASE_NOTES.draft.md` at rc2 and use it as the
  Release body (`gh release create v0.9.0 --notes-file <file> <assets…>` — operator-only, after
  §8/§9 are unblocked, or with hand-built §6 assets as the draft already allows)".

### 8. missing — §5 omits the smoke test's freshness gate, which is the reason §4 must precede it

- Location: §5 lines 198–204.
- Evidence: `scripts/smoke-test-sidecars.mjs:912 _assertAllFresh(triple)` runs before any
  spawn and `:898` logs `[smoke] freshness gate: all bundled sidecar binaries are newer than
  their source.`; the §1 edit to `sidecar/app.py:327` makes a pre-bump binary stale, so a lead
  who re-runs §5 after any later sidecar edit without §4 gets a freshness failure the runbook
  never describes.
- Fix: one sentence in §5: "The script first refuses any binary older than its source
  (`_assertAllFresh`, :912); re-run §4 after any sidecar or ensure-script edit."

### 9. missing — §10 does not list the register's known Windows-red test

- Location: §10 lines 356–373.
- Evidence: `docs/redesign/verification/vysted-r15-register.json` entry
  `R15-CROSS-PLATFORM-002` (status `open`, severity `medium`): "windows-latest pytest goes red
  on a test-only defect: test_search_extract reads the Saksoft fixture with Path.read_text()
  and no encoding, which decodes as cp1252 on Windows and raises UnicodeDecodeError at byte
  0x9d" (evidence `sidecar/tests/test_search_extract.py:463-464`, `.github/workflows/test.yml:77-81`
  plain pytest, no `PYTHONUTF8`; FACTS "register" lists it under open medium). A Windows CI leg
  or local pytest is expected to fail on this at the sha; §10's bullet list should say so instead
  of leaving the reader to discover it. The draft's "only macOS/Linux dev-machine evidence exists
  in the register" is also unsupported — I found no Linux run evidence either; say "no Windows run
  evidence".
- Fix: add the bullet "Known: `R15-CROSS-PLATFORM-002` (open) — sidecar pytest is expected red on
  Windows until `test_search_extract.py:463-464` passes `encoding="utf-8"` (or the workflow sets
  `PYTHONUTF8=1`)"; drop "Linux".

### 10. missing (low) — §10 asks the reader to confirm a fact the sha already settles

- Location: §10 lines 367–370.
- Evidence: `src-tauri/Cargo.toml:34` `keyring = { version = "3", features = ["apple-native",
  "windows-native", "sync-secret-service", "crypto-rust"] }`.
- Fix: replace "confirm … carries it" with "confirmed at the sha: `Cargo.toml:34` carries
  `windows-native`".

### 11. unverifiable — §6 bundle output paths

- Location: §6 lines 225–226.
- Evidence: no build log at the sha names the dmg; the only bundle path in tracked evidence is
  `src-tauri/target/release/bundle/macos/Vysted Terminal.stale-r7.app`
  (`docs/redesign/verification/r15/census/refute/intent-blueprint-144.json:18`), which supports
  the `.app` path only. The `<productName>_<version>_<arch>.dmg` pattern is Tauri's default but
  is not quoted from anything in the repo. The draft already carries a VERIFY marker; the lead
  fills it from the real run. No change needed beyond keeping the marker.

## Checked and correct

- Line 1 is exactly `<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs
  wave; refresh before rc2 -->`. Target `docs/RELEASE_RUNBOOK.md` does not exist at the sha
  (`git cat-file -e` → missing), so it is a new file.
- Every path the draft names exists at the sha except the two it says do not
  (`docs/redesign/verification/r15/rc1/`, `.github/workflows/release.yml`) — both confirmed
  missing.
- Commands exist and do what the draft says: `pnpm ci-local` (`package.json:22`, verbatim
  modulo the draft's line-wrapping), `pnpm sidecars:build` = `node scripts/ensure-all-sidecars.mjs
  --force` (`package.json:21`; orchestrator `ensure-all-sidecars.mjs:28-47`, log strings
  `[ensure-all-sidecars] → node …` / `all sidecars present.` verbatim), per-script log strings
  `building … / wrote … / done. / present and fresh — skipping build.` (`ensure-sidecar.mjs:89,98,206,212`
  and the openbb/sec-edgar equivalents), `node scripts/smoke-test-sidecars.mjs` with
  `[smoke] all sidecars booted cleanly.` (`:942`) and `[smoke] FAILURES:` + `exit 1` (`:933-940`),
  `MAIN_BOOT_TIMEOUT_MS` (`:95`), `/health` version vs `package.json` (`:536`), screener universe
  (`:657`), ICONIKSPEV (`:669`), `/agents` + `agents_degraded` (`:762,775`), `/mcp/status` (`:696`),
  no-SLA `/history` probe (`:701`), PID-ledger-only tree-kill (`:27-33,56-58`). `pnpm tauri build`
  (`package.json:23` `"tauri": "tauri"`). `cargo update -p vysted-terminal --offline
  --manifest-path src-tauri/Cargo.toml` is CLAUDE.md:278-279 verbatim.
- Version facts: `0.8.0` at `package.json:3`, `Cargo.toml:3`, `tauri.conf.json:4`,
  `app.py:327`, `plugin-bootstrap.ts:37`, `Cargo.lock:5487` (block at :5486) — all confirmed;
  `package.json:76` is the prettier-plugin-tailwindcss pin; `test_data_cache.py:131-150` uses
  0.8.0/0.8.1 as cache-build tags.
- `tauri.conf.json`: `bundle.targets` `["deb","appimage","nsis","app","dmg"]` (`:32`),
  `externalBin` (`:40-44`; the draft's `:41-44` are the three entries), `createUpdaterArtifacts:
  false` (`:45`), `beforeBuildCommand` (`:10`). The multi-OS target list is the same config
  `.github/workflows/build.yml:77` runs `pnpm tauri build` against on all three runners.
- CI: all three workflows `on: push: branches: [main]` + `pull_request`, matrix
  `[windows-latest, macos-latest, ubuntu-latest]` (`build.yml:3-13`, `lint.yml:3-13`,
  `test.yml:3-13`) — matches FACTS "ci" and §10.
- DECISIONS quotes: §2.8 (`DECISIONS_FOR_OPERATOR.md:135-144`), §2.9 (`:148-152`, heading
  `:146`), §2.10 (`:156-162`), §2.11 (`:166-172`) — verbatim. NEEDS-OPERATOR items map 1:1:
  §8 ↔ 2.8 / R15-RELEASE-001; §9 ↔ 2.9, 2.10, 2.11 / R15-RELEASE-002/003/004 (all four
  `blocked_tier4` in FACTS "register"). Nothing in the draft claims signing, notarization, a
  release pipeline or a working updater exists; the draft's §6 correctly says no
  `latest.json`/`.sig` is produced.
- Batch-9 chain table is verbatim from `stage-c/batch-9/VERDICTS.md:33-41`; `a3b8218` is an
  ancestor of the sha (`git merge-base --is-ancestor` → yes).
- `DisclaimerFlow.tsx:4-6` header and `:35` licence sentence ("source-available under PolyForm
  Strict 1.0.0 (noncommercial use) or a commercial license — see LICENSING.md") quoted verbatim;
  `LICENSING.md` exists at the sha. `RC1_GATE_PLAN.md:21` quotes verbatim.
- Tag precedent: `v0.8.0` is an annotated tag object, message `v0.8.0 — Phase 8 deep audit` +
  body (`git cat-file -p v0.8.0`); `git tag --list 'v*' --sort=-creatordate` → v0.8.0, v0.7.0,
  v0.6.5, v0.6.1, v0.6.0, … as the draft lists. `gh release delete <tag>` leaves the tag unless
  `--cleanup-tag`, consistent with §11.
- Product rules: no broker/order/paper/live wording anywhere in the draft; licence split and
  0.9.0 target stated correctly; three PyInstaller sidecars; the clean-profile macOS check is
  assigned to the lead, later. No key, token or keystore content in the draft (the `pubkey` at
  `tauri.conf.json:52` is not copied; `TAURI_SIGNING_PRIVATE_KEY` appears only as a variable
  name inside a verbatim DECISIONS quote).
- Step order is sound once findings 4–6 are applied: bump → install → ci-local (staleness-aware
  ensure) → forced sidecar rebuild → smoke (freshness gate + `/health` version check need the
  post-bump binaries) → tauri build (re-runs ensure, no-op if fresh) → clean-profile check.
