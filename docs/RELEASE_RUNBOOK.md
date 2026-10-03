# Release Runbook — Vysted Terminal 0.9.0

Reader: the lead or operator cutting the 0.9.0 release, step by step. Sourced from
`docs/redesign/verification/r15/stage-d/FACTS.md` (sha `4d893147`) and the sha's own
scripts/docs; promoted here ahead of rc2 as docs-promotion pass 1. The merge-to-main and
`v0.9.0` tag step below (§9) is written for the operator and is not executed by this
promotion — nothing in this document has been run against a release-candidate sha yet. §4/§5's
`<!-- fill at rc2 -->` markers record real build/smoke evidence still pending the actual
release-candidate run; refresh this file once that evidence exists.

## Checklist

- [ ] 0. Prerequisites: `PATH` + sidecar venv activated (§0) — `pnpm ci-local` fails without it
- [ ] rc gate round 2 verdict PASS at the candidate sha (confirmed at the tag)
- [ ] 1. Confirm the five version sources read `0.9.0` (no merge step; the bump is in the candidate)
- [ ] 2. `pnpm install --frozen-lockfile`
- [ ] 3. `pnpm ci-local`
- [ ] 4. Build the three sidecar binaries
- [ ] 5. `node scripts/smoke-test-sidecars.mjs`
- [ ] 6. `pnpm tauri build` (macOS bundles)
- [ ] 7. Clean-profile launch check on macOS (lead, not this wave)
- [ ] 8. Signing and notarization — NEEDS-OPERATOR (re-run §6/§7 if a signing change lands)
- [ ] §2.18 commercial-licence contact swapped from the placeholder before any public
      0.9.0 announcement — NEEDS-OPERATOR
- [ ] 9. Tag (at the gated sha) and GitHub release — operator-only
- [ ] 10. Windows — NEEDS-MANUAL-CHECK
- [ ] 11. Rollback plan understood before cutting

---

## 0. Prerequisites (one shell, before §2)

