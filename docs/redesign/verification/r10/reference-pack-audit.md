AUDIT — reference pack, 10 stocks + 1 screen (as-of 2026-06-11 close)

**(1) Nulls / missing load-bearing figures**
None. All 10 stocks have every required field populated (price, mcap, P/E, 52w hi/lo, drawdown, dividend, yield, Q4 rev/PAT, growth %, ROE, BV, price_as_of). There is no gatherer laziness expressed as nulls — the laziness shows up instead as **stale or single-sourced values shipped into fields**:
- JYOTHYLAB `roe_pct: 19.0` and `book_value: 55.8` are knowingly FY25-vintage (notes admit screener's page is stale and estimate true FY26 consolidated ROE ~16.3%). This is the only field in the pack that is effectively wrong, not just disputed. Genuinely hard to source (FY26 consolidated ratios not yet published) — but the field should carry the ~16.3% estimate or a stale-flag, not 19.0.
- JYOTHYLAB 52w high/low rests on Google Finance only — laziness: the official NSE `CM_52_wk_High_low_11062026.csv` was fetched and used for ITC and CUMMINSIND the same day; one more row lookup covers this.
- Single-source ratios, honestly flagged: ITC ROE/BV (screener only), FEDERALBNK ROE, GARFIBRES 52w-low decimal (dhan only), RATNAMANI Q4 FY25 revenue base (rounded ₹1,715).

**(2) Internal consistency — verified by recomputation, all 10 pass**
- Drawdown = (high−close)/high: exact match all 10 (max deviation 0.00pp).
- Yield = FY26 DPS/close: exact match all 10; basis is consistently FY26-entitlement (interim+final), with alternate-basis yields enumerated in notes.
- Growth %: all match recomputation within 0.05pp (KPITTECH 11.95 vs rounded-base 11.98 and RATNAMANI −36.7 vs −36.75 are documented base-precision artifacts).
- Mcap plausibility: implied share counts all sane (ITC 1,252cr, LT 137.6cr, PERSISTENT 15.8cr, FEDERALBNK 246.7cr, KPIT 27.4cr, RATNAMANI 7.0cr, GARFIBRES 9.9cr, CUMMINS 27.7cr, POLYCAB 15.3cr, JYOTHY 36.7cr) and cross-check against EPS-implied counts in notes. No order-of-magnitude errors.
- P/E disagreements (ITC 17.1 vs 16.9, LT 33 vs 32.4/28.4, KPIT 31.65 vs 29.8, RATNAMANI 36.78 vs 33, GARFIBRES 34.5 vs 32.8) are all basis differences with the chosen basis shown arithmetically consistent. Good.
- One nit: ITC confidence note says "12,518 Cr shares" — unit slip for 1,251.8 Cr shares; harmless but fix.

**(3) Entity identity**
Complete for all 10: name, NSE symbol, BSE code, ISIN (all format-valid), sector, industry — with alternate taxonomies (Trendlyne/BSE) listed where vendors disagree. No gaps.

**(4) Screen completeness**
Strong. 31 matches + 18 near-misses; criteria implied (NSE-listed IT, mcap<5,000cr, P/E<20, ROE≥15). Near-misses are well-designed: one-criterion failures for each axis, boundary catches (CANARYS ROE 14.6, NEWGEN/AURIONPRO/EXCELSOFT P/E ≈19.x, TERASOFT 21.1), basis-flip traps (KELLTONTEC, SUBEXLTD, ROXHITECH, VGINFOTECH consolidated-vs-standalone), and a universe trap (BSE-only 544406). Residual weaknesses, all acknowledged: 11/31 matches are NSE Emerge/SME with tags verified for only 2 ("a few may have since migrated" — membership of the expected set is uncertain); SME ROE single-sourced; 7 contested boundary names (DATAMATICS worst: P/E 18.6 vs 22.93 cross-source); taxonomy coverage ~95% with BPO/KPO excluded by screener's classification.

**Gaps worth re-gathering (priority order)**
1. JYOTHYLAB ROE + book value — replace stale FY25 figures or explicitly mark the field as estimate (~16.3% / BV unpublished).
2. JYOTHYLAB (and LT, PERSISTENT, FEDERALBNK, KPITTECH, RATNAMANI, GARFIBRES, POLYCAB) 52w hi/lo from the already-fetched official NSE 52-wk CSV — one file, eight row lookups, upgrades 8 stocks from vendor-sourced to exchange-official.
3. Same for closes: NSE bhavcopy was used for only 4 of 10 stocks; the other 6 closes rest on secondary sources (triple-confirmed, but the authoritative file is in hand).
4. Second source for ITC ROE/BV and FEDERALBNK ROE; resolve FEDERALBNK Tickertape P/B-implied BV ~144 vs reported 162.
5. Screen: verify SME-vs-mainboard status for the 9 unverified Emerge tags, and pin DATAMATICS P/E from a third source (most contested expected-set member).
6. RATNAMANI Q4 FY25 revenue base and POLYCAB Q4 figures at filing precision (currently rounded crores).

**Verdict: battery-ready, with two asterisks.** Arithmetic, identity, and provenance discipline are excellent — disagreements are enumerated with bases rather than averaged, which is exactly what a validation pack needs. Ship it for price/52w/dividend/Q4/screen testing now. Do NOT grade an app's JYOTHYLAB ROE/BV against this pack until item 1 is fixed, and treat screen membership for the 9 unverified SME names + DATAMATICS as advisory until items 5 are closed.