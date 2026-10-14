# lows-P3/error-layer (set-95) — rc1-battery-14 at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-039 | source: sidecarRequest -> buildSearchHeaders({includeKey:false}) (sidecar-client.ts:289); streaming.ts:305 keeps default | keychain/key not read on ordinary GETs | ci_pinned (src/lib/search-headers.test.ts "includeKey:false omits the key and never reads the keychain") |
| R15-LIFECYCLE-027 | source: HEALTH_PROBE_TIMEOUT_MS=5s AbortSignal, withDeadline + DEFAULT_REQUEST_TIMEOUT_MS, persistence.load once | hung-socket repro needs the TS module under vitest | ci_pinned (sidecar-client.test.ts "a never-settling /health probe is bounded per round"; plugin-bootstrap.test.ts "persistence.load is called exactly once per catalog plugin") |
| R15-RESEARCH-031 | extracted RESEARCH_BEGIN_RE from streaming.ts and ran the repro string under node | /^research:begin\s+(\S+)\s+depth=(\S+)(?:\s+query=([\s\S]*))?$/ now matches the multi-line query (true, query captured with \n) | holds |
| R15-CODE-PLATFORM-038 | grep for branches on error codes in src/; run_manager detail source | codes now consumed: streaming.ts PROVIDER_FAILURE_CODES, ChatSidebar SETTINGS_FIX_CODES (auth/provider_402/model_not_found -> Settings fix, not Retry); run_manager.py:391 detail=humanize(...).message | holds (run crash path also pinned by test_run_manager.py::test_crashed_run_detail_is_humanized) |
| R15-LEAD-021 | source: StatusChrome connLabel | renders `Sidecar error — <reason>` when sidecarError set (GUI chip itself not driven) | ci_pinned (src/components/StatusChrome.test.tsx:250-257) |

COVERAGE: 5/5 ids raw; no raw: none
