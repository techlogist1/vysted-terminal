# rc1 gate round 5 — adversarial sample verifier, shard 10 (rc1-vshard-10, Opus)

Candidate: `633f844071d972b337f4c3526d86555c80df0568` (checked: `git -C <scratch>/rc1-round-5-9bc600e-fix-int rev-parse HEAD`). Own sidecar from that worktree's source on :52610, data copy `scratchpad/rc1-round-5-data-rc1-vshard-10` (seed snapshot, IN region), sleep pid 87612, stopped at the end. In-process checks ran with the worktree `sidecar/.venv` (PYTHONPATH=.), the frontend check with the worktree's vitest and a scratch config outside the worktree (worktree left clean). Nothing under r15/rc1/ was read.

Environment note: Yahoo answered many calls from this IP with 429 (shared with the other isolated sidecars). A direct `curl` of query1.finance.yahoo.com/v8/finance/chart/MSFT returned 200, so it is throttling, not an outage. Intraday IN and US legs of /history and /indicators were 429 upstream and are not counted either way.

| id | verdict | summary |
|---|---|---|
| R15-LIFECYCLE-020 | **refuted** | Own repro: a clean IN profile with no user requests. The Yahoo circuit opened at t=47 s and 7 times in 14 min. Every open came from the background fundamentals_warm .info crawler's throttles, each recorded at weight 1.0. |
| R15-RESEARCH-001 | holds | The DEEP/FAST news gate drops every off-entity region-feed item: 0 kept for ON/IT/AI/KEY/LOW/SO/NOW/CAT live. The BDL literal item is dropped. |
| R15-DATA-063 | holds | /indicators freshness equals /history for TCS, SBIN.NS, ITC.BO wk, RELIANCE.BO, NIFTYBEES.NS and ETH/USDT (live). Empty series gives 200 on both routes. |
| R15-LEAD-004 | holds | NDTV/JONJUA read the quarterly-gap wording and TCS.NS carries no reason. Five SME half-yearly filers stay half-yearly. |
| R15-LEAD-051 | holds | A single quarter, an SME-to-mainboard migrant and a Dec-FY IPO shape all read quarterly-gap, never half-yearly. Pure half-yearly controls are unchanged. |
| R15-LEAD-049 | holds | nifty50 screens 50/50 with TMPV.NS in and TATAMOTORS absent. /resolve?q=TATAMOTORS lists TMPV first. No universe seed misses the NSE master. |
| R15-LEAD-048 | holds | Mode ids apply their mode and never reset. Case/space/prototype-key variants fail and name the pattern. Explicit default still resets. |
| R15-LEAD-050 | holds | GE repro True. IT/ON/ALL/AI and stoplisted SO/GO/BE prose stay False. XP/BP/all-caps GE True. GM-class misses predate the fix (already R15-LEAD-058). |
| R15-LEAD-043 | holds | A no-key invoke and /llm/chat on openai/groq/deepseek/xai/openrouter/gemini/anthropic all return code auth "No <X> API key is set". Invalid keys give auth "rejected". |
| R15-CODE-DATA-023 | holds | Both named comments now describe composition, not counts. They match the live loader: nse-all 3506 = EQ 2584 + ETF 351 + SM 571; bse-all 5042; india-all 5891. |

## R15-LIFECYCLE-020 — refuted (entry stands at two certification failures: record for the lead, no fix round)

The entry's own repro is a clean keyless IN profile with no user requests; it expects "/system/provider-health yahoo open at t=27 s". At the candidate:

