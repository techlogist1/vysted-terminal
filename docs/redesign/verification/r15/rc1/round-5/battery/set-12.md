# batch-4/W3-chat-runs-mcp (rc1-battery-13, gate round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Own sidecar :52353 (data dir
`rc1-round-5-data-rc1-battery-13`), own openbb-mcp :52360 (spun up so it could be killed
without touching the shared :52153 stack) + shared sec-edgar-mcp :52154 (read-only).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-002 | `vitest run src/store/research-spaces.test.ts src/store/agent-spaces.test.ts src/modules/chat/ChatSidebar.test.tsx src/modules/chat/streaming.test.ts src/lib/delegate-runs.test.ts` | 5 files, 90/90 passed | holds (ci_pinned) |
| R15-AGENT-013 | same combined run, `src/lib/delegate-runs.test.ts` ("delegate-runs" describes) | 11 tests in that file, all passed | holds (ci_pinned) |
| R15-AGENT-029 | same combined run, `src/modules/chat/streaming.test.ts` | 23 tests in that file, all passed | holds (ci_pinned) |
| R15-CODE-PLATFORM-037 | same file/run as AGENT-029 | same 23/23 passed | holds (ci_pinned) |
| R15-LIFECYCLE-005 | live: killed my own openbb-mcp worker+bootloader (pids 57552/57538, port 52360) directly, then `GET /openbb-mcp/status` and `GET /fundamentals/MAZDOCK`, `/fundamentals/KPITTECH` on my sidecar :52353 | pre-kill status `available:true, lastToolCallOk:null, lastError:null`; post-kill status `available:false, lastToolCallOk:false, lastError:"ProviderError: ..."`, then after two /fundamentals calls (both 200) status settles to `lastError:"ProviderError: MCP server 'openbb-mcp' failed to open: ConnectError('All connection attempts failed')"`; both `/fundamentals` calls returned 200 (fell through to yfinance), not 500 | holds |
| R15-CODE-AGENT-002 | `pytest sidecar/tests/test_mcp_client.py::test_call_tool_failure_drops_session_and_raises_provider_error` (in the combined run below) | passed | holds (ci_pinned) |
| R15-DATA-083 | `pytest tests/test_openbb_mcp_provider.py -k status`, `tests/test_sec_filings_provider.py -k status` | passed | holds (ci_pinned) |
| R15-DATA-038 | `pytest tests/test_sec_filings_provider.py::test_dict_of_sections_parses_to_sections tests/test_sec_filings_provider.py::test_filing_level_form4_rows_are_listed` | both passed | holds (ci_pinned) |
| R15-DATA-039 | `pytest tests/test_sec_filings_provider.py -k "foreign_private_issuer or amendments_and_schedules"` | both passed | holds (ci_pinned) |

Combined pytest run: `sidecar/.venv/bin/python3 -m pytest tests/test_mcp_client.py
tests/test_openbb_mcp_provider.py tests/test_sec_filings_provider.py -v` → 86 passed, 4 warnings
(one fewer warning than round 4's 84 passed / 4 warnings — the extra 2 passed here reflect the
same suite, no regression; test count differs from round 4 only because round 4's candidate
was a different sha at a different point in the suite's growth).

Raw: `battery/raw/set-12/*.txt` (vitest-chat-runs.txt, pytest-mcp-sec.txt, R15-LIFECYCLE-005.txt
+ one pointer file per ci_pinned id naming its slice of the combined runs).

COVERAGE: 9/9 ids raw; no raw: none.
