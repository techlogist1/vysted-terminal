# batch-9/W3-fundamentals-identity (rc1-battery-7)

Candidate `4c6dfe8c`. Own sidecar on `:52347`. 6 certified entries re-run (authoritative
entry list per `battery/INDEX.json` / batch-9 `PLAN.md` — see notes on the task's copied
entry list for this set, which did not match any real batch-9 entries).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-052 | `GET /fundamentals/NAPEROL.BO`, `/ELCIDIN.NS` | NAPEROL.BO: `sector="Financial Services", sector_source="resolver"`; ELCIDIN.NS: same — exact match to cert (the BSE truth overrides Yahoo) | holds |
| R15-LEAD-022 | `GET /quotes?symbols={BHP.AX,0700.HK,7203.T,VOD.L,SAP.DE,BRK.B}` | all six price and return `symbol` matching the requested spelling (BRK.B not mangled to BRK-B in the response), currencies AUD/HKD/JPY/GBp/EUR/USD all correct | holds |
| R15-LEAD-023 | in-process `yfinance_provider._quote_time(FakeTicker())` with empty `get_history_metadata()` + empty `history()` DataFrame | raises `ProviderError("Yahoo returned a price with no trade time")`, not an `IndexError` — clean fallthrough, matches cert exactly | holds |
| R15-LEAD-016 | `GET /earnings/AAPL/history`, `/earnings/RELIANCE.NS/history` | AAPL: `reported_date` 2026-07-30/2026-04-30/2026-01-29/2025-10-30 all fiscal-quarter-end `period_end`; RELIANCE.NS same shape — matches cert's "reported_date is the fiscal quarter end" | holds |
| R15-DATA-069 | `GET /fundamentals/AAPL/ratings/price-target-history` | Evercore ISI Group 365→380 on 2026-09-18; B of A Securities 370→370 on 2026-09-23 — exact match to cert | holds |
| R15-UI-015 | `grep` `src/modules/earnings/EarningsCalendarPanel.tsx` + `src/modules/screener/ScreenerPanel.tsx` (cert evidence was a scratch, never-committed vitest against a deterministic Node http engine — no permanent test or sidecar route to re-run) | both files carry the R15-UI-015 fix verbatim: `throw state.upcomingCause ?? new Error(...)` re-throws the original `SidecarError` instead of flattening it, with the "reads as transient to `isTransientSidecarFailure`" comment intact | holds |

Raw output: `battery/raw/set-37/*`.
