# rc1-vshard-7 working log (gate round 4)

- 2026-09-27 05:09:53 candidate worktree HEAD = 68d5573aff9a579af084dcbb124843f2aecff6e8 (checked)
- 2026-09-27 05:09:53 own sidecar :52607 from worktree source, data dir scratchpad/rc1-round-4-data-rc1-vshard-7 (fresh cp of seed). sleep pid 34158 (sh 34156, python 34159)
- 2026-09-27 05:13:20 RESEARCH-002: _parse_verdict over 3 repro + 8 acceptance + 18 fresh strings in worktree venv -> all verdict-word cases correct; deep._reflect_says_complete labelled INCOMPLETE cases False. HOLDS. Adjacent low: marker fallback reads negated 'no source confirms' with no verdict word ('Not verified - no source confirms') as agree.
- 2026-09-27 05:13:20 AGENT-027: humanize() over 24 provider bodies (repro + acceptance + fresh anthropic/mistral/deepseek/gemini 404/429) -> every row a workable code; live vy.py nonsense slug on shared :52152 (vy.py refuses non-GET on 52607, outside its 52100-52399 allow-range) -> code model_not_found, user_id redacted. HOLDS.
- 2026-09-27 05:13:20 AGENT-092: scratch pytest (not committed) two-round variant -> host_actions only the dispatched round-1 note. HOLDS. Adjacent: halted round's publish_brief (never dispatched) still persisted as row.brief -> delegate-runs.ts enqueues it.
- 2026-09-27 05:13:20 DATA-115: /history/AMAL.BO 1y -> provider bse 255 bars (NSE 29); fresh RELIANCE.BO/INFY.BO/500325.BO quote+history -> bse. HOLDS.
- 2026-09-27 05:18:01 DATA-043: custom [AAPL,RELIANCE.NS,MSFT,TCS.NS] limit 2 -> page has INR+USD, coverage 'ranked within each currency'; criterion labels carry (USD/INR/listing currency); header 'Market cap' bare but cells carry row currency (D57). HOLDS (header-suffix of fix_shape replaced by per-cell currency; noted).
- 2026-09-27 05:18:01 DATA-112: live repro MANIKA.NS last in desc+asc; in-process None/' ' currency rows last in both dirs on market_cap and pe_ratio. HOLDS.
- 2026-09-27 05:18:01 DATA-068: ratings/earnings/analyst-extended routes all carry as_of; 2nd GET within TTL same as_of (AAPL, INFY.NS); stores carry fetchedAt+15m TTL+refresh; panels render As of + Refresh. HOLDS.
- 2026-09-27 05:18:01 DATA-114: in-process fetch_latest_fo: today failed/404 with yesterday cached -> cached day, 1 network call over 3 requests. HOLDS. Adjacent: today 404 + Monday transport failure + Friday cached -> None x3 (502) and Monday re-probed every request.
- 2026-09-27 05:25:58 UI-090: in-process frozen-clock quotes: AAPL/IN, ^NSEI/^BSESN hold; BHP.AX, 7203.T, ^N225, HSBA.L read live after their exchange closed (US-calendar default). REFUTED (not certified on the title claim).
- 2026-09-27 05:25:58 LEAD-010: live unhinted AAPL 10-K lookups 200 (25-000079, 24-000123, 21-000105, 17-000070); /sections forwards form_type; viewer passes the hint. HOLDS. Adjacents: 10-Q zero sections; unhinted MSFT 10-Q row 50 404.
- 2026-09-27 05:25:58 RELEASE-007: lint chains the audit; audit clean on the tree; fresh off-grid classes exit 1. HOLDS.
- 2026-09-27 05:25:58 DOCS-018: 3.3 matches registry ranks; adjacent low on the 'fundamentals hit yfinance first' clause.
- 2026-09-27 05:25:58 Stopped own sidecar (killed sleep pid 34158); :52607 down. Report verifier/shard-7.md, findings findings/rc1-vshard-7.json (7), raw evidence verifier/shard-7-evidence/.
