# Regression battery — batch-11/W1-scripts-build (set-47)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Live node script runs (no full builds,
no vitest/pytest suites) against the candidate worktree source.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-026 | source read `scripts/sidecar-specs.mjs` + all three `ensure-*.mjs` + `ensure-all-sidecars.mjs` | one `SIDECAR_SPECS` table (313 lines); the three ensure scripts are 14-16 line thin runners that `SIDECAR_SPECS.find(s => s.name === ...)` + `buildSidecar(spec)`; orchestrator loops `for (const spec of SIDECAR_SPECS)` | holds |
| R15-CODE-PLATFORM-027 | `node scripts/audit-design-tokens.mjs` (real repo scan); `node scripts/audit-design-tokens.mjs /tmp/audit-fixture-check/src` (fixture `gap-1.5 text-[12px]`); `node scripts/audit-design-tokens.mjs /tmp/audit-empty-dir` | real scan: "design-token audit clean (373 files)" exit 0; fixture: 2 violations reported, exit 1; empty dir: "scanned 0 files ... refusing to report clean", exit 1 (was silent exit-0 "clean" on a bad ROOT) | holds |
| R15-CODE-PLATFORM-028 | `grep include vitest.config.ts`; `find scripts -name '*.test.mjs'` | `include: [..., "scripts/**/*.test.mjs"]`; 4 script test files present (staleness, specs, freshness-gate, audit) | holds |
| R15-RELEASE-005 | in-process `isStale(binPath, [srcDir])` from `sidecar-staleness.mjs`, tmpdir fixture with a `.json.gz` source file | binary newer than `.gz` → `isStale: false`; bump the `.gz` mtime forward → `isStale: true` (previously `.json.gz` was invisible to the extension allow-list) | holds |
| R15-RELEASE-006 | `grep 'extraFiles:\s*\[join(ROOT, "scripts", "ensure-'` over `smoke-test-sidecars.mjs` (should be absent); grep for `SIDECAR_SPECS`/`assertAllFresh` imports | literal hardcode NOT FOUND; `smoke-test-sidecars.mjs:80` imports `SIDECAR_SPECS, assertAllFresh` from `sidecar-specs.mjs` and loops `for (const spec of SIDECAR_SPECS)` — one shared table drives both the builder and the gate | holds |

Raw output: `battery/raw/set-47/*.txt`.

COVERAGE: 5/5 ids raw; no raw: none.
