# set-48 — batch-11/W1-scripts-build (rc1-battery-12)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. All probes: static source check + direct `node --input-type=module` calls into the real modules (no build, no vitest suite run).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-026 | wc -l on the three ensure-*.mjs; grep sidecar-specs.mjs | ensure-sidecar.mjs=14, ensure-openbb-mcp-sidecar.mjs=16, ensure-sec-edgar-mcp-sidecar.mjs=15 lines (thin runners); scripts/sidecar-specs.mjs (313 lines) exports SIDECAR_SPECS/buildSidecar | holds |
| R15-CODE-PLATFORM-027 | `node scripts/audit-design-tokens.mjs` on macOS; grep ROOT | "design-token audit clean (373 files)" — walks real files (not the old 0-file false-clean); ROOT = resolve(import.meta.dirname, "..") matching sibling scripts, no `new URL(...).pathname` | holds |
| R15-CODE-PLATFORM-028 | grep vitest.config.ts include; ls scripts/*.test.mjs | include list has "scripts/\*\*/\*.test.mjs"; 4 script test files present (audit-design-tokens, sidecar-freshness-gate, sidecar-specs, sidecar-staleness) | holds |
| R15-RELEASE-005 | direct node probe of isStale() from sidecar-staleness.mjs against a tmp binary + a tmp `us_fundamentals_seed.json.gz` | binary newer than seed -> isStale=false; bump seed mtime newer -> isStale=true (the .gz IS tracked now) | holds |
| R15-RELEASE-006 | grep smoke-test-sidecars.mjs | imports `SIDECAR_SPECS, assertAllFresh` from `./sidecar-specs.mjs`; `_assertAllFresh` loops the shared table; the old literal duplicated `extraFiles: [join(ROOT,"scripts","ensure-...` blocks are absent (grep exit 1) | holds |

COVERAGE: 5/5 ids raw; no raw: none.
