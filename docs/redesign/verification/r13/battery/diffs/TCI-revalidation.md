# TCI — Transport Corporation of India Ltd (NSE TCI / BSE 532349; SPARE — not in the original fix-target set) — RE-VALIDATION diff vs reference pack

Collected 2026-07-10T14:42Z (ref pack 2026-07-10T10:07:46Z). This is a battery **SPARE**: the fixes below were written against BMW/BABA/META/NHL/GEE/CDG/BI/SIL/UFO/PML/TI/RBA — TCI was never touched by the fix loop. Proves the fixes generalize, not just fit the primaries.

## Resolve

| Probe                                                                                                      | Result                                                                                                                                                                                                  | Verdict           |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| Bare "TCI" (live collision probe: NYSE:TCI / Transcontinental Realty + historical Tele-Communications Inc) | Binds Transport Corporation of India Limited NSE conf 1.0; candidate #2 the BSE dual listing; candidate #3 **TRANSCONTINENTAL REALTY INVESTORS INC (US, conf 1.0)** — listed but not chosen (IN region) | MATCH             |
| Full name "Transport Corporation of India Ltd"                                                             | **Binds at 1.0, no disambiguation** — Ltd/Limited seam fix HOLDS on a fresh name                                                                                                                        | **FIX CONFIRMED** |
| Enriched fields                                                                                            | isin INE688A01022 = pack; bse_code 532349 = pack                                                                                                                                                        | MATCH             |

**New observation (not a fix regression, pre-existing):** the US collision candidate ("TRANSCONTINENTAL REALTY INVESTORS INC") carries TCI's own ISIN/bse_code/industry in its enrichment fields — a plainly wrong join (a US NYSE listing cannot have an Indian ISIN). Verified this is NOT new: the original battery's `collected/RBA.json` shows the identical pattern (RB GLOBAL INC. carrying RBA's Indian ISIN/bse_code) — pre-existing across the whole run, unflagged in the original diffs, out of scope for this fix wave but worth a ticket.

## Field table

| Field                   | Reference (as-of)                                           | Collected (as-of)                                                                                           | Verdict                                          |
| ----------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Price                   | 937 (2026-07-10)                                            | — (bundle price leg not separately re-verified; mcap/PE internally consistent)                              | n/a                                              |
| Mcap                    | ₹7,198 Cr                                                   | ₹7,185.6 Cr                                                                                                 | MATCH (~0.2%)                                    |
| PE                      | 15.9                                                        | 15.74                                                                                                       | MATCH                                            |
| PB                      | 2.80                                                        | 2.79                                                                                                        | MATCH                                            |
| 52w high/low            | 1299 / 868                                                  | 1289.0 / 868.05                                                                                             | MATCH                                            |
| Div yield               | 1.06%                                                       | 1.08%                                                                                                       | MATCH                                            |
| Shareholding (Mar 2026) | promoter 68.74, FII 3.03, DII 12.86, public(non-inst) 15.37 | promoter 68.73, FII 3.04, DII 12.86, public(non-inst) 15.37, `split_source: BSE`, `split_as_of: 2026-03-31` | **MATCH (near-exact)** — FII/DII split fix HOLDS |

## field_meta (null-reason stamping fix)

36 total fields; 2 null (`peg_ratio`, `identity_note`), both stamped `status: unavailable, reason: "provider did not publish this field"`. **FIX CONFIRMED** — every null field carries a reason, none bare.

## Income statement

`/fundamentals/TCI/income` — 200, 5 periods (2021–2025), 50 line items populated. Statement lines exist.

## Research bundle (gather_fast, 30.7s)

- **News leg**: `ok: true`, `data: []`, note: _"No on-entity news found for TCI — 135 item(s) returned by the news feed were off-entity/off-topic and dropped."_ — honest decline, zero collision leakage (the original battery's META Yahoo-collision leak does not recur here). **FIX CONFIRMED** (on-entity-or-honest-note).
- **Filings leg**: `ok: true`, provider `nse+bse`, 20 exchange announcements (AGM notice, BRSR filing, annual report — real, dated, on-entity). **FIX CONFIRMED** (was dead in all 12 original runs; now wired for a fresh name).
- **Derived leg**: 1 conflict — `held_percent_insiders` (71.30% yfinance vs 68.73% NSE promoter), `conflict_kind: definitional_expected` (small gap, correctly classified as a definitional insiders-vs-promoter difference, not a data contradiction).
- **Earnings-quality / range / mcap-witness legs**: none fired — correctly inapplicable/no-divergence for a clean name (`range_52w_exchange` = {1289.0, 868.05} — agrees with provider, no conflict emitted; `market_cap_witness` attached, no divergence past 10% tolerance).
- Web backend: **searxng** (managed), 0 citations this round — see summary's engine-state note (observed across most of this run's names).

## New finding — historical shareholding split corruption (pre-2026 quarters)

82 of 85 quarterly patterns (everything before 2026-03-31, plus a corrupted 2025-06-30/2025-03-31/2024-12-31 stretch) carry nonsensical FII/DII/institutions/public-non-institutional values in the **hundreds to low thousands** (e.g. 2025-06-30: FII 318%, DII 1238%, institutions 1556%) with `split_source: BSE` still stamped. The CURRENT quarter (2026-03-31, the one both the pack and the app's REST surface report) is correct. This is a genuine, previously-undiscovered defect in the "nearest BSE quarter" historical-split merge (not the current-quarter path the reference packs test) — **out of scope of the fix wave under test, but real** and worth a follow-up ticket. Confirmed NOT universal — see summary for which spares are/aren't affected.

## Verdict

**CLEAN.** Every fix targeted at the primaries generalizes to TCI: Ltd/Limited seam resolves at 1.0, field_meta stamps every null with a reason, FII/DII split merges in correctly for the current quarter, filings leg pulls real NSE+BSE announcements, news leg declines honestly instead of leaking generic/off-entity content. One pre-existing (non-regression) resolver enrichment bug noted, and one new historical-data-only defect discovered (does not affect current-quarter accuracy).
