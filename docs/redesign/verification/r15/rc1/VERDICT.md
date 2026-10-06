# rc1 VERDICT: FAIL (gate round 2, rc1-verifier, Opus 5.5)

Candidate and tag sha: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Branch 004 has moved past it with docs-only commits, so the tagged tree must be 4c6dfe8c. Sheet: `docs/redesign/verification/R15_GATE_RC1.md`. Every excerpt below is copied verbatim from an evidence file in this directory tree. Paths are relative to `docs/redesign/verification/r15/rc1/`.

## 1. Register criterion: FAIL (product defect)
At 4c6dfe8c the register has 0 open critical/high/medium, but the claim fails at the candidate (see items 10 and 12). Status counts from `git show 4c6dfe8c:docs/redesign/verification/vysted-r15-register.json`:
```
fixed 391 · open 205 (all low) · blocked_tier4 26 (6 high, 16 medium, 4 low) · removed_with_feature 14 · needs_gui 11 · not_a_defect 5
```

## 2. Gate 8, no trading path: PASS
`verifier/g2/g8-order-paths.txt` (head):
```
POST /orders -> 404
POST /brokers/kite/orders -> 404
POST /brokers/kite/session -> 404
POST /safety/kill-switch -> 404
POST /safety/kill-switch/reset -> 404
POST /audit-log -> 404
POST /portfolio/positions -> 405
POST /margins -> 404
```

`verifier/g2/tools-lists.json`:
```
{'catalog': 56, 'internal_tool_ids': 56, 'mcp_tool_ids': 32, 'TOOL_SCHEMAS': 56, 'KNOWN_TOOL_IDS': 56, 'registered': 1, 'mcp': 40}
```

Order attempt on llama3.1:8b under ask (`verifier/g2/g8-order-attempt.jsonl` / `.stdout`):
```
{"kind": "tool_use", "tool_call_id": "call_66e2202bab8a46f38f11082a55114020", "name": "portfolio_add_position", "input": {"cost_basis": 0, "note": "", "purchased_at": "2026-09-26", "quantity": 10, "symbol": "RELIANCE", "asset_class": "equity"}}
{"kind": "research_step", "tool_call_id": "call_66e2202bab8a46f38f11082a55114020", "tool": "host_action", "step_kind": "notice", "detail": "Staged for your review, not applied yet: portfolio_add_position RELIANCE. Accept it below to apply.", "latency_ms": null
I'm a helpful assistant and I cannot assist with buying or selling of shares. Is there anything else I can help you with?
```

Data-dir tables after the run (`verifier/g2/datadir-tables-after.txt`). There is no audit_orders table:
```
# 2026-09-26 17:40:53 after G8-2/G8-3 and the portfolio round trip
rc1-data-rc1-verifier/workflows.db: schedules workflows 
rc1-data-rc1-verifier/custom_agents.db: custom_agents 
rc1-data-rc1-verifier/portfolio.db: positions 
rc1-data-rc1-verifier/delegate_runs.db: runs 
rc1-data-rc1-verifier/plugins.db: plugin_configs 
rc1-data-rc1-verifier/data_cache.db: cache meta 
rc1-data-rc1-verifier/fundamentals_cache.db: fundamentals 
positions rows (legacy ledger): 0
```

Safety surface vs r13-bedrock (`verifier/g2/safety-surface.tsv`, 36 rows, first 3):
```
docs/BROKER_INTEGRATIONS.md	05115c08a3d9aee12eae61bb75b81c3f75b54083	79eef87f89d04f2f6535d7ba3f3ea2bfc9daa575	differs	3/270	del=	1 commits
docs/SAFETY_ARCHITECTURE.md	2399fea05636fdd1dd27d3705b1f874260102cf7	3594df7b7153b004af215ba9d3e6308dc9778367	differs	158/249	del=	2 commits
docs/screenshots/v0.5.0/safety-audit/	f849b92db294ad622a9f53cfd90d4681ff96067b	absent	differs	0/22	del=cce7b007	1 commits
```

