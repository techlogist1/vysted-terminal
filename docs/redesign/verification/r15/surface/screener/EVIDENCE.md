# screener — owner-drive evidence (R15 Stage B item 4, surf-S2B, agent S)

Worker: claude-opus-5-5[1m] ("agent S" in `_TWIN_AGENTS.md`; twin agent P owns panels-layouts).
Date 2026-09-23 08:22-08:40 IST. Headless only.

## Rig

- Sidecar `127.0.0.1:52219`, source run, data dir `$SCRATCH/vysted-iso/seat-screener/data`
  (`cp -R $SCRATCH/vysted-iso/data`, keyless `dev-keystore.json`), MCP pair `:53219/:53220`
  (`VYSTED_OPENBB_MCP_PORT`/`VYSTED_SEC_EDGAR_MCP_PORT`), `/health` -> `openbb-mcp: available`.
  Pids: `$SCRATCH/vysted-iso/pids-surf-S2B.json` (sleep 21347 / worker 21348).
- `harness/scr.py`: POSTs `/screener/run/stream` with exactly the body `src/store/screener.ts:315-385`
  builds and parses frames like `processFrame` (`:495-510`); one JSON record per run in `runs.jsonl`
  (request, status, progress frames, result minus rows, first 12 rows, full symbol list, skip-reason counts).
- `harness/*.s2b.test.ts(x)` + `vitest.s2b.config.mjs` (scratch config, nothing under `src/`): the REAL
  `useScreenerStore` + `ScreenerPanel`/`ScreenerFormulaLeaf` rendered in jsdom, `getSidecarBaseUrl`
  pointed at `:52219`, real `fetch` to the live sidecar (a wrapper records each request body).
  Output: `24-store-panel-replay.json` (+ `24b-...-tail.json` for the results-table text).
- Yahoo circuit: this IP is throttled for the whole drive. `/system/provider-health` read `open:true`
  at 08:22 (throttles_total 90 within 3 min of boot — the warm worker), closed briefly at 08:27
  (used for run 07c), re-opened after one sp500 sweep chunk. This IS the owner's normal condition
  on this machine.
- Seeded evidence: `seat-breaker/http-log.jsonl` has **0** screener calls; no seat transcript touched
  the screener; `screener-probe/` holds 5 warm-run records + a store-state note (no raw findings).
  Everything below is new. `screener-probe/warm-standing-sector-limit10.json` (result_count 10 vs 26
  at limit 200) independently corroborates finding 4.

## 1. Universe picker (`GET /screener/universe`, `ScreenerPanel.tsx:104-111`)

| id | result | score |
|---|---|---|
| sp500 / nifty50 / crypto-top50 / nse-all / bse-all / india-all | 200 in <10 ms; 506 / 50 / 50 / 2,675 / 4,873 / 5,156 symbols | ok |
| custom | 400 "custom universe is resolved per-request…" — the panel never calls it (`:105`) | ok |
| bogus | 422 literal_error — unreachable from the `<select>` | ok |

## 2. Runs (`runs.jsonl`, streaming path)

| # | Screen | Result | Score |
|---|---|---|---|
| 01 | **Panel default on first mount**: sp500, P/E<20, mcap>1e11, sector=Technology (`screener.ts:252-256,267`) | 0 of 506 evaluated, 506 `rate_limited`, **`partial:false`**, `throttled:true`, 20 ms | **broken** — see finding 1 |
| 02 | nifty50 P/E<30 | 26 rows, 49/50 evaluated, 17 `mixed` basis labelled, oldest 2026-07-14 | ok |
| 03 | india-all P/E 5-15, mcap>₹1e11, ROE>0.15 | 37 rows / 4,054 evaluated, 1,102 skipped (1,012 `missing_field:roe`, itemized), 0.8 s warm | ok |
| 04 | zero result (0<P/E<0.5 on nifty50) | 0 rows, 49 evaluated -> "No rows matched" is TRUE here | ok |
| 05 | pasted formula `roe > 0.2 and debt_to_equity < 0.3 and pe_ratio < 25`, nse-all | 89 rows; 926 skipped itemized per missing field | ok |
| 06 | OR group (P/E<12 OR yield>3%) | 12 rows | ok |
| 07 / 07b | custom bare `RELIANCE TCS INFY HDFCBANK COCHINSHIP`, circuit open | 0 of 5 evaluated, all `rate_limited` — store holds all five as `.NS` rows | **broken** — finding 7 |
| 07c | same, circuit closed | 5 of 5 live in 5.95 s | ok |
| 08 | custom `.NS`-suffixed, circuit open | 5 of 5 from store (mixed/live labelled) | ok |
| 09 | sector=Technology + mcap on nse-all | 43 rows (TCS, INFY, HCLTECH…); 236 `missing_field:sector` itemized | ok |
| 11 / 12 | india-all 0<P/E<40, limit 200 vs 1000 | `result_count` **200** vs **1000** for the same screen (≥1,000 matches) | **partial** — finding 4 |
| 13 | limit 1001 | 422 `less_than_equal` (panel always sends 200) | ok |
| 14 | empty criteria, nifty50 | 49 rows (all evaluated names) | ok |
| 15 | cancel after 3 s (sp500) | stream closed at 6.97 s (first sweep chunk blocked the read); no further US rows written to the store afterwards (sqlite count 5 -> 5) — consistent with the engine stopping; the engine's `logger.info("run cancelled")` is below the log level so it is not log-provable | partial |
| 16 | panel default again | circuit re-opened by run 15's chunk -> identical to 01 | broken (= 01) |

