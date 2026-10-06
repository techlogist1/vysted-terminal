# set-30: batch-8/W1-sidecar-lifecycle-transport

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-012 | curl POST /agents/nope/invoke and {} on candidate sidecar; client leg statically checked | 404 {"detail":"unknown agent: 'nope'"} and 422 array, both the shapes the client now parses via extractSidecarDetail (streaming.ts:333) | ci_pinned (streaming.test.ts: 'a non-2xx string detail reaches onError as the sentence', 'a 422 field-error array reaches onError as field: msg') |
| R15-UI-014 | kill-the-sidecar repro is client+Rust only; live kill not done (GUI list per batch-8) | sidecar-client.ts:172 'not responding' sentence, lib.rs:430 Terminated handler emits vysted://sidecar-terminated, store/app.ts:93 listens | ci_pinned (sidecar-client.test.ts:212,330; app.test.ts:28,64) |
| R15-CODE-PLATFORM-011 | curl POST /agents/buffett/runs budget.max_tokens 'abc' | 422 detail array (int_parsing) as in the repro; delegate-runs.ts renders via reasonOf | ci_pinned (delegate-runs.test.ts:288 'a rejected launch shows the 422 field errors, not [object Object]'; sidecar-client.test.ts:225) |
| R15-RESEARCH-032 | Settings panel behaviour; server legs GET /search/searxng/status and /system/hardware | both 200 with real payloads (searxng state degraded with reason) | ci_pinned (SettingsPanel.test.tsx:716 'a status 500 shows the sidecar's reason, not not connected') |
| R15-LIFECYCLE-011 | store re-probe; static + tests | app.ts listens for terminated, re-probe tests exist | ci_pinned (app.test.ts:28 'a refused call flips connected to error; a later answer flips back', :64 'while in error, /health is re-probed') |
| R15-LIFECYCLE-010 | renamed-binary launch needs GUI/packaged app | Rust tests a_spawn_failure_reaches_the_renderer_as_failed_with_its_reason (lib.rs:1006), the_boot_wait_keeps_an_earlier_exit_reason (:1021) exist; sidecar-client.ts:98 handles state failed | ci_pinned (lib.rs tests above; sidecar-client.test.ts:24,41) |
| R15-LIFECYCLE-023 | render-throw needs GUI; static check | main.tsx:32-33 onCaughtError/onUncaughtError, PanelHost wraps panels | ci_pinned (PanelHost.test.tsx:113 'a throwing panel shows the crash card; a sibling panel still renders') |

COVERAGE: 7/7 ids raw (set-30); no raw: none
