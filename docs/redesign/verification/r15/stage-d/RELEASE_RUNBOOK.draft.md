<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->

# Release Runbook — Vysted Terminal 0.9.0

Reader: the lead or operator cutting the 0.9.0 release, step by step. This draft is sourced
from `docs/redesign/verification/r15/stage-d/FACTS.md` (sha `f4444790`) and the sha's own
scripts/docs. Promoted to `docs/RELEASE_RUNBOOK.md` by the lead at rc2, never by this wave.

## Checklist

- [ ] 0. Prerequisites: `PATH` + sidecar venv activated (§0) — `pnpm ci-local` fails without it
- [ ] 1. Version bump every load-bearing occurrence to `0.9.0`
- [ ] 2. `pnpm install --frozen-lockfile`
- [ ] 3. `pnpm ci-local`
- [ ] 4. Build the three sidecar binaries
- [ ] 5. `node scripts/smoke-test-sidecars.mjs`
- [ ] 6. `pnpm tauri build` (macOS bundles)
- [ ] 7. Clean-profile launch check on macOS (lead, not this wave)
- [ ] 8. Signing and notarization — NEEDS-OPERATOR
- [ ] 9. Tag and GitHub release — operator-only
- [ ] 10. Windows — NEEDS-MANUAL-CHECK
- [ ] 11. Rollback plan understood before cutting

---

## 0. Prerequisites (one shell, before §2)

