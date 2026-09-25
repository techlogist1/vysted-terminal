<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->

# Release Runbook — Vysted Terminal 0.9.0

Reader: the lead or operator cutting the 0.9.0 release, step by step. This draft is sourced
from `docs/redesign/verification/r15/stage-d/FACTS.md` (sha `4d893147`) and the sha's own
scripts/docs. Promoted to `docs/RELEASE_RUNBOOK.md` by the lead at rc2, never by this wave.

## Checklist

- [ ] 0. Prerequisites: `PATH` + sidecar venv activated (§0) — `pnpm ci-local` fails without it
- [ ] rc gate round 2 verdict PASS at the candidate sha (confirmed at the tag)
- [ ] 1. Merge `worktree-agent-r15-version-0.9.0` (version bump to `0.9.0`) right after the
      r15-rc1 tag
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

`pnpm ci-local` (§3) calls bare `python`, `pytest`, `cargo`, `ruff` and `node`, and `pip`
via `python -m pip` (`package.json:20` — see §3's verbatim command). On a stock macOS shell, `python` and
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

- `rustc -vV` prints a `host:` line — `scripts/sidecar-specs.mjs`'s `targetTriple()`
  (`:190-195`) reads the target triple from it to name the sidecar binary; no `rustc` on
  `PATH` fails the sidecar build in §4 with `"could not determine host target triple from
  \`rustc -vV\`"` (`:193`).
- `pnpm --version` is `10.32.1` — pinned in all three CI workflows
  (`.github/workflows/{build,lint,test}.yml`, each `version: 10.32.1`); a different local
  pnpm can resolve dependencies differently than CI.

## 1. Version bump to 0.9.0

What: every load-bearing version string moves from `0.8.0` to `0.9.0` in the same commit.
Who: lead.

**Do not hand-edit these files.** A prepared branch already carries the bump:
`worktree-agent-r15-version-0.9.0`, two commits on top of `1db862d0` — `517da226
chore(release): bump version to 0.9.0` and `c1e9164c docs: the single CLAUDE.md commit for
the 0.9.0 release` (`git log --oneline -3 worktree-agent-r15-version-0.9.0`). Neither commit
is an ancestor of this sha (`git merge-base --is-ancestor 517da226 HEAD` fails at S). The
tracked run-state log records the merge plan: "MERGE PLAN (right after the r15-rc1 tag):
`git restore CLAUDE.md` first (the branch carries a held local hunk;
`scratchpad/claude-md-local.diff` keeps a copy), then `merge --no-ff`"
(`docs/redesign/verification/vysted-r15-run-state.md`, VERSION BRANCH entry) — merging it now
would tag a tree the gate never evaluated. Step: **merge `worktree-agent-r15-version-0.9.0`
into the release-candidate branch right after the r15-rc1 tag**, restoring `CLAUDE.md` first
per that note, then confirm the rc gate's register and grep criteria still hold on the merged
tree before proceeding to §2.

**What `517da226` touches — 8 files, audited here so a re-run or a manual rebase can be
checked against this list** (its own commit message: "Version sources: package.json,
src-tauri/Cargo.toml (+ Cargo.lock via cargo update -p vysted-terminal --offline),
src-tauri/tauri.conf.json (version string only), sidecar/app.py FastAPI(version=...),
HOST_VERSION in src/lib/plugin-bootstrap.ts. Also the README status line and the
marketplace store test fixture whose comment says it matches HOST_VERSION."):

- `package.json:3` — `"version": "0.8.0"`
- `src-tauri/Cargo.toml:3`
- `src-tauri/tauri.conf.json:4`
- `sidecar/app.py:329` — `FastAPI(title="Vysted Terminal Sidecar", version="0.8.0", …)`
- `src/lib/plugin-bootstrap.ts:38` — `export const HOST_VERSION = "0.8.0";`
- `src-tauri/Cargo.lock:5486-5487` — the `vysted-terminal` package block, via
  `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`
  (CLAUDE.md "Versioning & process": "At bump: grep for stale version strings and run
  `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`.")
- `README.md:53` — the "Honest status" line: "...and version strings sit at `0.8.0` pending
  a release cut" (confirmed at S: `git show S:README.md` line 53).
- `src/store/marketplace.test.ts:46` — `new PluginRuntime({ hostVersion: "0.8.0", ... })`,
  whose own comment says the fixture "matches HOST_VERSION so every catalog plugin satisfies
  requiredHostVersion" (`:43-45`) — the one non-source fixture the bump commit chose to move
  because its comment makes that claim explicitly; every *other* `"0.8.0"` test fixture below
  is left alone on purpose.

If for any reason the branch cannot be merged and the five-plus-three edits must be
reproduced by hand instead, edit exactly this 8-line list and regenerate `Cargo.lock` with
the `cargo update` command above — do not additionally touch any file in the "not a bump
target" list below.

**Not bump targets.** Every other `0.8.0` occurrence FACTS's `git grep` classes
`load_bearing` is a false positive of that tag, not a bump target — verified individually
against the code at the sha:

- `package.json:77` — `prettier-plugin-tailwindcss` pinned to `0.8.0`; an unrelated dep, not
  the app version.
- `src-tauri/Cargo.lock:281,290,758,2426,2443,3351,3368` — seven unrelated-crate
  `version = "0.8.0"` lines (`git grep -n '0\.8\.0' -- src-tauri/Cargo.lock` at the sha finds
  8 hits total: these seven plus `:5487` above).
- `plugins/vysted-lenses/manifest.json:6`, `plugins/vysted-news/manifest.json:6`,
  `plugins/yfinance/manifest.json:6` — each `"requiredHostVersion": "0.8.0"`. This is a
  **minimum-host pin**, not a value that tracks the host version: `checkCompatibility`
  rejects a plugin only when `!hostSatisfies(hostVersion, requiredHostVersion)`
  (`src/lib/plugin-runtime.ts:403,411`), and `hostSatisfies(host, required)` is `host >=
  required` by semver (`:151-157`). `0.9.0` satisfies `0.8.0`, so these three do not need
  editing for this bump; only raise one if that plugin starts requiring a 0.9.0+ host
  feature.
- `sidecar/tests/test_data_cache.py:131,133,141,142,150` — `0.8.0`/`0.8.1` used as arbitrary
  cache-build-tag literals in test fixtures, not the app version (FACTS).
- `sidecar/tests/test_schema_version.py:220,223,228,229,239` — same pattern, a new file at
  this sha: `data_cache.ensure_build("0.8.0")` then `("0.9.0")` are arbitrary build-tag
  strings exercising "back the data dir up once on a build change, never twice for the same
  build" (`:210-239`, confirmed read) — not a version statement, and note `"0.9.0"` is
  already used here as a fixture literal, unrelated to this bump.
- `src/components/SettingsPanel.test.tsx:886` — a `/system/diagnostics` response fixture,
  `{ version: "0.8.0", logTail: [...] }` (`:885-886`); the test's own assertions
  (`:894-900`) check `preview.textContent` for the `logTail` line and the
  `writeText`/"Copied" flow — none assert the version string, so this `"0.8.0"` is an
  arbitrary fixture literal, not a bump target.
- `src/lib/plugin-agents.test.ts:77` and `src/modules/marketplace/MarketplacePanel.test.tsx:40`
  — two more new-at-this-sha call sites, each `new PluginRuntime({ hostVersion: "0.8.0", … })`
  — a fixture host version chosen to satisfy every catalog plugin's `requiredHostVersion`
  (`marketplace.test.ts`'s own comment on the same pattern: "host version matches
  HOST_VERSION so every catalog plugin satisfies requiredHostVersion"), not an assertion on
  the real app version.
- `src/lib/plugin-runtime.test.ts:511,521,530,555,558,560,563,564,565,568,569` —
  `hostSatisfies`/`PluginRuntime` unit tests that use `"0.8.0"` as one arbitrary semver
  operand to exercise the comparison itself; the comparison behaviour is what's under test,
  not the app's actual version — not a bump target. (`src/store/marketplace.test.ts:46` looks
  like the same pattern but is NOT in this list — the bump commit moves it; see §1's bump
  list above.)
- `src/lib/plugin-runtime.ts:133` — a doc-comment example string (`written as ">=0.8.0"
  parses to its floor [0,8,0]`), not a version statement.
- `src/lib/workspace.test.ts:1574` — a doc comment, `/** v0.8.0 rows */`, labeling a fixture
  shape, not the app version.

Then the grep that proves nothing load-bearing is left (excludes the historical/prose docs
FACTS itself excludes — CHANGELOG.md, docs/archive, docs/redesign/verification,
docs/screenshots, pnpm-lock.yaml — since those are intentionally-preserved history, not
load-bearing):

```
git grep -n '0\.8\.0' -- . \
  ':!CHANGELOG.md' ':!docs/archive' ':!docs/redesign/verification' \
  ':!docs/screenshots' ':!pnpm-lock.yaml'
```

Expected output at S (confirmed by running it): **99 lines**, in two categories:

- **55 prose hits** — `BLOCKERS.md`, `README.md`, `docs/CURRENT_STATE.md`, `docs/redesign/*`
  reports, `docs/research/phase-10/*`. 54 of these are historical/narrative, not
  source-of-truth (the README/BLOCKERS/CURRENT_STATE drafts from this same Stage D wave
  carry corrected 0.9.0 prose, promoted separately at rc2). The 55th, `README.md:53`, is
  **not** historical narrative — it is a current-state claim ("version strings sit at
  `0.8.0` pending a release cut") and is one of the bump commit's 8 edits (§1 above).
- **44 source/lock/test/manifest hits**, every one confirmed non-bump-target above except the
  7 that flip on the bump: `package.json` (2: `:3` bumps, `:77` the dep pin doesn't),
  `src-tauri/Cargo.lock` (8: `:5487` bumps via `cargo update`, the other 7 don't),
  the three `plugins/*/manifest.json:6` `requiredHostVersion` pins (don't),
  `sidecar/app.py` (1, bumps), `src-tauri/Cargo.toml` (1, bumps),
  `src-tauri/tauri.conf.json` (1, bumps), `src/lib/plugin-bootstrap.ts` (1, bumps),
  `src/lib/plugin-runtime.ts:133`, `sidecar/tests/test_data_cache.py` (5),
  `sidecar/tests/test_schema_version.py` (5), `src/components/SettingsPanel.test.tsx:886`,
  `src/lib/plugin-agents.test.ts:77`, `src/lib/plugin-runtime.test.ts` (11),
  `src/lib/workspace.test.ts:1574`, `src/modules/marketplace/MarketplacePanel.test.tsx:40`
  (none of these last dozen bump), and `src/store/marketplace.test.ts:46` (bumps — reclassified
  in §1 above; every other test-fixture line on this list is left alone on purpose).

**Confirmed by running the grep against the actual bump commit, `517da226`
(`git grep -n '0\.8\.0' 517da226 -- . <same excludes> | wc -l`): 91**, i.e. 99 minus the 8
lines that flip (`package.json:3`, `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`,
`sidecar/app.py:329`, `src/lib/plugin-bootstrap.ts:38`, `src-tauri/Cargo.lock:5487` via
`cargo update`, `README.md:53`, `src/store/marketplace.test.ts:46`) — everything else on the
list above is unchanged by design (54 prose + 37 source = 91). A residual still at or near
99, or any hit against one of those 8 lines, means the bump was incomplete. Confirm this
count again once `worktree-agent-r15-version-0.9.0` is merged into the release-candidate
branch, in case later Stage-C batches added a new `0.8.0` occurrence upstream of the merge.

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
(that sha does not exist until §1's merge + rc gate round 2). `R15_GATE_RC1.md` (round 1,
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

| Binary | `SIDECAR_SPECS` `kind` | Output path |
| ------ | -------------- | ----------- |
| `vysted-sidecar` | `main` | `src-tauri/binaries/vysted-sidecar-<target-triple>[.exe]` |
| `vysted-openbb-mcp-sidecar` | `mcp` | `src-tauri/binaries/vysted-openbb-mcp-sidecar-<target-triple>[.exe]` |
| `vysted-sec-edgar-mcp-sidecar` | `mcp` | `src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-<target-triple>[.exe]` |

`<target-triple>` comes from `rustc -vV`'s `host:` line, read by `sidecar-specs.mjs`'s
`targetTriple()` (`:190-195`; the same function §0 checks `rustc` is on `PATH` for).

`tauri build` resolves `bundle.externalBin` (`binaries/vysted-sidecar`,
`binaries/vysted-openbb-mcp-sidecar`, `binaries/vysted-sec-edgar-mcp-sidecar`,
`tauri.conf.json` `bundle.externalBin` at the sha) against these triple-suffixed files, so
this step must run — and succeed for all three — before step 6.

<!-- fill at rc2: expected output from the lead's actual sidecar build run at the
release-candidate sha (no logged sidecar-build output exists at 4d893147) -->

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

<!-- fill at rc2: expected output from the lead's actual smoke-test run at the
release-candidate sha (no logged smoke-test output exists at 4d893147) -->

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

  **If macOS shows a keychain-access prompt during this launch, choose Allow.** A Deny (or a
  failed read) leaves the TOS dialog and onboarding permanently unrendered with no error
  shown — this is a known bug, not evidence the terms check passed or failed
  (R15-UI-044, `DECISIONS_FOR_OPERATOR.md §2.21`, Tier-4, open at this sha: "a denied/failed
  macOS keychain read during first-launch TOS hydrate leaves the TOS dialog (and onboarding)
  permanently unrendered with no error shown"). A blank first run under this condition should
  be filed against R15-UI-044, not treated as a new defect.

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

**Ordering note:** signing is read out of `tauri.conf.json` (`bundle.macOS.signingIdentity`,
`bundle.windows.signCommand`/`certificateThumbprint`) at build time, inside `pnpm tauri
build` itself — it is not a step applied to an already-built bundle. If the operator approves
any change here (including the minimal ad-hoc `"-"` unblock), that edit must land in
`tauri.conf.json` **before** re-running §6, and §6's `.app`/`.dmg` and the §7 launch check
must both be re-run afterward; a §6/§7 already done against the old (unsigned) config is
stale the moment §8 changes anything.

## 9. Tag and GitHub release — operator-only

What: cut the `v0.9.0` tag and publish a GitHub Release with installable assets.
Who: **operator runs this.**

**Do not tag before the rc gate passes.** `git tag --list 'r15*'` is empty at S — no
`r15-rc1` tag exists yet. `R15_GATE_RC1.md:3` reads "**Verdict: FAIL.** Do not tag rc1." for
round 1 (candidate `1d6511c89bb27f1785f7af4d2290983b2852d70a`); round 2 launches once
batch-24 merges (§1). This step runs only after a round shows a PASS verdict, against the
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

**Reverting the version bump**: revert the version-bump commit from §1
(`git revert <bump-commit-sha>`), which returns every load-bearing file to `0.8.0`, then
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
  `worktree-agent-r15-version-0.9.0` merged, i.e. before §1's merge step), rebuilding via
  §2-§6 from that tree — this stays post-D81 and on the current licence, unlike any tag.

To inspect an older tree read-only without checking it out over local edits, use
`git worktree add <dir> <ref>` into a scratch directory, never `git checkout <tag>` in the
main worktree (that also does not create a worktree; it detaches HEAD in place).

<!-- VERIFY: whether the operator keeps any locally-built prior .dmg/.app on hand outside
this repo — not something this read-only wave can check. -->

<!-- refresh f444479 to 4d89314: header/intro sha; §1 version-bump line numbers (app.py:329,
plugin-bootstrap.ts:38, hostSatisfies now :151-157/checkCompatibility :403,411), added 3
new-at-this-sha non-bump occurrences (test_schema_version.py, plugin-agents.test.ts:77,
MarketplacePanel.test.tsx:40) and corrected grep counts (92→99 pre-bump, 87→93 post-bump,
6 flipping lines not 5, per an actual git grep run at the sha); §1b CHANGELOG heading
pointers (newest is now batch-17 at :7, v0.7.0 moved to :760, v0.6.5 to :1008); §3 ci-local's
`pnpm lint` now also runs the new `audit-design-tokens.mjs` R9 token audit; §4 rewritten for
the ensure-*.mjs → `scripts/sidecar-specs.mjs` `SIDECAR_SPECS` consolidation
(R15-CODE-PLATFORM-026, R15-RELEASE-005, R15-RELEASE-006, all `fixed`); §5's freshness-gate
citation updated to the shared `assertAllFresh` import and its new line numbers; §10's
R15-CROSS-PLATFORM-002 bullet simplified (register now says `fixed`, matching the code — the
prior register/code disagreement is gone) and a new bullet added for
R15-CROSS-PLATFORM-001 (Windows/Linux CI has never run on this branch at all); §3's "rc1 has
not run" claim corrected — `docs/redesign/verification/r15/rc1/` now exists in the tree
(a round-1 gate, verdict FAIL, against the now-superseded candidate `1d6511c8`, 631
register entries vs this sha's 652) but is not usable as current-head evidence, no `r15-rc1`
tag exists. §2, §6, §7, §8, §9's quoted DECISIONS_FOR_OPERATOR blocks and §11 verified
unchanged byte-for-byte between the two shas and left as is. -->

<!-- critic-footer -->

## Critic findings applied

1. applied — `package.json:20` (verified: `pnpm ci-local` at S), and `pip` moved out of the
   bare-command list (it runs as `python -m pip`).
2. applied — citation moved to `scripts/sidecar-specs.mjs` `targetTriple()` (`:190-195`,
   verified at S), full error string quoted from `:193`.
3. applied — the bump commit `517da226` (branch `worktree-agent-r15-version-0.9.0`) verified
   to touch 8 files, not 6: `README.md:53` and `src/store/marketplace.test.ts:46` moved from
   "not a bump target" into §1's bump list; grep counts corrected to 99 pre-bump / 91
   post-bump (verified: `git grep -n '0\.8\.0' 517da226 -- . <excludes> | wc -l` = 91); the
   stale VERIFY comment (residual "exactly 93") replaced with the confirmed 91.
4. applied — §1 rewritten to point at merging `worktree-agent-r15-version-0.9.0` (verified:
   `git log --oneline -3` on that branch) instead of hand-editing; added an "rc gate round 2
   PASS" checklist item and a "do not tag before the gate passes" paragraph in §9 (verified:
   `git tag --list 'r15*'` empty at S, `R15_GATE_RC1.md:3` "Do not tag rc1"); tag command
   changed to take an explicit gated sha instead of bare `HEAD`.
5. applied — added an "Ordering note" to §8: any signing change must land in
   `tauri.conf.json` before §6/§7 re-run, since signing/notarization happen inside `tauri
   build` itself, not as a step against an already-built bundle; also flagged on the
   checklist line.
6. applied — added §2.18 (commercial-licence contact, quoted verbatim from
   `DECISIONS_FOR_OPERATOR.md:230-236`) as a NEEDS-OPERATOR item before §9's tag step and on
   the checklist; added §2.21 (R15-UI-044 keychain-deny silent failure, quoted verbatim from
   `DECISIONS_FOR_OPERATOR.md:257-265`) as a note inside §7's keychain-check walkthrough.
7. applied — §11's "restore v0.8.0" path replaced: verified `git ls-tree --name-only v0.8.0
   plugins/ sidecar/services/` still lists the broker/trading surface D81 removed, and
   `git show v0.8.0:LICENSE | head -1` is AGPLv3, not PolyForm Strict. Rollback is now
   "pull the Release" or "fix forward from the pre-bump commit on 004", with an explicit
   "no pre-D81 tag is a rollback target" statement and `git worktree add` in place of
   `git checkout <tag>`.
8. applied — §3's expected-output paragraph rewritten to cite `R15_GATE_RC1.md` items 4-5
   (verified) as the latest full-chain `ci-local`/smoke PASS on record, and the batch-23 (plus
   batch-16/batch-22) integrator chain (verified: `VERDICTS.md` in each batch dir) as the
   nearest evidence to this sha, explicitly labeled as integration-branch runs, not the
   release candidate. The batch-9 per-gate table was dropped as instructed. §4/§5's `<!-- fill
   at rc2 -->` comments were left as is — they correctly state no logged build/smoke output
   exists at this sha, which newer evidence does not contradict (the rc1-gate smoke result is
   for a different, superseded candidate sha, not this one).
9. applied — "17 Stage-C batch headings" corrected to 16 (verified:
   `git show S:CHANGELOG.md | grep -c '^## R15 Stage C — batch'` = 16); the promotion
   instruction for `RELEASE_NOTES.draft.md` corrected to "drop the line-1 DRAFT marker and
   the trailing `<!-- refresh ... -->` comment, fill or remove every `<!-- fill at rc2 -->`"
   (verified: that draft has no critic-footer section, its trailing block is a `<!-- refresh
   f4444790 to 4d89314: ... -->` comment plus `<!-- fill at rc2 -->` markers).
10. applied — the `[ensure-vysted-sidecar]`-style log-tag description corrected to the real
    `sidecar-specs.mjs:236` pattern (`vysted-` prefix stripped): `[ensure-sidecar]`,
    `[ensure-openbb-mcp-sidecar]`, `[ensure-sec-edgar-mcp-sidecar]`.
11. applied — "per the lead note" (an unpromotable workflow-prompt citation) replaced with a
    quote from the tracked `docs/redesign/verification/vysted-r15-run-state.md` VERSION
    BRANCH entry for the merge-timing claim, and with direct `R15_GATE_RC1.md`/`git tag
    --list` citations for the "no r15-rc1 tag yet" claim in §3 and §9.