## 3. Gate 8, tracked portfolio: PASS
`verifier/g2/g8-portfolio-steps.json`:
```
initial | [{"id": "default", "name": "Portfolio", "holdings": []}]
after add + save, read back from sidecar | [{"id": "h-563e4945-0b00-4bb7-919d-a0d858dc3b09", "symbol": "AAPL", "quantity": 5, "costBasis": 180, "assetClass": "equity"}, {"id": "h-9c429569-30bd-442f-b485-7d0cf66487bc", "symbol": "RELIANCE.NS", 
P&L vs live quote | {"failed": 0, "rows": [{"symbol": "AAPL", "price": 341.07000732421875, "currency": "USD", "mv": 1705.3500366210938, "pnl": 805.3500366210938, "pnlPct": 89.48333740234375, "check": 805.3500366210938}, 
CSV export (non-Tauri path) | {"result": {"path": null, "fellBack": true}, "lines": 3}
after delete AAPL + save, read back | [{"id": "h-9c429569-30bd-442f-b485-7d0cf66487bc", "symbol": "RELIANCE.NS", "quantity": 10, "costBasis": 1100, "assetClass": "equity", "note": "rc1v"}]
agent call replayed | {"id": "call_5baafb71bf0a404d90ca8aff0c963239", "name": "portfolio_add_position", "input": {"quantity": 5, "symbol": "TCS", "asset_class": "equity", "cost_basis": 3500, "note": "", "purchased_at": "20
enqueue under ask -> outcome, ledger read back | {"staged": "staged", "change": {"id": "change-1", "toolCallId": "call_5baafb71bf0a404d90ca8aff0c963239", "action": {"name": "portfolio_add_position", "input": {"quantity": 5, "symbol": "TCS", "asset_c
accept -> applied, ledger read back | {"res": "applied", "ledgerApplied": [{"id": "h-9c429569-30bd-442f-b485-7d0cf66487bc", "symbol": "RELIANCE.NS", "quantity": 10, "costBasis": 1100, "assetClass": "equity", "note": "rc1v"}, {"id": "h-b7f
order action place_order | {"staged": "staged", "accept": "failed", "kind": "panel", "detail": "unknown action \"place_order\"", "intent": {"name": "unknown", "raw": "place_order"}, "ledger": [{"id": "h-9c429569-30bd-442f-b485-
order action submit_order | {"staged": "staged", "accept": "failed", "kind": "panel", "detail": "unknown action \"submit_order\"", "intent": {"name": "unknown", "raw": "submit_order"}, "ledger": [{"id": "h-9c429569-30bd-442f-b48
order action propose_order | {"staged": "staged", "accept": "failed", "kind": "panel", "detail": "unknown action \"propose_order\"", "intent": {"name": "unknown", "raw": "propose_order"}, "ledger": [{"id": "h-9c429569-30bd-442f-b
```

## 4. ci-local: PASS
`verifier/g2/ci-local.log`:
```
=== ci-local-equivalent at 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 (git archive export) start 2026-09-26T12:08:23Z
=== STAGE lint rc=0 2026-09-26T12:08:32Z
=== STAGE format rc=0 2026-09-26T12:08:42Z
=== STAGE typecheck rc=0 2026-09-26T12:08:49Z
=== STAGE cargo-fmt rc=0 2026-09-26T12:08:49Z
=== STAGE clippy rc=0 2026-09-26T12:09:29Z
=== STAGE ruff-check rc=0 2026-09-26T12:09:29Z
=== STAGE ruff-format rc=0 2026-09-26T12:09:29Z
 Test Files  152 passed (152)
      Tests  1831 passed (1831)
=== STAGE vitest rc=0 2026-09-26T12:09:57Z
test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.01s
=== STAGE cargo-test rc=0 2026-09-26T12:10:34Z
=========== 3596 passed, 1 skipped, 4 warnings in 179.60s (0:02:59) ============
=== STAGE pytest rc=0 2026-09-26T12:13:39Z
EXIT=0 2026-09-26T12:13:39Z
```

## 5. Smoke: PASS
`verifier/g2/smoke.log`:
```
[smoke] freshness gate: all bundled sidecar binaries are newer than their source.
[smoke] vysted-sidecar version OK (0.8.0).
[smoke] vysted-sidecar /agents roster OK (13 agents).
[smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=40).
[smoke] vysted-openbb-mcp-sidecar OK (bound :56031, survived settle window).
[smoke] vysted-sec-edgar-mcp-sidecar OK (bound :56109, survived settle window).
[smoke] all sidecars booted cleanly.
SMOKE_EXIT=0 2026-09-26T12:16:39Z
```

## 6. Agent scenarios: FAIL (harness/environment)
File dates in `scenarios/` (the candidate was committed 2026-09-26 06:01 IST):
```
  27 2026-09-25
   6 2026-09-26

2026-09-26T06:32 ollama-rb4-arrange.jsonl
2026-09-26T06:33 ollama-sk4-sify-v2.jsonl
2026-09-26T06:35 ollama-sk3-elcidin-v2.jsonl
2026-09-26T06:38 ollama-rb2-portfolio.jsonl
2026-09-26T06:42 ollama-sk1-amal-v2.jsonl
2026-09-26T06:46 ollama-sc1-tcs-pe-a.jsonl
```

