# R15 Stage C — batch-25 fresh-context verification

Verifier: Opus 5.5 (fresh context). Target `worktree-agent-batch-25-int@2e988c0d` (base `84280221`), checked out
in a scratch worktree. The main sidecar was booted from source on `127.0.0.1:52310` with a copied ISO data dir, and
the MCP subprocesses were on :52153 and :52154. The local model was ollama `llama3.1:8b`. No OpenRouter or OpenAI
spend was used.

**Chain.** The integrator's `ci-local-2.log` ran green end to end (vitest 1862, pytest 3663), and `smoke.log` is
green. At HEAD, which includes the review commit, this verifier re-ran the full sidecar pytest: **3664 passed,
1 skipped**. It also ran the six frontend test files the batch touched: **157 passed**.

**Tally.** 10 certified, 4 not certified, 0 needs_gui, 0 not-a-defect proposals.

| Entry | Verdict | Evidence (running app / outside world) | Fresh case |
|---|---|---|---|
| R15-CODE-PLATFORM-013 | certified | The register's re-proof `plat013.test.tsx`, run against this worktree, prints `after resetToDefaultLayout flag: false … plugin commands live: 0`. | Restoring an older blob `{plugin:vysted-example:false, news:false}` over an attached plugin keeps the flag `true` and applies `news:false`. A direct `setEnabledMap({plugin:x:false, chart:true})` leaves plugin:x `true`. |
| R15-LEAD-028 | certified | `/fundamentals/506597.BO` returns AMAL.BO 'Amal Ltd', and `544774.BO` returns 'SMR Jewels Limited'. `/fundamentals/506597.BO/income` returns 5 periods. `/quotes/506597.BO` returns AMAL 673.05 INR. `/history/544774.BO?range=1y` returns 72 bars (bse). Ratings and earnings for 532540.BO return 200. | `500325.BO` returns 'Reliance Industries Limited' (fundamentals) and 128 bars (history). `532540.BO` returns TCS. |
| R15-DATA-064 | certified | `/history/RELIANCE.NS?timeframe=30m&range=1y` returns 767 bars, reason null, partial true, coverage_start 2026-07-06. Default SPY 30m returns 286 bars. `/indicators/SPY?…&timeframe=30m` returns 200. In-process `_price_data` 30m returns ok for AAPL and RELIANCE.NS. | TCS.NS `1m&range=1mo` returns 2526 bars, partial. INFY.NS `1h&range=5y` returns 5038 bars, partial, coverage from 2023-10-18. MSFT `15m&range=6mo` is partial. HDFCBANK.NS `_price_data` 30m is ok. A range inside the cap (`30m&range=1mo`) has partial false. |
| R15-DATA-116 | certified | `/disclosures/shareholding` returns 200 for AMAL (104), NAPEROL (104) and ELCIDIN (118). There are 0 `index HTTP 403` lines in the sidecar log. | ICONIKSPEV (scrip 511260) returns 107 patterns, all `source: BSE`, with a www.bseindia.com XBRL URL. SMR and the bare code `544774` each return 200. |
| R15-CODE-AGENT-034 | certified | A FastMCP in-memory Client over `_build_server()` pointed at :52310 was used. `list_workspaces` returns is_error False and `{'workspaces': ['__autosave__','b25v desk']}`. `get_workspace('b25v desk')` returns the saved `{'version':1,'tag':'b25v'}`. A missing workspace returns `{ok: False, error: '…404…'}`. | A workspace name containing a space round-trips through the quoted path. |
| R15-DATA-113 | certified | `/earnings/WIT/estimates` returns revenue_currency INR, while currency is USD. INFY (US) returns INR. INFY.NS returns INR. TSM returns TWD. AAPL returns USD. `EpsEstimateGrid.test.tsx` is green. | HDB returns INR and IBN returns INR. BABA returns CNY (quarterly estimate 2.7e11, in band with CNY revenue). History rows carry INR for INFY and WIT, and null (not guessed) where Yahoo has no estimate (TM, SONY). |
| R15-RESEARCH-015 | certified | The register's `r015.py`, re-pointed at this worktree: case C (www + nsearchives.nseindia.com) and case D (SearXNG-only, two subdomains) give `verdict=unverified`, 0 verdict calls, and no 'corroborated across channels'. Control B stays agree/corroborated. | `www.sebi.gov.in` + `sebi.gov.in` (a .gov.in suffix) gives unverified. `m.economictimes.com` + `economictimes.indiatimes.com` gives agree (2 registrable domains). `deep.distinct_web_domains` over www/rbidocs.rbi.org.in plus www/api.bseindia.com gives {bseindia.com, rbi.org.in}. |
| R15-AGENT-019 | certified | Live (llama3.1:8b, agent, auto): 'Could you ditch my TCS holding?' emits a real `portfolio_delete_position` tool_use and a staged proposal. The write tool was on the surface. The model's own arg (`position_id:'get_portfolio'`) is weak, but that is model quality, not the gate. In-process `_agent_tool_ids` keeps every data write on all 11 title/repro phrasings: write-a-note, `screen for …`, save layout, 'Delete TCS…', 'I bought 10…', 'My RELIANCE lot…', 'Put 25 HDFC Bank…', 'Can you log…?' and 'Can you record…?'. | 'Would you please offload my SBIN stake?' and 'Will you knock HDFCBANK out of my portfolio?' keep the writes. Real read questions ('What is the dividend yield of ITC?', 'Is TCS cheaper than INFY on P/E?') still strip. |
| R15-AGENT-093 | certified | The register's `agent093.py`, re-pointed at this worktree: `max_strikes '5.0'` becomes int 5. `points[{'price':'185.5'}]` becomes 185.5. A stringified points list is parsed, then coerced. yield_curve nested `tenor '3'`/`rate '0.05'` become 3 and 0.05. `'ten'` still gives the sentinel. | Live llama3.1:8b 'Show me the NIFTY option chain with just 5 strikes' gives an `option_chain` tool_use `max_strikes: 5`, ok true, with no invalid-args sentinel. yield_curve_value with a stringified `instruments` array holding `tenor '6'`, `'5.0'`, `rate '0.051'`, and `sample_count '7.0'` gives ints and floats at every depth. Nested `'NaN'` stays a string and `'2.5'` for an integer gives the sentinel. A trendline with nested `'1e2'` gives 100.0. |
| R15-AGENT-053 | certified | The register's `news053.test.tsx`, against this worktree: `buttons named AMD: 1`, chip tag BUTTON, not inside the `<a>`, and `loadSymbolIntoChart calls: [["AMD"]]`. Earnings, analyst-ratings and SEC symbols already call `loadSymbolIntoChart`. `captureTerminalState` carries a generic per-source summary (batch-10). | A three-symbol item (HDFCBANK.NS, ICICIBANK.NS, SBIN.NS) gives 3 `type=button` chips, 0 inside the anchor. Clicking SBIN loads only `SBIN.NS`. The headline anchor still links to the article. |
| R15-DATA-002 | NOT certified | No fix was merged. The W1 region work is on `worktree-agent-batch-25-W1-data002-wip@b91ddef3`, which is not an ancestor of HEAD. `SymbolEntry` has no region, and `pickCandidate(c.symbol)` still drops it. | Sidecar control: AMAL returns INR 674.4 under IN and USD 47.58 under US. Only the watchlist propagation is missing. |
| R15-AGENT-010 | NOT certified | The `a010.py` hang race (never-answering proxy) still takes **31.07 s** where it must be <= 6 s. `yf.Search(..., timeout=5.0)` from a cold process takes 30.01 s, stuck in `_get_crumb_basic`: yfinance `_make_request` → `_get_cookie_and_crumb()` passes no timeout, so the default is 30. | With the crumb already warm, the same hung Search takes 5.00 s, so the fix holds only after a crumb is cached. The event loop does not stall (max_gap 21 ms). |
| R15-DATA-059 | NOT certified | ISIN: SIFY US82655M2061, ONC US07725L1026, AAPL US0378331005. The TCI(US) guard holds (US8936172092). Former name: ONC 'BeiGene, Ltd.'. **But** US `board` is null and there is no `listing_date` on /resolve, and `/fundamentals/ONC` has listing_date null and isin null. The title claim 'no … board or listing date' still holds. | MSFT US5949181045 and NVDA US67066G1040 are correct. AAPL board is null. |
| R15-RESEARCH-043 | NOT certified | The corpus holds with byte-identical parity: `[2, 3]` becomes `[2][3]`, `[NSE filing, August 2026; 2][3]` becomes `[2][3]`, and `[New findings]`/`[Structured: …]` are stripped (py) or `[?]` (ts). `[NSE: TCS]`, `[sic]`, links, `[?]` and reference definitions survive. **But** the any-token rule turns numeric prose brackets into citations. `Shares outstanding [1,234 mn] at year end.` becomes `[1]` on both sides with 0 broken, a silent fabricated citation. `[Rs 1,200] was set` and `[₹1,20,000 cr]` are erased (backend). At base these rendered verbatim. The register fix_shape requires EVERY token to be an integer. | The planner's held-out cases pass: `[Annual report FY25; 1-2]`, `[Moneycontrol]` flagged, `[the Company]` mid-sentence kept, `[4–6]` with 5 sources gives `[4][5]` plus 1 broken. |

## Issues noticed (outside the entries, not in the diff)

- The intent gate now keeps data writes on agent-addressed READ questions ('Can you tell me what EBITDA means?',
  'Would you say INFY is overvalued?'). This follows D-B3-3 by design: writes still stage for review. It is noted
  here in case the operator wants a narrower request cue.
- `/earnings/{RDY,TM,SONY}/estimates` return 502 `incomplete estimate fields`. That raise is pre-existing
  (earnings_provider.py:555, untouched by the diff).
- `/fundamentals/ONC` returns `isin: null` while `/resolve?q=ONC` carries the ISIN. The lazy lookup covers resolve
  only.
- Live llama3.1:8b yield-curve call: the model omitted the required `type`. That is a model-quality gap, not
  coercion.

## Verdict

**approve.** The chain is green, and 10 entries certify against the running app with fresh cases. None of the
certified entries is a regression. The RESEARCH-043 numeric-bracket defect is new behaviour on an edge input, and it
is not certified. It is not a block: at the integration level it replaces a much more common leak (grouped and label
brackets shipping verbatim). It still needs the every-token rule before it can close.
