# CRITIQUE — `scripts-build` (Scripts & Build Tooling)

**Subsystem:** `CODE_PARTITION.json#scripts-build` — 13 files, 2 566 LOC, **0 dedicated tests**.
**Files read in full:** all 13.
**Skill:** `aposd-critique` invoked and followed. **Assessment independence: degraded (sequential)** —
this worker has no sub-agent tool, so Assessment A (Strategic Thinker) was completed and recorded
before Assessment B (Tactical Tornado) began, per the skill's degraded-mode rule.

---

## Tactical Tornado verdict

**Risk: HIGH.** This is the most tactically-written subsystem I have read in this repo, and it is
tactical in the specific way that is hardest to see: *every individual decision is defensible and
heavily commented, and the structure still does not hold the invariants the comments promise.*

The three `ensure-*-sidecar.mjs` scripts are ~190 lines each of which ~90 are byte-identical
copies (`targetTriple`, `run`, `sleepSync`, `copyWithRetry`, the staleness guard, the venv
bootstrap, the copy/sign/tidy tail); `_rustcTargetTriple` is a fourth copy inside
`smoke-test-sidecars.mjs:519`. The freshness config that gates CI
(`smoke-test-sidecars.mjs:860-889`) is a hand-written second copy of the config the ensure scripts
own (`ensure-sidecar.mjs:73-80`). The MCP bind budget is aligned to the Rust supervisor **by a
comment** (`smoke-test-sidecars.mjs:97-100` vs `src-tauri/src/lib.rs:78,83`). And the staleness
whitelist that exists solely to prevent stale bundles has a hole large enough for a 717 KB bundled
data file to fall through — which it does, today (**COD-scripts-build-1**, proven below).

The most damning single pattern: `scripts/sidecar-staleness.mjs:41` encodes "what counts as build
input" as a **file-extension regex**, while `scripts/ensure-sidecar.mjs:182-189` encodes the same
fact as an **`--add-data` path list**. Two encodings of one truth, already drifted, and the
belt-and-suspenders gate written to catch exactly that drift
(`sidecar-staleness.mjs:108` `assertFresh`) reads the drifted copy.

