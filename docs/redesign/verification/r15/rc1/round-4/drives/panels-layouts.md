# rc1-drive-panels-layouts — gate round 4 re-drive

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `127.0.0.1:52323`
(sleep pid 71382, worker pid 71383), source `<worktree>/sidecar`, data dir a fresh
`cp -R` of `rc1-round-4-seed-data`, pointed at the shared read-only MCP pair
`:52153`/`:52154`. Reads went to the shared, read-only `:52152` stack; writes
(workspace save) and compute-only quant POSTs went to my own `:52323`. No previous
round-4 attempt existed for this role -- started fresh from round-3's drive and the
census `EVIDENCE.md`.

Round-3 baseline: 14 register-fixed/open rows re-verified live, all held (one
open-low, R15-UI-077, confirmed still open as documented, no fix round warranted).
Since round 3, batch-27 (per the lead note) fixed two items touching this group:
R15-DATA-117 (ADR price-to-book mixed-currency) and R15-LEAD-040 (resolver pool).
This round re-verified those two plus a regression spot-check of the highest-severity
round-3-held rows, re-confirmed R15-UI-077, and filled round-3's budget-limited
`NOT TESTED` gaps where this round's budget allowed.

## Scored table

| # | Row | Score | Evidence |
|---|---|---|---|
| 1 | R15-DATA-117: TSM fundamentals (mixed-currency P/B) | ok (fix holds) | `01-fundamentals-tsm-pb-fix.json`: `price_to_book`/`book_value`/`price_to_sales` all `status:"withheld"`, reason names both USD and TWD; P/E stays `ok` |
| 2 | R15-DATA-117: HDB fundamentals | ok (fix holds) | `02-fundamentals-hdb-pb-fix.json`: `price_to_book`/`book_value` withheld (INR statements) |
| 3 | R15-DATA-117: AAPL control (US-domestic, unaffected) | ok | `03-fundamentals-aapl-control.json`: `price_to_book: 46.34`, `status: "ok"` -- fix is scoped to mixed-basis names only |
| 4 | R15-UI-077: duplicate yield-curve pillar | broken, as documented (adjudicated, no fix round) | `04-yieldcurve-dup-pillar.txt`: still `500 Internal Server Error`, no `access-control-allow-origin` header |
| 5 | R15-LEAD-040: resolver pool fix | ok (fix holds, code-read) | `05-lead040-resolver-pool-grep.txt`: dedicated `_RESOLVE_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="resolver")` (`symbol_resolver.py:160`), `resolve_async`/`autocomplete_async` route through it via `run_in_executor`, separate from the shared default `to_thread` pool |
| 6 | panel-backtest: strategies list | ok (not tested r3) | `07-backtest-strategies.json`: 200, populated |
| 7 | R15-DATA-064: chart 30m AAPL | ok (fix holds) | `08-chart-30m-aapl-regression.json`: 200, 286 real bars (was 0 at census) |
| 8 | R15-DATA-011: binomial gamma, 200 steps | ok (fix holds) | `09-binomial-gamma-regression.json`: gamma 0.018842, theta -6.430 (correct sign for a long call) |
| 9 | R15-DATA-011: binomial gamma, 201 steps (odd) | ok (fix holds) | `10-binomial-gamma-oddsteps.json`: gamma 0.018797 -- no parity flip vs 200-step (was 0 at census) |
| 10 | R15-DATA-038: SEC sections, AAPL 10-K | ok (fix holds) | `11-sec-sections-aapl-regression.json`: 2 real sections (business, risk_factors), 10,000 chars each |
| 11 | R15-DATA-038: SEC insider, AAPL | ok (fix holds, as documented) | `11b-sec-insider-aapl-regression.json`: 5 rows returned; blank reporter fields are the documented filing-level fallback (`sec_filings_provider.py:437-438`), not a parser miss |
| 12 | R15-DATA-028/029/067: earnings upcoming, IN region | ok (fix holds) | `12-earnings-upcoming-in-regression.json`: 60 events, `.NS` names present (DEEPA.NS, ANSALAPI.NS, ...), `fiscal_period: null` (honest-null fix shape, not a wrong label) |
| 13 | News: INFY.NS relevance | **new defect (medium)** | `13-news-infy-ns-regression.json`: top 2 of 15 articles are off-topic crypto pieces from Yahoo's per-symbol feed, tagged `symbols:["INFY.NS"]` |
| 14 | News: AAPL control | ok | `14-news-aapl-control.json`: all articles genuinely Apple-relevant |
| 15 | News: RELIANCE.NS | NOT TESTED (data gap, not misleading) | `15-news-reliance-ns.json`: `[]` -- honestly empty, no fabricated content; not pursued further this round (budget) |
| 16 | Workspace save: colon in name | ok (fix holds) | `16-ws-save-colon-regression.json`: 200 saved |
| 17 | Workspace save: 300-char name | ok (fix holds) | `17-ws-save-300char-regression.json`: clean 400 (was 500 at census) |
| 18 | panel-greeks-dashboard | ok (not tested r3) | `18-greeks-dashboard.json`: delta 0.637, gamma 0.01876 (consistent with row 8/9's binomial gamma), theta -6.414 |
| 19 | panel-bond-pricer | ok (not tested r3) | `19-bond-pricer.json`: clean price 1039.91, duration 8.04 -- premium bond, consistent with YTM(4.5%) < coupon(5%) |
| 20 | R15-UI-003: agent-builder tool-ids (backend half) | ok (fix holds) | `20-agent-builder-tool-ids-regression.json`: 56 ids (full catalog) |

## Census -> rc1 deltas

No regressions: every round-3-held row this round re-checked still holds at the new
candidate. Two additional fixes since round 3 (R15-DATA-117, R15-LEAD-040) both
verified live/by code-read and both hold. R15-UI-077 remains open exactly as
documented (adjudicated, no fix round expected).

## New defect

**INFY.NS news feed surfaces off-topic articles as company news.** `GET
/news?symbols=INFY.NS` (IN region) returns Yahoo per-symbol-feed items about
Chainlink/crypto tagged `symbols:["INFY.NS"]` with no Infosys mention, ranked above
a genuinely relevant Economic Times market-wrap article. Control (`AAPL`) returns
only relevant articles. This is distinct from R15-DATA-029 (already fixed: bare-ticker
US/ADR mixup) -- here the symbol resolves correctly, but `news_provider.py`'s
per-symbol Yahoo RSS fetch tags every item from that feed URL with the queried
symbol without checking the article text, so a thin/generic Yahoo per-symbol feed
degrades into misattributed content. Filed as `rc1-drive-panels-layouts:1`, medium
(wrong value, not every symbol -- AAPL unaffected).

## Not tested this round (budget)

`panel-context-publishers` (vitest-only, no sidecar surface), `layouts-arrange-templates`
(pure frontend `fitLayoutTemplate`, no sidecar surface) -- both carried forward at
their census/round-3 score, no register-fix or regression signal pointed at them.
News relevance for `RELIANCE.NS` (empty result, not misleading) noted but not chased
further under this round's budget. `layouts-macos-menu-bridge` and node-editor
canvas/palette drag remain `NEEDS-GUI` per the skeleton. Broker-connect/order-entry
are `removed_with_feature` (trading out of product).

## Sidecar stop

Stopped by killing sleep pid `71382` (own dedicated port `52323`); confirmed
unreachable after kill.