`pnpm ci-local` (§3) calls `python3 -m pip`, then bare `ruff`, `pytest`, `cargo` and `node`
(`package.json` `ci-local` — see §3's verbatim command). On a stock macOS shell `pytest` and
`ruff` are not on `PATH` until the sidecar venv is active, so step 3 dies at `ruff check
sidecar` (or `pytest`) with `command not found` after already spending the lint/typecheck
minutes. CI does not have this gap — its Python comes from `actions/setup-python`,
`python-version: "3.13"` (`.github/workflows/test.yml:41`) — so the local mirror needs the
same interpreter made available explicitly:

```
export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH
source sidecar/.venv/bin/activate
```

**In a fresh checkout or worktree, `sidecar/.venv` does not exist yet** — it is created by
`ensureBuildVenv` (`scripts/sidecar-specs.mjs:258-266`), which §3's own `pnpm ci-local`
(`node scripts/ensure-all-sidecars.mjs`) and §4's sidecar build both call. Run §3 or §4
first (either one creates `sidecar/.venv` on Python 3.13 from `requirements-dev.txt`), then
come back and `source sidecar/.venv/bin/activate` before re-running §3 for a real gate
(confirmed against a rehearsal on a fresh worktree at `64e9470e`,
`stage-d/bundle-rehearsal/REHEARSAL.md` correction 1).

The sidecar venv is Python 3.13.13 (`sidecar/.venv/bin/python --version`), matching CI;
activating it puts `python`/`pip`/`pytest`/`ruff` on `PATH` for the rest of the shell. Also
confirm before starting:

- `rustc -vV` prints a `host:` line — `scripts/sidecar-specs.mjs`'s `targetTriple()`
  (`:190-195`) reads the target triple from it to name the sidecar binary; no `rustc` on
  `PATH` fails the sidecar build in §4 with `"could not determine host target triple from
\`rustc -vV\`"` (`:193`).
- `pnpm --version` is `10.32.1` — pinned in all three CI workflows
  (`.github/workflows/{build,lint,test}.yml`, each `version: 10.32.1`); a different local
  pnpm can resolve dependencies differently than CI.

## 1. Version — already 0.9.0

No version-bump step remains. The bump landed on the integration branch (`06879089`), so
the five load-bearing sources already read `0.9.0` at the candidate: `package.json:3`,
`src-tauri/Cargo.toml` (+ `Cargo.lock`), `src-tauri/tauri.conf.json`, `sidecar/app.py`
`FastAPI(version=…)` and `HOST_VERSION` in `src/lib/plugin-bootstrap.ts`. The superseded
`worktree-agent-r15-version-0.9.0` branch is NOT merged; do not merge it. Confirm with
`git grep -n '"0\.9\.0"' -- package.json src-tauri/tauri.conf.json src/lib/plugin-bootstrap.ts`
and the smoke test's `/health` version assertion (§5), which fails if any source drifts.
The `requiredHostVersion` pins in `plugins/*/manifest.json` are a floor, not a bump target:
leave them.

### 1b. CHANGELOG entry

`CHANGELOG.md` has a `## <title> (<date>)` heading per release/batch entry — the newest at
this sha is `:7` `## R15 Stage C — batch 17: citation guard seeded from history, humanised
tool names and cross-line dump drop; partial tool-call marker hold (2026-09-25)`, one of 16
Stage-C batch headings (`git show S:CHANGELOG.md | grep -c '^## R15 Stage C — batch'`
= 16, batch 2 through batch 17) plus "R15 rc1 gate — round 1" (`:209`) and "R15 Stage C — trading
removed (D81, 2026-09-23)" (`:669`) added since `r13-bedrock` (per FACTS's Git section). The
last real numbered-version heading is `:760` `## v0.7.0 — Completion + Polish + Parity
(2026-05-17)` (`:1008` `## v0.6.5 — …`), and there is still no `## v0.8.0` heading at all
(`v0.8.0` was tagged off a docs-only commit, `f45019f6 docs(release/v0.8.0/H2): 6 new
CLAUDE.md gotchas from Phase 8 lessons` — `git log -1 v0.8.0`). Add `## v0.9.0 — <title>
(<date>)` above the current newest heading (the batch-17 line, or whatever Stage-C/gate entry
is newest by the time this is promoted), in the same commit as the version bump, so the file
keeps one heading per release with no gap.

§9's tag/Release step has no notes source of its own; this wave produced
`docs/redesign/verification/r15/stage-d/RELEASE_NOTES.draft.md` for that purpose. At rc2,
promote it — drop its line-1 DRAFT marker and its trailing `<!-- refresh ... -->` comment,
and fill or remove every remaining `<!-- fill at rc2 -->` marker — and pass it as the
Release body: `gh release create v0.9.0 --notes-file <promoted-path> <assets from §6>` —
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

Verbatim from `package.json:ci-local` (one command, `&&`-joined; wrapped here with `\`):

```
pnpm install --frozen-lockfile && \
node scripts/ensure-all-sidecars.mjs && \
pnpm lint && \
pnpm format:check && \
pnpm typecheck && \
cargo fmt --manifest-path src-tauri/Cargo.toml --check && \
cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings && \
python3 -m pip install ruff==0.15.12 && \
ruff check sidecar && \
ruff format --check sidecar && \
vitest run --coverage && \
cargo test --manifest-path src-tauri/Cargo.toml && \
cd sidecar && \
python3 -m pip install -r requirements-dev.txt && \
pytest
```

`pnpm lint` itself changed at this sha: `package.json`'s `lint` script is now `"eslint . &&
node scripts/audit-design-tokens.mjs"` (was bare `eslint .`) — the new second half is the R9
design-token audit (`scripts/audit-design-tokens.mjs` header comment: enforces
`R9_DESIGN_SYSTEM.md`'s spacing-step and dead-type-size rules over `src/` and `plugins/`,
failing on an arbitrary/off-grid Tailwind value with no `tokens-ok:` justification comment).
It runs in `--report`-less (enforcing) mode as part of `pnpm lint`, so a step-3 lint failure
can now also be a design-token violation, not only an ESLint one.

CLAUDE.md: "`pnpm ci-local` mirrors CI byte-for-byte … If it's skipped or red at tag time,
the tag is invalid."

Expected output: no full `ci-local` run exists yet against the release-candidate sha itself
(that sha does not exist until the rc gate's final round). `R15_GATE_RC1.md` (round 1,
verdict **FAIL**, candidate `1d6511c89bb27f1785f7af4d2290983b2852d70a`, "Do not tag rc1")
records the most recent full-chain run on record: item 4, "`ci-local` — **PASS** —
... vitest 1825/1825, cargo 19, pytest 3150 passed and 1 skipped, `EXIT=0`" (`:18`), and
item 5, "`smoke` — **PASS** — ... `SMOKE_EXIT=0` ... 3 sidecars, 13 agents, mcp toolCount 40"
(`:19`, at `1d6511c8`). That candidate is superseded — its own register carried 631 entries
against this sha's 652 (FACTS's Register section), i.e. it predates roughly a dozen later
Stage-C batches, and the round's overall FAIL verdict was on other gate items (register
conformance, agent scenarios, owner-drives, the fixed-name battery), not on `ci-local` or
`smoke`. No `r15-rc1` tag exists yet; gate round 2 launches once batch-24 merges.

