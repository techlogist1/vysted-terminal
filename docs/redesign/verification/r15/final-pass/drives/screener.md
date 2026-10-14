# Final-pass owner-drive — screener (final-drive-screener)

Head `d38b5d1a`. Reads (universe picker, formula validate) on the shared `:52800`; every run, the
jsdom harness and the agent turn on my own sidecar `:52842` (source run from `final-cand/sidecar`,
data dir = fresh copy of `final-seed-data`, MCP pair `:52801/:52802`, sleep pid 76687, stopped at the
end). Drivers: the census `surface/screener/harness/scr.py` (the exact body `src/store/screener.ts`
builds), a scratch jsdom vitest harness (config root = `final-cand`, jsdom url
`http://localhost:5173`, real `useScreenerStore` + `ScreenerPanel` + `host-actions` against
`:52842`, never committed), and `vy.py` (scratch copy admitting :52842, same as the composer lane)
for one llama3.1:8b turn under the Ollama lock. The Yahoo circuit was open for most of the drive
(`/system/provider-health` → `yahoo.open:true`); that is the owner's normal state on this IP.
`POST /system/provider-health/trip` is 404 at this head (R15-LIFECYCLE-033 made it rig-only), so the
zero-evaluated state was driven by the natural throttle instead.

Evidence: `docs/redesign/verification/r15/surface/screener/final/` — `01-universe.txt`,
`runs.jsonl` (one record per run, labels below), `09-formula-validate.txt`, `30-jsdom-replay.json`
(S1..S11), `40-agent-screen-llama.{stdout.txt,jsonl}`, `41-agent-tooluse-accept-replay.json`,
`50-attachments.md`.

## Scored table

