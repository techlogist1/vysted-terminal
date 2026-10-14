# batch-4/W3-chat-runs-mcp

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52348 (own data dir
`rc1-round-4-data-rc1-battery-8`), own openbb-mcp :52349 (killed mid-run for
LIFECYCLE-005, not restarted) + sec-edgar-mcp :52350.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-002 | `vitest run src/store/research-spaces.test.ts src/store/agent-spaces.test.ts src/modules/chat/ChatSidebar.test.tsx` | 3 files, 57/57 passed, incl. the two tests named for this id (`a chat tab's conversation survives a research-space round trip` / `switching tab mid-stream stops the run first and archives the partial as stopped`) | holds (ci_pinned) |
| R15-AGENT-013 | `vitest run src/lib/delegate-runs.test.ts` (describe "delegate-runs — output delivery", R15-AGENT-013 comment) | 11/11 passed | holds (ci_pinned) |
| R15-AGENT-029 | `vitest run src/modules/chat/streaming.test.ts` (describe "exactly one terminal callback (R15-AGENT-029 / CODE-PLATFORM-037 / LIFECYCLE-005)") | 23/23 passed | holds (ci_pinned) |
| R15-CODE-PLATFORM-037 | same file/run as AGENT-029 | same 23/23 passed | holds (ci_pinned) |
| R15-LIFECYCLE-005 | live: killed my own openbb-mcp worker+bootloader (pids 81918/81912, port 52349) directly (a kill of the `sh -c "sleep\|binary"` wrapper pid alone leaves the binary running — noted and corrected), then `GET /openbb-mcp/status` and `GET /fundamentals/KPITTECH` on my sidecar :52348 | status: `available:false, lastToolCallOk:false, lastError:"ProviderError: MCP server 'openbb-mcp' failed to open: ConnectError(...)"` (was `true/null` on base); `/fundamentals/KPITTECH` returns 200, `provider:"yfinance"` (falls through, was a 500 on base) | holds |
| R15-CODE-AGENT-002 | `pytest tests/test_mcp_client.py::test_call_tool_failure_drops_session_and_raises_provider_error` (in the combined run below) | passed | holds (ci_pinned) |
| R15-DATA-083 | `pytest tests/test_openbb_mcp_provider.py -k status`, `tests/test_sec_filings_provider.py -k status` (R15-DATA-083 docstring) | passed | holds (ci_pinned) |
| R15-DATA-038 | `pytest tests/test_sec_filings_provider.py::test_dict_of_sections_parses_to_sections tests/test_sec_filings_provider.py::test_filing_level_form4_rows_are_listed` | passed | holds (ci_pinned) |
| R15-DATA-039 | `pytest tests/test_sec_filings_provider.py -k "foreign_private_issuer or amendments_and_schedules"` | passed | holds (ci_pinned) |

Combined pytest run: `sidecar/.venv/bin/python3 -m pytest tests/test_mcp_client.py
tests/test_openbb_mcp_provider.py tests/test_sec_filings_provider.py -v` → 84 passed, 4 warnings.

Raw: `battery/raw/set-12/*.txt`.
