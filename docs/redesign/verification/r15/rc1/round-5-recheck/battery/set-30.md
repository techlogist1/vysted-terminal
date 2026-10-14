# set-30 — batch-8/W1-sidecar-lifecycle-transport (rc1-battery-22, shard 22)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52362 (seed-data copy);
shared read-only :52152 used for the two ephemeral `/agents/{id}/invoke` GET-shaped probes.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-012 | `POST :52152/agents/nope/invoke` (register's exact body + `{}`) + source read of `streaming.ts` `consumeSseStream` `!response.ok` branch | Sidecar returns `{"detail":"unknown agent: 'nope'"}` and the 422 array exactly as the register states; `streaming.ts:341-349` now JSON-parses the body and calls `extractSidecarDetail(parsed, fallback)`, with a comment explicitly citing R15-UI-012 | holds |
| R15-UI-014 | source read of `sidecarFetch` (sidecar-client.ts) + `lib.rs` `CommandEvent::Terminated` handling | `sidecarFetch` wraps `fetch` in try/catch → `SidecarError(0, SIDECAR_UNREACHABLE)` ("The data engine is not responding — it may have stopped. Restart Vysted."), drops the cached `readyPromise`; `lib.rs` matches `Terminated`, calls `.fail(reason)`, emits `vysted://sidecar-terminated` | holds |
| R15-CODE-PLATFORM-011 | `POST :52362/agents/buffett/runs` with `budget.max_tokens:"abc"` (register's exact 422) + `POST :52362/runs/run-does-not-exist-b8v/cancel` + source read of `delegate-runs.ts`/`sidecar-client.ts` | Own sidecar returns the exact int_parsing 422 and unknown-run detail; `delegate-runs.ts` now uses the single `sidecarRequest<T>` verb, `reasonOf(err)` passes `SidecarError.message` through verbatim → no `[object Object]` | holds |
| R15-RESEARCH-032 | `GET :52362/search/searxng/status`, `GET :52362/system/hardware` + source read of `SettingsPanel.tsx` | Both live endpoints return real payloads (SearXNG `degraded` with reasons, hardware detection populated); `SettingsPanel.tsx` now calls `sidecarGet`/`sidecarRequest` (not a private raw-fetch client) and re-fetches on both `visibilitychange` and `focus` | holds |
| R15-LIFECYCLE-011 | source read of `src/store/app.ts` (`markReachable`, `SIDECAR_REPROBE_MS`, `wireLifecycle`) | `sidecarStatus` is now written by `markReachable`, fed by every `sidecarFetch` result and the Rust terminated event; a failure starts a 20s `/health` re-probe interval that flips back to `connected` on success | holds |
| R15-LIFECYCLE-010 | source read of `src-tauri/src/lib.rs` (`SidecarPhase`, `SidecarStatus::fail`, `get_sidecar_port`) + `resolvePortToBaseUrl` consumer | `SidecarStatus{port,state,reason}` set from every spawn-failure arm and `Terminated`; frontend `resolvePortToBaseUrl` short-circuits on `state==="failed"` with `SidecarError(0, status.reason)`, no blind 120s probe; Rust unit tests `a_spawn_failure_reaches_the_renderer_as_failed_with_its_reason` / `the_boot_wait_keeps_an_earlier_exit_reason` present | holds |
| R15-LIFECYCLE-023 | source read of `PanelHost.tsx` (`PanelErrorBoundary`) + `main.tsx` (`onCaughtError`/`onUncaughtError`) | Every dockview panel component wrapped in `PanelErrorBoundary` (Reload panel / Copy error UI); `createRoot` now passes `logRenderError` for both caught and uncaught errors, forwarding to `diag_log_line` | holds |

Notes: a fully-live GUI crash/kill/rename-binary walkthrough is out of scope (No GUI); every
"holds" verdict above is backed by (a) a live curl reproducing the register's exact backend
payload where the repro is curl-able, and (b) a direct read of the exact evidence lines cited
in the register/batch-8 VERDICTS.md, confirming the described fix code is present unchanged in
candidate 949c3c9f. No regression found in this set.
