# batch-8/W1-sidecar-lifecycle-transport (rc1-battery-23, round 5)

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `127.0.0.1:52363`, data dir
`rc1-round-5-data-rc1-battery-23` (copied from the ISO seed). Rust checks ran with
`cargo test --lib <name> -- --nocapture` in `src-tauri` (single pinned tests, not the full
suite); frontend checks ran with `vitest run <specific file>` (never the full 136-file run).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-011 | Live `POST /agents/buffett/runs` with `budget.max_tokens:"abc"` against `:52363`; grepped `extractSidecarDetail` (src/lib/sidecar-client.ts:49-73) and `launchDelegateRun` (src/lib/delegate-runs.ts:187). | 422 `int_parsing` array, same shape as the register repro; the field/msg join logic that turns it into `max_tokens: Input should be a valid integer, unable to parse string as an integer` is unchanged; `Could not start: ${reasonOf(err)}` still wraps it. No raw-object path. | holds |
| R15-LIFECYCLE-010 | `cargo test --lib a_spawn_failure_reaches_the_renderer_as_failed_with_its_reason` and `the_boot_wait_keeps_an_earlier_exit_reason` (src-tauri/src/lib.rs), each alone. | Both `ok`, printing "The data engine could not start (binary not found)." and "The data engine stopped (exit code 1)." respectively — the exact certified sentences. | ci_pinned |
| R15-LIFECYCLE-011 | `vitest run src/store/app.test.ts` (targeted). | `sidecar status follows reachability > a refused call flips connected to error; a later answer flips back and re-runs a panel load` and `> while in error, /health is re-probed until the engine answers` both pass. | ci_pinned |
| R15-UI-012 | Live `POST /agents/nope/invoke` with a real prompt, an empty body, and `mode:"bogus-mode"` against `:52363`; grepped streaming.ts for `.text()`/`extractSidecarDetail`. | `unknown agent: 'nope'`; 422 `Field required` on prompt; 422 `mode: Input should be 'agent', 'ask', 'edit', 'build' or 'delegate'` — matches the register exactly. streaming.ts:348 routes every non-2xx through `extractSidecarDetail`; the old raw `response.text().slice(0,500)` path is gone. | holds |
| R15-UI-014 | Source check: `sidecarFetch()` (src/lib/sidecar-client.ts:164-196) and `CommandEvent::Terminated` (src-tauri/src/lib.rs:304); same store-level re-probe pinned by the LIFECYCLE-011 test above. | `SIDECAR_UNREACHABLE` = "The data engine is not responding — it may have stopped. Restart Vysted." still wraps every raw fetch rejection into `SidecarError(0, ...)`; Terminated is still handled in Rust. | holds |
| R15-RESEARCH-032 | `vitest run src/components/SettingsPanel.test.tsx` (targeted). | `a status 500 shows the sidecar's reason, not 'not connected'` passes. | ci_pinned |
| R15-LIFECYCLE-023 | `vitest run src/components/PanelHost.test.tsx` (targeted). | `panel error boundaries > a throwing panel shows the crash card; a sibling panel still renders; Reload remounts it` passes; PanelHost.tsx:119-173 still wraps every panel in `PanelErrorBoundary`, main.tsx:17-27 still wires `onCaughtError`/`onUncaughtError` to `diag_log_line`. | ci_pinned |

COVERAGE: 7/7 ids raw; no raw: none.
