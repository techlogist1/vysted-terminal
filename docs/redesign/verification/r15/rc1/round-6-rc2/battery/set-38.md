# Set: batch-9/W4-market-lanes-errors-quant (set-38) — rc1-battery-19 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-066 | GET /quotes?symbols=<20 NIFTY .NS names> with X-Vysted-Region IN, cold then warm | warm re-run 0.00 s, 20/20 quotes nse_direct eod (was 23 s). Cold first batch took 86 s on a machine shared with other agents (register said 23 s warm base / 85 s cold; verifier saw 21-23 s cold). Steady-state refresh fixed | holds (cold-batch latency noted) |
| R15-DATA-062 | GET /quotes?symbols=RELIANCE.NS,ZZZNOTREAL.NS,BHP.AX and COCHINSHIP,MAZAGONDOCK | RELIANCE.NS returned stamped "RELIANCE.NS" (not stripped), BHP.AX stamped; unknown symbols still omitted on the wire (frontend derives "unavailable", verified by batch-9 jsdom) | holds |
| R15-LIFECYCLE-021 | in-process dead NSE session (stubbed _get_json raises) x4 NSE quotes; live /system/provider-health | 4 quotes served by provider nse; fallthroughs [{nse_direct, quote, count 4}]; live endpoint carries the fallthroughs array | holds |
| R15-UI-053 | GET /macro/catalog?provider=imf, then GET /macro/<id>?provider=imf for every id | 10/10 catalog ids HTTP 200 with observations (incl. WEO/IND.NGDP_RPCH.A) | holds |
| R15-DATA-065 | GET /history SPY 1mo, AAPL 1wk, TCS.NS 1mo, RELIANCE.NS 1wk (today Sat 2026-10-03) | current bars eod: SPY 1mo 2026-10-01, AAPL 1wk 2026-09-28, TCS 1mo 2026-10-01, RELIANCE 1wk 2026-09-28; no stale, no future-dated bar | holds |
| R15-DATA-073 | live NSE holiday-master (CM) vs locale._NSE_HOLIDAYS 2026 | 20 vs 20, no difference either way; regenerate_holidays.py present | holds |
| R15-UI-051 | frontend render only (vitest); not run here | pinned: OptionPricerPanel.test.tsx "R15-UI-028: in region IN, ₹ price..." (+ display-currency select), BondPricerPanel.test.tsx "R15-DATA-100: in region IN, prices render with ₹" exist at candidate | ci_pinned (OptionPricerPanel.test.tsx, BondPricerPanel.test.tsx) |

COVERAGE: 7/7 ids raw (battery/raw/set-38/); no raw: none
