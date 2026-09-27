# Set 25 — batch-7/W2-delegate-runs-runtime (regression battery, shard 0, round 5)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar: own boot on :52340,
data dir `rc1-round-5-data-rc1-battery-0`. Agent `copilot`. Local model `llama3.1:8b`
via Ollama (under the local-model lock) for the delegate-runtime probes; one free
OpenRouter slug (`nvidia/nemotron-3-super-120b-a12b:free`, same slug batch-7's own
verifier used) for the planner half of AGENT-039, key read in-process from the dev
keystore and never printed (`X-LLM-Api-Key` header on `/start`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-034 | `POST /agents/copilot/runs {budget:{}}` then `GET /runs/{id}`; `POST … {budget:{maxSteps:0}}` | `budget:{}` stores `maxTokens 120000 / maxSpendUsd 1.0 / maxWallSeconds 600 / maxSteps 12`; `maxSteps:0` → 422 "Input should be greater than 0". | holds |
| R15-AGENT-035 | Launch ollama/llama3.1:8b, breach `maxTokens:1500` → error; `POST /resume` (no body) | Resumed run keeps `provider:"ollama"`, `model:"llama3.1:8b"` in `GET /runs`; Ollama `/api/ps` confirms `llama3.1:8b` still loaded (not evicted for the agent default `qwen2.5:7b`). Cost accumulates 7604→15208 tokens. | holds |
| R15-AGENT-036 | Launch a prompt that triggers `ask_user`; pause; `POST /answer` "ANSWER ONE: AAPL" | Transcript order is `[user ORIGINAL PROMPT] → [assistant ask_user →Q] → [user ANSWER ONE: AAPL]` — correct order, prompt never replayed after the answer, no reversal. Run then completes normally via `resolve_symbol`→`price_data`→done. | holds |
| R15-AGENT-037 | `maxTokens:1000`, prompt asking for 4 sequential tool calls | `status:error`, `detail:"token ceiling 1000 reached (7659 used)"`, `steps:1` — aborts after round 1, no second provider round dispatched. | holds |
| R15-AGENT-038 | `maxSteps:1`, a prompt forced to a pure-text final answer (no tool/ask_user) on the ceiling round | `status:"done"`, `detail:"completed (step ceiling 1 reached (1 taken) on the final round)"`, transcript + `answer` field carry the complete text. | holds |
| R15-AGENT-039 | Compound-cue prompt "Check the news for RELIANCE, then add it to my watchlist, and then show me the chart." via OpenRouter free `nvidia/nemotron-3-super-120b-a12b:free` | Parks `status:"planned"` with a 4-step plan, `detail:"plan ready: start or discard it"`; `POST /start` with `X-LLM-Api-Key` runs it to `done` with typed activity rows (`resolve_symbol` ok, `news` ok, `add_to_watchlist`/`set_chart_symbol` staged) — not bare `[tool_use name]` strings. | holds |
| R15-AGENT-074 | Launch with NO `provider` field, `maxSpendUsd:0.01` | Resolves to the agent default (`ollama`), completes `done`, `spend_usd:0.0` across 7721 tokens (the \$5/M default would have breached instantly at that ceiling). | holds |
| R15-CODE-AGENT-010 | `POST /cancel` on a done run, an error run, and an unknown run id | `{"detail":"run '…' is done; it cannot become cancelled"}`, `"…is error; it cannot become cancelled"`, and `404 {"detail":"unknown run: …"}` respectively — every non-eligible transition is refused with a named reason. | holds |
| R15-CODE-AGENT-011 | `grep pause_run` (0 production hits outside the pinned test); live ask_user pause + `POST /answer` cycles (same runs as AGENT-036/038) | The bare `pause_run()`/`/pause` route stay absent (design fact unchanged), but the production control plane — `status:"paused"` + `question` + `POST /answer` — fires correctly on every ask_user tool call and resumes in order. | holds |
| R15-LIFECYCLE-012 | Launch ollama run, let 2 steps checkpoint, `kill -9` the sidecar process, restart pointing at the same data dir | `GET /runs/{id}` post-restart: `status:"error"`, `detail:"interrupted by sidecar restart"`, checkpoint held 5 messages / 3 steps / 19114 tokens (written per-round, not only at exit); `POST /resume` succeeds (`{"resumed":true}`, status→running). | holds |
| R15-LIFECYCLE-013 | Same run/evidence as R15-AGENT-035 | Resume preserves provider+model; Ollama confirms `llama3.1:8b` (not swapped for the agent's Qwen2.5 7B default). | holds |
| R15-UI-040 | Frontend/client-store behavior — permanently pinned in `src/lib/delegate-runs.test.ts` ("adopts a live sidecar run the store never saw (a webview reload), once"; "a failed cancel leaves the run running with a retry message") | Not re-run live (frontend vitest is the heavy lane's domain per this role's scope) — certified via a committed regression test, not a scratch/throwaway one. | ci_pinned |

COVERAGE: 12/12 ids raw; no raw: none.
