# R13 Long-Tail Validation Battery — Manifest

Collection timestamp: **2026-07-10T10:07:46Z** (all reference packs date-stamped with this `collected_at`; individual data points carry their own `as_of`).
Reference packs: `docs/redesign/verification/r13/battery/reference-packs/<SYMBOL>.json` (17 files).
All 17 names verified present in the app's bundled masters (`sidecar/services/resolver_masters/nse_instruments.json`, `bse_instruments.json`) — symbol, BSE code, and ISIN in each pack match the master rows byte-for-byte.

## Battery table

| # | Role | Symbol | Exchange | BSE code | Mcap (₹ Cr, as-of in pack) | Tier | Sector | Why hostile |
|---|------|--------|----------|----------|------|------|--------|-------------|
| 1 | P1 | BMW | BSE only | 542669 | 1,216 | small | Metals / steel processing | BSE-only + collision: bare "BMW" is 100% Bayerische Motoren Werke AG on the open web |
| 2 | P2 | BABA | BSE only | 532380 | 88 | micro | Media / film IP | BSE-only, group X (trade-to-trade) + collision: bare "BABA" is 100% Alibaba (NYSE: BABA); mid-open-offer (Skybridge Interactive), figures moving; former name Galaxy Multimedia |
| 3 | P3 | META | BSE only | 534535 | 811 | small | IT / Web3-GameFi | BSE-only, group T + collision: bare "META" is 100% Meta Platforms; renamed from Bio Green Papers (Apr 2025); Jun-2026 bonus issue reset share count |
| 4 | P4 | NHL | BSE only | 544245 | 29 | micro (SME) | Travel & tourism | BSE-only, SME group M, 165 shareholders, Sep-2024 IPO + collision: bare "NHL" is 100% National Hockey League; thinnest coverage in battery |
| 5 | P5 | GEE | BSE only | 504028 | 546 | small | Capital goods / welding consumables | BSE-only, group X illiquid; numeric-scrip-identified in practice — screener/press address it as 504028, not "GEE"; former name General Electrodes and Equipments |
| 6 | P6 | CDG | BSE only | 534796 | 265 | micro | Chemicals/diversified → logistics | BSE-only, group XT + collision: bare "CDG" is Charles de Gaulle Airport / Comme des Garçons; numeric-scrip-identified (534796); RENAMED to Jujhar Logistics Ltd effective 2026-07-02 — 8 days before collection, aggregators not caught up; name lineage Pankaj Polypack → Urbaknitt Fabs → CDG Petchem → Jujhar Logistics |
| 7 | P7 | BI | NSE+BSE | 526853 | 147 | micro | Industrials / pharma packaging | 2-char ticker, multi-entity collision (Bank Indonesia, Power BI, Biogen, KOSDAQ Bi Matrix); distressed history: 2013 default → 2019 NCLT → 2023 settlement |
| 8 | P8 | SIL | NSE+BSE | 530017 | 107 | micro | Trading / diversified (est. 1892) | Collision: bare "SIL stock" is 100% Global X Silver Miners ETF; legal name shadowed by the famous US "Standard Industries" (GAF) conglomerate; former name Standard Mills; loss-making (PE null) |
| 9 | P9 | UFO | NSE+BSE | 539141 | 271 | micro | Media / digital cinema | Common-word collision (bare "UFO" = alien phenomena); pledged promoter holding; small-cap with real quarterly variance across sources |
| 10 | P10 | PML | NSE+BSE | 539113 | 150 | micro | Financial services / forex & remittance | No name collision (verified — hypothesis rejected); hostile via data-quality trap: PE spread 0.59x–51.06x across sources from one-off ₹259.69 Cr gold-loan-sale gain; Q4-only results unpublished |
| 11 | P11 | TI | NSE+BSE | 507205 | 11,089 | MID (contrast) | Alcoholic beverages | Collision: bare "TI stock" is 100% Texas Instruments; subtle tier: reported FY26 PAT ₹20.9 Cr vs adjusted ~₹232 Cr (Imperial Blue one-offs), Q4 was a net loss |
| 12 | P12 | RBA | NSE+BSE | 543248 | 4,236 | MID (contrast) | QSR (Burger King India/Indonesia) | Multi-entity collision: bare "RBA" is Reserve Bank of Australia + NYSE:RBA (RB Global); loss-making (PE null everywhere); live ownership churn: promoter down to 9.22% amid Lenexis open offer |
| 13 | S1 | TCI | NSE+BSE | 532349 | 7,198 | mid (spare) | Logistics / multimodal | Live ticker collision with currently-trading NYSE:TCI (Transcontinental Realty) + historical Tele-Communications Inc; sibling-confusion trap with TCI Express (different listed company) |
| 14 | S2 | ADOR | NSE+BSE | 517041 | 2,309 | small/mid boundary (spare) | Capital goods / welding | Boundary-mcap probe; former name Advani-Oerlikon (2003); cross-source price variance noted |
| 15 | S3 | PVP | NSE+BSE | 517556 | 721 | small (spare) | Real estate (+healthcare, film financing) | Multi-segment, unprofitable; PE null vs junk third-party PE 553 in the wild (aggregator-rejection probe); "PvP" common-acronym overlap |
| 16 | S4 | APEX | NSE+BSE | 540692 | 1,225 | small (spare) | Food processing / shrimp export | Generic-word ticker; dividend declared 30-May-2026 with per-share/record-date not yet in aggregators (declared-vs-paid probe) |
| 17 | S5 | DEN | NSE+BSE | 533137 | 1,394 | small (spare) | Communication services / cable & broadband | Common-word ticker; zero dividend since 2015 (yield-honesty probe); cross-source mcap variance |

