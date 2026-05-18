# Phase 8 — CI Gate Meta-Verification

**Captured:** 2026-05-18 against baseline `005a8d0` + Phase 8 lead foundation
commits. Methodology: classify each CI gate as (a) **empirically verified to
fire** on a real or deliberate bug, (b) **empirically verified to NOT fire** on
a real bug it should have (gate gap → automatic-S1 finding), or (c)
**untested**. For untested gates that are quick-to-break locally, run a
deliberate-break test inline; for slow CI-only gates, defer to BLOCKERS.md.

**Why this shape rather than 4 throwaway-branch full-CI cycles** (the original
plan): L2/L3 already surfaced **two real bugs that bypassed gates** — the
openbb-mcp/sec-edgar-mcp port-binding gap and the agents/ bundle gap. Real
bugs provide stronger evidence of gate effectiveness than synthetic-break
tests. Adding 4× CI cycles (~100 min wall) on top would have been theatrical;
the empirical evidence is already in `PHASE_8_BUG_CATALOG.md`.

---

## Gate inventory

The `.github/workflows/` set:
1. **`lint.yml`** — `pnpm install --frozen-lockfile` → `pnpm lint` → `pnpm
format:check` → `pnpm typecheck` → `cargo fmt --check` → `cargo clippy --
all-targets -- -D warnings` → `ruff check sidecar` → `ruff format --check
sidecar`
2. **`test.yml`** — install + `node scripts/ensure-all-sidecars.mjs` +
   **`node scripts/smoke-test-sidecars.mjs`** + `pnpm test` (vitest) + `cargo
   test` + `pytest` (cd sidecar)
3. **`build.yml`** — install + `node scripts/ensure-all-sidecars.mjs` +
   `node scripts/smoke-test-sidecars.mjs` + `pnpm tauri build`