The most recent Stage-C integrator chain in the tree, closer to this sha, is batch-23's:
`docs/redesign/verification/r15/stage-c/batch-23/VERDICTS.md:12-15` — "ci2 `CI_EXIT=0`
(3471 passed, 1 skipped). ci1 was red only on format:check, which the newline commit fixes
... smoke `SMOKE_EXIT=0`" at `worktree-agent-batch-23-int@9aa9fb6c`. (Batch-16's and
batch-22's integrator chains are the same pattern and also green:
`batch-16/VERDICTS.md:5` `CI_EXIT=0`, 3271 passed, 1 skipped;
`batch-22/VERDICTS.md:13-16` `CI_EXIT=0`, 3456 passed, 1 skipped, plus `SMOKE_EXIT=0`.)
These are all **integration-branch runs on a batch's own merged tree, not the release
candidate** — each batch's own verifier separately found the model behaviour underneath
that green chain still blocking (batch-22 and batch-23 both verdict "block" on
R15-LEAD-035-class regressions), so a green `ci-local`/smoke chain here is necessary but not
sufficient evidence for a tag.

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

**Build mechanism changed at this sha** (register `R15-CODE-PLATFORM-026`, status `fixed`):
the three PyInstaller command lines used to be hand-duplicated across
`scripts/ensure-sidecar.mjs`, `scripts/ensure-openbb-mcp-sidecar.mjs` and
`scripts/ensure-sec-edgar-mcp-sidecar.mjs` (~90 of ~190 lines identical per file); they now
all read one table, `SIDECAR_SPECS`, in `scripts/sidecar-specs.mjs` (header comment: "The one
table of what each sidecar binary is built from, and the one builder that turns a row into a
binary"). Each per-sidecar script is now a thin wrapper — e.g. `scripts/ensure-sidecar.mjs`
in full:

```
import { SIDECAR_SPECS, buildSidecar } from "./sidecar-specs.mjs";
buildSidecar(SIDECAR_SPECS.find((s) => s.name === "vysted-sidecar"), { force: process.argv.includes("--force") });
```

and `scripts/ensure-all-sidecars.mjs` loops `SIDECAR_SPECS` directly rather than spawning the
three child scripts:

```
import { SIDECAR_SPECS, buildSidecar } from "./sidecar-specs.mjs";
for (const spec of SIDECAR_SPECS) buildSidecar(spec, { force });
```

logging `[ensure-all-sidecars] → <spec.name>[ --force]` per step and, per spec,
`[ensure-<name>] building <outName> ...` then `[ensure-<name>] wrote <outPath>` and
`[ensure-<name>] done.` on a fresh build, or `[ensure-<name>] <outName> present and fresh —
skipping build.` if already built and current (`buildSidecar`, `sidecar-specs.mjs`), where
`<name>` is `spec.name` with its `vysted-` prefix stripped (`sidecar-specs.mjs:236`:
`` const tag = `[ensure-${spec.name.replace(/^vysted-/, "")}]` `` ) — the three real tags are
`[ensure-sidecar]`, `[ensure-openbb-mcp-sidecar]` and `[ensure-sec-edgar-mcp-sidecar]`; it
aborts on the first spec that throws (`ensure-all-sidecars.mjs`: `catch (err) { … process.exit(1); }`).

Two staleness bugs this consolidation fixed (both `fixed` in the register, relevant because
they'd otherwise silently ship a stale binary): `R15-RELEASE-005` — the staleness gate used to
allow-list source extensions (`\.(py|txt|toml|cfg|ini|json|csv)$`), so regenerating a bundled
`.json.gz` data seed never tripped a rebuild; it is now a deny-list (`IGNORE_FILE =
/\.(pyc|pyo|log)$|^\.DS_Store$/i`, `sidecar-staleness.mjs`) — every source file is build input
by default. `R15-RELEASE-006` — the CI freshness gate used to hand-copy each sidecar's
staleness config separately from the build; both now read the same `spec.stale` off
`SIDECAR_SPECS` (`sidecar-specs.mjs` `assertAllFresh`), so the gate cannot certify a different
source set than the build actually used.

`VYSTED_SKIP_DEV_SIGN=1` still matters: `buildSidecar` calls `signDevBinary(outPath,
spec.identifier)` unconditionally after the binary copy (`sidecar-specs.mjs`, step 4), and
`signDevBinary` (`scripts/macos-dev-sign.mjs:36-46`) runs `codesign` with the lead's local
5-year self-signed "Vysted Terminal Dev Signing" identity (`CLAUDE.md` "macOS keychain
re-prompts…" gotcha, `scripts/macos-dev-setup.sh`) whenever that identity is present in the
login keychain, and is a no-op only on non-Darwin, a missing identity, or this env var
(`macos-dev-sign.mjs:37-40`). Without it, the three `externalBin` payloads that ship inside
the release bundle (§6) carry a signature from a dev-only cert — never intended for shipping.
With the env var set, the build log should NOT show `[dev-sign] signed …`
(`macos-dev-sign.mjs:45`) for any of the three binaries; if it does, the skip did not take
effect and the binaries are dev-signed.

Where each lands (`sidecar-specs.mjs` `binaryPath()`; `bundle.externalBin` in
`src-tauri/tauri.conf.json:40-44`):

| Binary                         | `SIDECAR_SPECS` `kind` | Output path                                                             |
| ------------------------------ | ---------------------- | ----------------------------------------------------------------------- |
| `vysted-sidecar`               | `main`                 | `src-tauri/binaries/vysted-sidecar-<target-triple>[.exe]`               |
| `vysted-openbb-mcp-sidecar`    | `mcp`                  | `src-tauri/binaries/vysted-openbb-mcp-sidecar-<target-triple>[.exe]`    |
| `vysted-sec-edgar-mcp-sidecar` | `mcp`                  | `src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-<target-triple>[.exe]` |

`<target-triple>` comes from `rustc -vV`'s `host:` line, read by `sidecar-specs.mjs`'s
`targetTriple()` (`:190-195`; the same function §0 checks `rustc` is on `PATH` for).

`tauri build` resolves `bundle.externalBin` (`binaries/vysted-sidecar`,
`binaries/vysted-openbb-mcp-sidecar`, `binaries/vysted-sec-edgar-mcp-sidecar`,
`tauri.conf.json` `bundle.externalBin` at the sha) against these triple-suffixed files, so
this step must run — and succeed for all three — before step 6.

**Observed on a rehearsal run** (`stage-d/bundle-rehearsal/REHEARSAL.md`, sha `64e9470e`, not
the release-candidate sha — re-confirm at the actual tag): `VYSTED_SKIP_DEV_SIGN=1 node
scripts/ensure-all-sidecars.mjs --force` exited 0 in 316s with pip's wheel cache warm; the log
showed three `[ensure-*] done.` lines and, per the `VYSTED_SKIP_DEV_SIGN=1` guard above, no
`[dev-sign] signed …` line for any binary. Sizes: `vysted-sidecar` 87.4 MB, `vysted-openbb-mcp-
sidecar` 54.5 MB, `vysted-sec-edgar-mcp-sidecar` 82.8 MB (all within the ≤120 MB target).

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

The script first refuses any binary older than its source: it imports `assertAllFresh` from
`scripts/sidecar-specs.mjs` (`:80`) — the same freshness check §4's build uses, off the same
`SIDECAR_SPECS` table (`R15-RELEASE-006`, fixed, see §4) — wraps it in a local
`_assertAllFresh(triple)` (`:857-859`) called at `:873`, with the log line `[smoke] freshness
gate: all bundled sidecar binaries are newer than their source.` (`:859`) — re-run §4 after
any later sidecar or spec edit, or this step fails on staleness before it boots anything.

**Observed on a rehearsal run** (`stage-d/bundle-rehearsal/REHEARSAL.md`, sha `64e9470e`, not
the release-candidate sha — re-confirm at the actual tag): `node scripts/smoke-test-sidecars.mjs`
exited 0 in 138s — `/health` OK at the built version, `/agents` roster OK with 13 agents,
`/mcp/status` `ready=true, toolCount=40`, the screener/ICONIKSPEV and BSE-bhavcopy/NSE-direct
probes passed, both MCP subprocesses bound their ports and survived the settle window, and the
run ended with `[smoke] all sidecars booted cleanly.` The script tree-killed its own three
children cleanly; a `ps` check afterwards found none of them alive.

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

- `src-tauri/target/release/bundle/macos/Vysted Terminal.app` (~234 MB on disk, `du`; the
  host binary alone is 8.65 MB)
- `src-tauri/target/release/bundle/dmg/Vysted Terminal_<version>_aarch64.dmg`

**Observed pattern** (`stage-d/bundle-rehearsal/REHEARSAL.md`, sha `64e9470e`, still on
version `0.8.0` because the bump had not landed there — the candidate reads `0.9.0`, so the
version segment will differ): `Vysted Terminal_0.8.0_aarch64.dmg`, 228.6 MB. `VYSTED_SKIP_
DEV_SIGN=1 pnpm tauri build` exited 0 in 196s (cargo release 2m29s cold); the log had no
`[dev-sign] signed` line, and `beforeBuildCommand` logged "present and fresh — skipping
build" for all three sidecars.

**Signing state without §8.** The bundle is ad-hoc only and unsealed: `codesign -dv
--verbose=2` on the `.app` prints `Signature=adhoc`, `TeamIdentifier=not set` (the identifier
is the linker's own ad-hoc signature, not `com.vysted.terminal`), and the same is true of all
three sidecars under `Contents/MacOS`. `codesign --verify --deep --strict` exits 1 ("code has
no resources but signature indicates they must be present") and `spctl -a -t exec` exits 1.
**The dmg is not distributable until §8 runs.**

`bundle.createUpdaterArtifacts` is `false` at this sha (`tauri.conf.json`), so no
`latest.json`/`.sig` is produced by this step — see §8/§9 on the updater and release
pipeline, both blocked pending operator sign-off.

## 7. Clean-profile launch check (macOS)

What: launch the just-built `.app` against a fresh app-data directory and confirm first-run
terms, keyless mode and sidecar warm-up. Who: **the lead**, performed later from a clean
profile — **not performed by this Stage D wave** (per this wave's own brief: "The macOS
production build is proven from a clean profile later by the lead, not by this wave.").

**Isolation mechanism.** This section names no mechanism for a fresh app-data directory
because there is no dedicated env var for one. `src-tauri/src/lib.rs:186` (`resolve_data_dir`
→ `app.path().app_data_dir()`) resolves it to the fixed OS path
`$HOME/Library/Application Support/com.vysted.terminal`; the core passes that path to the
sidecar as `--data-dir` (`lib.rs:277`). So a clean-profile run means overriding `HOME` and
launching the bundle's own binary directly:

```
HOME=<fresh dir> "<bundle>/Contents/MacOS/vysted-terminal"
```

Do not launch it with `open` — `open` does not forward the environment, and LaunchServices
can re-activate an already-running instance instead of respecting `HOME=`. (Rehearsed on sha
`64e9470e`, `stage-d/bundle-rehearsal/REHEARSAL.md` correction 4.)

**Sidecar warm-up (observed at `64e9470e`, cold first launch, HOME= isolation).** 0–30s: no
listener (cold `_MEI` extraction). ~40s: the main sidecar is listening. ~60s: all three are
listening (main, openbb-mcp, sec-edgar-mcp). Copy these numbers as the expectation to set,
not a guarantee — they were not re-measured on the release-candidate sha
(REHEARSAL.md correction 8).

**WKWebView is not isolated by `HOME=`.** Even under a `HOME=` override, WKWebView website
data and caches still go to the real `~/Library/WebKit/com.vysted.terminal` and
`~/Library/Caches/com.vysted.terminal` — 10 files were touched there on the rehearsal run
(`ResourceLoadStatistics/pcm.db*`/`observations.db*`, `CacheStorage/salt`,
`AlternativeServices/*`). No LocalStorage/IndexedDB files changed. This is a known boundary
of the `HOME=` isolation method, not something to clean up as part of a run — **do not
delete these files**, they belong to the operator's real profile (REHEARSAL.md correction 6).

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

  **If macOS shows a keychain-access prompt during this launch, choose Allow.** A Deny (or a
  failed read) leaves the TOS dialog and onboarding permanently unrendered with no error
  shown — this is a known bug, not evidence the terms check passed or failed
  (R15-UI-044, `DECISIONS_FOR_OPERATOR.md §2.21`, Tier-4, open at this sha: "a denied/failed
  macOS keychain read during first-launch TOS hydrate leaves the TOS dialog (and onboarding)
  permanently unrendered with no error shown"). A blank first run under this condition should
  be filed against R15-UI-044, not treated as a new defect.

  **This read-only check is not sufficient on its own, and `HOME=` isolation cannot stand in
  for it.** Rehearsed on `64e9470e`: under a `HOME=<fresh>` launch, the terms dialog did NOT
  appear and the app was fully usable without an ack — not because the check passed, but
  because `HOME=` redirection leaves no default keychain at all. The unified log shows
  `SecKeychainCopyDomainDefault` failing with `MacOS error: -25307` (`errSecNoDefaultKeychain`)
  repeatedly from launch; every `keychain_get` then fails, `FirstLaunchTosDialog` awaits
  `refreshFirstLaunchAck()` with no catch (`DisclaimerFlow.tsx:44-49`), `hydrated` stays
  `false`, and the dialog returns `null` (`:68`) — this is the R15-UI-044 failure mode,
  triggered here by the isolation method itself rather than by a Deny click. **Treat a
  `HOME=`-isolated run's terms result as inconclusive, not a pass, and never delete the
  operator's own keychain items to force a clean check.** The terms/onboarding check needs a
  separate macOS user account instead — its own login keychain and its own
  `~/Library/WebKit` — run the check there:

  ```
  security find-generic-password -s vysted-terminal -a app-meta:first-launch-terms
  ```

  `HOME=` isolation is still correct for proving the data directory and sidecar warm-up (above)
  — it just does not prove the terms/keychain path (REHEARSAL.md correction 5).

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

**A rehearsal of this step ran on `64e9470e`** (not the release-candidate sha, and not a
substitute for this checklist item): `HOME=<fresh>` launch, window rendered populated (agent
dock, Equity Overview, a populated Watchlist, News with sentiment, Portfolio;
`first-run-1x.png`, 1280×832), status bar read `CONNECTED · OLLAMA (LOCAL)`, `/health`
returned `{"status":"ok","service":"vysted-sidecar","version":"0.8.0",…,"agents_degraded":[]}`
— but the terms-dialog result was inconclusive per the keychain note above, not a pass.

<!-- fill at rc2: the lead's actual clean-profile run at the release-candidate sha — a
separate macOS user account for the terms/keychain check per the note above, screenshots,
/health output, and confirmation the terms dialog appeared -->

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

**Ordering note:** signing is read out of `tauri.conf.json` (`bundle.macOS.signingIdentity`,
`bundle.windows.signCommand`/`certificateThumbprint`) at build time, inside `pnpm tauri
build` itself — it is not a step applied to an already-built bundle. If the operator approves
any change here (including the minimal ad-hoc `"-"` unblock), that edit must land in
`tauri.conf.json` **before** re-running §6, and §6's `.app`/`.dmg` and the §7 launch check
must both be re-run afterward; a §6/§7 already done against the old (unsigned) config is
stale the moment §8 changes anything.

## 9. Merge to main, tag and GitHub release — operator-only

What: merge the release branch to `main`, cut the `v0.9.0` tag on the merge commit, and
publish a GitHub Release with installable assets.
Who: **operator runs this.** Nothing in this section has been executed by any promotion or
docs pass — it is written, not run.

**9a. Merge `004-r4-experience-rebuild` into `main`.** Use a merge commit, not a fast-forward
or squash, so the branch's full commit history (654+ commits of R15 work) stays attributable
and the merge commit itself is a clean tag target:

```sh
git checkout main
git pull origin main
git merge --no-ff 004-r4-experience-rebuild -m "Merge 004-r4-experience-rebuild: R15 LAUNCH, Vysted Terminal 0.9.0"
git push origin main
```

Only merge once the rc gate's PASS verdict is confirmed at the candidate sha on
`004-r4-experience-rebuild` (checklist item above) — do not merge an unverified tree.

**9b. Tag `v0.9.0` on the merge commit**, not on the pre-merge branch head, so the tag
resolves on `main`:

```sh
git tag -a v0.9.0 -m "v0.9.0 — R15 LAUNCH: trading removed, PolyForm Strict + commercial licence, audit and fix pass"
git push origin v0.9.0
```

**9c. Publish the draft release.** If the draft was created with `--target <sha>` before the
merge (`GITHUB_RELEASE_v0.9.0.md`'s publish command), either let it point at that already-built
asset or re-point it at the tag once pushed (`gh release edit v0.9.0 --tag v0.9.0`), then:

```sh
gh release edit v0.9.0 --draft=false
```

**Do not tag before the rc gate passes.** `git tag --list 'r15*'` is empty at S — no
`r15-rc1` tag exists yet. `R15_GATE_RC1.md:3` reads "**Verdict: FAIL.** Do not tag rc1." for
round 1 (candidate `1d6511c89bb27f1785f7af4d2290983b2852d70a`); later rounds ran
at later shas. This step runs only after a round shows a PASS verdict, against the
sha that round evaluated.

**Precedent for tag format** (existing tags, e.g. `v0.8.0`): an annotated tag,
`tagger`/message form `<version> — <one-line description>` followed by a short changelog
body (`git cat-file -p v0.8.0`). Tag the exact sha the rc gate's round-2 PASS verdict
evaluated — never bare `HEAD`, which may have moved since the gate ran. Operator runs, e.g.:

```
# operator runs this — <gated-sha> is the sha the rc1 gate round-2 PASS verdict names
git tag -a v0.9.0 <gated-sha> -m "v0.9.0 — <summary>"
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

**NEEDS-OPERATOR — commercial-licence contact.** `DECISIONS_FOR_OPERATOR.md` §2.18
(R15-DOCS-002): `COMMERCIAL_LICENSE.md`/`LICENSING.md` name `commercial@vysted.com`, a domain
with no MX or A record. Quoted verbatim (`DECISIONS_FOR_OPERATOR.md:230-236`):

> **Blocked:** `COMMERCIAL_LICENSE.md`/`LICENSING.md` name `commercial@vysted.com`; the
> domain has no MX or A record, so a would-be licensee has no way to reach you.
>
> **Why Tier-4:** business/identity decision (owning a real inbox), not a code change.
>
> **Smallest unblock:** approve a real contact address; it gets swapped into both files
> before any public 0.9.0 announcement.

A GitHub Release is a public 0.9.0 announcement — get the real contact address into both
files before this step, not after.

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
  remains anywhere under `sidecar/tests/` at this sha — pinned by a dedicated AST-scan
  regression test, `sidecar/tests/test_tests_encoding.py`, whose docstring names it as the fix
  for `R15-CROSS-PLATFORM-002` (register status `fixed` at this sha, consistent with the
  code). Not an active red-on-Windows risk.
- `R15-CROSS-PLATFORM-001` (register `blocked_tier4`, `DECISIONS_FOR_OPERATOR.md §2.17`):
  655+ commits on `004-r4-experience-rebuild` have never had 3-OS CI signal at all — same
  root cause as §9/R15-RELEASE-004 (no PR, no trigger). The "Windows build" this section asks
  for has literally never run in CI on this branch, so any Windows-specific breakage in the
  654 commits of R15 work is undiscovered, not merely unverified.

<!-- fill at rc2: an actual Windows build + install + smoke-test run, or an explicit
decision to ship 0.9.0 macOS/Linux-only pending that verification -->

## 11. Rollback

**Pulling a published release**: delete or "yank" the GitHub Release and its assets
(`gh release delete v0.9.0`), leaving the git tag in place unless the operator also wants it
gone (`git tag -d v0.9.0 && git push origin :refs/tags/v0.9.0`) — operator-only, same as §9.

**Reverting the version bump**: revert the version-bump commit (`06879089`;
`git revert <bump-commit-sha>`), which returns every load-bearing file to `0.8.0`, then
re-run `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml` to
sync `Cargo.lock` back down.

**No pre-D81 tag is a rollback target.** `v0.8.0` and every earlier tag (`v0.7.0`, `v0.6.5`,
`v0.6.1`, `v0.6.0`, …) predate D81's permanent removal of the trading surface (`a122dbf6
feat(d81)`) and still carry it: `git ls-tree --name-only v0.8.0 plugins/ sidecar/services/`
lists `plugins/brokers`, `plugins/tradesa-v2`, `sidecar/services/broker_base.py`,
`sidecar/services/brokers` and `sidecar/services/kill_switch.py`. They are also licensed
differently — `git show v0.8.0:LICENSE | head -1` gives `GNU AFFERO GENERAL PUBLIC LICENSE`,
not PolyForm Strict 1.0.0. Rebuilding and shipping any of these tags as a "rollback" would
re-ship the removed broker/order surface under the old AGPL licence — do not do this, no
matter how urgent the rollback.

**Restoring a working prior build instead** means one of:

- pull the published GitHub Release for the prior tag, once one exists (§9); or
- fix forward on `004-r4-experience-rebuild` from the pre-bump commit (the commit before
  the `06879089` version bump), rebuilding via
  §2-§6 from that tree — this stays post-D81 and on the current licence, unlike any tag.

To inspect an older tree read-only without checking it out over local edits, use
`git worktree add <dir> <ref>` into a scratch directory, never `git checkout <tag>` in the
main worktree (that also does not create a worktree; it detaches HEAD in place).

<!-- VERIFY: whether the operator keeps any locally-built prior .dmg/.app on hand outside
this repo — not something this read-only wave can check. -->
