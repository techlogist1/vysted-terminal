# DEN — Den Networks Ltd (NSE DEN / BSE 533137; SPARE, cable/broadband; affirmed-zero probe) — RE-VALIDATION diff vs reference pack

Collected 2026-07-10T14:45Z (ref pack 2026-07-10T10:07:46Z). Battery **SPARE** — not in the original fix-target set. This is also **Task C**: does the affirmed-zero dividend render as `0.0 "no dividends paid (trailing 12m)"` instead of null?

## Resolve

| Probe                        | Result                                                                     | Verdict                              |
| ---------------------------- | -------------------------------------------------------------------------- | ------------------------------------ |
| Bare "DEN"                   | Binds Den Networks Limited NSE conf 1.0                                    | MATCH                                |
| Full name "Den Networks Ltd" | **Binds at 1.0, no disambiguation**                                        | **FIX CONFIRMED** (Ltd/Limited seam) |
| Enriched fields              | isin INE947J01015 = pack; bse_code 533137 = pack; industry "Entertainment" | MATCH                                |

## Field table

| Field                   | Reference (as-of)                                          | Collected (as-of)                                                                                         | Verdict                                          |
| ----------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Mcap                    | ₹1,394 Cr                                                  | ₹1,391.7 Cr                                                                                               | MATCH (~0.2%)                                    |
| PE                      | 8.42                                                       | 8.39                                                                                                      | MATCH                                            |
| PB                      | 0.36                                                       | 0.37                                                                                                      | MATCH                                            |
| 52w high/low            | 42.8 / 22.5                                                | 42.6 / 22.52                                                                                              | MATCH                                            |
| Shareholding (Mar 2026) | promoter 74.90, FII 0.46, DII 0.14, public(non-inst) 24.42 | promoter 74.9, FII 0.45, DII 0.14, public(non-inst) 24.41, `split_source: BSE`, `split_as_of: 2026-03-31` | **MATCH (near-exact)** — FII/DII split fix HOLDS |

## field_meta (null-reason stamping fix)

36 total fields; 4 null (`peg_ratio`, `dividend_yield`, `dividend_per_share`, `identity_note`), all stamped with an honest reason. **FIX CONFIRMED.**

## Task C — affirmed-zero probe (the point of this name)

`dividend_per_share_ttm: None`, `dividend_declared: None`, `dividend_yield: None`. `field_meta["dividend_per_share_ttm"]` = `{status: "unavailable", reason: "insufficient dividend-history depth to affirm a trailing-12m zero"}`.

**This is NOT the affirmed-zero rendering the probe hoped for — it falls to honest null instead.** Root-caused directly: `yf.Ticker("DEN.NS").dividends` returns a **completely empty series (0 rows)** — DEN has never once had a dividend event recorded by yfinance, consistent with the reference pack's own note ("Dividend payout has been 0% every year from Mar 2015 through Mar 2026"). The affirmed-zero mechanism (`services/dividend_history._sum_trailing_dividends`) requires **at least one dividend older than the 12-month window** to establish "real depth" before it will assert a stateable zero — by design, an empty series is treated as indistinguishable between "never paid" and "no data coverage," so it declines rather than guesses.

**Contrast with PVP** (same battery, same probe class): PVP's yfinance series has 10 historical dividend rows (most recent 2004, still >20 years stale) — enough depth to clear the bar, so PVP correctly gets `dividend_per_share_ttm: 0.0` with the affirmed-zero label. DEN's total absence of any dividend event ever is the one shape the depth-anchor heuristic cannot resolve.

**Verdict on the probe: A real, narrow edge-case gap, not a broken fix.** The D56 affirmed-zero mechanism works correctly whenever there is ANY historical dividend anchor (confirmed on PVP here, and on SIL/UFO/PML/RBA in the original battery). It has no coverage for the "never paid a single dividend in the company's listed life" case specifically, because an entirely empty provider series is genuinely ambiguous between two states the code cannot tell apart without a second signal (e.g. IPO date vs listed-history length). Worth a follow-up: gate the empty-series case on IPO/listing age instead of dividend-series depth, so a company like DEN — over a decade of clean zero-dividend history — can still earn the affirmed-zero label.

## Research bundle (gather_fast, 21.6s)

- **News leg**: `ok: true`, **8 real citations** (Yahoo Finance DEN.NS, TradingView NSE:DEN, Screener.in, Kotak Neo — all on-entity, no collision leakage). The one name in this SPARES batch where the web/news leg actually returned content this run (see summary for the backend-degradation pattern across the other 8 names).
- **Filings leg**: `ok: true`, provider `nse+bse`, 20 announcements (board-meeting intimation, trading-window closure, physical-share-demat window — matches the pack's own recent-filings list). **FIX CONFIRMED.**
- **Range/mcap-witness legs**: `range_52w_exchange` = {42.6, 22.52} — exact agreement, no conflict; `market_cap_witness` attached, no divergence.

## New finding — historical shareholding split: CLEAN

DEN's 68 quarterly patterns show **zero corrupted (>100%) rows** — same as PVP, the historical-split defect does not reproduce here, further bounding it to specific names (TCI/ADOR/APEX), not a universal regression.

## Verdict

**CLEAN on every fix except the affirmed-zero dividend edge case**, which is a genuine, well-understood, narrow gap (empty-series ambiguity) rather than a regression — the mechanism's OTHER path (real depth → affirmed zero) is independently confirmed working on PVP in the same run. Ltd/Limited seam, field_meta, FII/DII split, and filings wiring all hold cleanly.