## 3. Formula leaf + grammar parity (`10-formula-parity.json`, `22-formula-leaf-states.json`)

39 formulas through BOTH `compileScreenerExpr` (TS, the panel pre-flight) and
`POST /screener/formula/validate` + a real `/screener/run`. **Zero drift** in verdict or caret
position (the one mismatch, `"   "`, is trimmed to empty by the store and never sent). Pre-flight
works: `S3` in the replay — `pe < 20 and roe > 15%` -> banner `Formula: unexpected character '%'
(col 21)`, **0 network calls**; the leaf renders `^ unexpected character '%'`. Unknown fields
(`roce`, `promoter_holding`) list the 29 valid fields. Score **ok**. (Known, not re-filed: boolean
coercion `pe + (roe > 0.1) > 5` accepted = COD-screener-6; `pe / 0 > 1` silently evaluates to 0
matches with no skip.)

## 4. Presets (`ScreenerPresets.tsx`), replay S4/S5

| Drive | Result | Score |
|---|---|---|
| "Founder-aligned (NSE)" from a clean store (S5) | request = preset criteria only; 18 rows | ok |
| same click while the Nested editor holds `(P/E<12 OR yield>4%)` and formula `pe < 12` (S4) | request carries the preset criteria **plus the old `group` and `formula`**; server evaluates the old tree (`screener.ts:359-363`); **3 rows** (NTPC, ONGC, COALINDIA) presented as the preset; builder still shows the old nested tree (`advanced:true`) | **broken** — finding 2 |
| 7 of 8 presets target `sp500` | on this IP every sp500 preset = run 01 (0 evaluated) | broken (via finding 1; default-universe issue = COD-screener-4) |

## 5. Agent-authored screen (`20-*`, `21-*`)

Build-intent phrasing (the `/screener` expansion is classified `read` and loses the tool — SURF-
COMPOSER-CHAT-5): "Set up a screener on the NSE full market: P/E below 20, ROE above 15% and debt to
equity under 0.5, then run it." — llama3.1:8b, AUTO, 99 s. The model called
`write_screener_filters` with `criteria` as a **JSON string** and ROE as `gt {min:15,max:15}`, then
said "I have dispatched the filters for your review in the panel." Replayed through the real
`applyHostAction` (`21-agent-screen-replay.json`): string criteria -> `null` (nothing applied, store
still the sp500 default); the same args with a real array -> "Wrote 2 screener criteria — review and
Run" (the ROE leaf silently dropped) and a real run returns 200 rows with no ROE filter. Score
**broken** — findings 5, 6. (Ack impossible anyway: `tool_call_id ""` = SURF-COMPOSER-CHAT-8.)

## 6. Error / state channels (replay S1, S6, S7, S9)

| State | Read-back | Score |
|---|---|---|
| zero-evaluated result | panel text: "0 rows (0 evaluated, 506 skipped, 20 ms) … No rows matched the criteria — No stocks in this universe passed every filter. Loosen a threshold or reset to the defaults." + throttle line "showing cached/snapshot values" (none shown); no PARTIAL badge | broken (finding 1) |
| stream `{"event":"error"}` frame (shape from `routers/screener.py:127-139`) | store error `Stream ended without a result frame`; table: "Could not load results … loosen a criterion"; the server's message is discarded | broken (finding 3) |
| custom + empty symbols | Run button `disabled:true` + "Enter at least one ticker" | ok |
| custom lower-case `reliance, tcs infy` | uppercased, 3 of 3 | ok |
| save / load / delete screen | load restores universe+formula; delete empties the strip; screens are session-only (never in the workspace blob — COD-workspace-layout-6, not re-filed) | partial |
| existing unit tests `src/modules/screener` | 4 files / 41 tests pass (`23-existing-screener-tests.log`) | ok |

NEEDS-GUI: row-click drill (`openCompanyOverview` + `loadSymbolIntoChart` need a mounted dockview),
CSV download (Blob `<a download>` — WLD-T-2), column-resize/overflow at narrow width.