| # | Control / state | Final result | Score | Evidence |
|---|---|---|---|---|
| 1 | Universe picker, 6 ids | 200: sp500 503, nifty50 50, crypto 50, nse-all 3,506, bse-all 5,042, india-all 5,891; custom 400 (per-request), bogus 422 | ok | 01-universe.txt |
| 2 | Region default universe (R15-CODE-DATA-004) | `GET /screener/default-universe` → `nifty50` on the IN profile | ok | 01-universe.txt |
| 3 | Panel default on first mount (sp500 P/E<20, mcap>1e11, Technology) | 502 of 503 evaluated, 4 matched (MU, WDC, UBER, ACN, USD); jsdom panel renders the rows, "Market cap (USD)", basis + skip lines. sp500 resolved US under the IN session (R15-LEAD-044) | ok | runs 01; replay S1 |
| 4 | nifty50 P/E<30 (warm) | 27 of 49 | ok | runs 02 |
| 5 | Genuine zero match (0<P/E<0.5) | 49 evaluated, 0 rows; panel "No rows matched the criteria … Loosen a threshold" (true here) | ok | runs 04; S8b |
| 6 | Zero evaluated (circuit open, 3 unknown tickers) (R15-UI-055) | `evaluated 0, partial true, throttled true`; panel "Nothing could be screened — The data provider is throttled; retry in a moment." + PARTIAL badge | ok | runs 08; S8 |
| 7 | Partially throttled zero match (bse-all, 2,579 rate-limited) | panel takes the "No stocks in this universe passed every filter … Reset filters" branch | broken (known: open R15-LEAD-076, attached) | runs 23; 50-attachments.md |
| 8 | india-all P/E 5–15, mcap, ROE (cold-ish, 31 s) | 34 rows / 5,217 evaluated, 674 skipped itemized (288 missing mcap, 204 rate-limited, 157 not_found) | ok | runs 03 |
| 9 | Pasted formula on nse-all | 100 rows, 1,421 skipped itemized per field; 13 rows labelled stale/snapshot with oldest date | ok | runs 05 |
| 10 | OR group | 6 rows (each passes P/E<12 or yield>3%) | ok | runs 06 |
| 11 | Matched vs page (R15-UI-006) + Show more | india-all 0<P/E<40: `matched 3,064, result_count 200`; Show more → request `limit 400`, 400 rows | ok | runs 11; S2a/S2b |
| 12 | Tenth row + header sort | 50 body rows, row 10 = HINDUNILVR; P/E header click → `sort_by pe_ratio desc` server re-run, DIVISLAB 84.0 first | ok | S10 |
| 13 | Server sort asc | nifty50 P/E asc limit 10: ONGC 6.43, COALINDIA 8.32, NTPC 9.63 | ok | runs 19 |
| 14 | Bare Indian tickers on custom (R15-DATA-093) | `RELIANCE TCS INFY HDFCBANK COCHINSHIP` → 5 of 5 as `.NS` with the circuit open; lower-case `reliance, tcs infy` → 3 of 3 | ok | runs 07; S7 |
| 15 | Custom with no tickers | Run button disabled + "Enter at least one ticker"; API 422 "requires a non-empty custom_symbols list" | ok | S7; runs 17 |
| 16 | Currency round-robin (R15-DATA-043) | 2 USD + 6 INR, limit 4 → RELIANCE, HDFCBANK, AAPL, MSFT; coverage "spans INR, USD — ranked within each currency" | ok | runs 18 |
| 17 | limit 1001 / empty criteria | 422 `le 1000`; empty criteria → all 50 | ok | runs 13, 14 |
| 18 | Formula pre-flight, malformed `%` | banner "Formula: unexpected character '%' (col 21)", leaf caret, **0 network calls** | ok | S3 |
| 19 | Formula validate grammar | unknown field lists fields; `min(pe<5,roe)` and `pe + (roe>0.1)` rejected (R15-RESEARCH-025 holds); `roe > (pe_ratio < 15)` still ok:true | partial (known: open R15-LEAD-069, attached) | 09-formula-validate.txt |
| 20 | Division by zero in a formula | `pe_ratio / 0 > 1` and `< 1` both 0 rows, no skip; documented "did not match" (`screener_formula.py:632`), census-known, not refiled | ok (by design) | runs 20, 21 |
| 21 | Preset after nested group + formula (R15-UI-007) | click "High insider holding (Yahoo)": request carries only the preset's 3 criteria on nifty50, `group null, advanced false, formula ""`; 17 rows | ok (now live-driven; rc1 was code-only) | S4 |
| 22 | Stream error frame (R15-UI-056) | store error and panel banner = server text "missing universe snapshot 'nifty50.json'" | ok (now live-driven) | S6 |
| 23 | Save / load / delete + workspace blob (R15-CODE-FRONTEND-018) | `savedScreens` slice reads into the blob and restores; load restores universe+formula; delete empties | ok | S9 |
| 24 | Agent recipe with criteria as a JSON string (census shape) | describe "no well-formed criteria — can't apply", apply `failed` (honest, not a silent no-op) | ok | S11 |
| 25 | Agent recipe with a malformed ROE leaf (R15-AGENT-043) | "Wrote 2 of 3 screener criteria; dropped roe: value must be a number" | ok | S11 |
| 26 | Flat group + stale flat criteria (R15-AGENT-096) | run sends the group's leaves as `criteria` (not the stale `pe<99`), 6 rows | ok | S11 |
| 27 | Live agent-authored screen, llama3.1:8b, ask | runtime normalised criteria to arrays (R15-AGENT-024 holds), `run:true`, staged; replayed through accept → roe drop disclosed, run fires, 536 matched / 200 shown | ok | 40-…stdout.txt; 41-…json |
| 28 | Same turn's chat prose | after only staging, the model narrates "15 stocks matched" and market caps (RELIANCE ₹6.31T vs ₹15.8T served) | known limitation (R4, R15-LEAD-030 / DECISIONS 4.9) | 40-…stdout.txt |
| 29 | Cancel mid-run | not reachable: with the circuit open every run is served from the store in ≤0.5 s (bse-all, 207 frames, finished before the 3 s cancel) | NOT TESTED (no slow run available) | runs 15-cancel-bse-cold |
| 30 | Row-click drill, Export CSV feedback, narrow width | needs a mounted dockview / native save | NEEDS-GUI | NEEDS_GUI.md |

## Census → final deltas

- Census broken → final ok: SURF-SCREENER-1 (zero-evaluated), -2 (preset over nested, now live in
  jsdom), -3 (error frame, now live in jsdom), -4 (matched vs page, plus Show more), -5 (agent JSON
  string criteria: normalised at runtime and an honest failed apply on the frontend), -6 (dropped
  leaf disclosed), -7 (bare Indian tickers).
- rc1 code-confirmed items now driven live: #2, #3, R15-CODE-FRONTEND-018 (blob round-trip), the
  live agent tool_use (rc1's run never finished).
- Fixes landed after rc1 and driven here: R15-AGENT-096 (flat group), R15-LEAD-044 (sp500 under the
  IN session resolves US), R15-UI-069 (memoized ledger lines render). R15-LIFECYCLE-020 (warm 429s
  no longer open the user circuit) was not isolable: the user-run india-all sweep itself hit 204
  rate limits, which opens the circuit legitimately.
- Census ok → final not ok: none. No regression of a fixed entry.
- Still open and reproduced (attached, not new): R15-LEAD-069, R15-LEAD-076.
- No new defect admitted. Considered and not filed: "0 matched · showing top 0 by market cap"
  header copy on an empty result, and the generic "Could not load results" table text under a
  formula pre-flight error whose banner is correct (both polish; neither would change a decision).
  Price levels (e.g. MU $1,074.89 / $1.21T) are snapshot data with no outside source checked here;
  not judged by this lane.
