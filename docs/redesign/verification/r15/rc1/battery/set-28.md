# batch-8/W1-sidecar-lifecycle-transport

Candidate 4097dac4. Own sidecar :52346. Raw output: `raw/set-28/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LIFECYCLE-001 | Cold packaged launch main-loop freeze check (needs a real reboot + packaged binary) | Unchanged: original verdict was needs_gui, no headless path exists | needs_gui |
| R15-LIFECYCLE-010 | Rust pinned tests `boot_returns_at_once_and_spawns_the_sidecar_before_any_mcp_bind_wait_ends`, `a_spawn_failure_reaches_the_renderer_as_failed_with_its_reason`, `the_boot_wait_keeps_an_earlier_exit_reason` present in `src-tauri/src/lib.rs`; renderer half pinned in `src/lib/sidecar-client.test.ts` ("get_sidecar_port answering failed throws its reason at once, without a /health probe"). Not re-run (vitest/cargo suite banned for this shard) | Source unchanged since certification; tests present and named | ci_pinned |
| R15-UI-014 | `src/lib/sidecar-client.test.ts` ("a refused connection is SidecarError(0) with the unreachable sentence, not 'Load failed'"); Rust `CommandEvent::Terminated` handler in lib.rs unchanged | Test present, not re-run (vitest banned) | ci_pinned |
| R15-LIFECYCLE-011 | `src/store/app.test.ts` ("a refused call flips connected to error...", "while in error, /health is re-probed until the engine answers") | Test present, not re-run | ci_pinned |
| R15-UI-012 | `curl -X POST :52346/agents/nope/invoke -d '{"prompt":"hi","provider":"ollama"}'`; then `-d '{"mode":"bogus-mode"}'` | `{"detail":"unknown agent: 'nope'"}`; 422 array with `mode` literal_error "Input should be 'agent', 'ask', 'edit', 'build' or 'delegate'" — matches register repro exactly | holds |
| R15-CODE-PLATFORM-011 | `curl -X POST :52346/agents/buffett/runs -d '{"prompt":"x","budget":{"max_tokens":"abc"}}'`; `curl -X POST :52346/runs/run-does-not-exist-rc1b6/cancel` | `{"detail":[{"type":"int_parsing",...,"msg":"Input should be a valid integer, unable to parse string as an integer"}]}`; cancel → `{"detail":"unknown run: 'run-does-not-exist-rc1b6'"}`. Backend contract matches register exactly. Frontend string-formatting fix pinned by `src/lib/delegate-runs.test.ts` ("a rejected launch shows the 422 field errors, not [object Object]", "a refused cancel names the sidecar's reason...(class pin, R15-CODE-PLATFORM-011)") | holds |
| R15-RESEARCH-032 | `curl :52346/search/searxng/status`; `curl :52346/system/hardware`; `src/components/SettingsPanel.test.tsx` ("searxngChipMeta speaks the designed chip vocabulary for every state") | status → well-formed `degraded` state with reason string (engines suspended this session, matches batch-8 Issue 6, not a crash/500); hardware → full device/ollama JSON, no 500. Chip-vocabulary logic pinned by test | holds |

Summary: 1 needs_gui (unchanged), 3 ci_pinned (frontend/Rust behavior unrun per stall rule, source unchanged, tests present), 3 holds (live backend contract matches register exactly). No regressions.