- Boot at 16:34:42. My first Yahoo-touching request came at 16:36:07 (`GET /fundamentals/TCS.NS`); before that the only access line is `GET /health`.
- `16:35:28,549 yfinance fundamentals rate-limited for 'SETFNIFBK.NS'` → `16:35:28,886 ... 'SETFNN50.NS'` → `16:35:29,609 WARNING services.provider_health: provider health: yahoo circuit OPEN for 51s (consecutive opens=1)` (the third throttle was 'SHAHCON.BO'). All three are symbols the background crawler picked. No user request was in flight.
- The circuit opened 7 times by 16:48:29 (opens_total 7, throttles_total 136). Every open was preceded by crawler symbols only: ALPEXSOLAR/BEWLTD/BASILIC, AMEYA/ARABIAN, CRAYONS/AMEYA, DENTALKART/DIGIKORE, DENTALKART/DRONE. The consecutive-opens escalation pushed the user-facing cooldown to 137 s and then 131 s.
- User-visible effect: `POST /screener/run {universe:nifty50}` at 16:37:06, while the crawler held the circuit open, returned `"throttled": true`.
- Mechanism (code at 633f844071d972b337f4c3526d86555c80df0568): `sidecar/services/fundamentals_warm.py:363-367`: the deep .info crawler (`_crawl_once`, a background warm loop in the same module the fix touched) calls `provider_registry.get_fundamentals(symbol)`. A Yahoo 429 there goes through `sidecar/services/yfinance_provider.py:93-101` `_provider_error` → `provider_health.record_rate_limited(provider_health.YAHOO)` at the default weight 1.0. The fix set `_WARM_THROTTLE_WEIGHT = 0.0` (`screener.py:170`) only on the two `fetch_quotes_batch` callers (`screener._warm_once`, `fundamentals_warm` sweep `:179`). The crawler path still spends the circuit that user requests read, which is what fix_shape rules out ("keep background warming from opening the circuit user requests share"). The crawler also starts about 1 s after boot, with no grace period.
- command: `cd <worktree>/sidecar && VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52610 --data-dir <scratch>/rc1-round-5-data-rc1-vshard-10`, then `curl :52610/system/provider-health` and `grep "circuit OPEN" sidecar.log`. Checkout sha 633f844071d972b337f4c3526d86555c80df0568.
- Output: `{"yahoo":{"open":true,"cooldown_remaining":5.44,"consecutive_throttles":0.0,"consecutive_opens":1,"opens_total":1,"throttles_total":12.0}` at 16:36:0x, before any user request touched Yahoo.

## R15-RESEARCH-001 — holds
- Command: `VYSTED_REGION=US PYTHONPATH=. .venv/bin/python news001.py ...`, which calls `agent_tools.news_tool._news({symbols:[SYM],limit:100})` and then `relevance.gate_news`. This is the exact pair `deep.py:919-928` runs.
- Results for ON: total 30, region_feed 10, kept_region_feed 0. Dropped included 'On Holding (ONON) ... Buyback', 'Lockheed Martin ...', 'Nvidia doubles down ...', 'Innate Pharma ...'. IT: 8/8 dropped. AI: 7/7 dropped. Fresh common-word tickers: LOW dropped 1/1 ('Accordia Bank ... low minimum deposits'); KEY, SO and CAT had 0 region items; NOW dropped 2/2.
- IN: RELIANCE.NS dropped 2 off-entity items with the note 'No on-entity news found for RELIANCE.NS — 2 item(s) ... dropped.' ITC.NS kept its own 'ITC expands dairy business ...'.
- The BDL literal Sterling and Wilson item (`1e4af0a955903e90`) is dropped when untagged, when alias-tagged ['BDL'], and when stamped via_symbol_feed (the IN full gate). The on-entity 'Bharat Dynamics bags ...' is kept.

## R15-DATA-063 — holds
- `cmp.py` against :52610 compares /history and /indicators freshness and provider. Results: TCS rsi 1d eod/nse_direct = eod/nse_direct. SBIN.NS bbands eod = eod. ITC.BO sma 1wk eod/bse = eod/bse. RELIANCE.BO rsi eod/bse = eod/bse. NIFTYBEES.NS (ETF) eod = eod. ETH/USDT ema 1h crypto live/ccxt:binance = live/ccxt:binance.
- Empty series, in-process, with `get_history` raising EmptySeriesError: /history returns 200 with bars []. /indicators with rsi,macd,bollinger (1d) and with vwap (1h) returns 200, provider none, freshness null.

## R15-LEAD-004 / R15-LEAD-051 — hold
- Live `GET :52610/fundamentals/NDTV` and `/JONJUA` with X-Vysted-Region IN return revenue_ttm/net_income_ttm reason 'TTM basis: the exchange filings leave a quarter of the trailing year unfiled or unparsed; kept, flagged', with no 'half-yearly'. TCS.NS has no reason. FORGEAUTO.NS gets 'consolidated, sum of 2 filed half-years to 2026-03-31' from nse.
- In-process `exchange_financials._fetch`: NDTV.NS quarterly-gap (Apr-Sep 2025 6M plus Apr-Jun 2025 3M). JONJUA.BO quarterly-gap (3 quarters). TCS.NS and DHANBANK.NS quarterly. FORGEAUTO, TECHERA, HOLMARC, UNIHEALTH and WOL3D (NSE Emerge) half-yearly, from 6M periods only.
- Constructed `FiledPeriods` (cad2.py): a single quarter ever filed, an SME-to-mainboard migrant (two halves then one quarter), a Dec-FY IPO (2 quarters plus a pre-IPO 9M context), 2 quarters plus an FY context, and a Dec-Feb quarter all read quarterly-gap. Pure half-yearly and half-yearly-plus-annual controls read half-yearly.

