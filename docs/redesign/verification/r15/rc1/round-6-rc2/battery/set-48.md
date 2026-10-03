# Set batch-11/W1-scripts-build (set-48)

Candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, node v24.15.0, `node` scripts run directly (no vitest, no builds). Raw: battery/raw/set-48/<id>.txt

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-026 | design repro: line counts + SIDECAR_SPECS import | ensure-sidecar/openbb/sec-edgar are 14/16/15-line runners over one `SIDECAR_SPECS` table (sidecar-specs.mjs, 318 lines); 3 rows load, one targetTriple; argv byte-identity pinned by sidecar-specs.test.mjs (not run) | holds |
| R15-CODE-PLATFORM-027 | `node scripts/audit-design-tokens.mjs` on real tree, a nonexistent scan root, and an out-of-tree violating fixture | real tree exit 0; nonexistent root "scanned 0 files ... refusing to report clean" exit 1; fixture `gap-1.5 text-[12px]` -> "2 violation(s)" exit 1; ROOT uses import.meta.dirname, no URL.pathname ROOT in scripts/ | holds |
| R15-CODE-PLATFORM-028 | `ls scripts/*.test.mjs`, vitest include | 5 test files (staleness 8, specs 1, freshness-gate 1, smoke 9, audit 6 it-blocks); vitest.config.ts includes `scripts/**/*.test.mjs` (execution belongs to the heavy lane) | holds |
| R15-RELEASE-005 | tmp tree: `.json.gz` seed newer than the binary through `isStale`; allow-list grep | no SOURCE_EXT allow-list; old seed -> isStale false, regenerated .json.gz only -> isStale true | holds |
| R15-RELEASE-006 | grep literal staleness blocks; read gate and builder opts | no literal `extraFiles: [join(ROOT,"scripts","ensure-` blocks in smoke-test-sidecars.mjs; gate (sidecar-specs.mjs:213) and builder (:251) both read `spec.stale.dirs/opts`; `assertAllFresh` over the fresh candidate binaries passes | holds |

COVERAGE: 5/5 ids raw; no raw: none