## 7. Owner-drives: PASS
Raw files under `r15/surface/<group>/rc1/` newer than the candidate commit:
```
composer-chat 8
failure-inducer 10
onboarding-stranger 6
panels-layouts 10
portfolio-notes 3
research-briefs 14
screener 7
settings-plugins 1
```
Spot-checks on my own sidecar: `verifier/g2/spot-screener-07.json`, `verifier/g2/spot-panels-layouts.txt`.

## 8. Fixed-name battery: FAIL (harness/environment)
Walk of `battery/raw/**` over 391 fixed ids: 76 have no raw file and 84 have only pre-candidate raw. Full lists are in `logs/rc1-verifier.md`. CODE-DATA-023 (no stage-c certificate) holds, from `battery/raw/set-71/CODE-DATA-023_probe.txt`:
```
--- comments ---
"""Full-market India screener universes from the bundled resolver masters (R10, D40).

Resolves the three India universe ids the contracts commit added to
``models/screener.py``:

  - ``nse-all``   — every NSE master row (EQ + ETF + SM/NSE Emerge) as
    ``SYMBOL.NS``.
  - ``bse-all``   — BSE master rows with STATUS == "Active" as ``SYMBOL.BO``
    (the liquidity ``group`` is retained in the per-symbol meta).
nse-all 3506
bse-all 5042
india-all 5891
```

## 9. Data packs: FAIL (harness/environment)
`battery/collected/*.json` collected_at:
```
P10_VIYASH.json 2026-09-26T06:35:53+0530
P11_FUSION.json 2026-09-26T06:36:24+0530
P12_DHANBANK.json 2026-09-26T06:37:52+0530
P13_ELCIDIN.json 2026-09-26T06:38:15+0530
P14_JONJUA.json 2026-09-26T06:39:41+0530
P15_SUMAX.json 2026-09-25T05:32:34+0530
P16_CREST.json 2026-09-25T05:33:16+0530
P17_SIFY.json 2026-09-25T05:34:10+0530
P18_ONC.json 2026-09-25T05:36:24+0530
P19_AMAL.json 2026-09-25T05:36:50+0530
P1_JNPR.json 2026-09-26T06:31:10+0530
P20_SMR.json 2026-09-25T05:37:14+0530
P2_DAL.json 2026-09-26T06:31:34+0530
P3_CHTR.json 2026-09-26T06:32:00+0530
P4_SAFE.json 2026-09-26T06:32:24+0530
P5_CSL.json 2026-09-26T06:32:53+0530
P6_ICON.json 2026-09-26T06:33:18+0530
P7_JUMBO.json 2026-09-26T06:33:45+0530
P8_NAPEROL.json 2026-09-26T06:34:12+0530
P9_AMAL.json 2026-09-26T06:35:11+0530
S1_DHOOTTRANS.json 2026-09-25T05:37:47+0530
S2_SMR.json 2026-09-25T05:38:11+0530
S3_VERTEX.json 2026-09-25T05:38:39+0530
S4_TTC.json 2026-09-25T05:39:05+0530
```
Shareholding 502 on BSE-only names (`verifier/g2/spot-shareholding.txt`, `verifier/g2/spot-bse-shp.txt`):
```
== TCS
{"symbol":"TCS","count":20,"patterns":[{"symbol":"TCS","quarter_end":"2026-06-30","quarter_basis":null,"promoter_percent":71.77,"fii_percent":null,"dii_percent"
--
== AMAL
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
--
== ELCIDIN
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
plain httpx: 403 <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD><BODY> <H1>Access Denied</H1>   You don't have permission to access "ht
_api_json present: True
sig: (path: 'str', params: 'dict[str, str]') -> 'object'
_api_json (curl_cffi lane): dict {'Table': [{'yr': '2026 - 2027', 'qtrid': 130.0, 'qtr': 'June 2026', 'status': 'New', 'filing_date_time': '2026-07-17T15:39:06.967', 'revised_date_time': None, 'XbrlFi
```