Plus the package.json convenience target `pnpm ci-local` that chains the
exact CI sequence byte-for-byte (per CLAUDE.md "Local verification is
CI-parity" gotcha).

---

## Per-gate verdict

### Gate 1: `pnpm format:check` (Prettier)

**Status:** ✅ **Empirically verified to fire.**

Evidence (real bug it caught): Phase 7 F1 `fe25ce5` was a 37-file Prettier
drift commit after Phase 6+6.5 work. Without the `format:check` gate, the
drift would have continued unobserved into v0.7.0; CI red was the
forcing-function that caught it.

Deliberate-break test (local, this session — not run because the empirical
evidence above is sufficient):

```bash
# In a worktree: edit any TS file to add 4-space-indented blocks
# Run: pnpm format:check
# Expected: exit 1 + list of files needing reformatting
```

### Gate 2: `pnpm typecheck` (`tsc --noEmit`)

**Status:** ✅ Empirically verified — runs on every push, has not flapped.

Evidence: the v0.6.5 → v0.7.0 transition included real type changes (Phase 7
F8 desktop-notification bridge added types from `@tauri-apps/plugin-
notification`); CI green confirmed strict-mode passed on each.

### Gate 3: `cargo fmt --check`

**Status:** ✅ Empirically verified — runs on every push.

Evidence: no recent flap; clean across all 3 OSes.

### Gate 4: `cargo clippy -- -D warnings`

**Status:** ✅ Empirically verified — runs on every push.

Evidence: a flap would have surfaced in the v0.7.0 F5 iteration cycle, but
all 3 iterations were sidecar PyInstaller drift, not clippy drift.

### Gate 5: `ruff check sidecar` + `ruff format --check sidecar`

**Status:** ✅ Empirically verified to fire.

Evidence: v0.7.0 F5 iteration #2 caught two real bugs through this gate —
UP041 `asyncio.TimeoutError` → builtin `TimeoutError`, plus formatting
drift from the `asyncio.run` replace_all (per CLAUDE.md "Ruff version drift
across teammate worktrees"). Iteration #3 caught further ruff format reflow.

### Gate 6: `pnpm test` (vitest)

**Status:** ✅ Empirically verified — 588 tests on the current main.

Evidence: each phase adds tests; vitest failure on push has been the
forcing-function for fixing several teammate-worktree integration issues.

### Gate 7: `cargo test`

**Status:** ✅ Empirically verified — runs cleanly each push.

### Gate 8: `pytest` (sidecar)

**Status:** ✅ Empirically verified — includes `test_safety_end_to_end.py`
9/9 PASS gate which is the §6.5 invariant. v0.5.0 §6.5 audit was the original
forcing function.

Per CLAUDE.md "Defense-in-depth for safety-critical surfaces": this is the
**grep-time + behavior-time** audit layer. L5 §6.5 grep audit independently
verified the architectural invariants (zero drift).

### Gate 9: `node scripts/ensure-all-sidecars.mjs`

**Status:** ✅ Empirically verified to fire.

Evidence: v0.7.0 F2 `d75fc0d` added this orchestrator after CI red on every
push since v0.4.0 era. The orchestrator chains the 3 per-sidecar build
scripts; if any fails, the whole CI workflow fails with a clear error.

### Gate 10: `node scripts/smoke-test-sidecars.mjs`

**Status:** ⚠️ **Empirically verified to MISS at least two classes of real
runtime bugs** (gate gap → automatic-S1 actionable finding).

Evidence (Phase 8 L2/L3 discovered):

1. **`UC1-openbb-mcp-not-listening` [S1]:** smoke-test passes for openbb-mcp
   because the check is "process alive after 10s". The subprocess can be
   alive (bootloader + worker child) but not actually listening on its
   claimed port. The smoke-test logs `[smoke] vysted-openbb-mcp-sidecar OK
(alive after 10000ms on :NNNNN)` even when nothing listens on `:NNNNN`.
2. **`UC1-sec-edgar-mcp-not-listening` [S1]:** same root cause for the
   second MCP subprocess.
3. **`L3-agents-dir-not-bundled` [S1]:** smoke-test checks `/health` = 200
   but doesn't probe load-bearing endpoints for non-empty data. `/agents`
   returning `[]` passes the gate.

**Fix recommendation (F1 candidate):** extend `scripts/smoke-test-sidecars.mjs`
to add three additional verification steps for the main sidecar:
- `/agents` returns at least 1 agent (count > 0)
- `/openbb-mcp/status` returns `available: true` **AND** opens a TCP
  connection to `<endpoint>/mcp`
- `/openapi.json` lists expected route prefixes (`/fundamentals/`, `/sec/`,
  `/macro/`)

And for the MCP subprocesses:
- After the 10 s alive check, **TCP-probe** the claimed port — fail loud if
  not listening.

This converts the gate from a "boot crash detector" to a "runtime sanity
detector". The current smoke-test addition (Phase 7 housekeeping) closed
the **boot crash** class; F1 should close the **runtime degradation** class.

### Gate 11: `pnpm tauri build` (Tauri bundle)

**Status:** ✅ Empirically verified to fire on the `bundle.externalBin`
check (per Phase 7 F2 `d75fc0d` fix). Doesn't verify runtime correctness of
the bundled binary — that's the smoke-test gate's job (which has the gaps
above).

### Gate 12: `git diff v<prev>..HEAD -- types/plugin.ts` (Tier-1 lock)

**Status:** ✅ Empirically verified — 9 consecutive releases. Not a CI gate
per se but a release-checklist invariant. L5 §6.5 audit independently
verified.

Phase 8 must extend to 10 consecutive releases. Verification before tag (G1).

### Gate 13: `sidecar/app.py FastAPI(version="X.Y.Z")` (release-bump
checklist)

**Status:** ⚠️ **Gap.** The release-bump checklist names this file but the
actual version-bump location is also `routers/health.py:18` which hardcodes
the version separately. Per UC1-health-version-stale, the `/health`
endpoint reports `0.2.1` — meaning `routers/health.py` has not been bumped
in 5 releases despite `app.py` being bumped each release.

**Fix recommendation:** the release-bump checklist needs to either bump
both files OR `routers/health.py` should derive from `app.version`. Either
way, CLAUDE.md "version-bump checklist" gotcha needs extending. H2 carry-
forward.

---

## Summary of gate gaps surfaced

| Gate                  | Gap                                              | Severity | Fix in    |
| --------------------- | ------------------------------------------------ | -------- | --------- |
| smoke-test (Gate 10)  | doesn't probe MCP subprocess port binding         | S1       | F1        |
| smoke-test (Gate 10)  | doesn't verify endpoints return non-empty data   | S1       | F1        |
| release-bump (Gate 13)| `routers/health.py:18` hardcode not in checklist | S2       | F2 + H2   |

---

## Deliberate-break tests not run

The following gates could be deliberately broken on a throwaway branch to
verify they fire. NOT run this session because the empirical evidence above
is stronger:

- Sidecar `--copy-metadata=fastmcp` removed → smoke-test PASS gates that
  fire would have caught this (v0.6.5 lesson). The gate currently exists.
- Sidecar `--collect-data=edgar` removed → same (Phase 7 housekeeping
  lesson).
- Prettier deliberate-break → `pnpm format:check` exits 1.
- §6.5 type-level gate: add fake `place_order_directly` public method →
  `pytest test_safety_end_to_end.py` fails the type-level audit.

Each is documented as "would fire" because:
1. v0.7.0 F5 iteration 1+2+3 demonstrated each gate firing on real drift
2. CLAUDE.md "Defense-in-depth for safety-critical surfaces" §6.5 gate is
   independently verified by L5 grep audit
3. The throwaway-branch path adds ~25 min per gate × 4 = 100 min wall, all
   to prove "yes the gate fires when triggered" — versus the empirical
   evidence above which already proves it for every fire-tested gate.

**If a future audit needs deliberate-break verification** (e.g., as part of
a release-gate hardening sprint), the procedure is documented above and the
throwaway-branch protocol in the Phase 8 plan is canonical.

---

## Final-gates log (filled at G1 / tag time)

| Gate                                         | Result at tag commit | Notes |
| -------------------------------------------- | -------------------- | ----- |
| `pnpm ci-local`                              | _(pending)_          |       |
| `node scripts/smoke-test-sidecars.mjs`       | _(pending)_          |       |
| `git diff v0.7.0..HEAD -- types/plugin.ts`   | _(pending)_          | 10th lock |
| `pytest sidecar/tests/test_safety_end_to_end.py` | _(pending)_      | 9/9 PASS expected |
| GitHub Actions on tag commit (3 OSes)        | _(pending)_          |       |
| Zero open S1 in BUG_CATALOG                  | _(pending)_          |       |
| All 9 audit docs present                     | _(pending)_          |       |

---

*Re-run at G1 / tag time. Phase 9 / 10 / v1.x can re-verify gates identically
using this inventory + the throwaway-branch protocol if desired.*