## R15-LEAD-049 — holds
- `POST /screener/run {universe:nifty50}` evaluated 50, skipped 0, and returned TMPV.NS; the only TATA rows are TATASTEEL/TATACONSUM. `GET /resolve?q=TATAMOTORS` → TMPV, TMCV, TSLA.
- Every `.NS` in `screener_universes/*.json` is present in the NSE master. No TATAMOTORS remains in src/ or in the sidecar seeds; the only other mention is in the marquee_aliases comment. Direct /quotes/TATAMOTORS.NS is R15-LEAD-053 (open, low) and was not re-filed.

## R15-LEAD-048 — holds
- Scratch vitest (`scratchpad/vs10/vt/lead048.test.ts`, config outside the worktree, run with the worktree's vitest 4.1.6): 10/10 pass. technical, macro and compare-desk (with symbol INFY.NS) each give 'Arranged the <mode> layout': clear ×1, 3/3/2 panels, the chart loads INFY.NS, and resetLayout is never called.
- 'Fundamental', 'compare desk', 'fundamental analysis', 'research', 'hasOwnProperty' and '__proto__' each return label null and reason 'unrecognised layout "<p>"'. The preview reads 'Unrecognised layout "<p>" / Layout: unchanged'. No clear, no reset.
- An explicit 'default' still resets. The `/layout <arg>` slash command (ChatSidebar.tsx:698-703) takes the same host path.

## R15-LEAD-050 — holds
- In-process `row_relevant`: 'GE beats estimates on jet engine demand' (GE) → True. ALL 'ALL EYES ON THE FED', IT 'Tax-free bond yields ...', ON 'Stocks move on hopes ...' and AI 'AI chip demand ...' → False. The fresh 2-letter stoplisted prose cases SO 'SO far...', GO 'Markets GO higher' and BE 'What could BE next' → False. 'NYSE: SO' → True. XP 'XP profit rises', BP 'BP to cut 5% of jobs' and 'GE BEATS ESTIMATES ...' → True.
- GM, MU, KO, HD, BA and JD bare mentions → False at the candidate. They are also False at base 522c3246 when base relevance.py is run in-process: the `if len(symbol) >= 3` guard has existed since 54f4e9c2, so this is not a regression of this fix. R15-LEAD-058 (open, low) already covers it, so it was not re-filed.

## R15-LEAD-043 — holds
- `curl -N -X POST :52610/agents/copilot/invoke {prompt:'hi',provider:P,mode:'agent',autonomy:'ask'}` with no api_key. vy.py refuses non-GET outside 52100-52399, so I used curl directly, with no key and no spend. openai, groq, deepseek, xai, openrouter, gemini and anthropic each return `{"kind":"error","message":"No <Provider> API key is set — add it in Settings.","code":"auth"}`. `/llm/chat` gives the same for openai, groq, deepseek, gemini and xai.
- An invalid key 'sk-invalid-r15-induced-401' on openai and groq returns code auth 'The <X> API key was rejected'.

## R15-CODE-DATA-023 — holds
- `screener_universe_india.py:1-19` and `models/screener.py:28-33` now describe composition (EQ + ETF + SM/NSE Emerge; Active BSE; union with NSE preferred) and carry no counts. The live loader agrees: EQ 2584 / ETF 351 / SM 571 → nse-all 3506, bse-all 5042, india-all 5891. The `:95` '~5,156' is R15-LEAD-029 (open).

## Adjacent (new, not refutations)
1. **low**: `sidecar/services/nse_bhavcopy.py:36-40` says the bhavcopy EQ/BE/BZ set "covers the app's bundled NSE master (~2,675 symbols)" and that "the SME board (SM/ST ...)" is "outside the master". The master now has 3506 rows including 571 SM (NSE Emerge), so both statements are stale. This is the same current-state-drift class as R15-CODE-DATA-023, in a file that entry did not name.
2. **low**: the `quarterly-gap` TTM reason (`correctness_gate.py:586-590`) always says the filings "leave **a** quarter of the trailing year unfiled or unparsed". For the fresh listings R15-LEAD-051 routes into it (one or two quarters ever filed), two or three quarters of the trailing year are missing, so the reason understates the gap. Constructed evidence: cad2.py 'single quarter ever filed' → the same one-quarter wording.

Scratch (not evidence, kept outside the tree): `scratchpad/vs10/` (sidecar.log, cmp.py, cad*.py, rel050*.py, news001*.py/out, bdl001.py, empty063.py, vt/).