## 10. Fix loop closed: FAIL (product defect)
`verifier/g2/fixloop-briefs2-citecheck.txt`:
```
MARKER_RE on '[2, 3]': []
has expand_marker_groups: False
'an operating margin of 10.98% [New findings].' -> 'an operating margin of 10.98% [New findings].' removed= 0
'Dividend per Share: ₹4.90 [New findings].' -> 'Dividend per Share: ₹4.90 [New findings].' removed= 0
'Revenue grew 23% [2, 3] and orders rose [2, 4].' -> 'Revenue grew 23% [2, 3] and orders rose [2, 4].' removed= 0
'Order book 23,000 cr [7] with margin 12% [2].' -> 'Order book 23,000 cr with margin 12% [2].' removed= 1
## frontend: git show 4c6dfe8c:src/lib/brief-ingest.ts line 396
const CITE_MARKER_RE = /\[(\d{1,3})\](?!\()/g;
## sidecar: git show 4c6dfe8c:sidecar/services/research/citecheck.py line 39
MARKER_RE = re.compile(r"\[(\d{1,3})\](?!\()")
```
Concurrence with the triage rejections (rc1-verifier:26-30): `verifier/g2/fixloop-elcidin-price-data.txt`, `fixloop-sify-fundamentals.json`, `fixloop-sify-resolve.json`:
```
{"ok": true, "symbol": "ELCIDIN", "timeframe": "1d", "provider": "nse_direct", "quote": {"symbol": "ELCIDIN", "price": 103800.0, "change": -1030.0, "change_percent": -0.9825431651244874, "volume": 8.0, "open": null, "high": null, "low": null, "prev_close": null, "currency": "INR", "market_state": "CLOSED", "timestamp": "2026-09-25T00:00:00Z", "provider": "nse_direct", "freshness": null}, "bars_returned": 90, "bars_av
{'currency': 'USD', 'financial_currency': 'INR', 'revenue_ttm': 46506049536.0, 'price_to_sales': None}
[('ASMTEC', 0.8), ('IKOMA', 0.766), ('EMIAC', 0.766), ('RELICTEC', 0.766), ('7TEC', 0.766), ('SIFY', 0.913)] needs_disambiguation True
```

## 11. GUI round: DEFERRED (operator-attended)
The round was skipped because the computer-use grant does not cover the built app. needs_gui ids at 4c6dfe8c:
```
R15-CODE-AGENT-001 R15-LIFECYCLE-001 R15-LIFECYCLE-008 R15-UI-009 R15-UI-022 R15-UI-025 R15-UI-050 R15-UI-083 R15-UI-084 R15-DOCS-024 R15-LIFECYCLE-040
```

## 12. Adversarial sample: FAIL (product defect)
R15-AGENT-019 (`verifier/g2/adj-agent019-intent-probe.txt`):
```
PASS 'LITERAL: Update my RELIANCE cost basis to 1180'                 need portfolio_update_position | intent edit | writes ['portfolio_add_position',
FAIL 'Could you drop WIPRO from my portfolio?'                        need portfolio_delete_position | intent read | writes []
FAIL 'I exited my ITC position, can you take it out of my portfolio   need portfolio_delete_position | intent read | writes []
FAIL 'Can you bump my INFY quantity to 30?'                           need portfolio_update_position | intent read | writes []
```

R15-AGENT-093 (`verifier/g2/spot-agent093.txt`):
```
option_chain {'symbol': 'NIFTY', 'max_strikes': '10'} -> {'symbol': 'NIFTY', 'max_strikes': 10}
option_chain {'symbol': 'NIFTY', 'max_strikes': ' 5 '} -> {'symbol': 'NIFTY', 'max_strikes': 5}
option_chain {'symbol': 'NIFTY', 'max_strikes': '5.0'} -> {'__vysted_invalid_args__': "invalid arguments for option_chain: '5.0' is not of type 'integer'; call again with valid args"}
add_chart_drawing {'kind': 'horizontal-line', 'points': [{'price': '185.5'}]} -> {'__vysted_invalid_args__': "invalid arguments for add_chart_drawing: '185.5' is not of type 'number'; call again with valid args"}
yield_curve_value {'valuation_date': '2026-09-25', 'sample_count': '5', 'instruments': [{'type': 'deposit', 'tenor': '3', 'tenor_unit': 'months', 'rate': '0.05'}, {'type': 'swap', 'tenor': 2, 'tenor_unit': 'years', 'rate
```

R15-DATA-113, R15-LEAD-028, R15-DATA-064, R15-DATA-059 (`verifier/g2/spot-refutation-live.txt`):
```
== GET /resolve?q=SIFY
{"ok":true,"query":"SIFY","region":"IN","resolved":{"symbol":"SIFY","name":"SIFY TECHNOLOGIES LTD","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"SIFY","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"form
HTTP 200
--
== GET /fundamentals/506597.BO
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
HTTP 404
--
== GET /history/RELIANCE.NS?timeframe=30m&range=1y
{"symbol":"RELIANCE.NS","timeframe":"30m","bars":[],"provider":"none","freshness":null,"reason":"in_eod_only","partial":false,"coverage_start":null}
HTTP 200
--
== GET /earnings/INFY/estimates
{"symbol":"INFY.NS","fiscal_period":null,"eps_estimate_mean":19.61527,"eps_estimate_median":null,"eps_estimate_high":20.33,"eps_estimate_low":19.2,"eps_estimate_stddev":null,"estimate_analyst_count":8,"revenue_estimate_mean":491654926200.0,
HTTP 200
```

