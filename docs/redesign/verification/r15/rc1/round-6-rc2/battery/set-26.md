# Battery shard 1 (batch-7/W2-delegate-runs-runtime) at ace7dd76 [set-26]

 | id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-010 | live: cancel/resume/start/answer on a done run; cancel unknown run | 409 'run is done; it cannot become cancelled/running' x4, row unchanged; unknown -> 404 | holds |
| R15-AGENT-034 | live: launch budget {} ; max_steps 0 / spend -1 / wall 0 | stored 120000 tok/$1.0/600s/12 steps; the three invalid -> 422 gt 0 | holds |
| R15-AGENT-037 | in-process looping provider max_tokens=1000 + live llama max_tokens=1000 | provider calls 1 (was 2), cost recorded 100000; live error 'token ceiling 1000 reached', activity [] | holds |
| R15-AGENT-038 | in-process one-shot max_steps=1 + live one-shot | status done 'completed (step ceiling 1 reached (1 taken) on the final round)', answer kept (live F identical) | holds |
| R15-AGENT-074 | live launch with no provider (llama3.1:8b) + in-process buffett no provider | spend_usd 0.0 for 1798 tokens; buffett 0.0021 == opus rate (default-rate would be 0.00035) | holds |
| R15-AGENT-036 | in-process launch ORIGINAL -> pause -> answer ONE -> pause -> answer TWO | provider sees ORIGINAL, A1, tool turn, [ask_user], ANSWER ONE, A2, [ask_user], ANSWER TWO in order | holds |
| R15-AGENT-035 | live: breached run C (ollama llama3.1:8b) then POST /resume | row keeps provider ollama / model llama3.1:8b; tokens 6453 -> 12906, steps 2 | holds |
| R15-LIFECYCLE-013 | same live resume as AGENT-035 | provider/model preserved across resume; answer path reachable (see CODE-AGENT-011) | holds |
| R15-LIFECYCLE-012 | live: kill sidecar stdin mid-run after round 1, reboot, GET row, resume | checkpoint non-null while running (49 B); after reboot status error 'interrupted by sidecar restart'; resume 200, cancel 200. Kill before round 1 leaves no checkpoint (409 no checkpoint) - adjacent note | holds |
| R15-UI-040 | git grep pinning vitest at candidate + live GET /runs | tests 'adopts a live sidecar run...', 'a failed cancel leaves the run running...' exist in src/lib/delegate-runs.test.ts; vitest is the heavy lane's | ci_pinned |
| R15-CODE-AGENT-011 | live: delegate run told to ask -> paused; POST /answer 'MSFT please' | paused with question 'Please tell me which stock...'; answer 200 -> done, user turn follows the ask turn, resolve_symbol MSFT then research | holds |
| R15-AGENT-039 | in-process planner-patched launch (plan half) + live ollama compound launch (activity half) | planned 'plan ready: start or discard it', 0 provider calls before Start, then done with typed activity; live activity row compare_symbols error w/ summary | holds |

COVERAGE: 12/12 ids raw; no raw: none
