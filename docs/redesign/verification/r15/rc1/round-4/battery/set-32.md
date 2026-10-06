# set-32 — batch-8/W3-data-error-honesty (rc1-battery-15)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, own sidecar :52355.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-061 | in-process `agent_tools.fundamentals._classify_reason` with the register's two `not_found`/`network` kinds; `curl /fundamentals/ZZZZNOTREAL`, `/fundamentals/KSE.NS`, `/fundamentals/509470.BO` | both `not_found`-kind cases classify `not_found`; `network` kind classifies `provider_error`; ZZZZNOTREAL → HTTP 404 `code:"not_found"`; KSE.NS and 509470.BO now return real fundamentals records (not not_found) | holds |
| R15-AGENT-030 | in-process `services.errors.error_frame(exc)` for RuntimeError/ValueError/TypeError/KeyError; `humanize(None, httpx.ConnectError(...))` | all four internal exceptions → `code:"internal"`, "The terminal hit an internal error.", detail carries `TypeErrorName: message`; a real `httpx.ConnectError` still humanizes to `code:"network"` | holds |
| R15-LEAD-005 | `curl -H 'X-Vysted-Region: US' /quotes/NSRGY` and `/quotes/TKOMY` at 2026-09-26T21:54:28Z | NSRGY and TKOMY both stamped `timestamp:"2026-09-25T20:00:00Z"` — a fixed prior EOD trade time, not the request wall-clock (21:54:28Z); provider yfinance, freshness eod | holds |
| R15-DATA-081 | `curl /quotes/BTC%2FUSDT?asset_class=crypto`; `curl /history/ETH%2FUSDT?range=1y&asset_class=crypto` | BTC/USDT slash-encoded quote resolves (84122.01 USDT, `ccxt:binance`, `live`); ETH/USDT 1y history returns 365 bars via `ccxt:binance` | holds |
| R15-UI-030 | jsdom/vitest component test (not run live — battery role does not run vitest suites) | pinned test found and read: `src/modules/macro/MacroPanel.test.tsx:116`, `it(...R15-UI-030)`, asserting the exact FRED→ECB tab-switch call sequence with no cold-boot-retry re-fire. Supplementary live check: `/macro/DGS10?provider=fred` still returns the deterministic keyless 502 sentence the test mocks against. | ci_pinned (MacroPanel.test.tsx, `R15-UI-030` test case) |
| R15-UI-029 | jsdom/vitest component test (not run live) | pinned test found and read: `src/modules/macro/MacroSeriesPicker.test.tsx:111`, `it(...R15-UI-029)`, asserting the catalog-503 error text renders and the skeleton is not stuck. | ci_pinned (MacroSeriesPicker.test.tsx, `R15-UI-029` test case) |

Note on R15-LEAD-005: the sidecar reads region from the `X-Vysted-Region` request header (a per-request ContextVar, `config.py`), not a query param; without it, US ADR symbols resolve against the IN provider chain and 404. Repro re-run with that header set.

COVERAGE: 6/6 ids raw; no raw: none (2 of 6 are ci_pinned, not a live probe — a pinned-test citation counts as this id's raw file per the harness convention for that verdict).