`pnpm ci-local` (§3) calls bare `python`, `pip`, `pytest`, `cargo`, `ruff` and `node`
(`package.json:22` — see §3's verbatim command). On a stock macOS shell, `python` and
`pytest` are not on `PATH` (`which python python3 pytest ruff cargo node pnpm` at the sha's
toolchain →`python`: not found, `python3`: `/opt/homebrew/bin/python3`, `pytest`: not found,
`ruff`/`cargo`/`node`/`pnpm`: found), so step 3 dies at `python -m pip install
ruff==0.15.12` (`command not found: python`) after already spending the lint/typecheck
minutes. CI does not have this gap — its `python` comes from `actions/setup-python`,
`python-version: "3.13"` (`.github/workflows/test.yml:41`) — so the local mirror needs the
same interpreter made available explicitly:

```
export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH
source sidecar/.venv/bin/activate
```

The sidecar venv is Python 3.13.13 (`sidecar/.venv/bin/python --version`), matching CI;
activating it puts `python`/`pip`/`pytest`/`ruff` on `PATH` for the rest of the shell. Also
confirm before starting:

- `rustc -vV` prints a `host:` line — `scripts/ensure-sidecar.mjs`'s `targetTriple()`
  (`:29-34`) reads the target triple from it to name the sidecar binary; no `rustc` on `PATH`
  fails the sidecar build in §4 with "could not determine host target triple".
- `pnpm --version` is `10.32.1` — pinned in all three CI workflows
  (`.github/workflows/{build,lint,test}.yml`, each `version: 10.32.1`); a different local
  pnpm can resolve dependencies differently than CI.

## 1. Version bump to 0.9.0

What: every load-bearing version string moves from `0.8.0` to `0.9.0` in the same commit.
Who: lead.

**Must-bump — 5 sources** (CLAUDE.md "Versioning & process" names exactly these five: "Version
lives in many sources — `package.json` + `Cargo.toml` + `tauri.conf.json` + sidecar `app.py
FastAPI(version=…)` + `HOST_VERSION` (`plugin-bootstrap.ts`)"):

- `package.json:3` — `"version": "0.8.0"`
- `src-tauri/Cargo.toml:3`
- `src-tauri/tauri.conf.json:4`
- `sidecar/app.py:327` — `FastAPI(version=…)`
- `src/lib/plugin-bootstrap.ts:37` — `HOST_VERSION` const

Then regenerate the lockfile's own version entry (`src-tauri/Cargo.lock:5486-5487`, the
`vysted-terminal` package block):

```
cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml
```

(CLAUDE.md "Versioning & process": "At bump: grep for stale version strings and run
`cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`.")

**Not bump targets.** Every other `0.8.0` occurrence FACTS's `version_occurrences` marks
`[load_bearing]` is a false positive of that tag, not a bump target — verified individually
against the code at the sha:

- `package.json:76` — `prettier-plugin-tailwindcss` pinned to `0.8.0`; an unrelated dep, not
  the app version.
- `src-tauri/Cargo.lock:281,290,758,2426,2443,3351,3368` — seven unrelated-crate
  `version = "0.8.0"` lines (`git grep -n '0\.8\.0' -- src-tauri/Cargo.lock` at the sha finds
  8 hits total: these seven plus `:5487` above).
- `plugins/vysted-lenses/manifest.json:6`, `plugins/vysted-news/manifest.json:6`,
  `plugins/yfinance/manifest.json:6` — each `"requiredHostVersion": "0.8.0"`. This is a
  **minimum-host pin**, not a value that tracks the host version: `checkCompatibility`
  rejects a plugin only when `!hostSatisfies(hostVersion, requiredHostVersion)`
  (`src/lib/plugin-runtime.ts:374-375`), and `hostSatisfies(host, required)` is `host >=
  required` by semver (`:129-138`). `0.9.0` satisfies `0.8.0`, so these three do not need
  editing for this bump; only raise one if that plugin starts requiring a 0.9.0+ host
  feature.
- `sidecar/tests/test_data_cache.py:131,133,141,142,150` — `0.8.0`/`0.8.1` used as arbitrary
  cache-build-tag literals in test fixtures, not the app version (FACTS).
- `src/components/SettingsPanel.test.tsx:831` — a `/system/diagnostics` response fixture,
  `{ version: "0.8.0", logTail: [...] }` (`:830-831`); the test's own assertions (`:839-845`)
  check `preview.textContent` for the `logTail` line and the `writeText`/"Copied" flow — none
  assert the version string, so this `"0.8.0"` is an arbitrary fixture literal, not a bump
  target.
- `src/lib/plugin-runtime.test.ts:498,508,517,542,545,547,550,551,552,555,556` and
  `src/store/marketplace.test.ts:43` — `hostSatisfies`/`PluginRuntime` unit tests that use
  `"0.8.0"` as one arbitrary semver operand to exercise the comparison itself (e.g. `:551`
  `expect(hostSatisfies("0.8.0", "0.9.0")).toBe(false)`); the comparison behaviour is what's
  under test, not the app's actual version — not bump targets.
- `src/lib/plugin-runtime.ts:115` — a doc-comment example string (`written as ">=0.8.0"
  parses to its floor [0,8,0]`), not a version statement.
- `src/lib/workspace.test.ts:1488` — a doc comment, `/** v0.8.0 rows */`, labeling a fixture
  shape, not the app version.

Then the grep that proves nothing load-bearing is left (excludes the historical/prose docs
FACTS itself excluded — CHANGELOG.md, docs/archive, docs/redesign/verification,
docs/screenshots, pnpm-lock.yaml — since those are intentionally-preserved history, not
load-bearing):

```
git grep -n '0\.8\.0' -- . \
  ':!CHANGELOG.md' ':!docs/archive' ':!docs/redesign/verification' \
  ':!docs/screenshots' ':!pnpm-lock.yaml'
```

Expected output at the sha (confirmed by running it): **92 lines**, in two categories, both
expected and not a sign of a missed bump once the five must-bump files above are edited:

- **55 prose hits** — `BLOCKERS.md` (5), `README.md` (3), `docs/CURRENT_STATE.md`,
  `docs/redesign/*` reports, `docs/research/phase-10/*` — historical/narrative, not
  source-of-truth (the README/BLOCKERS/CURRENT_STATE drafts from this same Stage D wave
  carry corrected 0.9.0 prose, promoted separately at rc2).
- **37 source/lock/test/manifest hits**, every one of them confirmed non-bump-target above:
  `package.json` (2: `:3` the version — bumps — and `:76` the dep pin — doesn't),
  `src-tauri/Cargo.lock` (8: `:5487` bumps via `cargo update`, the other 7 don't),
  the three `plugins/*/manifest.json:6` `requiredHostVersion` pins,
  `sidecar/app.py` (1, bumps), `src-tauri/Cargo.toml` (1, bumps),
  `src-tauri/tauri.conf.json` (1, bumps), `src/lib/plugin-bootstrap.ts` (1, bumps),
  `src/lib/plugin-runtime.ts:115`, `sidecar/tests/test_data_cache.py` (5),
  `src/components/SettingsPanel.test.tsx:831`, `src/lib/plugin-runtime.test.ts` (11),
  `src/lib/workspace.test.ts:1488`, `src/store/marketplace.test.ts:43`.

After the bump, the same grep drops from 92 to 87 (the five must-bump lines gone; everything
else on the list above is unchanged by design). A residual still at or near 92, or any hit
against one of the five must-bump paths, means the bump was incomplete.

<!-- VERIFY: re-run this grep after the actual bump commit and confirm the residual is
exactly 87, with no hit against the five must-bump paths — FACTS.md's occurrence list and
this section's counts are the sha's read, not a post-bump grep. -->

### 1b. CHANGELOG entry

`CHANGELOG.md` has a `## vX.Y.Z — <title> (<date>)` heading per release (confirmed:
`:401` `## v0.7.0 — Completion + Polish + Parity (2026-05-17)`, `:649` `## v0.6.5 — …`), and
there is no `## v0.8.0` heading at all (`v0.8.0` was tagged off a docs-only commit,
`f45019f6 docs(release/v0.8.0/H2): 6 new CLAUDE.md gotchas from Phase 8 lessons` — `git log
-1 v0.8.0`). Add `## v0.9.0 — <title> (<date>)` above the newest existing heading, in the
same commit as the version bump, so the file keeps one heading per release with no gap.

§9's tag/Release step has no notes source of its own; this wave produced
`docs/redesign/verification/r15/stage-d/RELEASE_NOTES.draft.md` for that purpose. At rc2,
promote it (drop its line-1 draft marker and this section's own critic footer) and pass it as
the Release body: `gh release create v0.9.0 --notes-file <promoted-path> <assets from §6>` —
operator-only, after §8/§9 are unblocked, or with hand-built §6 assets as §9 already allows.

## 2. Install

What: clean, lockfile-pinned install.
Who: lead.
Command (package.json has no explicit `install` script; this is the standard pnpm entry
CLAUDE.md's `ci-local` chain itself opens with):

```
pnpm install --frozen-lockfile
```

Expected output: exits 0, `Lockfile is up to date, resolution step is skipped` (or the
resolve+link summary) if the lockfile matches `package.json`; a frozen-lockfile mismatch
(e.g. an un-committed version-bump edit to a dependency) fails hard rather than rewriting
the lockfile.

## 3. `pnpm ci-local`

What: the full local mirror of CI. Who: lead.

```
pnpm ci-local
```

Verbatim from `package.json:ci-local` (`FACTS.md`):

```
pnpm install --frozen-lockfile && node scripts/ensure-all-sidecars.mjs && pnpm lint && \
pnpm format:check && pnpm typecheck && \
cargo fmt --manifest-path src-tauri/Cargo.toml --check && \
cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings && \
python -m pip install ruff==0.15.12 && ruff check sidecar && ruff format --check sidecar && \
pnpm test && cargo test --manifest-path src-tauri/Cargo.toml && \
cd sidecar && python -m pip install -r requirements-dev.txt && pytest
```

CLAUDE.md: "`pnpm ci-local` mirrors CI byte-for-byte … If it's skipped or red at tag time,
the tag is invalid."

Expected output: no full `ci-local` run exists yet at this sha (rc1 has not run —
`docs/redesign/verification/r15/rc1/` does not exist in the tree at `f4444790`). The
closest real per-gate evidence is the Stage C batch-9 verifier's independent re-run of the
individual gates against the merged code (`docs/redesign/verification/r15/stage-c/batch-9/
VERDICTS.md:33-40`, "Chain observed at the target (`a3b8218`, verifier re-run)"):

| Gate | Result |
| ---- | ------ |
| `pnpm exec vitest run` (full) | 141 files, 1683 tests passed, EXIT 0 |
| `pnpm typecheck` / `pnpm lint` / `pnpm format:check` | EXIT 0 / 0 / 0 |
| `pytest` (sidecar, full) | 2962 passed, 1 skipped, EXIT 0 |
| `ruff check` / `ruff format --check` | "All checks passed!" / "419 files already formatted" |
| cargo | no `src-tauri/` diff in that batch, unchanged from base |

This is not a literal `pnpm ci-local` invocation (it is per-gate, run by the batch-9
verifier from a scratch worktree, not the single composed script) and predates later
batches (through batch-9 only, per FACTS's `git` section).

<!-- fill at rc2: expected output from the lead's actual `pnpm ci-local` run at the
release-candidate sha -->

## 4. Sidecar builds

What: build the three PyInstaller `--onefile` sidecar binaries.
Who: lead.

```
VYSTED_SKIP_DEV_SIGN=1 pnpm sidecars:build
```

equivalent to (`package.json:sidecars:build`):

```
VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-all-sidecars.mjs --force
```

`VYSTED_SKIP_DEV_SIGN=1` matters: every ensure script signs its output after the copy
(`scripts/ensure-sidecar.mjs:207 signDevBinary(outPath, "com.vysted.sidecar")`, and the
openbb/sec-edgar equivalents, `:202`/`:194`), and `signDevBinary`
(`scripts/macos-dev-sign.mjs:36-40`) runs `codesign` with the lead's local 5-year self-signed
"Vysted Terminal Dev Signing" identity (`CLAUDE.md` "macOS keychain re-prompts…" gotcha,
`scripts/macos-dev-setup.sh`) whenever that identity is present in the login keychain, and is
skipped only on non-Darwin, a missing identity, or this env var (`:37-40`). Without it, the
three `externalBin` payloads that ship inside the release bundle (§6) carry a signature from
a dev-only cert — never intended for shipping. With the env var set, the build log should
NOT show `[dev-sign] signed …` (`macos-dev-sign.mjs:45`) for any of the three binaries; if it
does, the skip did not take effect and the binaries are dev-signed.

`scripts/ensure-all-sidecars.mjs` is an orchestrator that runs each per-sidecar script in
sequence and aborts on the first non-zero exit (source at the sha):

```
scripts/ensure-sidecar.mjs
scripts/ensure-openbb-mcp-sidecar.mjs
scripts/ensure-sec-edgar-mcp-sidecar.mjs
```

logging `[ensure-all-sidecars] → node <script> [--force]` per step and
`[ensure-all-sidecars] all sidecars present.` on success (script source, `ensure-all-sidecars.mjs`).

Where each lands (per-script header comments at the sha, `bundle.externalBin` in
`src-tauri/tauri.conf.json:41-44`):

| Binary | ensure script | Output path |
| ------ | -------------- | ----------- |
| `vysted-sidecar` | `scripts/ensure-sidecar.mjs` | `src-tauri/binaries/vysted-sidecar-<target-triple>[.exe]` |
| `vysted-openbb-mcp-sidecar` | `scripts/ensure-openbb-mcp-sidecar.mjs` | `src-tauri/binaries/vysted-openbb-mcp-sidecar-<target-triple>[.exe]` |
| `vysted-sec-edgar-mcp-sidecar` | `scripts/ensure-sec-edgar-mcp-sidecar.mjs` | `src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-<target-triple>[.exe]` |

`tauri build` resolves `bundle.externalBin` (`binaries/vysted-sidecar`,
`binaries/vysted-openbb-mcp-sidecar`, `binaries/vysted-sec-edgar-mcp-sidecar`,
`tauri.conf.json` `bundle.externalBin` at the sha) against these triple-suffixed files, so
this step must run — and succeed for all three — before step 6.

Expected output: each per-sidecar script logs `[ensure-<name>] building <outName> ...` then
`[ensure-<name>] wrote <outPath>` and `[ensure-<name>] done.` on a fresh build, or
`[ensure-<name>] <outName> present and fresh — skipping build.` if already built and
current (script source, all three ensure-*.mjs files).

<!-- fill at rc2: expected output from the lead's actual sidecar build run at the
release-candidate sha (no logged sidecar-build output exists at f4444790) -->

## 5. Sidecar smoke test

What: boots each built binary and probes it live — catches the PyInstaller `--onefile`
runtime-drop class of bug that `ci-local`'s source-level `pytest`/`tauri build` packaging
cannot ("v0.6.5 shipped a vysted-sidecar binary that crashed at startup with
`PackageNotFoundError: fastmcp`", `scripts/smoke-test-sidecars.mjs` header comment at the
sha). Who: lead.

```
node scripts/smoke-test-sidecars.mjs
```

CLAUDE.md: "`node scripts/smoke-test-sidecars.mjs` catches the binary-runtime gap `ci-local`
can't see (spawns each built sidecar, polls `/health`, checks MCP subprocesses survive)."

Per the script's own comment header at the sha: for `vysted-sidecar` it spawns on a fresh
ephemeral port, polls `/health` until `MAIN_BOOT_TIMEOUT_MS`, then asserts `/health` version
matches `package.json`, the screener-universe endpoint, the ICONIKSPEV deterministic
resolve, the `/agents` roster (count > 0, `agents_degraded` empty), `/mcp/status`, and (a
no-SLA probe) `/history/ICONIKSPEV`; for each MCP subprocess sidecar it TCP-probes the bound
port and confirms it survives a settle window. It tree-kills only processes its own run's
PID ledger recorded (never the operator's live app).

Success message (script source, `smoke-test-sidecars.mjs`): `[smoke] all sidecars booted
cleanly.` Failure: `[smoke] FAILURES:` followed by each failure line, exit 1.

The script first refuses any binary older than its source (`_assertAllFresh`, :870, called
at :912, log line `[smoke] freshness gate: all bundled sidecar binaries are newer than their
source.` at :898) — re-run §4 after any later sidecar or ensure-script edit, or this step
fails on staleness before it boots anything.

<!-- fill at rc2: expected output from the lead's actual smoke-test run at the
release-candidate sha (no logged smoke-test output exists at f4444790) -->

## 6. `pnpm tauri build` (macOS)

What: produce the installable macOS bundles.
Who: lead.

```
VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build
```

`beforeBuildCommand` re-runs `node scripts/ensure-all-sidecars.mjs` (`tauri.conf.json:10`,
no-op if §4 already built fresh binaries) before `pnpm build`, so the same
`VYSTED_SKIP_DEV_SIGN=1` guard from §4 applies here too — omit it and a re-triggered ensure
run signs the sidecar binaries with the lead's local dev identity again.

`bundle.targets` at the sha (`src-tauri/tauri.conf.json` `bundle`) is
`["deb", "appimage", "nsis", "app", "dmg"]` — on macOS this resolves to the `app` and `dmg`
targets, producing:

- `src-tauri/target/release/bundle/macos/Vysted Terminal.app`
- `src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_<arch>.dmg`

<!-- VERIFY: the exact dmg filename pattern (version + arch suffix) — read from an actual
tauri build run at the sha; not directly quoted from any file read in this wave. -->

`bundle.createUpdaterArtifacts` is `false` at this sha (`tauri.conf.json`), so no
`latest.json`/`.sig` is produced by this step — see §8/§9 on the updater and release
pipeline, both blocked pending operator sign-off.

## 7. Clean-profile launch check (macOS)

What: launch the just-built `.app` against a fresh app-data directory and confirm first-run
terms, keyless mode and sidecar warm-up. Who: **the lead**, performed later from a clean
profile — **not performed by this Stage D wave** (per this wave's own brief: "The macOS
production build is proven from a clean profile later by the lead, not by this wave.").

What to check, per the code at the sha:

- **First-run terms**: `src/modules/safety/DisclaimerFlow.tsx` — "the first-launch research
  terms (onboarding gate)," keychain-backed via
  `KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")` (file header comment,
  `DisclaimerFlow.tsx:4-6`); its body states "Vysted Terminal is source-available under
  PolyForm Strict 1.0.0 (noncommercial use) or a commercial license — see LICENSING.md."
  (`DisclaimerFlow.tsx:35`). **A fresh app-data directory alone does NOT reset this ack for
  a release build.** The ack is persisted in the OS keychain (`src/store/safety.ts:4-9,17`
  `FIRST_LAUNCH_TOS_ACCOUNT = KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")`), and which
  backend the Rust side uses is chosen at **build time**: a release build
  (`cfg(not(debug_assertions))`) is the login/OS keychain, service `"vysted-terminal"`
  (`src-tauri/src/keychain.rs:6-10,37`); the local JSON file keystore
  (`<app-data-dir>/dev-keystore.json`) exists only in debug builds
  (`keychain.rs:11-23,45 USE_DEV_KEYSTORE = cfg!(debug_assertions)`). So for the `pnpm tauri
  build` `.app` this step produces, the ack lives in the lead's login keychain, not under the
  app-data directory — if that keychain item is already present from a prior run, the dialog
  will not show and the check passes for the wrong reason. Before launch, check (read-only,
  never `-w`, never print the value):

  ```
  security find-generic-password -s vysted-terminal -a app-meta:first-launch-terms
  ```

  If present, either delete it (and the onboarding-complete flag,
  `keychain.ts:101` `app-meta:onboarding-complete`) or run the check as a separate macOS
  user:

  ```
  security delete-generic-password -s vysted-terminal -a app-meta:first-launch-terms
  security delete-generic-password -s vysted-terminal -a app-meta:onboarding-complete
  ```

  The same applies to every BYOK key stored under the `vysted-terminal` service: a release
  `.app` launched this way reads the operator's real keychain, so the run is not "keyless"
  unless those items are absent too. RC1's precedent (below) only worked keyless because it
  launched a **debug** bundle, whose keystore is the isolated file, not this keychain.
- **Keyless mode / sidecar warm-up**: no direct evidence was read in this wave beyond the
  smoke-test's own `/health` and `/agents` probes (§5). RC1's GUI phase is the actual
  attended-app precedent for the debug-build path — see `docs/redesign/verification/r15/
  tooling/RC1_GATE_PLAN.md` phase 5, which launches "a `tauri build --debug` bundle … with
  `HOME=` an isolated profile whose keystore reads `migrated: true`" and never touches "the
  operator's real data dir, caches, WebKit store and keychain." That isolation comes from the
  debug keystore file, not from the app-data directory alone — see the keychain note above
  before assuming the same isolation on a release `.app`.

<!-- fill at rc2: the lead's actual clean-profile run — screenshots, /health output, and
confirmation the terms dialog appeared -->

## 8. Signing and notarization — NEEDS-OPERATOR

What: every desktop bundle currently ships **unsigned**. A downloaded `.dmg` is refused by
Gatekeeper as "damaged"; the NSIS installer is flagged by SmartScreen before the app opens.
Who: **NEEDS-OPERATOR** (Tier-4 — `docs/redesign/DECISIONS_FOR_OPERATOR.md §2.8`,
R15-RELEASE-001).

Quoted verbatim from `DECISIONS_FOR_OPERATOR.md:133-142`:

> **Blocked:** every desktop bundle ships unsigned on macOS and Windows; a downloaded `.dmg`
> is refused by Gatekeeper as "damaged" and the NSIS installer is flagged by SmartScreen
> before the app ever opens.
>
> **Why Tier-4:** the fix edits `src-tauri/tauri.conf.json` (`bundle.macOS.signingIdentity`,
> `bundle.windows.signCommand`/`certificateThumbprint`) and needs paid credentials (an Apple
> Developer ID + notarization, a Windows code-signing certificate) — a locked file plus money
> and identity decisions, not code.
>
> **Smallest unblock:** at minimum set `bundle.macOS.signingIdentity: "-"` for an ad-hoc seal
> (turns "damaged" into the Open-Anyway path) — still a `tauri.conf.json` edit, so still needs
> your sign-off even for that minimal step.

Until the operator acts, the macOS bundle stays unsigned (Gatekeeper "damaged," workaroundable
only via the ad-hoc-seal minimal unblock above, itself still gated on sign-off since
`tauri.conf.json` is Tier-1) and the Windows bundle stays unsigned (SmartScreen warning on
every install).

Inner sidecar binaries (the three `externalBin` payloads): ad-hoc/linker-signed only when
§4/§6 were run with `VYSTED_SKIP_DEV_SIGN=1` as instructed; otherwise they carry the lead's
local dev-only signing identity (§4) — neither is a substitute for the outer-bundle signing
this section blocks on.

## 9. Tag and GitHub release — operator-only

What: cut the `v0.9.0` tag and publish a GitHub Release with installable assets.
Who: **operator runs this.**

**Precedent for tag format** (existing tags, e.g. `v0.8.0`): an annotated tag,
`tagger`/message form `<version> — <one-line description>` followed by a short changelog
body (`git cat-file -p v0.8.0`). Operator runs, e.g.:

```
# operator runs this
git tag -a v0.9.0 -m "v0.9.0 — <summary>"
git push origin v0.9.0
```

**No release pipeline exists yet** — Tier-4, `DECISIONS_FOR_OPERATOR.md §2.9`,
R15-RELEASE-002. Quoted verbatim (`DECISIONS_FOR_OPERATOR.md:146-152`):

> **Blocked:** pushing a `v*` tag produces no Release and no downloadable asset.
>
> **Why Tier-4:** the fix is a new `.github/workflows/release.yml` — `.github/` is Tier-1.
>
> **Smallest unblock:** approve adding `.github/workflows/release.yml` (3-OS matrix build via
> `tauri-apps/tauri-action`, `createUpdaterArtifacts: true`, `TAURI_SIGNING_PRIVATE_KEY`
> wired) so `latest.json` + `.sig` are attached; this also unblocks 2.10.

Until that workflow exists and is approved, tags `v0.6.0`..`v0.8.0` "have zero installable
builds" (§2.9 heading) and a `v0.9.0` tag will be no different: pushing the tag alone
produces no Release. The operator must approve `.github/workflows/release.yml` before this
step produces anything downloadable; until then, a Release (if the operator wants one)
would need bundles built locally (§6) and attached by hand.

**Auto-updater** — also blocked, Tier-4, `DECISIONS_FOR_OPERATOR.md §2.10`,
R15-RELEASE-003. Quoted verbatim (`DECISIONS_FOR_OPERATOR.md:154-162`):

> **Blocked:** the updater is registered and configured but never invoked, so no install can
> ever leave its install-day version, including past a security fix.
>
> **Why Tier-4:** the producer half needs `createUpdaterArtifacts: true` in
> `src-tauri/tauri.conf.json` and the release workflow from 2.9 (`.github/`).
>
> **Smallest unblock:** approve 2.9 first (it produces `latest.json`/`.sig`), then the
> `tauri.conf.json` flag; the consumer-side `app.updater()?.check()` call itself is not
> Tier-4 and can ship independently once the producer side exists.

So a v0.9.0 install will not be reachable by the auto-updater from any prior install, and
will not itself be auto-updatable, until §2.9 and §2.10 are both approved.

**CI has never run on `004-r4-experience-rebuild`** — Tier-4,
`DECISIONS_FOR_OPERATOR.md §2.11`, R15-RELEASE-004. Quoted verbatim
(`DECISIONS_FOR_OPERATOR.md:164-171`):

> **Blocked:** 654 commits (R4–R15) bypass GitHub Actions entirely on this branch; the newest
> cross-OS signal on `main` (2026-05-30) is a red lint run.
>
> **Why Tier-4:** the fix is either a `.github/` push-trigger edit, or opening a PR against
> `main` (a repo/process decision, not a code change this batch can make unilaterally).
>
> **Smallest unblock:** open a draft PR for `004-r4-experience-rebuild` (no workflow edit
> needed for this option) so the existing `pull_request` trigger runs the 3-OS matrix; fix
> the red lint on `main` first so the signal is meaningful.

Practically: before tagging, the operator should have real 3-OS CI signal on the
release-candidate tree, not just this wave's local `ci-local`/smoke evidence — none exists
yet on `004-r4-experience-rebuild` at this sha.

## 10. Windows — NEEDS-MANUAL-CHECK

**Nobody has verified a Windows build or install of this branch.** Prerequisites and bundle
targets from the sha's own config/CI, not from a real Windows run:

- CI declares a `windows-latest` leg in all three workflows (`.github/workflows/build.yml`,
  `lint.yml`, `test.yml` — `FACTS.md` `ci` section), but per §9/R15-RELEASE-004 those
  workflows have never actually executed on `004-r4-experience-rebuild`.
- `bundle.targets` includes `nsis` (`tauri.conf.json` `bundle.targets`) — the Windows
  installer target.
- Signing is unresolved for Windows too (§8, R15-RELEASE-001: "`bundle.windows.signCommand`/
  `certificateThumbprint`" needs "a Windows code-signing certificate" not yet obtained) —
  SmartScreen will flag the NSIS installer on every install until that lands.
- `keyring` Rust crate v3 needs the `windows-native` backend feature explicitly enabled
  (CLAUDE.md Gotcha: "`set_password` silently no-ops on a default-features build") — confirmed
  at the sha: `src-tauri/Cargo.toml:34` carries it (`keyring = { version = "3", features =
  ["apple-native", "windows-native", "sync-secret-service", "crypto-rust"] }`).
- The three PyInstaller sidecars must each build and smoke-test cleanly on Windows (§4/§5)
  — none of this wave's evidence (Stage C batch-9 chain, this wave's own reads) covers a
  Windows run; no Windows run evidence exists in the register at this sha.
- `sidecar/tests/test_search_extract.py:467` already passes `encoding="utf-8"` to the one
  `fixture.read_text(...)` call in that file, and no bare (no-`encoding`) `.read_text()` call
  remains anywhere under `sidecar/tests/` at this sha (`git grep -n '\.read_text(' --
  sidecar/tests/` at the sha: the only hit without `encoding=` is a docstring reference, not a
  call) — pinned by a dedicated AST-scan regression test,
  `sidecar/tests/test_tests_encoding.py`, whose docstring names it as the fix for
  `R15-CROSS-PLATFORM-002`. The register (`docs/redesign/verification/vysted-r15-register.json`)
  still shows that entry `"status": "open"` at this sha; the code disagrees. Not listed here as
  an active red-on-Windows risk — see the critic-findings footer for why.

<!-- fill at rc2: an actual Windows build + install + smoke-test run, or an explicit
decision to ship 0.9.0 macOS/Linux-only pending that verification -->

## 11. Rollback

**Pulling a published release**: delete or "yank" the GitHub Release and its assets
(`gh release delete v0.9.0`), leaving the git tag in place unless the operator also wants it
gone (`git tag -d v0.9.0 && git push origin :refs/tags/v0.9.0`) — operator-only, same as §9.

**Reverting the version bump**: revert the version-bump commit from §1
(`git revert <bump-commit-sha>`), which returns every load-bearing file to `0.8.0`, then
re-run `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml` to
sync `Cargo.lock` back down.

**Restoring the previous tag's build**: `git checkout v0.8.0` (or any prior `vX.Y.Z` tag,
`git tag --list 'v*' --sort=-creatordate` at the sha: v0.8.0, v0.7.0, v0.6.5, v0.6.1, v0.6.0,
…) into a clean worktree and re-run §2-§6 from that tree. Per §9/R15-RELEASE-002, none of
`v0.6.0`..`v0.8.0` has an installable build published via GitHub Releases — "rollback" for
an operator without a locally-built prior bundle means rebuilding from that older tag's
source, not re-downloading a prior release asset.

<!-- VERIFY: whether the operator keeps any locally-built prior .dmg/.app on hand outside
this repo — not something this read-only wave can check. -->

<!-- critic-footer -->

## Critic findings applied

1. applied — split the load-bearing list into the 5 must-bump sources and an explicit
   not-bump-target list covering the 3 manifest `requiredHostVersion` pins (with the
   `hostSatisfies`/`checkCompatibility` semantics that make them non-bump), corrected
   "two rows"/"five" to the verified 1 manifest-set / 7 Cargo.lock rows.
2. applied — §1 now states the 5 must-bump sources per CLAUDE.md and explicitly lists the
   11 `plugin-runtime.test.ts`/`marketplace.test.ts` lines plus `SettingsPanel.test.tsx:831`
   as non-bump literals, with the SettingsPanel assertion text verified against the file
   (`:839-845` asserts logTail/Copied/writeText, not the version).
3. applied — replaced the "no hits"/"~90" claim with the exact confirmed count (92 lines,
   55 prose + 37 source/lock/test/manifest, verified by running the grep at the sha) and an
   explicit post-bump expected count (87).
4. applied — added §0 Prerequisites (PATH export + sidecar venv activation, `rustc -vV`,
   pnpm 10.32.1) before §2, sourced from the toolchain probe and CI's `setup-python` step.
5. applied — rewrote §7's first-run-terms bullet: release build uses the login OS keychain
   (`keychain.rs:6-10,37`), a fresh app-data dir does not reset it, added the read-only
   `security find-generic-password` check and the delete/alternate-user workaround, and
   noted RC1's precedent was the debug-build (file-keystore) path, not this one.
6. applied — added `VYSTED_SKIP_DEV_SIGN=1` to both the §4 and §6 commands, explained why
   (the ensure scripts' `signDevBinary` call and the dev-sign identity), and added the
   inner-binary signing-status line to §8.
7. applied — added §1b (CHANGELOG `## v0.9.0` heading, added in the bump commit) and wired
   §9's Release-body source to `RELEASE_NOTES.draft.md`, promoted at rc2.
8. applied — added the freshness-gate note to §5 (`_assertAllFresh` at `:870`, called
   `:912`, log line `:898`) with the re-run-§4-after-any-later-edit instruction.
9. rejected: the finding's own suggested addition is factually wrong at this sha. Verified
   `sidecar/tests/test_search_extract.py:467` already reads
   `fixture.read_text(encoding="utf-8")`, `git grep '\.read_text(' -- sidecar/tests/` at the
   sha finds no remaining bare call, and `sidecar/tests/test_tests_encoding.py` is a
   dedicated AST-scan regression test whose docstring names it as the fix for
   `R15-CROSS-PLATFORM-002` — its closure commit `6b70230` is confirmed an ancestor of this
   sha (`git merge-base --is-ancestor 6b70230 f4444790` → yes). The register JSON still
   carries `"status": "open"` for that id at this sha (no `closure_evidence` field yet — a
   bookkeeping lag, not an active defect); adding the critic's suggested Windows-red bullet
   would put a now-false claim in the runbook. §10 instead states the corrected, verified
   status and flags the register/code disagreement rather than asserting either "open" or
   "fixed" outright.
10. applied — replaced "confirm … carries it" with the confirmed line-34 quote from
    `src-tauri/Cargo.toml` at the sha.
11. no_change_needed — the VERIFY marker in §6 was already correct per the critic; left as
    is.
