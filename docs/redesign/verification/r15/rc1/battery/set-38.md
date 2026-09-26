# batch-9/W4-market-lanes-errors-quant (rc1-battery-7)

Candidate `4c6dfe8c`. Own sidecar on `:52347`. 7 certified entries re-run (authoritative
entry list per `battery/INDEX.json` / batch-9 `PLAN.md`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-066 | `GET /quotes?symbols=` (5 NSE names) x3 | first two calls hit a cold-cache 15s client timeout (this box's multiple concurrent shards contending NSE/yfinance — same caveat as before, not a code-path issue); third call **0.00197s** — matches the cert's warm-cache claim exactly | holds |
| R15-DATA-062 | `grep sidecar/routers/quotes.py` | comment "a requested symbol absent from the list is one that failed" + `result.symbol = requested` both present unchanged | holds |
| R15-LIFECYCLE-021 | `GET /system/provider-health` | `fallthroughs` array present and live: `nse`/`bse` × `quote`, count 6 each, `last_error` "'BRK.B' is not a known NSE/BSE instrument" — mechanism intact | holds |
| R15-DATA-065 | `GET /history/SPY?timeframe=1mo&range=3mo` | top-level `freshness: "eod"` with last bar 2026-09-01 — matches cert ("now reads eod (it read stale)") | holds |
| R15-DATA-073 | `grep sidecar/services/locale.py` NSE 2026 holiday set + `resolver_masters/regenerate_holidays.py` presence | 20 dates listed for 2026 (matches cert's "all 20 dates"); regenerator script present | holds |
| R15-UI-053 | `GET /macro/WEO%2FIND.NGDP_RPCH.A?provider=imf` | 2031 value `6.513934` — exact match to cert | holds |
| R15-UI-051 | `grep src/modules/quant/OptionPricerPanel.tsx` | `displayCurrency` state + region-driven default + select input all present (same pattern shared with BondPricerPanel/GreeksDashboard, R15-DATA-100 sibling fix) | holds |

Note: the first DATA-065 probe was mis-read (checked per-bar `freshness` instead of the
series-level field) and corrected in this pass before judging — see raw file.

Excluded (not certified in batch-9): R15-DATA-061 (macro error-mapping still leaks raw
upstream text on a fresh case), R15-UI-028 (rho still unlabelled — batch-10's UI-028 fix
supersedes this, out of this writer set's scope).

Raw output: `battery/raw/set-38/*`.
