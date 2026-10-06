# triage-b — rc1-vshard-4:2 (tie R15-RESEARCH-027)

Audited 07:31 IST at HEAD bed3b166. The code tree equals 01015033, and the fix round did not touch research/fast.py or search/keyless.py.

## Claim (shard 4)
NORMAL research is not bounded when the web round stalls. The shard measured 18-20 s against the FR-070 budget of 15 s. The structured cockpit is not published before web + prose.

## Code at HEAD
- `sidecar/services/research/fast.py:697`: `structured, web = await asyncio.gather(_structured(), _web())`. The bundle lands at max(structured, web).
- `fast.py:632-673`: every structured leg is boxed at `_WITNESS_LEG_TIMEOUT_S = 6.0` (:101-105, "so it never holds the NORMAL path past its FR-070 budget (<= 15 s)").
- `fast.py:675-695` and `:501-530`: `_web()` → `_web_round` → `_safe_call(tool_call, "web_search", ...)` runs with NO time box at the fast level.
- `sidecar/services/search/keyless.py:61-67`: `ENGINE_CHAIN = ("ddg", "brave", "mojeek")` and `ENGINE_DEADLINE_SECS = 6.0`. The comment reads "Three engines x 6 s = 18 s, inside the 25 s web_search tool cap". So the web leg of a NORMAL run may take 18-25 s by design, above the 15 s budget.
- The fix_shape's "publish the structured cockpit as soon as the gather returns (before web + prose)" is absent. Nothing is emitted between the two gathers.

## Repro 1 at HEAD: offline, deterministic (the repo's own test fixtures)
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/r027/test_web_stall.py` reuses `_SlowLegToolCall` and `_stub_offline_crosschecks` from `sidecar/tests/test_research_fast.py`. That fixture is the one the existing R15-RESEARCH-027 test uses for price/news. Here it runs with the slow leg set to `web_search` (a 20 s sleep).
Command: `cd sidecar && ./.venv/bin/python -m pytest /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/r027/test_web_stall.py -q -s -p no:cacheprovider`
```
   step plan | resolving "Apple" | None
   step plan | resolved → AAPL | 0
   step tool | pulling market data for AAPL | None
   step search | searching the web for Apple Inc. | None
   step tool | growth cross-check | 0
   step tool | ownership cross-check | 0
   step tool | declared dividend cross-check | 0
   step tool | 52-week range cross-check | 0
   step tool | market-cap witness cross-check | 0
   step tool | earnings quality cross-check | 369
   step tool | dividend TTM cross-check | 738
   step tool | pulled 4/4 data sources | 882
   step search | 1 web source(s) | 20001
   step synthesize | assembling the research bundle | None
.
1 passed in 20.38s
ELAPSED_S 20.0 WEB {'available': True, 'reason': None, 'note': None} FUND_OK True
```
The structured fan-out finished at 882 ms ("pulled 4/4"), but the bundle returned at **20.0 s**. The web leg is the one leg the existing `test_a_stalled_leading_leg_is_time_boxed_and_the_rest_publish` (`test_research_fast.py:947-977`, parametrised on price_data and news only) does not cover.

## Repro 2 at HEAD: real resolver and real providers, keyless engines stalled
This is the shard's shape. `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/r027/r027.py` patches `DdgSearchBackend`/`BraveSearchBackend`/`MojeekSearchBackend.search` to `await asyncio.sleep(60)` and runs `fast.gather_fast(q, region="IN", tool_call=agent_tools.invoke_tool)` in-process against a scratch data dir.
Command: `cd sidecar && ./.venv/bin/python -u /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/r027/r027.py /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/data-inproc stall Saksoft "Tata Elxsi"`
```
{"mode": "stall", "q": "Saksoft", "wall_s": 24.4, "symbol": "SAKSOFT", "legs_ok": {"price": false, "fundamentals": false, "news": true, "filings": true}, "web": {"available": false, "reason": "unreachable", "note": "No web-search backend configured \u2014 structured data only", "detail": "keyless web search has no engine availab
{"mode": "stall", "q": "Tata Elxsi", "wall_s": 18.4, "symbol": "TATAELXSI", "legs_ok": {"price": false, "fundamentals": false, "news": true, "filings": true}, "web": {"available": false, "reason": "unreachable", "note": "No web-search backend configured \u2014 structured data only", "detail": "keyless web search has no engine av
```
Saksoft: structured done at 6.2 s, web at 24.4 s ("no web backend — structured only", 24,290 ms), bundle **24.4 s**. Tata Elxsi: structured at 6.4 s, bundle **18.4 s**. The prose turn still has to follow, so the NORMAL answer is well above 15 s. Price and fundamentals timed out cold in this in-process run. That is honest and dropped at 6 s, and it is not the defect.

## Duplicate search
R15-RESEARCH-008 (keyless DDG hang vs the 25 s web_search tool cap) is a different bound, and it holds: 18-24 s < 25 s. R15-RESEARCH-028 is SearXNG status. Only R15-RESEARCH-027 owns the NORMAL <= 15 s budget.

## Classification: partial on R15-RESEARCH-027
Its stated repro (33-38 s from unboxed structured legs) no longer reproduces. Every structured leg is boxed and the web leg runs concurrently. But the class, `research-latency-budget`, is not closed. Its fix_shape asks for a per-leg timeout on slow legs so the fast path "still publishes within budget" and for the cockpit to publish before web + prose. Its batch-8 note already records the leading legs as the open part. The web leg is the remaining unboxed leg of the same path.

## Severity: medium (unchanged)
A stated feature (the interactive NORMAL budget) is degraded only when every keyless engine stalls. The answer still arrives, honestly labelled "structured only", within the 25 s tool cap.

## Certification failures
The baseline for R15-RESEARCH-027 is 1: stage-c batch-8 not_certified. It is certified in batch-9, its note has no clause, and no refutation-audit verdicts exist for it. This partial adds 1, for a total of 2.
