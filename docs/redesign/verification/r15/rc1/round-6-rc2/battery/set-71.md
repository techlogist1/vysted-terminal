# Set: lows-P1/rust-core (set-71) — candidate ace7dd76, sidecar :52345

All entries are Rust/frontend source repros whose certification is a pinned cargo/vitest test (heavy lane runs them); this lane re-checked the fix sites and the named test exist at the candidate (grep raw in battery/raw/set-71/).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-055 | grep write_*_atomic in lib.rs | both commands delegate to one `write_atomic` (lib.rs:563,610,620); test `tests::write_atomic_text_and_bytes` present | ci_pinned |
| R15-CODE-PLATFORM-054 | grep sync_all in lib.rs | `f.sync_all()` :581 + parent dir sync_all :602; test `tests::write_atomic_round_trip_leaves_no_tmp` present | ci_pinned |
| R15-CODE-PLATFORM-058 | grep app_data_dir policy | single `app_data_dir()` (lib.rs:237); keychain `file_path` calls `crate::app_data_dir`; no named test (cargo test chain) | holds |
| R15-CODE-PLATFORM-059 | grep lock().unwrap().take() sites | guard released: `let child = state.0.lock().unwrap().take();` at lib.rs:773, openbb_mcp.rs:190, sec_edgar_mcp.rs:185; no if-let scrutinee form left | holds |
| R15-CODE-PLATFORM-056 | grep migrated flag | `store.migrated = failed.is_empty()` (keychain.rs:216), no unwrap_or(None); test `migrate_with_erroring_reader_leaves_unmigrated_and_retries` present | ci_pinned |
| R15-CODE-PLATFORM-057 | grep wait/progress | `wait` callback emits WAITING_EVENT before sleep (keychain.rs:262-269); test `on_wait_called_before_sleep` present | ci_pinned |
| R15-CROSS-PLATFORM-011 | grep onboarding + cfg | sleep gated `cfg!(target_os="macos")`; vitest "rejecting keychain keeps seen:true once markSeen ran" present (onboarding.test.ts:49) | ci_pinned |
| R15-LIFECYCLE-037 | grep clear_mcp_endpoint_file | called at boot start (:386), failed boot (:432), RunEvent::Exit (:782); test `clear_mcp_endpoint_file_removes_existing` present | ci_pinned |
| R15-CODE-PLATFORM-074 | grep remove_file/RunEvent | same removal on Exit (:770-782); same pinned test present | ci_pinned |
| R15-LIFECYCLE-038 | grep /health gate | `sidecar_healthy` GET /health check (lib.rs:127-139, :461-466); test `plain_tcp_listener_is_not_healthy` present | ci_pinned |
| R15-CODE-PLATFORM-060 | grep -rni tray src-tauri/src + tauri.conf.json + BLUEPRINT | 0 hits in Rust (as the entry's repro) and 0 in BLUEPRINT.md: the doc no longer promises a tray (docs-only fix) | holds |

COVERAGE: 11/11 ids raw; no raw: none