P = primary (12), S = spare (5).

## Selection-criteria attestation

- **Count:** 17 names (12 primary + 5 spares) ≥ 16 required.
- **Small/micro-cap majority:** 13/17 under ₹2,000 Cr (10/12 primaries). Deliberate mid-cap contrast: TI (₹11,089 Cr), RBA (₹4,236 Cr), spare TCI (₹7,198 Cr); ADOR sits on the boundary (₹2,309 Cr).
- **BSE-only ≥ 4:** six — BMW, BABA, META, NHL, GEE, CDG. All six carry alphabetic BSE symbols (satisfies the alphabetic-symbol requirement several times over). **Numeric-scrip-only note:** the bundled BSE master carries an alphabetic symbol for every row (zero symbol-less entries — verified by scan), so a strictly symbol-less listing cannot exist in-master. The numeric-scrip class is covered by GEE (504028) and CDG (534796), whose canonical public identity is the numeric code (screener.in and most press address them only by scrip code; their screener URLs are numeric). Probe these two by BOTH the alphabetic symbol and the bare numeric code; for CDG the code is additionally the only stable handle across its 2026-07-02 rename.
- **Collision-class ≥ 3:** nine verified collisions among primaries — BMW→Bayerische Motoren Werke, BABA→Alibaba, META→Meta Platforms, NHL→National Hockey League, TI→Texas Instruments, SIL→Global X Silver Miners ETF (+ US Standard Industries), RBA→Reserve Bank of Australia (+ NYSE:RBA), CDG→Charles de Gaulle/Comme des Garçons, BI→multi-entity (Bank Indonesia/Power BI/Biogen); plus spare TCI→NYSE:TCI. Each verified by a bare-ticker web search on 2026-07-10: top results dominated by the foreign entity, zero front-page mentions of the Indian listing. One hypothesized collision (PML→Pakistan Muslim League) was tested and REJECTED — recorded as no-collision, PML kept for its data-quality traps instead.
- **Sector spread:** max 2 per sector (Capital Goods/welding: GEE+ADOR; everything else 1 each across steel, film media, Web3/IT, tourism, logistics-via-rename, pharma packaging, diversified trading, digital cinema, forex/financials, alco-bev, QSR, multimodal logistics, real estate, seafood export, cable). ≤ 3 satisfied.
- **Exclusion list:** all 17 symbols AND all 17 BSE codes checked programmatically against the full R13 exclusion list (prior batteries + tonight's probes, incl. KIRIINDUS/TIRUMALCHM/ORIENTBELL/GOKEX/IOC/PFC): **zero overlap**.
- **Master presence:** every name grep-verified in `nse_instruments.json` / `bse_instruments.json` (read-only); the six BSE-only names confirmed ABSENT from the NSE master.

## Reference-pack conventions

Each pack: identity block (symbol/exchanges/bse_code/isin/legal name/former names/sector), `collected_at` (fixed 2026-07-10T10:07:46Z), `collected_from` URLs, and a `reference` block — recent close (with as-of), mcap, PE, PB, ROE, dividend yield, declared-vs-paid note, 52w high/low, shareholding (promoter/FII/DII/public + quarter), latest quarterly results, recent filings, peers — every value carrying an as-of; nulls are backed by explicit `world_gaps` entries (genuinely unpublished fields), never fabricated. Sources: screener.in (primary), bseindia.com, trendlyne, moneycontrol, tickertape, exchange filings.

Known subtle-tier traps deliberately embedded in this battery (for gate scoring): CDG's 8-day-old rename; META's bonus-issue share-count reset; BABA's live open offer; RBA's promoter collapse to 9.22% mid-open-offer; TI's reported-vs-adjusted PAT divergence; PML's one-off-gain PE spread; APEX's declared-but-not-yet-tabulated dividend; SIL's cross-source dividend-yield conflict (3.33% vs 1.6%, flagged unresolved); NHL's SME-thin world (Q4-only figures genuinely unpublished).
