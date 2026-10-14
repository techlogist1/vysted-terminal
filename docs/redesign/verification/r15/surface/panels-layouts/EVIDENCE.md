# panels-layouts: owner-drive evidence (R15 Stage B, surf-S2B)

Worker: agent **P**, claude-opus-5-5[1m], 2026-09-23 08:22-09:00 IST. Twin split: see
`_TWIN_AGENTS.md` (S drove screener, T refuted screener, P drove this group).

## Stack and method

- Sidecar `127.0.0.1:52220`, booted by twin S at 08:22:26 (sleep pid 21350) from source, with
  data dir `scratchpad/vysted-iso/seat-panels-layouts/data` (a `cp -R` of the ISO operator copy)
  and S's MCP pair on :53219 (openbb) / :53220 (sec-edgar). P reused it (COMMON.md: reuse a
  live sidecar on your port) and stopped it at the end (see the bottom of this file).
- Driver `scratchpad/s2b-panels/d.py` (GET/POST) + `sse.py` (SSE), sending exactly what each
  panel's `api.ts`/store sends, including the `X-Vysted-Region: IN` header `sidecarGet` adds.
  Every call is one line in `P-http-log.jsonl` (label, url, body, status, ms, bytes, excerpt).
  Five request bodies over 4 KB were elided for size after the run (`_elided_for_size`).
- Pure layout logic: scratch vitest `scratchpad/s2b-panels/vt/arrange-probe.test.ts` (outside
  `src/`, run with a scratch config) -> `P-arrange-probe.json`. One existing test file run:
  `src/modules/panel-context-publishers.test.tsx` (13/13 passed).
- Upstream-shape check for the SEC parsers: the sidecar's own `_call_tool` + parser functions
  run in the sidecar venv against MCP :53220 -> `P-sec-parser-check.txt`.
- Freshness labels for period bars: `services.locale.freshness_for` evaluated at fixed dates ->
  `P-freshness-period-bars.txt`.
- LLM lanes: one local-lane invoke (ollama llama3.1:8b, $0) -> `P-agent-open-panels-llama.*`.
  No free or paid calls.

## What each surface did (score, and the line in the log that shows it)

Full per-row scoring with evidence pointers is in `COVERAGE.json` (32 rows: 5 ok, 10 partial,
9 broken, 4 NOT TESTED, 4 NEEDS-GUI). The short version:

| Surface | Score | What the log shows |
|---|---|---|
| Chart | broken | 7 of 8 timeframes load for US and IN. 30m returns 0 bars for every symbol, and the empty-state copy gives the wrong reason (**-3**). 1wk/1mo freshness badge is wrong (**-4**). Crypto 404 (COD-fe-data-9). All 50 indicators compute. One unknown key 400s the whole set (COD-fe-data-8). |
| Watchlist | broken | US + crypto rows ok. `.NS` rows never join (COD-mdp-2-2, live). An IN list of 20 names takes 23 s warm and slows unrelated quotes ~9x (**-7**). |
| News | broken | US rows ok. For IN, bare `BDL` returns Flanigan's Enterprises headlines tagged BDL (**-2**). |
| Equity Overview | partial | Every section loads for RELIANCE, KAYNES and AAPL. The keyless narrative path is honest. The LLM narrative is NOT TESTED (see below). |
| Agent Builder | partial | CRUD, 409, 422 and 400 paths all work. The 20-of-50 tool allow-list drift is confirmed (COD-fe-agent-shell-1/2). |
| Backtest | partial | The default run works, and the IN run returns an honest warning. Mixed good+junk symbols report clean (COD-backtest-5, live). Out-of-range params give a silent 0-trade result (COD-backtest-8). |
| Macro | broken | The FRED default needs a key (honest message). ECB and World Bank work. All 8 IMF catalog entries 404 (**-5**). |
| SEC Filings | broken | The filings list works. Filing sections and insider trades are always empty (**-1**). The detail metadata is fabricated (COD-mdp-2-1, live). Company search returns [] upstream. |
| Earnings Calendar | broken | The default universe is 10 US names (WLD-T-7). `INFY` returns the NYSE ADR with USD EPS mixed with INR revenue (**-2**). Quarter labels are off by one (**-8**). `.NS` becomes `RELIANCE-NS` (COD-mdp-1-3). |
| Analyst Ratings | broken | AAPL works. All three tabs are empty for every IN symbol, although Yahoo has targets for RELIANCE.NS (COD-mdp-1-3, live). The empty-state copy implies there is no coverage. |
| Option Pricer | broken | Black-Scholes and MC are correct. Binomial gamma is 1.4x-5.6x off, or 0 (**-6**), and theta has the wrong sign (COD-mq-1, live). The 120-way concurrency race was not reproduced (COD-mq-2). |
| Greeks / Bond | ok | Both match analytic and hand-computed values. |
| Yield Curve | partial | Defaults work. A duplicate pillar gives a 500 with no CORS header (**-9**). |
| Node editor (API) | partial | Save/load works. The run streams. Invalid, cyclic and unknown-type specs return 0 frames (COD-wf-4). `7 ** 10 ** 7` stalls the whole sidecar (COD-wf-7, larger blast radius). |
| Arrange templates | partial | Fit thresholds are as documented. Apply is rAF-deferred while it reports success (COD-wl-9). Menu and agent layouts differ for the same id (COD-wl-10). The local-lane agent sent the tool id `sec_filings_list` as a panel and a string where `panels` should be a list, then narrated success. |
| Workspace save/load | partial | Round-trip is equal. `Research: X` returns 400 (COD-wl-2). A 300-character name returns 500 (COD-wl-7). A corrupt file is listed but GET returns 404 (COD-wl-8). Deserializing needs a mounted dockview. |

