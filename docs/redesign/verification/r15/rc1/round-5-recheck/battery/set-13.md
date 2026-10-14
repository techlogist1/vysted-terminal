# batch-4/W3-chat-runs-mcp — shard rc1-battery-12

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-002 | No GUI/vitest this shard; read pinned tests (`agent-spaces.test.ts:57`, `research-spaces.test.ts:190`, both explicitly named for this entry) + source (`agent-spaces.ts` switchTo now calls `stopLive()` first) | Pinned tests exist at candidate SHA and assert the exact fixed behaviour (abort fires once, archived partial `stopped:true`, chat tab survives research-space round trip) | ci_pinned |
| R15-AGENT-013 | Real Delegate run via runs API on own sidecar (ollama llama3.1:8b, under lock), polled to `done`, `GET /runs/{id}` read directly | `answer` 588 chars, complete sentence (not cut at 500); `brief` full structured object present (not dropped); `host_actions` correctly empty for this prompt | holds |
| R15-AGENT-029 | No GUI/vitest; read pinned test (`streaming.test.ts:318`) + source | Test asserts sidecar-not-ready rejection resolves via onError once, fetch never called — matches register's exact failure mode | ci_pinned |
| R15-CODE-PLATFORM-037 | No GUI/vitest; read pinned tests (`streaming.test.ts:330,349,357`) + source | Tests assert consumer-throw keeps its own message (not "unparseable SSE frame") and EOF-without-done (both raw-chat and agent-invocation) fires onError once with STREAM_ENDED_EARLY | ci_pinned |
| R15-LIFECYCLE-005 | Booted a separate disposable sidecar (:52381) with VYSTED_OPENBB_MCP_PORT pointed at a closed port (simulating the child dying, without touching the shared :52153 child) | `/fundamentals/{MAZDOCK,KPITTECH,BEL}` all 200 via yfinance fallthrough (never 500); `/openbb-mcp/status` correctly flips to `available:false` with a real ConnectError `lastError` | holds |
| R15-CODE-AGENT-002 | In-process, register's own stub-session repro (ClosedResourceError/BrokenResourceError/httpx.ReadError) + a genuine-cancellation control | All three now raise ProviderError with session dropped=True (was False); genuine outer `task.cancel()` still propagates CancelledError | holds |
| R15-DATA-083 | In-process, register's own stub-client repro (ok call then isError call) | lastToolCallOk flips False / lastError set with real error text after the isError call (was stuck True/None) | holds |
| R15-DATA-039 | Live GET /sec/filings on own sidecar for INFY (register's repro, FPI 20-F/6-K filer) and AAPL (fresh case) | INFY: 40 rows incl. 20-F, 16×6-K (was `[]`); AAPL: 40 rows incl. 144, 8-K/A, SD, SCHEDULE 13G/A (previously dropped by the 7-form Literal) | holds |

COVERAGE: 8/8 ids raw; no raw: none.
