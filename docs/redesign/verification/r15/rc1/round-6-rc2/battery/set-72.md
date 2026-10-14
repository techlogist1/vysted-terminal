# set-72 lows-P1/scripts-build (rc1-battery-20, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RELEASE-009 | grep smoke script budget + lib.rs constants + pinned rust test (raw: raw/set-72/R15-RELEASE-009.txt) | lib.rs MCP_PORT_WAIT_SECS=45 x ATTEMPTS=2, smoke MCP_BIND_TIMEOUT_MS=90_000, test fn smoke_bind_budget_matches_supervisor exists at lib.rs:1112 (cargo not run, heavy lane) | ci_pinned src-tauri/src/lib.rs tests::smoke_bind_budget_matches_supervisor |
| R15-RELEASE-010 | curl vysted.com / terminal.vysted.com; BLUEPRINT domain lines (raw: raw/set-72/R15-RELEASE-010.txt) | curl exit 6 both (still unresolved); BLUEPRINT now says 'Domain structure (planned, not yet resolved)' so the doc no longer states it as fact | holds |
| R15-DOCS-023 | grep README status + CURRENT_STATE link (raw: raw/set-72/R15-DOCS-023.txt) | 'being specified; build follows operator review' gone; README says build phase tracked in CURRENT_STATE; the P1_P3_BUILD_REPORT reference is now a removal note, not a dead link | holds |