`-N` = `census/raw/surf-panels-layouts.json` SURF-PANELS-LAYOUTS-N. COD-mdp = code-market-data-
providers, COD-mq = code-macro-quant, COD-wf = code-workflow-engine, COD-wl = code-workspace-
layout, COD-fe-data = code-frontend-panels-data-surfaces, COD-fe-agent-shell =
code-frontend-panels-agent-shell.

## New findings (9), headline facts

1. **SEC viewer and insider tab are dead.** Upstream returns 20,000 characters of Apple 10-K
   sections and 5 Form-4 rows. The parsers keep 0 of each, and the empty result is cached for
   24 h / 1 h. (high)
2. **Bare NSE tickers resolve to US companies in News and Earnings.** `BDL` returns Flanigan's
   headlines. `INFY` returns the ADR: EPS 0.205 "USD" alongside revenue of 491.5B at INR scale,
   shown without a currency. (high)
3. **Chart 30m is dead for every symbol.** The yfinance map requests 3mo, beyond Yahoo's 60-day
   cap. The IN empty-state blames EOD-only exchanges while 1m/5m/15m/1h load. (medium)
4. **The period-bar freshness badge is wrong.** The monthly chart always shows stale, the weekly
   chart shows stale by Friday, and NSE period-end bars show "EOD as of" a future date. (medium)
5. **The Macro IMF tab is dead.** Series ids contain `/`, the route is not `:path`, and all 8
   entries return 404, including the only India series. (medium)
6. **Binomial gamma is wrong.** It is 2.82x Black-Scholes at the panel's default 200 steps, 0 at
   201 steps, and 1.39x on the panel's default inputs. (high)
7. **The IN watchlist is slow and starves other routes.** The nse_direct throttle serialises the
   batch: 20 names take 23 s, and a concurrent single quote goes from 1.1 s to 9.5 s. EOD closes
   are re-polled every cycle. (medium)
8. **Earnings quarter labels are one quarter late.** For example JPM's Oct-13 Q3 report is
   labelled "Q4 2026". The agent tool receives this label. (medium)
9. **A duplicate yield-curve pillar causes an uncaught 500 with no CORS header**, so the panel
   cannot show the cause. (low)

## Existing code-critique findings this drive confirmed live (no new raw id filed)

COD-market-data-providers-2-1 (SEC detail fabricated "10-K filed today" for any accession, incl.
`0000000000-00-000000`), -2-2 (`.NS` quote rows never join), -1-3 (earnings + ratings dead for
`.NS`: `RELIANCE-NS`), COD-frontend-panels-data-surfaces-8/-9, COD-frontend-panels-agent-shell-1/-2,
COD-backtest-5/-6/-8/-13, COD-macro-quant-1/-3/-4/-8, COD-workflow-engine-1/-4/-7,
COD-workspace-layout-2/-7/-8/-9/-10, WLD-T-7, SURF-COMPOSER-CHAT-4.

**Not reproduced live:** COD-macro-quant-2 (QuantLib global evaluation-date race). I sent 12
parallel Monte Carlo requests, then 3 bursts of 40 parallel American-binomial requests, with
alternating valuation dates. All 120+12 results equal the serial values (`P-quant-concurrency.json`).
This is evidence for its refuter, not proof it cannot happen.

## NOT TESTED / NEEDS-GUI

- **Equity Overview LLM narrative.** The route reads the BYOK key from headers, and `vy.py` only
  drives `/agents/*/invoke`, so a key-safe narrative call needs a vy.py mode that does not exist.
  Cost if added: about $0.001 on gpt-5-nano.
- **Broker Connect and Order Entry** were removed with the trading feature (scope fact 1). The
  Audit Log viewer is order-audit only: its empty state and CSV export were driven, and the rest
  is removed with the feature.
- **Chart sync menu and market-session indicator** are browser-only stores or pure functions
  with no sidecar surface in this group.
- **NEEDS-GUI:** node-editor canvas, node palette drag, chart draw gesture, macOS Layout menu.
  Also any panel render state (loading skeletons, overflow, error-row text as painted).
  `deserializeWorkspace` needs a mounted dockview.

## Sidecar stop

See the final line of `_TWIN_AGENTS.md`.