Patterns the Tactical scan caught that the Strategic pass did not rank: the unreachable `catch`
at `smoke-test-sidecars.mjs:393`; the bare `statSync` at `sidecar-staleness.mjs:63` sitting six
lines above the same call correctly guarded; `ImageFont.load_default()` silently collapsing three
font sizes into one in both screenshot generators.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line:pattern) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **violate** | `ensure-sidecar.mjs:29-62` ≡ `ensure-openbb-mcp-sidecar.mjs:46-78` ≡ `ensure-sec-edgar-mcp-sidecar.mjs:36-68` — 4 helpers copied verbatim, log prefix only diff | CLAUDE.md has to *document a ritual* ("Adding one: `externalBin` + the SCRIPTS list + `.gitignore`/`.prettierignore`") because the code can't hold it |
| 2 | Deep modules | **violate** | Each `ensure-*.mjs` exposes a trivial interface ("node it") over ~190 lines, ~90 duplicated; `ensure-all-sidecars.mjs:28-32` is a 47-line file whose whole content is a 3-string array + a spawn loop | Interface≈implementation; the only "deep" module in the subsystem is `sidecar-staleness.mjs` |
| 3 | Information hiding / leakage | **violate** | Bundle-input truth in two encodings: `sidecar-staleness.mjs:41` `SOURCE_EXT=/\.(py\|txt\|toml\|cfg\|ini\|json\|csv)$/i` vs `ensure-sidecar.mjs:182-189` `addData[]` | **Proven drift** — `india_fundamentals_seed.json.gz` is bundled and invisible to staleness (F1) |
| 4 | Temporal decomposition | **at-risk** | `ensure-sidecar.mjs:96,102,106,201,207` numbered steps "1. venv / 2. pip / 3. pyinstaller / 4. copy / 5. tidy" as top-level script body | Structure mirrors execution order, so the only reuse unit is copy-paste — this is *why* #1 happened |
| 5 | General- over special-purpose | **violate** | `_assertAllFresh` (`smoke-test-sidecars.mjs:860-889`) hard-codes one literal block per sidecar instead of consuming a spec table | 4th sidecar = 6 edit sites |
| 6 | Different layer, different abstraction | **violate** | `smoke-test-sidecars.mjs:370-399,413-471,706-720` — live BSE/NSE/history internet probes live inside the frozen-binary correctness gate | Deterministic gate conjoined with nondeterministic reachability; ~95 s of CI time that can never fail (F4) |
| 7 | Pass-through methods / variables | **pass** | `sidecar-staleness.mjs:75-88` `newestSourceMtime` genuinely transforms; `macos-dev-sign.mjs:36` `signDevBinary` adds platform/identity/env policy | No pass-throughs found |
| 8 | Pull complexity downward | **at-risk** | `smoke-test-sidecars.mjs:97-100` pushes the "90 s = 45×2" derivation onto the reader instead of the Rust constants owning it (`src-tauri/src/lib.rs:78,83`) | Cross-language constant drift is undetectable (F13) |
| 9 | Better together / apart | **violate** | `smoke-test-sidecars.mjs` = 944 lines doing PID-ledger lifecycle + freshness gate + binary smoke + exchange reachability | Four responsibilities, one exit code, only one of them able to set it |
| 10 | Define errors out of existence | **violate** | `smoke-test-sidecars.mjs:323` `_writeState([])` + `:141-150` read-modify-write on a **fixed-path** shared ledger | Concurrent runs drop each other's rows; a per-run filename removes the race entirely (F11) |
| 11 | Design it twice | **at-risk** | `smoke-test-sidecars.mjs:18-68` documents a v1 (`pgrep -f vysted-.*sidecar`) redesigned into v2 (scoped ledger) — evidence it *was* designed twice; the ensure trio shows no such second pass | Uneven |
| 12 | Comments say what code cannot | **pass (strength)** | `ensure-sidecar.mjs:122-193`, `ensure-sec-edgar-mcp-sidecar.mjs:128-144` name the exact runtime failure each PyInstaller flag prevents, with the release that shipped it | Genuinely excellent; the best asset in the subsystem |
| 13 | Comments as invariant-holder (anti-pattern) | **violate** | `smoke-test-sidecars.mjs:97-100` "aligned with the Rust supervisor's MCP_PORT_WAIT_SECS(45) x MCP_PORT_WAIT_ATTEMPTS(2)"; `ensure-sidecar.mjs:69-72` "Editing this script's build recipe … must also invalidate the binary" | Both are *prose assertions of an invariant the structure does not enforce* |
| 14 | Naming | **pass** | `isStale`/`assertFresh`/`newestSourceMtime` (`sidecar-staleness.mjs:94,108,75`) read as their contract; `_SMOKE_MARKER`/`_STATE_FILE` scoping is explicit | — |
| 15 | Keep the design clean while modifying | **violate** | `render_phase_6_e_screenshots.py:26-34` + `render_phase_6_sc_screenshots.py:28-36` still carry the retired amber/charcoal palette (CLAUDE.md: replaced by zinc + cool-indigo at 003) and their PNGs are still the committed "proof" at v0.8.0 | Dead build tooling accreting instead of being deleted (F8/F9) |
| 16 | Consistency | **violate** | `audit-design-tokens.mjs:23` `new URL("..", import.meta.url).pathname` vs `import.meta.dirname` in all four sibling scripts (`ensure-sidecar.mjs:18`, `smoke-test-sidecars.mjs:82`) | Windows-broken + silently "clean" (F7) |
| 17 | Obviousness / design for reading | **at-risk** | `smoke-test-sidecars.mjs:382-398` wraps a function that provably cannot throw (`:334-345` swallows all) in try/catch | Reader reasons about a second failure path that does not exist (F5) |
| 18 | Tests / no special-casing to satisfy a test | **violate** | `CODE_PARTITION.json#scripts-build.tests = []`; `sidecar-staleness.mjs` (the subsystem's one real module, and the one with the proven bug) has **zero** unit tests despite being pure, filesystem-only, and trivially testable with a tmpdir | The regex hole in F1 is exactly what a 10-line test would have caught |

**Summary: 3 pass, 5 at risk, 10 violate — 3/18 pass.**

---

## Overall impression

The comments in this subsystem are better than the code. Someone paid real scar-tissue prices
(v0.6.5 `PackageNotFoundError: fastmcp`, v0.7.0 `secforms.csv`, Phase 8 `agents/` absent for three
releases, Phase 9.5 stale-bundle false regressions) and wrote every lesson down **as prose next to
the flag that fixed it**. That is why the subsystem keeps *almost* working.

The single biggest opportunity: **stop encoding the same fact twice in different shapes.** One
`SIDECAR_SPECS` table — name, source dir, `--add-data` sources, pyinstaller flags, identifier,
bind budget — consumed by the three ensure scripts, `ensure-all-sidecars`, `_assertAllFresh`, and
the smoke loop, collapses F1, F2, F3, and F5's sibling class at once and turns "add a sidecar"
from a six-site ritual into one row.

---

## What's working

1. **`macos-dev-sign.mjs:36-49`** is a genuinely deep, correct module: four fail-open guards
   (non-Darwin, `VYSTED_SKIP_DEV_SIGN`, missing file, missing identity), a memoised
   `security find-identity` probe (`:19-33`), and a documented promise it keeps — *"Never throws —
   a failed dev signature must not fail a build."* 49 lines that three callers reuse without
   knowing anything about codesign.
2. **The PyInstaller flag commentary** (`ensure-sidecar.mjs:122-193`,
   `ensure-sec-edgar-mcp-sidecar.mjs:128-144`) explains *the runtime failure each flag prevents and
   the release that shipped it*. This is textbook "comments say what code cannot" and it is the
   reason the `--add-data`/`--copy-metadata` lists have not been "cleaned up" by a well-meaning
   later hand.
3. **`smoke-test-sidecars.mjs`'s ATTENDED-SAFE redesign** (`:18-33`, `:283-331`). Replacing a
   blanket `pgrep -f vysted-.*sidecar` with a self-written PID ledger plus a PID-reuse confirmation
   step (`:237-270`) is a real second design, and `:310-321` — *alive but marker mismatch → leave it
   alone* — is the right call in the right place.

---

## Priority issues

### [P0] Bundled `.gz` seed pack is invisible to the staleness gate → stale binaries ship silently

- **Principle:** Information hiding / leakage (duplicated truth in two encodings)
- **Complexity symptom:** Unknown unknowns
- **Evidence:** `scripts/sidecar-staleness.mjs:41`
  `const SOURCE_EXT = /\.(py|txt|toml|cfg|ini|json|csv)$/i;` — vs
  `scripts/ensure-sidecar.mjs:179,184-186` which bundles the whole
  `sidecar/services/screener_universes/` directory via `--add-data`. That directory holds
  `india_fundamentals_seed.json.gz` (717 KB, `Jul 8 19:54`), read at runtime by
  `sidecar/services/fundamentals_seed.py:37 _PACK_FILENAME = "india_fundamentals_seed.json.gz"`.
- **Proof (run in-repo):**
  ```
  $ node -e "console.log(/\.(py|txt|toml|cfg|ini|json|csv)$/i.test('india_fundamentals_seed.json.gz'))"
  false
  ```
  `\.json$` does not match `…json.gz`. The file is therefore excluded from
  `newestMtime` (`:62`), so `isStale` (`:94`) returns `false` no matter how recently the pack was
  regenerated.
- **Why it matters:** `scripts/regenerate_fundamentals_seed.py`
  (`sidecar/services/screener_universes/regenerate_fundamentals_seed.py:107`) rewrites the pack
  **without touching any `.py`**. After a regeneration: (a) `ensure-all-sidecars.mjs` — wired into
  `tauri.conf.json` `beforeBuildCommand` and `package.json:19` `ci-local`, both **without
  `--force`** — prints *"present and fresh — skipping build"* (`ensure-sidecar.mjs:84`); and
  (b) `assertFresh` (`sidecar-staleness.mjs:108`), the belt-and-suspenders gate written for
  precisely this trap and invoked at `smoke-test-sidecars.mjs:886`, also passes. A local release
  build therefore bundles the **previous** Indian fundamentals snapshot and every gate is green.
  This is the Phase-9.5 S0-2 stale-bundle trap re-entering through the fix's own allowlist, on
  money-relevant data (P/E, market cap for Indian equities).
- **Fix:** invert the rule — walk everything and skip a small deny-list (`.pyc`, `.log`, `.DS_Store`)
  rather than allow a fixed extension set; **and** add the `--add-data` source paths as `extraFiles`
  so the two encodings become one. Minimum viable: `/\.(py|txt|toml|cfg|ini|json|csv|gz|xml|yaml|yml)$/i`
  plus a tmpdir unit test that asserts a `.gz` under the source dir marks a binary stale.

### [P1] The CI freshness gate hand-copies the config the ensure scripts own

- **Principle:** General-purpose over special-purpose; information leakage
- **Complexity symptom:** Change amplification
- **Evidence:** `scripts/smoke-test-sidecars.mjs:862-884` re-declares, per sidecar, the
  `excludeDirs` + `extraFiles` that `scripts/ensure-sidecar.mjs:73-80` (and `:88-90` in each MCP
  script) already declare:
  ```js
  opts: { excludeDirs: [ join(SIDECAR_DIR,"openbb_mcp_subprocess"), … ],
          extraFiles: [ join(ROOT,"scripts","ensure-sidecar.mjs"), staleness ] }
  ```
- **Why it matters:** the two copies are byte-identical **today** — which is the danger, not the
  reassurance. The moment one side gains an entry (say F1's `--add-data` paths), the gate certifies
  freshness against a *different source set* than the builder used, and reports green. A gate that
  can silently diverge from the thing it gates is worse than no gate: it converts "we didn't check"
  into "we checked and it's fine".
- **Fix:** export a `SIDECAR_SPECS` array from `sidecar-staleness.mjs` (or a new
  `scripts/sidecar-specs.mjs`): `{name, sourceDir, staleOpts, identifier}`. `_assertAllFresh`
  becomes `for (const s of SIDECAR_SPECS) assertFresh(_binaryPath(s.name, triple), s.sourceDir, s.staleOpts)`;
  each ensure script reads its own row.

### [P1] Three ensure scripts are one script copied twice; the bundle identity is spread over six sites

- **Principle:** Strategic over tactical; deep modules; temporal decomposition
- **Complexity symptom:** Change amplification
- **Evidence:** `targetTriple` (`ensure-sidecar.mjs:29-34` / `ensure-openbb-mcp-sidecar.mjs:46-51` /
  `ensure-sec-edgar-mcp-sidecar.mjs:36-41` / `smoke-test-sidecars.mjs:519-524` — four copies),
  `run` (`:36-39`/`:53-56`/`:43-46`), `sleepSync` (`:42-44`/`:59-61`/`:49-51`),
  `copyWithRetry` (`:50-62`/`:64-78`/`:54-68`), the staleness guard (`:81-91`/`:91-101`/`:81-91`),
  the venv bootstrap (`:97-100`/`:107-110`/`:97-100`), and the copy/sign/tidy tail
  (`:201-210`/`:178-187`/`:159-171`).
- **Why it matters:** CLAUDE.md's *"Adding one: `externalBin` + the SCRIPTS list in
  `scripts/ensure-all-sidecars.mjs` + `.gitignore`/`.prettierignore` + `pnpm sidecars:build`"* is a
  written-down ritual — an operational checklist standing in for a structural invariant. Adding a
  4th sidecar today touches: a new ~190-line script, `ensure-all-sidecars.mjs:28-32`,
  `smoke-test-sidecars.mjs:862-884`, `smoke-test-sidecars.mjs:905-909`, `tauri.conf.json`
  `externalBin`, `.gitignore`/`.prettierignore`. Six sites, five of them silently-skippable.
- **Fix:** one `scripts/build-sidecar.mjs` exporting
  `buildSidecar({name, sourceDir, venvDir, requirements, pyinstallerFlags, identifier, staleOpts})`.
  The three scripts collapse to ~20-line declarations. `sidecar-staleness.mjs` already proves the
  extraction works — the shared-module pattern exists, it was just applied to one helper instead of
  the whole recipe.

### [P1] The smoke test conflates "is the frozen binary correct" with "is the exchange reachable"

- **Principle:** Different layer, different abstraction; better together or better apart
- **Complexity symptom:** Cognitive load + dead CI time
- **Evidence:** three live-internet probes inside the binary-correctness gate that runs on every
  push (`.github/workflows/test.yml:69`, `.github/workflows/build.yml:74`):
  `_probeBseBhavcopyNoSla` (`smoke-test-sidecars.mjs:370-399`, 4 s),
  `_probeNseDirectNoSla` (`:413-471`, a **blocking** `execFileSync(venvPy, ["-c", code], {timeout: 60_000})`
  at `:451`), and the `/history/ICONIKSPEV` probe (`:706-720`, 30 s). All three can only
  `console.warn` (`:387`, `:459`, `:715`).
- **Why it matters:** up to ~95 s of nondeterministic wall-clock per CI run producing signal nobody
  reads — CI logs get opened when a run is red, and these probes structurally cannot make it red.
  Worse, the stated purpose ("flag a URL-SHAPE regression early", `:390`, `:461`) is unachievable
  from the warn as written: a URL-shape break and "CI has no outbound network" produce the same line.
- **Fix:** split them out into `pnpm probe:exchanges` (a separate script the operator runs attended,
  where a warn is actually seen), or gate them behind `--require-network` so a caller that *knows*
  it has a network gets a hard failure. The binary smoke stays hermetic and fast.

### [P2] Fabricated screenshots are still the committed visual-verification evidence

- **Principle:** Keep the design clean while modifying; comments/artifacts that assert what the
  structure does not hold
- **Complexity symptom:** Unknown unknowns (false confidence)
- **Evidence:** `scripts/render_phase_6_e_screenshots.py:81-87` and
  `scripts/render_phase_6_sc_screenshots.py:54-62` hard-code invented rows
  (`("AAPL","May 20, 2026","Apple Inc.","After close","1.50","0.050 / 20")`;
  `("MSFT","Microsoft Corporation","Technology",3.18e12,19.4,425.18,0.45,22_140_000)`) and PIL-draw
  them into `docs/screenshots/v0.6.0/teammate-{e,sc}/`. Those PNGs are still committed and still
  referenced as the evidence set (`docs/screenshots/v0.6.0/teammate-e/README.md:18`,
  `teammate-sc/README.md:35`). Both docstrings promise *"the lead replaces them with real
  chrome-devtools captures at integration"* — the repo is at `package.json` `version: 0.8.0`.
- **Why it matters:** CLAUDE.md's protocol bans empty screenshots because *empty shots hide layout
  bugs*. A **drawing of the intended UI** is strictly worse: it looks populated, so it passes the
  eye-check the protocol depends on, while proving nothing about the React panels at all. Three
  releases of reviewers have had a drawing offered to them as a capture.
- **Fix:** delete both scripts and the mock PNGs (the real mechanism is now the Quartz path,
  `/tmp/rigcap.py`, per CLAUDE.md), or move the PNGs to `docs/mockups/` under names that cannot be
  mistaken for captures and strike the README claims.

---

## Minor observations

- **`smoke-test-sidecars.mjs:382-398`** — the `try/catch` around `await _httpGetOk(url, 4000)` is
  unreachable: `_httpGetOk` (`:334-345`) has `catch { return false }`. Two apparent failure paths,
  one real. The genuinely useful distinction (404 vs DNS failure vs no network) was discarded at
  `:341`; returning `{ok, status, error}` would let the warn at `:387` actually say which.
- **`sidecar-staleness.mjs:63`** — `const m = statSync(full).mtimeMs;` is bare while
  `readdirSync` (`:51-55`) and the `extraFiles` stat (`:79-85`) are both guarded. A broken symlink
  or a file deleted between `readdirSync` and `statSync` (plausible with a concurrent
  `pytest`/`ruff` writing caches) throws ENOENT out of `isStale` → out of `ensure-sidecar.mjs:81`
  → `pnpm tauri dev` dies before starting, with a trace naming neither the file nor the build. The
  correct handling is already written six lines below.
- **`smoke-test-sidecars.mjs:97-100` vs `src-tauri/src/lib.rs:78,83`** — `MCP_BIND_TIMEOUT_MS =
  90_000` is aligned to `MCP_PORT_WAIT_SECS(45) × MCP_PORT_WAIT_ATTEMPTS(2)` **by comment**. Shrink
  the Rust budget and the smoke gate keeps passing binaries the app will give up on; nothing fails.
- **`smoke-test-sidecars.mjs:119,141-150,323`** — the PID ledger is a fixed-path, read-modify-write,
  multi-writer file, and `_scopedOrphanPreflight` ends with an unconditional `_writeState([])`. Two
  concurrent runs lose each other's rows; in-memory `_LIVE_PIDS` covers the clean-exit path, so the
  dropped case is exactly the crashed-run case the ledger exists for (orphaned PyInstaller worker
  holding the `_MEI` lock — the CLAUDE.md gotcha). A per-run filename
  (`live-children-<node pid>.json`) + glob-and-reap-if-owner-dead removes the race by construction
  rather than by lock.
- **`audit-design-tokens.mjs:23`** — `new URL("..", import.meta.url).pathname` yields `/C:/Users/…`
  on Windows (and `%20`-escapes spaces), so `join(ROOT,"src")` misses, `statSync` throws, `:80`
  `continue`s every scan root, and the script prints **`design-token audit clean`** having read
  nothing. A false-clean is the worst failure mode a linter has, and CLAUDE.md requires green on
  Windows. All four sibling scripts use `import.meta.dirname` (`ensure-sidecar.mjs:18`,
  `smoke-test-sidecars.mjs:82`). Same file, `:62`: `SKIP_FILES = new Set(["styles/tokens.css"])` is
  dead under the default `SCAN = ["src","plugins"]` (`:27`) and would compare against `\`-separated
  paths on Windows anyway.
- **`audit-design-tokens.mjs` is wired to nothing** — absent from `package.json:6-21`, from every
  `.github/workflows/*`, and from `ci-local`. `docs/redesign/R9_DESIGN_SYSTEM.md:40-42` states it
  *"runs in the gate battery"*. It does not. Verified clean today
  (`node scripts/audit-design-tokens.mjs --report` → `design-token audit clean`), so the cost is
  latent: nothing prevents the 274-violation state (`R9_TRACK_TIERS_REPORT.md:129`) returning. One
  line in `package.json` + one step in `lint.yml` closes it.
- **`scripts/*.py` is outside every Python gate** — `.github/workflows/lint.yml:87-89` and
  `package.json:19` both run `ruff check sidecar` / `ruff format --check sidecar`, path-scoped.
  `render_phase_6_sc_screenshots.py:191` carries `f"6 rows  (100 evaluated, 320 ms)"` (ruff F541,
  f-string with no placeholder) and `:151,208,220-221` run far past the formatter's width. CLAUDE.md's
  own rule (*"Before any Python commit: `ruff format <files> && ruff format --check sidecar`"*)
  inherits the same blind spot. Fix: `ruff check sidecar scripts`.
- **Both screenshot generators need an undeclared dependency and degrade silently without it** —
  `from PIL import Image, ImageDraw, ImageFont` (`render_phase_6_e_screenshots.py:20`) with no
  `Pillow` in `sidecar/requirements.txt`, `requirements-dev.txt`, or either subprocess
  `requirements.txt`. And `load_font` (`:37-48`, mirrored at `..._sc...py:39-47`) tries only
  `C:/Windows/Fonts/consola.ttf` / `cour.ttf`, then `except OSError: continue` →
  `ImageFont.load_default()`, which ignores `size`. On macOS/Linux `fnt_small`, `fnt_med` and
  `fnt_lg` are therefore the **same** bitmap font, making the 1920×1080 and 2560×1440 "pair" one
  render at two canvas sizes. Silent wrong output from a swallowed exception.
- **`install-head-guard.sh`** is a correct, minimal 19-line script guarding a hazard CLAUDE.md
  records as having actually bitten (teammate worktree contamination) — but nothing verifies it is
  installed. It depends on a human remembering, per clone. A one-line check in `ci-local` or the
  lead's pre-dispatch step would make the guard's presence observable.
- **`ensure-all-sidecars.mjs:43`** `process.exit(result.status ?? 1)` correctly handles the
  signal-killed child (`status === null`) — a detail most orchestrators get wrong. Noted as a
  positive.

---

## Persona walkthrough

**Tactical Tornado.** If the Tornado owned this subsystem, the next sidecar would arrive as
`scripts/ensure-fourth-mcp-sidecar.mjs` — another 190-line copy of
`ensure-sec-edgar-mcp-sidecar.mjs` with the strings swapped, because that is the fastest path and it
demonstrably works. They would add its literal block to `smoke-test-sidecars.mjs:862-884`, forget
the `_assertAllFresh` entry (CI still green — the gate just checks one fewer binary), and paper over
the next PyInstaller gap by appending to `copyMeta` at `:148`. The comment blocks would keep growing
(they are the only place the knowledge lives), the extension whitelist at `sidecar-staleness.mjs:41`
would gain `|gz` the week a stale seed pack bit someone in production, and `smoke-test-sidecars.mjs`
would cross 1 200 lines with a fifth no-SLA probe. Every step defensible; the sum unmaintainable.

**Strategic Thinker.** They would spend the afternoon on one `scripts/sidecar-specs.mjs`: a
`SIDECAR_SPECS` array where each row states name, source dir, requirements file, PyInstaller flags,
bundled-data source paths, codesign identifier, and bind budget. `buildSidecar(spec)` runs the
recipe; `ensure-all-sidecars.mjs` maps over the array; `assertFresh` derives its `extraFiles`
**from `spec.bundledData`** so F1 cannot recur by construction; `smoke-test-sidecars.mjs` loops the
same array instead of three literal blocks; the Rust bind constants are emitted into the spec (or
the spec into Rust) so `MCP_BIND_TIMEOUT_MS` stops being a comment. They would then delete the two
`render_phase_6_*.py` generators and their mock PNGs outright, move the three exchange probes to a
separate attended script, and write the ~40-line tmpdir test file that
`CODE_PARTITION.json#scripts-build.tests = []` has been missing — which would have caught the `.gz`
hole the day it was introduced.

---

## Questions to consider

- If `assertFresh`'s `extraFiles` were derived from the same list that feeds `--add-data`, could
  the stale-bundle class of bug be defined out of existence rather than re-patched per file type?
- The smoke test's exit code is a single boolean over four distinct claims (fresh / boots / serves
  the right data / exchange reachable). Which of those does a red build actually mean — and does
  the current design let a reader tell?
- `sidecar-staleness.mjs` is pure, filesystem-only, and ~124 lines. What stopped a test file from
  existing for it, and does that reason also apply to the next shared build module?

## Run notes

- Target: `scripts-build` (13 files, all read in full).
- Ignore list: `.aposd/critique/ignore.md` — not present, nothing dropped.
- **Assessment independence: degraded (sub-agents unavailable in this worker)** — A completed and
  recorded before B was begun.
- Snapshot persistence: skipped (`.aposd/critique/` writes are out of scope for an R15 census
  worker; the census tree is the archive).
- No process started, stopped or killed. No GUI interaction. One read-only command run against the
  repo (`node scripts/audit-design-tokens.mjs --report`) plus a one-line `node -e` regex check.
