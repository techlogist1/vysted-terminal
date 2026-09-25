# batch-9/W3-fundamentals-identity-earnings (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 6 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-052 | `GET /fundamentals/NAPEROL.BO`, `/ELCIDIN.NS` | NAPEROL.BO: `sector="Financial Services", sector_source="resolver"`; ELCIDIN.NS: same — exact match to cert (the BSE truth overrides Yahoo) | holds |
| R15-LEAD-022 | `GET /quotes/{BHP.AX,0700.HK,7203.T,VOD.L,SAP.DE,BRK.B}` | all price and match Yahoo chart meta with no dot-to-dash mangling on the intl suffixes; fresh case `BRK.B` → `symbol: BRK-B`, 505.18 USD (dash conversion correct) | holds |
| R15-LEAD-023 | in-process `yfinance_provider._quote_time` with a fake ticker: empty `get_history_metadata()` + empty `history()` DataFrame | raises `ProviderError("Yahoo returned a price with no trade time")`, not an `IndexError` — clean fallthrough | holds |
| R15-LEAD-016 | `GET /earnings/AAPL/history`, `/earnings/RELIANCE.NS/history` | AAPL: `reported_date` 2025-10-30 and 2026-01-29 present, `period_end` is the fiscal quarter end; fresh case RELIANCE.NS: reported 2025-10-17 and 2026-07-17 — exact match to cert | holds |
| R15-DATA-069 | `GET /fundamentals/AAPL/ratings/price-target-history` | Evercore ISI Group 365→380 on 2026-09-18; B of A Securities 370→370 on 2026-09-23 — exact match to cert | holds |
| R15-UI-015 | `grep` `src/modules/earnings/EarningsCalendarPanel.tsx` + `src/modules/screener/ScreenerPanel.tsx` (cert evidence was a scratch, never-committed vitest against a deterministic Node http engine — no permanent test or sidecar route to re-run) | both files carry the R15-UI-015 fix verbatim: `loadDefault` re-throws `state.upcomingCause` (the original `SidecarError`) instead of a flattened `new Error(string)`, with the comment "a flattened error always reads as transient to `isTransientSidecarFailure`, so a deterministic 502 was retried instead of settling after one try" | holds |

Raw output: `battery/raw/set-35/*`.
