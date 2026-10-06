# R15 Hostile Data Battery — Manifest

Curated: **2026-09-19**. 20 primaries (P1–P20) + 4 spares (S1–S4) = 24 names, none used by any
previous run.

Machine-readable twin: `manifest.json` (same directory).
Repo masters consulted read-only: `sidecar/services/resolver_masters/{bse,nse,us}_instruments.json`.

**Master generation dates (the hostility clock):** BSE master `_generated` = **2026-06-09**
(4,873 rows), NSE master **2026-06-05** (2,675 rows, series `EQ` + `ETF` ONLY — no SME/Emerge
series exists in it), US master 10,365 rows. Anything listed after early June 2026, and every
NSE Emerge name ever, is structurally absent from the bundled masters. Four battery names sit
in that blind spot on purpose (P1 JNPR, P15 SUMAX, S1 DHOOTTRANS, and the BGNE→ONC ticker
change behind P18).

## Battery table

| Slot | Symbol | Company | Exchange | BSE code | Mcap / price (as-of) | Master presence | Hostile traits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | **JNPR** | Juniper Green Energy Ltd | NSE + BSE | 544853 | ₹15,050 cr; ₹264.5 NSE / ₹263.8 BSE (2026-09-15) | **ABSENT from BSE + NSE masters** (listed 2026-08-06, after both were generated). US master has no `JNPR` either | RECENT LISTING (mainboard, 2026-08-06, 44 days old). Triple collision: `JNPR` was Juniper Networks' NYSE ticker until the HPE acquisition; `JUNIPER` in the NSE/BSE masters is **Juniper Hotels Ltd** (544129) — a different listed company; and "Juniper Green" vs "Juniper Networks" vs "Juniper Hotels" is a name collision on top of the ticker one |
| P2 | **DAL** | Dynamic Archistructures Ltd | **BSE only** (grp X) | 539681 | ₹25.0 cr; ₹49.9 | BSE master ✔ `["539681","DAL","Dynamic Archistructures Ltd","X","INE874E01012","Active"]`; NSE ✘; **US master has `DAL` = DELTA AIR LINES, INC.** | COLLISION, in-app and on the open web: bare "DAL" is 100% Delta Air Lines. Both sides live in the app's own masters, so the resolver must disambiguate by exchange, not by string. Nano-cap (₹25 cr), group X illiquid, and the business is a *name lie* — "Archistructures" is an NBFC, not a construction company |
| P3 | **CHTR** | Chatterbox Technologies Ltd | **BSE only** (grp MT, **BSE SME**) | 544546 | ₹49.5 cr; ₹35.0 (2026-09-18) | BSE master ✔ (`MT`, ISIN INE1B4801017); NSE ✘; **US master has `CHTR` = CHARTER COMMUNICATIONS, INC. /MO/** | SME BOARD + COLLISION with a US mega-cap in the app's own US master. Trades as "Chtrbox"/"Chtrsocial" (influencer marketing) — brand names that don't match the legal name or the ticker |
| P4 | **SAFE** | Sodhani Academy of Fintech Enablers Ltd | **BSE only** (grp M, **BSE SME**) | 544257 | ₹66.6 cr; ₹117 (2026-09-18, −6.96%) | BSE master ✔ (`M`, ISIN INE0Q3401017); NSE ✘; **US master has `SAFE` = Safehold Inc.** | SME BOARD + COMMON-ENGLISH-WORD ticker + US collision. ₹3.65 cr of sales against a ₹66.6 cr cap and a PE of 69.4 — the kind of ratio aggregators quietly drop |
| P5 | **CSL** | Continental Securities Ltd | **BSE only** (grp X) | 538868 | ₹76.9 cr; ₹24.2 | BSE master ✔ (`X`, ISIN INE183Q01020); NSE ✘; **US master has `CSL` = CARLISLE COMPANIES INC** | MULTI-ENTITY COLLISION: `CSL` is Carlisle (NYSE, in-master), CSL Limited (ASX, one of Australia's largest companies), and Container Store Group historically. Micro-cap NBFC; TTM revenue ₹4.22 cr — a scale where "revenue" definitions diverge wildly between sources |
| P6 | **ICON** | Icon Facilitators Ltd | **BSE only** (grp MT, **BSE SME**) | 544426 | ₹50.4 cr; ₹64.2 (52w ₹38.0–₹85.0) | BSE master ✔ (`MT`, ISIN INE0Y0E01012); NSE ✘; **US master has `ICON` = Icon Energy Corp** | SME BOARD + COMMON-WORD ticker + US collision, and a third shadow: ICON plc (NASDAQ: ICLR) is the famous "Icon" in finance. Facility-management micro-cap, zero dividend against 17.9% ROE |
| P7 | **JUMBO** | Jumbo Bag Ltd | **BSE only** (grp X) | 516078 | ₹75.3 cr; ₹90.0 (52w ₹105 / ₹49.1) | BSE master ✔ (`X`, ISIN INE699D01015); NSE ✘ | COMMON-WORD ticker ("jumbo"). Group X illiquid nano-cap. Profit CAGR 82.2%/5y against sales CAGR 6.81% — a divergence that makes every derived ratio source-dependent. Also an IOCL polymer-trading associate, so "revenue" mixes manufacturing and trading |
| P8 | **NAPEROL** | Naperol Investments Ltd | **BSE only** (grp X) | 500298 | ₹371 cr; ₹645 (2026-09-18) | BSE master ✔ (`X`, ISIN INE585A01020); NSE ✘ | HOLDING COMPANY + the holding-company discount trap in its purest form: **market value of investments ₹888 cr vs market cap ₹371 cr**, book value ₹1,609 against a ₹645 price, ROE 1.03%. Wadia-group vehicle whose stated business ("peroxygen chemicals" + "long term investments") makes sector classification a coin flip |
| P9 | **AMAL** | Amal Ltd | **BSE only** (grp B) | 506597 | ₹893 cr; ₹722 | BSE master ✔ (`B`, ISIN INE841D01013); NSE ✘; **US master has `AMAL` = Amalgamated Financial Corp.** | COLLISION — and its partner is P19, the same ticker on NASDAQ. Both sides are in the app's masters: the resolver must not merge an Indian sulphuric-acid maker with a US bank holding company. PE 132 at 9× book on 5% ROE; Atul Ltd subsidiary, so consolidated-vs-standalone ambiguity is live |
| P10 | **VIYASH** | Viyash Scientific Ltd | NSE + BSE | 512529 | ₹10,998 cr; ₹250 | BSE ✔ `["512529","VIYASH","Viyash Scientific Ltd","B",...]`; NSE ✔ `["VIYASH","Viyash Scientific Limited","EQ"]` — **under the NEW name only; `SEQUENT` resolves to nothing in either master** | RECENT RENAME (2026): Sequent Scientific Ltd → Viyash Scientific Ltd, symbol `SEQUENT` → `VIYASH` effective **2026-01-23**. Every pre-2026 chart, filing, peer table and news archive is filed under SEQUENT. Deliberate mid-cap contrast |
| P11 | **FUSION** | Fusion Finance Ltd | NSE + BSE | 543652 | ₹2,997 cr; ₹185 (2026-09-18 close; 52w ₹243–₹136) | BSE ✔ (`B`); NSE ✔ (`EQ`) | NBFC + COMMON-WORD ticker. Renamed from Fusion Micro Finance, so half the world's data is under the old name. Microfinance: "revenue" means interest income, and the 23.4–23.98% lending yield vs. AUM vs. NII definitions are exactly where aggregators disagree. 3-year price CAGR −32% |
| P12 | **DHANBANK** | Dhanlaxmi Bank Ltd | NSE + BSE | 532180 | ₹1,163 cr; ₹29.5 (2026-09-18, +2.04%) | BSE ✔ (`B`); NSE ✔ (`EQ`); **the BSE master also carries `["750942","DHAN-RE","Dhanlaxmi Bank Ltd","R",...]` — the rights-entitlement line as a separate instrument** | BANK SMALL-CAP (definitional revenue traps: interest income vs. total income vs. NII; PE/PB conventions differ for banks) + **CORPORATE ACTION**: a rights issue lifted equity capital ₹253 cr (Mar-2025) → ₹395 cr (Mar-2026). The `DHAN-RE` row is a live resolver hazard — a rights entitlement that will string-match "DHAN" queries |
| P13 | **ELCIDIN** | Elcid Investments Ltd | NSE + BSE | 503681 | ₹2,103 cr; **₹1,05,130/share** (2026-09-18, −1.07%) | BSE ✔ (`B`, ISIN INE927X01018); NSE ✔ (`EQ`) | HOLDING COMPANY + EXTREME-MAGNITUDE trap: a five-figure rupee price that overflows naive price formatters and axis scaling, book value **₹3,01,137**, P/B 0.35, ROE 1.23%. Holds the founding family's Asian Paints stake, so "sector" is unresolvable (NBFC? paints?). Historically quoted at ₹3 before the 2024 call auction — stale-price archives are still in the wild |
| P14 | **JONJUA** | Jonjua Overseas Ltd | **BSE only** (grp MT, **BSE SME**) | 542446 | ₹11.2 cr; ₹3.19 | BSE master ✔ (`MT`, ISIN INE793Z01027); NSE ✘ | **CORPORATE ACTION, 15 days old**: 7:24 bonus issue, record date **2026-09-04**, allotment **2026-09-07**. Share count and every per-share figure moved *after* the masters were built. Penny price (₹3.19) on an ₹11 cr cap — the smallest name in the battery, and an SME name on top |
| P15 | **SUMAX** | Sumax Engineering Ltd | **NSE SME (Emerge)** | — (Emerge, no BSE line) | Listed at ₹111 vs ₹101 issue price (2026-09-02) | **ABSENT from the NSE master** — and structurally so: the NSE master holds series `EQ` and `ETF` only, so no Emerge name can ever appear in it | SME BOARD (NSE Emerge) + RECENT LISTING (**2026-09-02**, 17 days old). Double-blind to the resolver: too new *and* on a series the master doesn't carry. IPO ₹53.4 cr (43 L fresh + 10 L OFS). Auto-refinish consumables — a sector no standard taxonomy has a bucket for |
| P16 | **CREST** | Crest Ventures Ltd | NSE + BSE | 511413 | ₹1,041 cr; ₹366 (2026-09-18, −1.42%) | BSE ✔ (`B`, ISIN INE559D01011); NSE ✔ (`EQ`) | COMMON-WORD ticker + HOLDING-COMPANY structure: a "Systemically Important Non-Deposit Taking NBFC / Investment and Credit Company" that invests in real-estate SPVs and JVs while carrying some projects on its own balance sheet. Real estate or financials? Consolidated or standalone? Every source answers differently |
| P17 | **SIFY** | Sify Technologies Ltd (ADR) | NASDAQ (US) | — | $13.80 (2026-09-18, +1.25%); mcap **$989.09M (Morningstar) vs $897.87m (Hargreaves Lansdown) vs $789M (13-Feb-2026)** — sources disagree by >10% | US master ✔ `["SIFY","SIFY TECHNOLOGIES LTD"]`; absent from both Indian masters (correctly — it has no NSE/BSE line) | US **ADR**, and the nastiest kind: an **Indian** company that is US-listed only. **1 ADR = 6 ordinary shares**, so any per-share figure lifted from an Indian source is off by 6×, and rupee/dollar conversion sits on top. 72.43M ADS outstanding. A terminal that "resolves Indian names" must not invent an NSE line for it |
| P18 | **ONC** | BeOne Medicines AG | NASDAQ (US) | — | FY2025 revenue $5.3bn, op. income $447M, net income $286.9M; H1-2026 revenue $1.71bn (+30% YoY) | US master ✔ `["ONC","BeOne Medicines Ltd."]` — **note the master says "Ltd.", but the company redomiciled to Switzerland in May 2025 and is now BeOne Medicines AG**; **`BGNE` is ABSENT from the US master** | US **TICKER CHANGE + RENAME + REDOMICILE**: BeiGene, Ltd. → BeOne Medicines, ticker `BGNE` → `ONC` (January 2025), Cayman → Basel, Switzerland (May 2025). Three identity changes on one security. Also a *semantic* collision — `ONC` reads as the oncology sector abbreviation. The master's own entity suffix is already stale |
| P19 | **AMAL** | Amalgamated Financial Corp. | NASDAQ (US) | — | $49.17 (2026-09-04); mcap **$1.39B**; all-time high $47.89 on 2026-07-01 (**note: the quoted 2026-09-04 price exceeds the quoted ATH — sources conflict, recorded as-is, not reconciled**) | US master ✔ `["AMAL","Amalgamated Financial Corp."]`; **BSE master has `AMAL` = Amal Ltd (506597)** | US **SMALL-CAP** ($1.39B) + the in-app **COLLISION partner of P9**. Same string, two masters, two continents, two currencies, two industries (US bank holding co vs Indian bulk-chemicals). Last quarter EPS $0.80 vs $0.95 estimate (−15.79% surprise) — a miss that some feeds reflect and others don't |
| P20 | **SMR** | NuScale Power Corp | NYSE (US) | — | mcap $4.59B; price **$8.45 vs $10.21 — two figures for mid-Sep-2026 in the same search, recorded as a conflict, not reconciled** | US master ✔ `["SMR","NUSCALE POWER Corp"]`; **BSE master has `SMR` = SMR Jewels Ltd (544774, grp MT, BSE SME)** | US COLLISION with an Indian symbol that is in the app's own BSE master (see S2). Doubly hostile because `SMR` is also a **sector abbreviation** (small modular reactor) that NuScale's own coverage uses generically — a name/ticker/acronym three-way. $1.0bn ATM programme completed Jun-2026, so share count moved mid-year |
| S1 | **DHOOTTRANS** | Dhoot Transmission Ltd | NSE + BSE | 544867 | ₹31,825.63 cr (NSE) / ₹31,800.06 cr (BSE); ₹1,600 NSE / ₹1,599 BSE (2026-09-16) | **ABSENT from BSE + NSE masters** (listed 2026-08-17). The BSE master's only "Dhoot" row is `["526971","DHOOTIN","Dhoot Industrial Finance Ltd","X",...]` — an unrelated company | SPARE — RECENT LISTING #2 (mainboard, 2026-08-17, 33 days old) + **near-miss name collision with an in-master company** (`DHOOTIN` / Dhoot Industrial Finance). Listed at ₹1,200 vs ₹871 issue price (+37.8%); large-cap contrast |
| S2 | **SMR** | SMR Jewels Ltd | **BSE only** (grp MT, **BSE SME**) | 544774 | ₹177 cr; ₹95.0 (2026-09-18, −1.04%) | BSE master ✔ (`MT`, ISIN INE11XK01017); NSE ✘; **US master has `SMR` = NUSCALE POWER Corp** | SPARE — the Indian half of the P20 collision. SME board, 2026-vintage listing. Scale trap: FY26 sales **₹432 cr against a ₹177 cr market cap** (2.4×) with 67% ROE — a B2B jewellery pass-through whose "revenue" is mostly gold value, which sector screens routinely mis-tier |
| S3 | **VERTEX** | Vertex Securities Ltd | **BSE only** (grp X) | 531950 | ₹48.4 cr; ₹3.27 | BSE master ✔ (`X`, ISIN INE316D01024); NSE ✘ | SPARE — COMMON-WORD ticker (and a collision with Vertex Pharmaceuticals' famous "Vertex"). Penny price on a ₹48 cr cap; negative ROE −21.8% / ROCE −13.4% (so PE is null, not a number); **promoter holding collapsed 73.41% → 36.44%**, so shareholding tables are mid-flight across sources |
| S4 | **TTC** | Toss The Coin Ltd | **BSE only** (grp M, **BSE SME**) | 544303 | — (world_gaps: live price/mcap not collected) | BSE master ✔ (`M`, ISIN INE0XAY01012); NSE ✘; **US master has `TTC` = TORO CO** | SPARE — SME board + US collision (Toro Co, NYSE) + a legal name that reads as a sentence, not a company ("Toss The Coin Ltd"), which breaks entity extraction and headline matching |

## Required-mix attestation

| Requirement | Satisfied by | Count |
| --- | --- | --- |
| Mostly sub-₹2,000 cr | Of the 16 Indian primaries, **12 are sub-₹2,000 cr** (P2 ₹25 cr, P3 ₹49.5, P4 ₹66.6, P5 ₹76.9, P6 ₹50.4, P7 ₹75.3, P8 ₹371, P9 ₹893, P12 ₹1,163, P14 ₹11.2, P15 SME micro, P16 ₹1,041). Deliberate contrast above the line: P1 ₹15,050 cr, P10 ₹10,998 cr, P11 ₹2,997 cr, P13 ₹2,103 cr; spare S1 ₹31,826 cr | 12/16 |
| ≥5 BSE-ONLY (no NSE listing, numeric scrip code) | P2 DAL 539681, P3 CHTR 544546, P4 SAFE 544257, P5 CSL 538868, P6 ICON 544426, P7 JUMBO 516078, P8 NAPEROL 500298, P9 AMAL 506597, P14 JONJUA 542446 (+ spares S2 SMR 544774, S3 VERTEX 531950, S4 TTC 544303) | **9** primaries |
| ≥5 COLLISION tickers | P1 JNPR (Juniper Networks + Juniper Hotels), P2 DAL (Delta Air Lines), P3 CHTR (Charter), P4 SAFE (Safehold + common word), P5 CSL (Carlisle + CSL Ltd ASX), P6 ICON (Icon Energy + ICON plc + common word), P7 JUMBO (common word), P9/P19 AMAL (both sides in-master), P11 FUSION (common word), P16 CREST (common word), P18 ONC (oncology abbreviation), P20/S2 SMR (NuScale + SMR Jewels + "small modular reactor") | **12** |
| 1–2 RECENT RENAMES (2026) | P10 VIYASH — Sequent Scientific → Viyash Scientific, `SEQUENT` → `VIYASH`, effective **2026-01-23** | 1 |
| 1–2 RECENT LISTINGS (mainboard, last ~4 months) | P1 JNPR (**2026-08-06**), S1 DHOOTTRANS (**2026-08-17**) | 2 |
| 1–2 SME-board names | BSE SME: P3 CHTR, P4 SAFE, P6 ICON, P14 JONJUA (+ S2 SMR, S4 TTC). **NSE Emerge: P15 SUMAX** | 5 primaries (both boards) |
| 1 recent corporate action (split/bonus 2026) | P14 JONJUA — **7:24 bonus, record date 2026-09-04, allotted 2026-09-07** (15 days before curation). Secondary: P12 DHANBANK rights issue (equity ₹253 cr → ₹395 cr across FY26) | 2 |
| 1 bank/NBFC small-cap | P12 DHANBANK (bank, ₹1,163 cr). Also NBFC-classified: P11 FUSION, P16 CREST, P2 DAL, P5 CSL | 1 (+4) |
| 1 holding company | P8 NAPEROL (investments ₹888 cr > mcap ₹371 cr). Also P13 ELCIDIN, P16 CREST | 1 (+2) |
| 3–4 US names, each hostile | P17 SIFY (**ADR**, Indian issuer, 1 ADR = 6 shares), P18 ONC (**ticker change + rename + redomicile**), P19 AMAL (**small-cap $1.39B + collides with an Indian symbol**), P20 SMR (**collides with an Indian symbol**) | 4 |

## Exclusions attested

- Source of truth: `docs/redesign/verification/r15/stage0/BATTERY_EXCLUSIONS.txt` (130 entries,
  assembled 2026-09-19 from the R13 run-state exclusion list + the R13 probe names
  KIRIINDUS / TIRUMALCHM / ORIENTBELL / GOKEX / IOC / PFC + the full R13 SELECTED set
  P1–P12 BMW, BABA, META, NHL, GEE, CDG, BI, SIL, UFO, PML, TI, RBA and spares TCI, ADOR,
  PVP, APEX, DEN + R11/R12 batteries + KSE and 509470).
- **Every symbol and every BSE code in this manifest was checked programmatically against that
  file: zero overlap.** Re-run the check with:

  ```
  python3 - <<'PY'
  import json, pathlib
  root = pathlib.Path("docs/redesign/verification/r15")
  excl = set((root / "stage0/BATTERY_EXCLUSIONS.txt").read_text().split())
  names = json.loads((root / "battery/manifest.json").read_text())["names"]
  hits = [n["slot"] + ":" + t for n in names for t in (n["symbol"], n.get("bse_code") or "") if t and t in excl]
  print("OVERLAP:", hits or "none")
  PY
  ```

- The 24 names are also disjoint from the R13 SELECTED set by construction: no R13 name and no
  R13 BSE code appears here.

## World gaps (recorded, never fabricated)

| Slot | Missing | What was tried |
| --- | --- | --- |
| P15 SUMAX | Current price, market cap, BSE/ISIN identifiers, NSE Emerge series code | Listing facts (date 2026-09-02, ₹111 listing vs ₹101 issue, ₹53.4 cr issue) confirmed via search. Per-name quote pages for Emerge SME names are thin and screener.in coverage of Emerge names is inconsistent; not collected rather than guessed |
| P20 SMR (NuScale) | A single agreed price | Two figures for mid-Sep-2026 came back in one search ($8.45, −7% and $10.21, −5.55%). **Recorded as a conflict, not reconciled** — a useful diff target in itself |
| S2 SMR Jewels | Exact listing date | Price/mcap/financials collected. The scrip code (544774) and 2026-vintage ISIN place the listing in 2026; the precise date was not confirmed and is not guessed |
| S4 TTC | Live price and market cap | screener.in host-verification failure on the fetch for scrip 544303; master row confirmed locally |
| P18 ONC | Current price and market cap | Revenue/income figures and the full identity history collected; a live quote was not fetched |
| P19 AMAL (US) | Reconciled price/ATH | Two figures from the same search conflict ($49.17 on 2026-09-04 vs an "all-time high $47.89 on 2026-07-01"). **Recorded as a conflict, not reconciled** — this is itself a useful diff target |
| P17 SIFY | Single authoritative market cap | Three sources give $989.09M / $897.87m / $789M. Recorded as a spread, not averaged |

## Sources

Masters (local, read-only): `sidecar/services/resolver_masters/bse_instruments.json`
(`_generated` 2026-06-09), `nse_instruments.json` (2026-06-05), `us_instruments.json`.

Outside truth, all fetched 2026-09-18/19:

- screener.in company pages: [539681](https://www.screener.in/company/539681/),
  [538868](https://www.screener.in/company/538868/),
  [544257](https://www.screener.in/company/544257/),
  [544546](https://www.screener.in/company/544546/),
  [544426](https://www.screener.in/company/544426/),
  [516078](https://www.screener.in/company/516078/),
  [500298](https://www.screener.in/company/500298/),
  [506597](https://www.screener.in/company/506597/),
  [542446](https://www.screener.in/company/542446/),
  [ELCIDIN](https://www.screener.in/company/ELCIDIN/),
  [VIYASH](https://www.screener.in/company/VIYASH/),
  [FUSION](https://www.screener.in/company/FUSION/),
  [DHANBANK](https://www.screener.in/company/DHANBANK/),
  [511413](https://www.screener.in/company/511413/),
  [531950](https://www.screener.in/company/531950/)
- Juniper Green Energy listing + symbol:
  [Business Today JNPR](https://www.businesstoday.in/stocks/juniper-green-energy-ltd-jnpr-share-price-547999),
  [chittorgarh IPO page](https://www.chittorgarh.com/ipo/juniper-green-energy-ipo/2492/),
  [screener JNPR](https://www.screener.in/company/JNPR/consolidated/)
- Dhoot Transmission listing + identifiers:
  [BSE quote page (scrip 544867)](https://www.bseindia.com/stock-share-price/dhoot-transmission-ltd/dhoottrans/544867),
  [trendlyne DHOOTTRANS](https://trendlyne.com/equity/3612273/DHOOTTRANS/dhoot-transmission-ltd/),
  [chittorgarh IPO page](https://www.chittorgarh.com/ipo/dhoot-transmission-ipo/2859/)
- Sequent → Viyash rename circular:
  [NSE circular, symbol change effective 2026-01-23](https://rhnvrm.github.io/stock-market-circulars/circulars/nse/2026/nse-2026-01-19-af3b07e9de837f6c-change-in-name-and-symbol-of-sequent-scientific-limited/)
- Jonjua bonus 7:24: [india-ipo bonus note](https://www.indiaipo.in/news/detail/724-bonus-share-by-small-cap-record-date-soon-check-expected-trading-date),
  [screener 542446](https://www.screener.in/company/542446/)
- Sumax Engineering NSE Emerge listing:
  [5paisa listing report](https://www.5paisa.com/blog/sumax-engineering-ipo-listing),
  [ANI announcement](https://aninews.in/news/business/sumax-engineering-limited-announces-ipo-on-nse-emerge-to-fund-new-manufacturing-capacity-bidding-opens-august-2520260824124225/),
  [IPO Watch](https://ipowatch.in/sumax-engineering-ipo/)
- SME IPO calendar (Aug–Sep 2026): [IPO Watch SME list](https://ipowatch.in/upcoming-sme-ipo-list/)
- US names: [Morningstar SIFY](https://www.morningstar.com/stocks/xnas/sify/quote),
  [Hargreaves Lansdown SIFY ADR ratio](https://www.hl.co.uk/shares/shares-search-results/s/sify-technologies-ltd-adr-each-repr-6-ords/company-information),
  [BeOne Medicines (Wikipedia, ticker/redomicile history)](https://en.wikipedia.org/wiki/BeOne_Medicines),
  [BeOne IR](https://ir.beonemedicines.com/),
  [Amalgamated Financial (Morningstar)](https://www.morningstar.com/stocks/xnas/amal/quote),
  [TradingView NASDAQ:AMAL](https://www.tradingview.com/symbols/NASDAQ-AMAL/),
  [stockanalysis NuScale SMR](https://stockanalysis.com/stocks/smr/),
  [TipRanks SMR market cap](https://www.tipranks.com/stocks/smr/market-cap),
  [NuScale investor stock information](https://www.nuscalepower.com/investors/stocks)
- SMR Jewels: [screener 544774](https://www.screener.in/company/544774/)
