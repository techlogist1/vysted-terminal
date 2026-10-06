# set-91: lows-P2/scripts-build (rc1-battery-23, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-061 | node: newestSourceMtime/isStale over a dir with a dangling symlink | returns mtime, isStale=true, no throw | holds |
| R15-CODE-PLATFORM-062 | node: _httpGetOk on 404 / 200 / offline port | {status:404,error:null} vs {status:null,error:"fetch failed"} distinguished | holds |
| R15-LIFECYCLE-039 | node: _scopedOrphanPreflight with private TMPDIR, live-owner ledger vs dead-owner ledger | live-owner child alive, dead-owner child reaped | holds |
| R15-RELEASE-008 | node: _shouldProbeExchanges default vs --require-network | false by default, true with flag; probes gated | holds |
| R15-CROSS-PLATFORM-010 | resolveBuildPython() live; ci-local script grep | returns python3.13; ensure via sidecar-specs->ensureBuildVenv; ci-local uses python3 | holds |
| R15-RELEASE-011 | grep vitest.config/package.json/workflows | coverage thresholds lines:81.4 autoUpdate; ci-local runs vitest run --coverage (workflows untouched, .github locked) | holds |
| R15-DOCS-012 | ls scripts/render_phase_6_*, docs/screenshots/v0.6.0 | generators and teammate-e/sc dirs gone; mocks relocated to docs/mockups with README label | holds |
| R15-CODE-PLATFORM-064 | run the generator with venv python | file absent (deleted, per docs/mockups/README); no tracked render_phase_6 files | holds |

COVERAGE: 8/8 ids raw; no raw: none
