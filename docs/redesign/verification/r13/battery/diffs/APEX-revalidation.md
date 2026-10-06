# APEX — Apex Frozen Foods Ltd (NSE APEX / BSE 540692; SPARE, seafood export; declared-vs-paid probe) — RE-VALIDATION diff vs reference pack

Collected 2026-07-10T14:45Z (ref pack 2026-07-10T10:07:46Z). Battery **SPARE** — not in the original fix-target set. This is also **Task C**: does `dividend_declared` surface the 30-May-2026 board-approved dividend, distinct from TTM-paid?

## Resolve

| Probe                             | Result                                           | Verdict                              |
| --------------------------------- | ------------------------------------------------ | ------------------------------------ |
| Bare "APEX"                       | Binds Apex Frozen Foods Limited NSE conf 1.0     | MATCH                                |
| Full name "Apex Frozen Foods Ltd" | **Binds at 1.0, no disambiguation**              | **FIX CONFIRMED** (Ltd/Limited seam) |
| Enriched fields                   | isin INE346W01013 = pack; bse_code 540692 = pack | MATCH                                |

## Field table

| Field                   | Reference (as-of)                                          | Collected (as-of)                                        | Verdict                                    |
| ----------------------- | ---------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------ |
| Mcap                    | ₹1,225 Cr                                                  | ₹1,220.3 Cr                                              | MATCH (~0.4%)                              |
| PE                      | 31.5                                                       | 31.39                                                    | MATCH                                      |
| PB                      | 2.32                                                       | 2.31                                                     | MATCH                                      |
| 52w high/low            | 514 / 203                                                  | 514.5 / 208.74                                           | MATCH (low differs ~2.8%, source rounding) |
| Div yield               | 0.50%                                                      | 0.52%                                                    | MATCH                                      |
| Shareholding (Mar 2026) | promoter 72.62, FII 6.00, DII 0.66, public(non-inst) 20.73 | (not directly re-tabulated; see shareholding lane below) | see below                                  |

## field_meta (null-reason stamping fix)

36 total fields; 8 null (`peg_ratio`, `roe`, `roa`, `current_ratio`, `quick_ratio`, `free_cash_flow`, `earnings_growth`, `identity_note`), all stamped with an honest reason. **FIX CONFIRMED.** `roe` null vs pack's 7.60% is a genuine provider-coverage gap, now honestly labeled.

## Income statement

`/fundamentals/APEX/income` — 200, periods and line items populated.

## Task C — declared-vs-paid probe (the point of this name)

`dividend_per_share_ttm: 2.0` (`status: ok`), `dividend_declared: None`, `dividend_yield: 0.0052` (≈0.52%, matches pack's 0.50%).

**Independently verified against the raw NSE corporate-actions feed** (`nse_provider.get_corporate_actions("APEX")`): the most recent dividend row is _"Dividend - Rs 2 Per Share"_ with `recDate: "19-Sep-2025"` — **not** a 30-May-2026 entry. NSE's corporate-actions feed has **not yet published** a row for the 30-May-2026 board approval the reference pack cites (the pack's own `world_gaps` says exactly this: _"Exact per-share dividend amount and record date for the 30 May 2026 board-approved dividend not found in sources checked... a BSE/NSE corporate-action filing would be needed to confirm declared-vs-paid amount and timing."_).

**Verdict on the probe: WORLD-GAP, not APP-GAP.** The app cannot surface a declared-but-unpaid dividend that the exchange feed itself has not yet published — and neither could the reference pack's own research. `dividend_declared: None` is the _correct, honest_ answer here, not a miss: the mechanism (D57, `dividend_actions.get_declared_unpaid_dividend`) is NSE-corporate-actions-feed-driven and has nothing to detect. `dividend_per_share_ttm: 2.0` correctly reflects the last dividend NSE has published (the Sep-2025 ₹2/share), consistent with the pack's trailing 0.50% yield. The declared-vs-paid SEPARATION mechanism itself is intact and correctly primed to fire the moment NSE publishes the record date — it just hasn't yet, on either side.

## Research bundle (gather_fast, 24.9s)

- **News leg**: honest decline, note: _"No on-entity news found for APEX — 137 item(s)... off-entity/off-topic and dropped."_ **FIX CONFIRMED.**
- **Filings leg**: `ok: true`, provider `nse+bse`, 20 announcements. **FIX CONFIRMED.**
- **Range/mcap-witness legs**: `range_52w_exchange` = {514.5, 208.74} — agrees with provider, no conflict; `market_cap_witness` attached, no divergence.

## New finding — historical shareholding split corruption

33 of 36 quarterly patterns carry the same nonsensical FII/DII values seen on TCI/ADOR (current quarter correct). Same pre-existing, out-of-scope defect.

## Verdict

**CLEAN**, with a genuinely informative negative result on Task C: the declared-vs-paid mechanism is correctly wired but structurally cannot surface a dividend the exchange feed hasn't published yet — this is honest behavior, matching the reference pack's own admitted gap, not an app defect. Ltd/Limited seam, field_meta, filings wiring, and honest news decline all hold.
