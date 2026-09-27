# set-40 — batch-10/W1-runtime-backtest (rc1-battery-22, shard 22)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Backend probes run in-process
against the candidate's sidecar venv (standalone scripts mirroring the pinned
tests' fixtures, never pytest itself) and via curl against own sidecar :52362.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-050 | in-process call to `services.llm.anthropic._split_system_and_messages` with persona/date/preamble system messages + a tool-result turn | `system_blocks[0]` (persona) carries `cache_control: ephemeral`; date/preamble blocks after it do not; the last tool_result block carries the second breakpoint | holds |
| R15-LEAD-018 | in-process replay of `tests/fixtures/llm/nemotron_cot.jsonl` through the real `ReasoningSplitter` | 24 reasoning chunks all route to `thinking` events; 0 reached `delta` (answer) events; no CoT leak markers in the answer text | holds |
| R15-CODE-PLATFORM-029 | standalone async script running `backtest_engine.run_backtest` on the register's exact scenario (4 flat bars @100, buy 10 every bar, capital 100000) | `total_return -4e-05` (was `-0.03004`), one merged 40-share lot, final equity `99996.0` | holds |
| R15-LIFECYCLE-015 | standalone script: 3 `backtest_store.put()`, `list_runs()`, `reset_for_tests()` (simulated restart), `list_runs()` again, `get()` on the oldest | newest-first both before and after the simulated restart; `get(oldest)` still resolves from disk | holds |
| R15-UI-010 | `POST :52362/backtest/run` mean_reversion with `window:0`, `window:-5`, `window:""` (register's exact cases) | `{"detail":"\`window\` must be between 5 and 200"}` (x2), `{"detail":"\`window\` must be an integer"}` — never a raw Python exception | holds |
| R15-UI-011 | source read of `BacktestPanel.tsx` (AbortController + Stop button); register's own repro is a live-run rail-control state, not curl/python-reachable | AbortController + Stop wiring present and matches fix_shape; certified in batch-10 only via `BacktestPanel.test.tsx` ("swaps Run for Stop while a backtest is streaming", "Stop aborts the live stream, idles the run, and Retry runs on a fresh controller") | ci_pinned |

Notes: R15-LEAD-018 used the register-cited fixture (a real captured OpenRouter
nemotron response) rather than a fresh live network call — no free-tier
OpenRouter key was available to this shard, and the account lane is shared
across concurrently-running battery shards; replaying the fixture through the
production `ReasoningSplitter` module is still a live code-path exercise, not
a static read. No regression found in this set.