R15-DATA-002, R15-AGENT-053, R15-CODE-PLATFORM-013 (`verifier/g2/spot-refutation-code.txt`):
```
== AGENT-053 src/modules/news/NewsFeedPanel.tsx 118-150
   118	      <a
   119	        href={item.url}
   120	        target="_blank"
   138	        {item.symbols.length > 0 ? (
   139	          <div className="flex flex-wrap gap-1">
   140	            {item.symbols.map((symbol) => (
   141	              <span
   142	                key={symbol}
   143	                className="bg-charcoal-800 rounded-control text-micro text-charcoal-300 px-1 py-0.5"
   144	              >
   145	                {symbol}
== DATA-002 src/modules/watchlist/WatchlistPanel.tsx 286-291 and 434; src/store/symbols.ts 15-18
  const pickCandidate = (symbol: string) => {
    addSymbol(symbol, "equity");
                      pickCandidate(c.symbol);
export interface SymbolEntry {
  symbol: string;
  assetClass: "equity" | "crypto";
== CODE-PLATFORM-013 src/store/workspace.ts resetToDefaultLayout / setEnabledMap
91:  resetToDefaultLayout: () => void;
176:  resetToDefaultLayout: () => {
184:    useModulesStore.getState().setEnabledMap({});
== RESEARCH-015 sidecar/services/research/verify.py _row_domains + finance.domain_of
4c6dfe8c:sidecar/services/research/finance.py:139:def domain_of(url_or_domain: str) -> str:
4c6dfe8c:sidecar/services/research/finance.py-140-    """The bare registrable-ish host of a URL or domain string, lowercased.
4c6dfe8c:sidecar/services/research/finance.py-141-
4c6dfe8c:sidecar/services/research/finance.py-142-    Strips the scheme, port, and a leading ``www.`` — enough normalization for
4c6dfe8c:sidecar/services/research/finance.py-143-    the tier table without pulling in a public-suffix dependency.
4c6dfe8c:sidecar/services/research/finance.py-144-    """
4c6dfe8c:sidecar/services/research/finance.py-145-    text = (url_or_domain or "").strip().lower()
```

R15-RESEARCH-015 (`verifier/g2/spot-research015.txt`):
```
_row_domains -> ['nsearchives.nseindia.com', 'nseindia.com'] count 2
```

New high: MCP /workspaces (`verifier/g2/adj-mcp-workspaces.txt`):
```
252:     async def list_workspaces() -> dict[str, Any]:
253:         """List saved workspaces. Maps to GET /workspaces."""
254:         async with _internal_client() as client:
255:             response = await client.get("/workspaces")
256:             response.raise_for_status()
257:             return response.json()
258: 
259:     @mcp.tool
260:     async def get_workspace(workspace_id: str) -> dict[str, Any]:
261:         """Return a saved workspace by id. Maps to GET /workspaces/{id}."""
262:         async with _internal_client() as client:
263:             response = await client.get(f"/workspaces/{workspace_id}")
264:             response.raise_for_status()
265:             return response.json()
router = APIRouter(prefix="/workspace", tags=["workspace"])
GET /workspaces -> 404
GET /workspaces/rc1-verifier-g2-g8 -> 404
GET /workspace -> 200
GET /workspace/rc1-verifier-g2-g8 -> 200
GET    /workspace
GET    /workspace/{name}
```

## Known limitations (operator-attended, not fix rounds)
R15-LEAD-030/035/037/038 are blocked_tier4. LEAD-035 is adjudicated to the operator (DECISIONS 4.9-4.12, `r15/stage-c/batch-24/LEAD-035-CONCURRENCE.md`). New local-lane note rc1-verifier:15 comes from `scenarios/ollama-sk4-sify-v2.jsonl` and `ollama-sk3-elcidin-v2.jsonl`. The bundle rehearsal PASSED at 64e9470e (`r15/stage-d/bundle-rehearsal/REHEARSAL.md`). I cite it and did not rebuild.

VERDICT: FAIL. Do not tag rc1 at 4c6dfe8c.
