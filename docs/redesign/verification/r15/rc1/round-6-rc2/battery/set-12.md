# batch-4/W3-chat-runs-mcp (set-12), shard rc1-battery-9, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-002 | vitest-only store behaviour; grep pins | agent-spaces.test.ts:57 'switching tab mid-stream stops the run first...' and research-spaces.test.ts:223 'a chat tab's conversation survives a research-space round trip' exist | ci_pinned |
| R15-AGENT-013 | live POST /agents/copilot/runs (ollama llama3.1:8b) then GET /runs/{id} | status done, answer_len 583 (>500, not cut), ends in full sentence; pinned test_run_output_is_returned_untruncated_by_get_run exists | holds |
| R15-AGENT-029 | vitest-only (streaming.ts); grep pins | streaming.test.ts block '[One terminal callback per stream call (R15-AGENT-029 / CODE-PLATFORM-037 / LIFECYCLE-005)]' present | ci_pinned |
| R15-CODE-PLATFORM-037 | vitest-only (streaming.ts); grep pins | same streaming.test.ts block pins consumer-throw and EOF-without-done | ci_pinned |
| R15-LIFECYCLE-005 | in-process ASGI app with openbb-mcp port closed (52379): GET /fundamentals/MAZDOCK, KPITTECH, /openbb-mcp/status | both 200 via yfinance fallthrough (~16 s first-call, no 500); status available:false lastError ConnectError (pre-fix: 500 + available:true). Live child-kill + research-SSE not re-run (shared MCP child is read-only) | holds |
| R15-CODE-AGENT-002 | in-process McpClient, stub session raising ClosedResource/BrokenResource/ReadError/EndOfStream/RemoteProtocolError | each raises ProviderError and session dropped True (repro expected dropped True) | holds |
| R15-DATA-083 | in-process stub: ok call then isError call; status() for openbb-mcp and sec-edgar-mcp | status after isError: available false, lastToolCallOk false, lastError 'upstream 500' for both | holds |
| R15-DATA-038 | GET /sec/filings/0000320193-25-000079?identifier=AAPL; /sec/insider/AAPL; /sec/insider/NVDA?form=4 (live EDGAR via sec-edgar-mcp) | sections Business 10000 + Risk Factors 10000 (total 20000); insider 16 Form-4 rows each, issuer Apple Inc./NVIDIA CORP. The /sections sub-route is now 404 (detail route carries sections) | holds |
| R15-DATA-039 | GET /sec/filings?symbol=INFY and AAPL | INFY 40 rows (6-K 16, 20-F 1, 3/A, F-6...) vs 0 pre-fix; AAPL carries 144, 8-K/A, SD, SCHEDULE 13G rows | holds |

COVERAGE: 9/9 ids raw; no raw: none
