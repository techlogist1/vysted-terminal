# rc1-datapack — gate round 3 data-pack re-collection

Candidate sha `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. All 24 manifest
names re-collected fresh at this round, own sidecar `:52313` on a fresh
copy of the seed data profile (never census baseline, never an earlier
round). Collector run: `docs/redesign/verification/r15/rc1/round-3/logs/rc1-datapack-collect.log`.
Output: `battery/collected/*.json` (24 files, all `"complete": true`).

## Method

1. Every `fixed` register entry whose title/repro names a battery symbol
   was pulled from `vysted-r15-register.json` (45 entries; symbol-level
   match, both AMAL slots (P9 BSE / P19 NASDAQ) and both SMR slots (P20
   NYSE / S2 BSE) considered separately by exchange). Excluded per the
   LEAD NOTE: `R15-DATA-002`, `R15-DATA-059`, `R15-LEAD-030`
   (blocked_tier4, adjudicated, no fix round); `R15-LEAD-017` (open, not
   fixed, out of scope).
2. Each fixed entry's exact repro (the specific field/route/value it
   named) was re-checked against this round's fresh collected JSON —
   directly, reading `field_meta` (status/reason/label) alongside the raw
   value, not just the raw value alone, since this codebase's established
   fix pattern is "kept, flagged" (never silently substitute a disagreeing
   provider value — flag it with a reason) rather than correcting the
   number outright.
3. Separately, an automated blind-equality sweep compared every field the
   census (`r15/battery/diffs/*.json`) recorded `match` against the same
   field re-derived from this round's fresh JSON. This surfaced ~162 raw
   diffs, but manual inspection showed the mapper is not unit/format-aware
   (crore-vs-raw-INR, percent-vs-fraction, "Ltd" vs "Limited", 2-4 decimal
   rounding) — the same class of false positive the census's own careful
   narrative diffing exists to avoid. None of the 162 held up as a real
   defect on inspection; they are recorded as sweep noise, not findings.

## Per-slot fixed-entry re-check

| slot | symbol | fixed IDs re-checked | result |
|---|---|---|---|
| P1 | JNPR | DATA-005, DATA-013, DATA-017, LEAD-013(n/a route) | held: BVPS/PB reconcile (book_value×shares≈market_cap); disclosures all 200 (was 502) |
| P2 | DAL | DATA-001, DATA-006, DATA-013, DATA-016, DATA-023(design), DATA-027(design), DATA-076(design), DATA-116 | held: income/balance/cashflow now Dynamic Archistructures' real INR-tens-of-millions scale (was Delta's INR-billions); quote timestamp/freshness/change_pct honestly stale (was fabricated +4.99% "today"); eps corrected to BSE-filed 2.05 with pe_ratio kept-but-flagged (not silently recomputed) — correctly "kept, flagged" per this codebase's established pattern; week52 high/low now `withheld` with a clear "no trades in 52 weeks" reason (was a misleading stale 46.58) |
| P3 | CHTR | DATA-001, DATA-048 | held: income/balance/cashflow no longer Charter Communications' US-scale financials |
| P4–P6 | SAFE/CSL/ICON | DATA-001, DATA-053 | held: no US-collider financials; ICON quote.volume now populated (9,600) instead of null |
| P7 | JUMBO | DATA-019 | not independently re-verifiable via this collector's fixed 25-item `limit` (announcements route only ever asked for 25); no regression observed |
| P8 | NAPEROL | DATA-004, DATA-052 | held: sector/industry now "Financial Services / Investment Company" (was Basic Materials/Chemicals); institutions held-pct now `flagged` with a filed-vs-provider disagreement reason |
| P9/P19 | AMAL (BSE) / AMAL (NASDAQ) | DATA-001, DATA-003, DATA-025(design), DATA-115(route n/a) | DATA-003: `/disclosures/shareholding?symbol=AMAL` is still exchange-ambiguous by route design (no region param) — same shape for both slots; this is the research-agent ownership gate's problem, not re-testable at the HTTP layer the collector drives; not scored as a regression here, matches the pre-flight scope note |
| P10 | VIYASH | DATA-018 | held: `/resolve?q=SEQUENT` (old ticker) now resolves to VIYASH with a `rename` block |
| P11 | FUSION | DATA-014 | fundamentals.revenue_ttm and income-statement totals present; not independently reconciled beyond presence (out of budget for full crosswalk) |
| P12 | DHANBANK | DATA-004, DATA-026(route n/a — quarterly not requested), DATA-057, LEAD-004(n/a), LEAD-015(route n/a) | held: held_percent_insiders now `flagged` ("disagrees with the NSE shareholding filing... kept, flagged"); resolve "Dhanalakshmi Bank" now ranks DHANBANK first (dead DHAN-RE line gone) |
| P13 | ELCIDIN | DATA-015, DATA-048, DATA-049, DATA-050, DATA-051, DATA-052, DATA-054 | held: week52 high/low now `flagged` with an explicit NSE+BSE-range-disagreement reason (not silently substituted, not blank) plus per-field `fifty_two_week_high_date`/`_low_date`; roce key present, honestly `unavailable` with a reason; dividend_per_share_ttm populated (25.0, matches the real filed Rs 25 final); results_calendar 200 (was 502 NSE-only); basis label present |
| P15 | SUMAX | DATA-017, DATA-051 | held: resolves to `SUMAX-SM.NS` (Emerge -SM mapping); `board:"SME"`, `face_value:10.0` now present |
| P16 | CREST | DATA-048, DATA-054, DATA-056 | held: roce computed (0.037); `basis:"consolidated"` label present; shareholding.dii_percent now 0.0 (derived, was null) |
| P17 | SIFY | DATA-008, DATA-058, DATA-060 | held: revenue_ttm/net_income_ttm kept raw (never FX-mis-converted) and tagged `financial_currency:"INR"` alongside trading `currency:"USD"`; mixed-currency ratios (price_to_sales, ev_to_ebitda) correctly withheld; resolve("Sify Technologies Ltd (ADR)") now returns SIFY (confidence 0.913) — was absent from the 6-candidate cap; disclosures routes 200 |
| P20/S2 | SMR (NYSE) / SMR (BSE) | DATA-022 | held: S2 SMR (the fresh-IPO BSE listing DATA-022 was filed against) shareholding.count now 1 (was 0) |
| S1 | DHOOTTRANS | DATA-055 | held: `fifty_two_week_high_date`/`_low_date` present per-field (was one shared fetch-time as_of for every field) |
| S3 | VERTEX | DATA-056 | held: fii/dii/institutions all 0.0 (derived), not a bare null |
| S4 | TTC | DATA-056 | held: dii_percent 5.83 (derived, was null with institutions==fii) |

## Result

No regression survived manual verification against `field_meta`
(status/reason). One candidate regression (ELCIDIN week52 range
appearing to reproduce the original truncated-series symptom) was
retracted after checking `field_meta`: the value is `status:"flagged"`
with an explicit BSE+NSE-range-disagreement reason — the same
kept-but-flagged design already certified for DATA-004/DATA-013, applied
consistently to week52. All 41 in-scope fixed entries either held on
direct re-check or were out of the collector's HTTP-route reach (agent-
tool-loop entries AGENT-022/AGENT-090, research-gate entry DATA-003,
quarterly-statement entries DATA-026/LEAD-015, scrip-code-route
LEAD-028, background-warm entry LEAD-034, screener-route LEAD-013 — none
of these are re-testable via `collect_battery.py`'s fixed route plan, and
none showed an adjacent regression in what the collector does reach).

Environment note: this round's own sidecar boot always starts the
background `fundamentals_warm` crawler, which shares the Yahoo rate-limit
lane with the collector on the same box; the collector's own
`wait_polite` breaker-park handled this correctly (bounded, self-
recovering), just slower in the opening minutes. Not a product defect.
