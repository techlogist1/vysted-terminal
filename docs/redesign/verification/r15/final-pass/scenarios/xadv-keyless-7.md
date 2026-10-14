# xadv-keyless-7 — keyless research on a small Indian stock ("research KITEX.NS", local llama3.1:8b, no Docker search)

LOCAL-MODEL LOCK held 15:20:12 -> released by trap at exit (EXIT=0). Same curl harness as xadv-keyless-5 (vy.py's port guard refuses :52900).
```
POST :52900/agents/copilot/invoke {"prompt":"research KITEX.NS","provider":"ollama","model":"llama3.1:8b","mode":"agent"}
```
Raw SSE: docs/redesign/verification/r15/final-pass/raw/xadv-keyless/inv7.sse

## Research trace (research_step events)
```
1 engine  research:begin depth=normal query=KITEX.NS
3 plan    resolved → KITEX
4 tool    pulling market data for KITEX
5 search  searching the web for Kitex Garments Limited
6 tool    error 6005ms  filings timed out after 6s — dropped
7 tool    error 6000ms  price timed out after 6s — dropped
8-11 tool ok   growth / earnings quality / market-cap witness / dividend TTM cross-checks
12 search skipped 8000ms "no web backend — structured only"   (brief: web_available false, web_reason "timeout", note "Web search did not answer within 8s — structured data only")
13-15     ownership / declared dividend / 52-week range cross-checks timed out after 6s — dropped
16 tool   pulled 2/4 data sources
```
Auto-published brief (staged behind the §6.5 gate: "Staged for your review, not applied yet: publish_brief KITEX. Accept it below to apply."): `structured.price = {"ok": false, "error": "price timed out after 6s — dropped"}`; fundamentals ok (yfinance).
Model prose: "We couldn't retrieve KITEX.NS's price due to a provider error ... Market Cap: ₹2,329 cr, Dividend Yield: 0.43%, EPS (TTM): -1.19". All three figures trace to the fundamentals tool result (market_cap 23291625472 -> ₹2,329 cr; dividend_yield 0.0043; eps -1.19). No fabricated figure; the §6.5 gate held (publish staged, not applied).

## Defect A — the brief loses the price because price_data fetches 6 months of history first (keyless:4)
- `sidecar/services/research/fast.py:355` `_time_boxed("price", _safe_call(tool_call, "price_data", {"symbol": symbol}), on_step, box)` with `box = _WITNESS_LEG_TIMEOUT_S = 6.0` (:106, :353); the brief keeps only the quote from it: `:364 "price": _structured_value(price_res, "quote")`.
- `sidecar/services/agent_tools/price_data.py:48-56`: `series = await asyncio.to_thread(provider_registry.get_history, symbol, timeframe, str(range_), asset_class)` THEN `quote = await asyncio.to_thread(provider_registry.get_quote, ...)` — sequential; the quote waits behind the history chain.
- Live: the history chain for an NSE small cap takes ~10 s whenever nse_direct's historical API resets the connection (main.log `15:21:07 provider nse_direct failed for ohlcv ... /api/historicalOR/cm/equity: ... curl: (35) Recv failure: Connection reset by peer`, then `15:21:18 provider nse failed for ohlcv ... ConnectionResetError`), so the whole leg is dropped although the quote alone answers at once: `GET /quotes/NAHARCAP.NS` 0.25 s cold, `GET /quotes/KITEX.NS` 0.001 s (116.68, nse_direct).
- Second case (fresh symbol, no LLM): MCP `tools/call price_data {"symbol":"SHAILY.NS"}` on :52900/mcp/ -> `elapsed 10.6s`, ok true, provider "nse" (log `15:25:59 provider nse_direct failed for ohlcv ... Connection reset by peer`); `GET /history/SHAILY.NS?timeframe=1d&range=6mo` 10.06 s. Inside research that leg would be dropped at 6 s; the quote it carries (3009.1) was already cached.
- The NSE reset itself is upstream (a plain-curl probe of the same endpoint answered 200 in 1.3 s, so it is per-client throttling, not an outage); the product defect is the coupling: a history hiccup on a leg whose only consumed output is the quote erases the price from the brief and its metric cards on the keyless small-cap path.
- R3: R15-RESEARCH-027 (fixed) added the 6 s witness boxes (latency target); no entry names price_data's history-before-quote ordering or a dropped price leg. New, medium (R2: the research brief for an Indian small cap silently loses its headline number under a common NSE throttle).

## Defect B — FAST research's 8 s web round cannot reach the keyless chain's last resort (keyless:5)
- `services/search/keyless.py:61 ENGINE_CHAIN = ("ddg", "brave", "mojeek")`, `:67 ENGINE_DEADLINE_SECS = 6.0` (comment :63-66: "Three engines x 6 s = 18 s, inside the 25 s web_search tool cap, so a hanging engine ... can never keep a healthy later engine ... from being tried").
- `services/research/fast.py:120 _WEB_ROUND_TIMEOUT_S = 8.0`, `:693 web = await asyncio.wait_for(_web_round(tool_call, web_query), _WEB_ROUND_TIMEOUT_S)`.
- By construction, when DuckDuckGo hangs the research web round gives Brave at most ~2 s and never reaches Mojeek (which the chain comment calls "the engine most likely UP when the other two throttle in lockstep", :58-60). The R15-RESEARCH-008 guarantee holds for chat web_search (25 s cap) but not for the research path, which is where the README's "web research" lives.
- Live today: html.duckduckgo.com direct probe `000` after 10.07 s (hang); the research web round timed out at 8 s; MCP `web_search` (25 s cap) on the same stack: 11.4 s, "DuckDuckGo: unreachable; Brave: rate-limiting; Mojeek: rate-limiting" — on this shared IP Brave/Mojeek were throttling too (Mojeek direct probe returned a captcha page), so today's empty web leg is not attributable to the budget alone. Filed on the code-level mechanism only, low. Also the step text "no web backend — structured only" (fast.py:711) is shown for a timeout, which misnames an existing-but-slow backend.
- R3: R15-RESEARCH-008 (fixed, high) — its promise for web_search holds; this is the research-path residue. R15-LEAD-065 (open) — the web-ONLY branch has no time box at all (opposite problem, different branch). New, low.

VERDICT xadv-keyless-7: finding keyless:4, keyless:5
