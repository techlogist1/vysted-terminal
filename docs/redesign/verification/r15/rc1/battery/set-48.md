# batch-11/W1-scripts-build (rc1-battery-1, candidate 4c6dfe8c)

Note: all 5 ids closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-026 | `wc -l` + grep `SIDECAR_SPECS` across scripts/*.mjs | single `SIDECAR_SPECS` table exported at `scripts/sidecar-specs.mjs:180`; `ensure-all-sidecars.mjs` shrunk to 29 lines and imports from it; `ensure-sidecar.mjs`/`ensure-openbb-mcp-sidecar.mjs` also import from the shared table — matches the "-620 lines" cert exactly | holds |
| R15-CODE-PLATFORM-027 | grep `import.meta.dirname`/`import.meta.url).pathname` in `audit-design-tokens.mjs` | `ROOT = resolve(import.meta.dirname, "..")` at line 25; comment at line 23 explicitly documents avoiding the Windows-broken `URL.pathname` form; no `.pathname` usage remains | holds |
| R15-CODE-PLATFORM-028 | grep `scripts/**` in `vitest.config.ts`; `ls scripts/*.test.mjs` | `vitest.config.ts:11` includes `"scripts/**/*.test.mjs"`; 4 script test files present (audit-design-tokens, sidecar-freshness-gate, sidecar-specs, sidecar-staleness) | ci_pinned |
| R15-RELEASE-005 | grep `.json.gz`/extension-allowlist remnants in `sidecar-staleness.mjs` | no extension allow-list remains; a comment documents its removal specifically citing the `.json.gz` fundamentals-seed miss this entry describes | holds |
| R15-RELEASE-006 | grep `extraFiles` in `smoke-test-sidecars.mjs`; grep `SIDECAR_SPECS` usage across ensure scripts | no literal hand-copied `extraFiles` string remains; `sidecar-freshness-gate.test.mjs` present, pinning `assertAllFresh` over the same shared `SIDECAR_SPECS` table used by the build scripts | holds |

COVERAGE: 5/5 ids raw; no raw: none.
