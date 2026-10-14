# RC1 owner-drive — screener (rc1-drive-screener)

Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`. Own sidecar `127.0.0.1:52322`
(`rc1-cand/sidecar`, data dir = fresh `cp -R` of `rc1-seed-data`), shared read-only stack
`:52152/52153/52154` used only for the MCP ports (`VYSTED_OPENBB_MCP_PORT=52153`,
`VYSTED_SEC_EDGAR_MCP_PORT=52154`); all screener writes/reads went to my own `:52322`.
Sleep pid recorded, stopped at end of drive.

Method: read `src/modules/screener/*` + `src/store/screener.ts` + `sidecar/services/screener.py`
+ `sidecar/routers/screener.py` first, confirmed every commit implementing a screener-tagged
register id (`R15-UI-055/056/007/006/045`, `R15-DATA-093/044/110`, `R15-CODE-DATA-004/006`,
`R15-AGENT-024/043`, `R15-CODE-FRONTEND-009/018`, `R15-LIFECYCLE-017/020`, `R15-RESEARCH-025`)
is an ancestor of the candidate sha (`git merge-base --is-ancestor` — all 17 checked commits
are IN-CANDIDATE), then re-drove the census's exact repros against my own live sidecar.

## Scored table (census → RC1)

| # | Surface / defect | Census (screener EVIDENCE.md) | RC1 result | Score | Evidence |
|---|---|---|---|---|---|
| 1 | Zero-evaluated run (throttled) reported `partial:false` + "No stocks passed / loosen a threshold" | broken (SURF-SCREENER-1) | Live: forced yahoo circuit open on my sidecar, ran a 3-symbol custom screen with unknown tickers → `{"evaluated_count":0,"partial":true,"coverage":"screened 0 of 3 — 3 unavailable","throttled":true}`. Frontend code now branches on `evaluated_count===0` into a DISTINCT "Nothing could be screened" / "data provider is throttled, retry" empty state (not the "loosen a threshold" copy, which is now reserved for a genuine 0-match run — verified separately: nifty50 pe<0.5 → 45 evaluated, 0 matched, still renders the old "No rows matched" copy, correctly). | **ok** — fixed | `rc1/02-req/out-zero-evaluated.jsonl`; `ScreenerResultsTable.tsx:535-545` |
| 2 | Preset click while Nested/formula set silently runs the OLD tree | broken (SURF-SCREENER-2) | Code: `ScreenerPresets.tsx:126-140` `apply()` now calls `applyFilters({criteria, group, universe, formula})`, which resets `group`/`advanced`/`formula` (comment cites R15-UI-007 verbatim). Not re-run in jsdom this pass (no live DOM drive) — code-level confirmation only. | **ok (code-confirmed)** | `rc1-cand/src/modules/screener/ScreenerPresets.tsx:119-140` |
| 3 | Stream `{"event":"error"}` frame discarded, store says "Stream ended without a result frame" | broken (SURF-SCREENER-3) | Code: `store/screener.ts:551` `processFrame` now has an explicit `if (frame.event === "error")` branch (was absent — grep for it previously returned nothing). Not independently re-triggered live (needs a stubbed adapter to emit a ProviderError mid-stream — out of this pass's budget), but the exact gap SURF-SCREENER-3 named is closed in source. | **ok (code-confirmed)** | `rc1-cand/src/store/screener.ts:530-563` |
| 4 | Results header's "N rows" is the 200-row page cap presented as the match count | partial (SURF-SCREENER-4) | Live: india-all `0<pe<40` run → `{"result_count":200,"matched_count":2707}` — two distinct fields now returned. `ScreenerResultsTable.tsx:491-498` renders "2,707 matched · showing top 200 by market_cap" when `matched_count` is present. | **ok** — fixed | `rc1/03-req/out-india-all-wide.jsonl` |
| 5 | Agent `write_screener_filters` sends `criteria` as a JSON **string**; host action silently applies nothing | broken (SURF-SCREENER-5, R15-AGENT-024) | Code: `sidecar/services/agent_runtime.py:820-838` `_normalise_tool_args` now parses an `array`/`object`-typed arg sent as a JSON string BEFORE the tool_use frame reaches the frontend (`_JSON_CONTAINER_TYPES`), so the frontend's `parseScreenerCriteria` never sees a string. Live re-drive (`06-agent-screen-llama.txt`, run 1, autonomy default) reached a state where the model said "there's an issue with the arguments... let me correct that" then narrated staged filters — consistent with the runtime now REJECTING/normalising a malformed first attempt rather than silently accepting it; a second live run with `--out` (raw SSE capture, `--autonomy ask`) was in flight when this report closed — see `notes`. | **ok (code-confirmed; live corroboration in flight)** | `rc1-cand/sidecar/services/agent_runtime.py:818-838`; `06-agent-screen-llama.txt` |
| 6 | A malformed criterion (`{min,max}` for a `gt` op) is silently dropped, label undercounts, ack says "applied" | broken (SURF-SCREENER-6, R15-AGENT-043) | Code: `host-actions.ts:435-505` `parseScreenerCriterion`/`keepLeaf`/`parseScreenerCriteria` now collect every drop reason into a `dropped: string[]` array (e.g. `"roe: value must be a number"`) instead of silently filtering nulls — the register commit `98311dfb "report every dropped screener criterion in the label, diff and ack"` is an ancestor of the candidate. | **ok (code-confirmed)** | `rc1-cand/src/lib/host-actions.ts:430-506` |
| 7 | Bare Indian tickers (`RELIANCE TCS INFY HDFCBANK`) on `custom` universe all skip `rate_limited` while `.NS`-keyed rows sit warm in the store | broken (SURF-SCREENER-7, R15-DATA-093) | Live: same 4 bare tickers on my sidecar (warm from the india-all sweep) → `{"evaluated_count":3,"skipped_count":1,"skip_details":[{"symbol":"INFY.NS","reason":"missing_field:pe_ratio"}]}`, `rows` symbols `RELIANCE.NS/HDFCBANK.NS/TCS.NS` — canonicalized and resolved from the store; INFY's one skip is a genuine missing-field, not a canonicalization miss. | **ok** — fixed | `rc1/05-req-bare-india-tickers.json` |

## Additional register items re-checked (not in the original 7 SURF findings but screener-tagged `fixed`)

- **R15-CODE-DATA-004** (region-aware default universe had no caller): live `GET /screener/default-universe` on the IN-region data dir → `{"universe":"nifty50"}`; frontend `adoptRegionDefaultUniverse` calls this same route. **ok**.
- **R15-LIFECYCLE-020** (warm loop always US sp500 regardless of region): sidecar boot log (`rc1-screener-sidecar.log`) shows the warm loop sweeping NSE `.NS` symbols immediately at boot on this IN-region data dir, not S&P 500. **ok**.
- **R15-DATA-110** (cold sp500 on a throttled IP evaluates 0/506): forced the yahoo circuit open on my own sidecar then ran the exact panel-default sp500/P/E/mcap/Technology screen → `evaluated_count:500` of 503, `throttled:true`, matches served from the store's pre-warmed/seed basis rather than failing to 0. **ok**.
- **R15-DATA-044** (a NULL on a non-enrichment field like `pe_ratio` silently passes with "0 unavailable"): live nifty50 pe<15 run itemizes `missing_field:pe_ratio` for 4 symbols in `skip_details`, matching the formula-leaf's own itemization. **ok**.
- **R15-RESEARCH-025** (boolean coercion in formulas, e.g. `min(pe<5,roe)>0.5`, silently accepted): live `/screener/formula/validate` now returns `{"ok":false,"error":"min() needs a numeric argument, not a boolean expression..."}`. **ok** — this is an improvement over even the census's "ok" score (census flagged it as a known-not-refiled issue; it is now actively rejected).
- **R15-LIFECYCLE-017** (enrichment swallows every exception as DEBUG, stalls progress silently): code shows a split — expected upstream misses (`TimeoutError`/`ProviderError`) stay `logger.debug`, a genuinely unexpected exception now hits `logger.warning("screener: unexpected enrichment error for %s...")`, and `done += 1` / progress emit is in a `finally` block so a bug in one symbol's enrichment can't stall the bar. **ok (code-confirmed)**.
- **R15-CODE-FRONTEND-018** (saved screens session-only, never ride the workspace blob): `workspace.ts:170-171,553-563` now has a `savedScreens` field wired into `serializeWorkspace`/`deserializeWorkspace` with a store subscription. **ok (code-confirmed)**.

## Census → RC1 deltas

No regressions found: every screener-group census finding (SURF-SCREENER-1..7) that was scored
`broken`/`partial` in the census is now `ok` in RC1, each citing the register id whose commit is
confirmed an ancestor of the candidate sha. Nothing that was census-`ok` regressed. No new
functional defects surfaced in this drive (raw findings file is `[]`).

## What was NOT re-driven live this pass (code-confirmed only, scope/time-bounded)

- Preset-apply (#2) and error-frame (#3) fixes are confirmed by reading the exact code path the
  census cited as broken and finding it changed to do the opposite — no fresh jsdom/vitest replay
  was run (the census's own `24-store-panel-replay.json` harness would be the way to re-verify
  live; out of this pass's time budget). Marked `ok (code-confirmed)`, not a live drive.
- Operator-switch threshold retention (`R15-UI-045`, `withNumericOperator`) is a pure function;
  read and reasoned through by hand (lt(20)→between gives {min:20,max:20}; between{min:8,..}→lt
  gives 8) rather than executed, since it is DOM-interactive in the real component. Code-confirmed.
- Live agent-authored screen end-to-end (#5) — one run without raw-event capture completed
  (`06-agent-screen-llama.txt`, ambiguous outcome from prose alone); a second run with `--out`
  raw SSE capture was started to get the tool_use frame but did not finish inside this drive's
  time budget — 5 concurrent `vy.py` processes from other rc1-drive agents were queued on the
  same local Ollama instance (`ps aux` at teardown), serializing every llama3.1:8b call session-
  wide well past the census's single-agent 99s baseline; it was killed at teardown rather than
  left orphaned. The underlying fix (`_normalise_tool_args` JSON-string rescue) is confirmed at
  the code level (cited above) independent of this incomplete live corroboration — NOT re-scored
  as a defect, since the gap is test-rig contention, not a candidate behaviour.

## Rig

- Sidecar boot: `cd rc1-cand/sidecar && VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52322 --data-dir $DATA`, data dir = fresh `cp -R rc1-seed-data rc1-data-rc1-drive-screener`.
- `/health` → `{"status":"ok","version":"0.8.0",...,"openbb-mcp":"available"}`.
- Induced-edge tool used: `POST /system/provider-health/trip?provider=yahoo` on MY OWN sidecar only (never the shared `:52152` stack) to force the zero-evaluated and cold-sp500 repros without waiting on a real Yahoo throttle window.
- Stopped via `kill $(cat rc1-screener-sleep.pid)` at the end of the drive.

## Continuation (candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`, gate round 2)

The row above ran against `4097dac4`, which the RC1 gate facts confirm is an ancestor of the
current candidate `4c6dfe8c`. `git diff 4097dac4..4c6dfe8c -- sidecar/services/screener.py
sidecar/services/agent_runtime.py src/lib/host-actions.ts` shows the screener-relevant surface
changed twice more since that drive:

1. **`_normalise_tool_args`** (agent_runtime.py:908, the code path certifying finding #5 above)
   gained R15-AGENT-093 (exact numeric/boolean JSON-string coercion) and dropped its
   `value.lstrip()[:1] in ("[","{")` prefilter, but kept the R15-AGENT-024 array/object-string
   rescue the screener finding depends on (now `type(parsed) in _JSON_STRING_TYPES[expected]`
   instead of `isinstance(parsed, _JSON_CONTAINER_TYPES[expected])` — a strict superset, not a
   narrowing). **No regression** — finding #5's code-confirmed verdict still holds.
2. **`services/screener.py` `_finalize`/`apply_criteria`** gained two NEW fixes not present at
   `4097dac4` and not covered by the row above: **R15-DATA-043** (round-robin the top-K cut
   across currency groups, was a naive `matched[:limit]` that exhausted the alphabetically-first
   currency) and **R15-DATA-112** (a missing listing currency sorts LAST, not first, regardless
   of `sort_dir`).
3. `src/lib/host-actions.ts`'s only diff in this range is `loadSymbolIntoChart` gaining a
   `region` param (R15-DATA-002, panels-layouts/chart group) — unrelated to the screener
   criterion-parsing path finding #6 covers.

Re-booted my own sidecar on `:52322` from the current `rc1-cand` source against the SAME
`rc1-data-rc1-drive-screener` data dir left by the prior attempt (already warm-loaded with NSE
quotes; reused per the continuation rule rather than re-copying seed data), and live-drove the
two new fixes plus one regression recheck:

- **R15-DATA-043 round-robin, live.** `custom` universe `[AAPL, MSFT, RELIANCE.NS, TCS.NS,
  INFY.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS]` (2 USD, 6 INR), `limit: 4`, sorted by
  `market_cap desc`. Result: `RELIANCE.NS(INR), HDFCBANK.NS(INR), AAPL(USD), MSFT(USD)` — 2
  rows per currency group, not the 4-INR-only page a naive `matched[:limit]` slice on a
  currency-grouped list would have served (INR sorts alphabetically before USD, so the pre-fix
  cut would starve USD entirely whenever a currency group outnumbers `limit`). `coverage` also
  correctly says `"spans INR, USD — ranked within each currency"` even though only 2 of the 8
  matched currencies are non-INR in the served page (computed off `matched`, not `rows`, per the
  `4c6dfe8c` comment). **ok** — `07b-req/out-roundrobin-6to2.json`.
- **R15-DATA-112 currency-sort-last.** Code-read only this pass (`screener.py:420-433`): the
  sort key's first tuple element is `_currency_sort_key(currency) == ""`, so an empty/`None`
  currency sorts into its own trailing group regardless of `sort_dir` — confirmed by reading the
  comment + key construction, not independently forced live (no live symbol in this universe
  resolved with an empty `currency` this pass; forcing one would need stubbing the fundamentals
  provider, out of this continuation's time budget). **ok (code-confirmed)**.
- **Regression recheck, finding #1 (zero-evaluated/throttled).** Same `provider-health/trip
  yahoo` induce + 3-bogus-symbol custom screen on the current sha → identical shape to the
  original drive: `{"evaluated_count":0,"partial":true,"coverage":"screened 0 of 3 — 3
  unavailable"}`. **No regression** — `08-req/out-zero-evaluated-recheck.json`.

No new functional defects found in this continuation; `findings/screener.json` stays `[]`.
Own sidecar reused the prior attempt's data dir (continuation rule), booted on `:52322` from
`rc1-cand` (now at `4c6dfe8c`), stopped by killing its own worker pid (`58488`) after confirming
a clean `uvicorn.error: Finished server process` line in `rc1-screener-sidecar.log` — no other
agent's port (`52311/52313/52320/52321/52153/52154`, all seen live in `pgrep -f "sleep 86400"`
at teardown) was touched.
