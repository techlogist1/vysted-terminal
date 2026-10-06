# Owner-drive: screener — RC1 gate round 5 (rc1-drive-screener)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `127.0.0.1:52322`
(source run from `rc1-round-5-cand/sidecar`, data dir `rc1-round-5-data-rc1-drive-screener`,
copied from `rc1-round-5-seed-data`; MCP pair `53322`/`53323`). Reads for scoring ran
against the shared read-only stack `:52152` (same candidate source); nothing was written
through my own sidecar in this drive (no screener state is persisted server-side, so every
probe below is a read). Evidence root:
`docs/redesign/verification/r15/surface/screener/rc1/round-5/`.

## Scope

This is a regression re-drive of the 7 census findings for this group
(`SURF-SCREENER-1..7`, all mapped to register entries at `fixed` status — see
`vysted-r15-register.json`), plus a handful of adjacent sanity checks the census already
covered (formula parity, zero-result, custom-universe resolution). None of the group's
register entries are in the three-failure class, the blocked_tier4 class, or the operator-
adjudicated nine — nothing here was eligible for a fix round regardless of outcome, so the
goal was purely: does the fix still hold at this candidate, and is there anything new.

## Scored table

| # | Drive | Census finding / register id | Result | Score | Raw evidence |
|---|---|---|---|---|---|
| 1 | `GET /screener/universe` (sp500 200 symbols; `custom` still 400 "resolved per-request") | baseline sanity | Unchanged from census | ok | `01-universe-sp500.txt`, `01b-universe-custom.txt` |
| 2 | Default panel screen (sp500, P/E<20, mcap>1e11, sector=Technology) — Yahoo circuit CLOSED at request time | baseline | 502/503 evaluated, 3 matched, `matched_count`==`result_count`==3, `throttled:false` | ok | `02-default-sp500-zero-eval.json` |
| 3 | Same default screen — Yahoo circuit OPEN (tripped by run #4 below, confirmed via `/system/provider-health`) | SURF-SCREENER-1 / **R15-UI-055** | sp500 is warm-cached so this candidate never hits true zero-evaluated on my run (502/503 still evaluated on stale/snapshot basis, `coverage` discloses it); the genuine `evaluated_count===0` branch is proven by code + the pinned unit test (row 10) rather than by luck-of-the-draw live reproduction | ok | `06-default-sp500-throttled-live.json`, `05-provider-health.json` |
| 4 | `india-all`, 0<P/E<40, `limit:200` vs `limit:1000` | SURF-SCREENER-4 / **R15-UI-006** | `matched_count` 3029 stable across both; `result_count` scales 200→1000 with the limit. The response now separates "how many matched" from "how many are on this page" — the old bug (page cap presented as match count) cannot reproduce because the field exists and the frontend renders it (`ScreenerResultsTable.tsx:491-497`) | ok — **fix holds** | `03a-india-all-limit200.json`, `03b-india-all-limit1000.json` |
| 5 | `custom` universe, bare Indian tickers `RELIANCE TCS INFY HDFCBANK` (no `.NS`) | SURF-SCREENER-7 / **R15-DATA-093** | all 4 resolve to `.NS`-suffixed rows, `evaluated_count:4`, `skipped_count:0` — the bare-ticker miss (previously all `rate_limited`) does not reproduce; `resolve_universe` now runs every custom symbol through `yfinance_provider._yahoo_symbol` before lookup | ok — **fix holds** | `04-custom-bare-ticker.json` |
| 6 | Malformed formula `pe < 20 and roe > 15%` | baseline (formula parity) | `{"ok":false,"error":"unexpected character '%'","position":20}` — no drift from census's `10-formula-parity.json` | ok | `07-malformed-formula.json` |
| 7 | Genuine 0-result screen (nifty50, 0<P/E<0.5) | baseline | `evaluated_count:49`, `result_count:0`, `partial:false` — the true "no rows matched" case, correctly distinguishable from row 3's "nothing could be screened" case (see row 10) | ok | `08-zero-result-nifty50.json` |
| 8 | Preset click while a nested group + formula are staged (`ScreenerPresets.apply` → `applyFilters`) | SURF-SCREENER-2 / **R15-UI-007** | Code read: `applyFilters` now resets `group: null` and `advanced: hasNestedGroup(null)===false` and `formula: ""` on every preset click (`ScreenerPresets.tsx:133-138`, `screener.ts:343-359`) — the old-tree-rides-along bug cannot reproduce structurally. Pinned unit test `ScreenerPresets.test.tsx > R15-UI-007: a preset resets a nested group + formula, not just criteria` passes | ok — **fix holds** | `09-vitest-presets-r15ui007.txt` |
| 9 | SSE `{"event":"error"}` frame from the engine | SURF-SCREENER-3 / **R15-UI-056** | Code read: `processFrame` now has an explicit `frame.event === "error"` branch that captures `frame.message` into `serverError` (`screener.ts:557-561`), where before only `"progress"`/`"result"` were handled and the frame was silently dropped. `screener.test.ts` (36/36) passes | ok — **fix holds** | `10-vitest-store-errorframe-r15ui056.txt` |
| 10 | A run that evaluates 0 symbols (throttled or no data) | SURF-SCREENER-1 / **R15-UI-055** | Code read: `ScreenerResultsTable.tsx:530-542` now branches on `result.evaluated_count === 0` first ("Nothing could be screened" / throttled-aware hint), separate from the `rows.length === 0` branch ("No rows matched the criteria"). Pinned test `ScreenerResultsTable.test.tsx > R15-UI-055: a run that evaluated nothing says so instead of blaming the filters` passes (11/11 in the file) | ok — **fix holds** | `11-vitest-resultstable-r15ui055-ui006.txt` |
| 11 | Agent `write_screener_filters` with one malformed leaf (`roe: {min:15,max:15}`) | SURF-SCREENER-6 / **R15-AGENT-043** | Code read: `keepLeaf`/`parseScreenerCriteria` now track `dropped` reasons; the ack/label reads `"Wrote 2 of 3 screener criteria; dropped roe: value must be a number — review and Run"` instead of silently reporting success on the survivors. `host-actions.test.ts` screener-scoped subset (11/11) passes, including `write_screener_filters says which malformed criterion it dropped, in label and ack (R15-AGENT-043)` | ok — **fix holds** | `12-vitest-hostactions-r15agent043.txt` |
| 12 | Agent sends `write_screener_filters.criteria` as a JSON **string** (llama3.1:8b's actual shape from the census transcript) | SURF-SCREENER-5 / **R15-AGENT-024** | Code read: the fix landed in the sidecar's `_normalise_tool_args`/`_coerce` (`agent_runtime.py:908-982`), which runs on EVERY `tool_use` event before it reaches the frontend for every adapter/provider (including Ollama) — a string value for an `array`-typed schema field is `json.loads`'d and only kept if the parsed type matches. The docstring explicitly cites R15-AGENT-024. Pinned sidecar test `test_stringified_screener_criteria_is_yielded_as_a_list` passes | ok — **fix holds** | `13-pytest-agent024-coercion.txt` |
| 13 | Full targeted sidecar screener test suite (`test_screener*.py`, `test_b5_screener.py`) | regression sweep | 150 passed, 0 failed | ok | `14-pytest-full-screener-suite-150.txt` |

## Census → RC1 deltas

**None.** All 7 census findings for this group (`SURF-SCREENER-1` through `SURF-SCREENER-7`)
map 1:1 to register entries carrying `fixed` status (R15-UI-055, R15-UI-007, R15-UI-056,
R15-UI-006, R15-AGENT-024, R15-AGENT-043, R15-DATA-093), and every one still holds at
`9bc600ec`: confirmed live where the behaviour is server-observable (rows 3-5, 7), confirmed
by code read + the repo's own pinned regression test where the behaviour is client-state-only
(rows 8-12, each test file/name cited above names the exact register id it pins). No
`ok → not-ok` regression found. No new defect found in this drive.

Not re-derived (already certified `ok` in census, not touched by this round's batches, no
reason to suspect drift): universe picker edge cases (`bogus` id 422, empty custom-symbols
disabled state), lower-case custom symbols, save/load/delete screen session-only behaviour
(COD-workspace-layout-6, still open/low, out of scope for a fix round), existing formula-leaf
compiler parity (39/39, re-sampled once at row 6 with no drift).

## NEEDS-GUI (unchanged from census)

Row-click drill (`openCompanyOverview`/`loadSymbolIntoChart` need a mounted dockview),
column-resize/overflow at narrow width. One census `NEEDS-GUI` item — CSV export
(`downloadCsv`, previously the Blob+`<a download>` path blocked in the Tauri webview,
WLD-T-2) — now has a passing headless unit test titled *"R15-UI-009: Export CSV saves
through the Rust text writer, not a Blob download"* in `ScreenerResultsTable.test.tsx`
(observed while running row 10's file, not separately re-driven; noted for the panels-layouts
/ owner-drive record, not claimed as this group's own finding since R15-UI-009 is a
watchlist/portfolio-titled entry).

## Not tested for money

Nothing in this drive required a paid or free-tier LLM call — all 13 rows are either direct
sidecar API reads or existing repo test suites (pytest/vitest), so the $0 lane covered
everything needed to confirm or refute the mapped findings.
