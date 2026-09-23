# R15 Battery Diff Summary

24 battery slots diffed (943 fields total) against outside sources. Every field is one of `match`, `mismatch`, `app blank`, `no source truth`, `definitional difference`, `as-of skew`, or `not collected`. "Subtle tier" fields are the spec-mandated set (per `COMMON.md`/`PROMPT_data_s2.md`) covering things like as-of dates on 52-week highs/lows and zero-is-a-real-value cases — the gameable, easy-to-fake-plausible class of field, tracked separately from the rest.

## Overall field-status tally

| status | all fields | subtle-tier fields | normal fields |
|---|---|---|---|
| app blank | 249 | 9 | 240 |
| as-of skew | 25 | 0 | 25 |
| definitional difference | 62 | 0 | 62 |
| match | 367 | 0 | 367 |
| mismatch | 120 | 2 | 118 |
| no source truth | 115 | 0 | 115 |
| not collected | 5 | 0 | 5 |

**2 subtle-tier mismatches** vs **118 normal-field mismatches** — the subtle tier mismatches at a materially higher rate per field than the rest, consistent with its design as the gameable-field sweep.

**115 "no source truth" cells** — fields where no outside source could be reached to compare against (recorded honestly, not treated as a pass).

## Per-slot

| slot | symbol | fields | match | mismatch | app blank | no source truth | subtle mismatches | DAT raw ids |
|---|---|---|---|---|---|---|---|---|
| P10 | VIYASH | 34 | 20 | 1 | 6 | 4 | 0 | DAT-P10-1, DAT-P10-2, DAT-P10-3, DAT-P10-4, DAT-P10-5 |
| P11 | FUSION | 44 | 19 | 2 | 10 | 6 | 0 | DAT-P11-1, DAT-P11-2, DAT-P11-3, DAT-P11-4 |
| P12 | DHANBANK | 40 | 22 | 1 | 6 | 7 | 0 | DAT-P12-1, DAT-P12-2, DAT-P12-3, DAT-P12-4, DAT-P12-5 |
| P13 | ELCIDIN | 38 | 10 | 0 | 25 | 2 | 0 | DAT-P13-1, DAT-P13-2, DAT-P13-3, DAT-P13-4, DAT-P13-5, DAT-P13-6, DAT-P13-7, DAT-P13-8, DAT-P13-9, DAT-P13-10, DAT-P13-11, DAT-P13-12, DAT-P13-13, DAT-P13-14, DAT-P13-15, DAT-P13-16, DAT-P13-17, DAT-P13-18, DAT-P13-19, DAT-P13-20, DAT-P13-21, DAT-P13-22, DAT-P13-23, DAT-P13-24, DAT-P13-25 |
| P14 | JONJUA | 38 | 18 | 5 | 8 | 5 | 0 | DAT-P14-1, DAT-P14-2, DAT-P14-3, DAT-P14-4, DAT-P14-5, DAT-P14-6, DAT-P14-7 |
| P15 | SUMAX | 39 | 2 | 2 | 28 | 7 | 0 | DAT-P15-1, DAT-P15-2, DAT-P15-3, DAT-P15-4, DAT-P15-5 |
| P16 | CREST | 37 | 19 | 2 | 6 | 3 | 0 | DAT-P16-1, DAT-P16-2, DAT-P16-3, DAT-P16-4, DAT-P16-5, DAT-P16-6 |
| P17 | SIFY | 45 | 15 | 3 | 13 | 5 | 0 | DAT-P17-1, DAT-P17-2, DAT-P17-3, DAT-P17-4, DAT-P17-5, DAT-P17-6 |
| P18 | ONC | 40 | 18 | 4 | 8 | 7 | 0 | DAT-P18-1, DAT-P18-2, DAT-P18-3, DAT-P18-4, DAT-P18-5, DAT-P18-6 |
| P19 | AMAL | 33 | 1 | 22 | 6 | 4 | 1 | DAT-P19-1, DAT-P19-2, DAT-P19-3, DAT-P19-4, DAT-P19-5 |
| P1 | JNPR | 43 | 14 | 4 | 18 | 4 | 0 | DAT-P1-1, DAT-P1-2, DAT-P1-3, DAT-P1-4, DAT-P1-5 |
| P20 | SMR | 41 | 5 | 21 | 8 | 7 | 1 | DAT-P20-1 |
| P2 | DAL | 37 | 16 | 7 | 10 | 2 | 0 | DAT-P2-1, DAT-P2-2, DAT-P2-3, DAT-P2-4, DAT-P2-5, DAT-P2-6, DAT-P2-7, DAT-P2-8, DAT-P2-9 |
| P3 | CHTR | 40 | 16 | 4 | 5 | 4 | 0 | DAT-P3-1, DAT-P3-2, DAT-P3-3, DAT-P3-4, DAT-P3-5 |
| P4 | SAFE | 39 | 23 | 5 | 5 | 5 | 0 | DAT-P4-1, DAT-P4-2, DAT-P4-3, DAT-P4-4, DAT-P4-5, DAT-P4-6, DAT-P4-7, DAT-P4-8 |
| P5 | CSL | 38 | 16 | 1 | 16 | 3 | 0 | DAT-P5-1, DAT-P5-2 |
| P6 | ICON | 49 | 23 | 4 | 13 | 5 | 0 | DAT-P6-1, DAT-P6-2, DAT-P6-3, DAT-P6-4, DAT-P6-5, DAT-P6-6, DAT-P6-7, DAT-P6-8, DAT-P6-9, DAT-P6-10 |
| P7 | JUMBO | 35 | 14 | 2 | 7 | 6 | 0 | DAT-P7-1, DAT-P7-2, DAT-P7-3, DAT-P7-4, DAT-P7-5, DAT-P7-6 |
| P8 | NAPEROL | 42 | 18 | 5 | 5 | 8 | 0 | DAT-P8-1, DAT-P8-2, DAT-P8-3, DAT-P8-4, DAT-P8-5, DAT-P8-6, DAT-P8-7 |
| P9 | AMAL | 39 | 15 | 6 | 10 | 4 | 0 | DAT-P9-1, DAT-P9-2, DAT-P9-3, DAT-P9-4, DAT-P9-5, DAT-P9-6, DAT-P9-7, DAT-P9-8 |
| S1 | DHOOTTRANS | 28 | 8 | 7 | 7 | 2 | 0 | DAT-S1-1, DAT-S1-2, DAT-S1-3, DAT-S1-4, DAT-S1-5, DAT-S1-6, DAT-S1-7, DAT-S1-8 |
| S2 | SMR | 42 | 18 | 3 | 15 | 3 | 0 | DAT-S2-1, DAT-S2-2, DAT-S2-3, DAT-S2-4, DAT-S2-5, DAT-S2-6, DAT-S2-7, DAT-S2-8, DAT-S2-9 |
| S3 | VERTEX | 37 | 17 | 5 | 5 | 7 | 0 | DAT-S3-1, DAT-S3-2, DAT-S3-3, DAT-S3-4, DAT-S3-5, DAT-S3-6, DAT-S3-7 |
| S4 | TTC | 45 | 20 | 4 | 9 | 5 | 0 | DAT-S4-1, DAT-S4-2, DAT-S4-3, DAT-S4-4, DAT-S4-5, DAT-S4-6, DAT-S4-7, DAT-S4-8, DAT-S4-9, DAT-S4-10 |

## Mismatches by slot, subtle tier called out

### P10 VIYASH — `r15/battery/diffs/P10_VIYASH.json`

- mismatches (1, **bold** = subtle tier): net_profit_ttm
- no source truth (4): week52.high_date / week52.low_date, shareholding.pledged_pct_of_promoter, latest_results.filing_date, latest_results.reported_consolidated (sales/op profit/net profit/eps)

### P11 FUSION — `r15/battery/diffs/P11_FUSION.json`

- mismatches (2, **bold** = subtle tier): revenue_ttm, week52.low
- no source truth (6): identity.listing_date, roe, dividend.last_declared_record_or_ex_date, week52.high.as_of_date, week52.low.as_of_date, shareholding.pledged_pct_of_promoter

### P12 DHANBANK — `r15/battery/diffs/P12_DHANBANK.json`

- mismatches (1, **bold** = subtle tier): shareholding.fundamentals.held_percent_insiders (Equity Overview 'Insiders' field)
- no source truth (7): identity.listing_date, price.day_range (high/low), debt_to_equity, dividend.last_declared_per_share (+ record/ex date), week52.dates (high/low made-on dates), shareholding.pledged_pct_of_promoter, consolidated_vs_standalone

### P13 ELCIDIN — `r15/battery/diffs/P13_ELCIDIN.json`

- no source truth (2): identity.listing_date_bse, shareholding.pledged_pct_of_promoter

### P14 JONJUA — `r15/battery/diffs/P14_JONJUA.json`

- mismatches (5, **bold** = subtle tier): identity.sector, identity.industry, revenue_ttm (+ as-of date), net_profit_ttm (+ as-of date), shareholding.fundamentals.held_percent_insiders (Equity Overview 'Insiders' field)
- no source truth (5): identity.former_names, shareholding.fii_pct, shareholding.dii_pct, shareholding.pledged_pct_of_promoter, consolidated_vs_standalone

### P15 SUMAX — `r15/battery/diffs/P15_SUMAX.json`

- mismatches (2, **bold** = subtle tier): identity.legal_name, resolve(company name search)
- no source truth (7): identity.former_names, identity.isin, identity.nse_series, dividend.last_declared_per_share, week52.dates (high and low), shareholding.pledged_pct_of_promoter, consolidated_vs_standalone

### P16 CREST — `r15/battery/diffs/P16_CREST.json`

- mismatches (2, **bold** = subtle tier): shareholding.promoter_pct (fundamentals held_percent_insiders), consolidated_vs_standalone (basis disclosure)
- no source truth (3): identity.former_names, identity.listing_date, shareholding.pledged_pct_of_promoter

### P17 SIFY — `r15/battery/diffs/P17_SIFY.json`

- mismatches (3, **bold** = subtle tier): identity.resolve_by_company_name, revenue_ttm (as labeled: currency=USD), net_profit_ttm (as labeled: currency=USD)
- no source truth (5): roce, week52.as_of (date the extremum was actually set), shareholding.fii_pct, shareholding.dii_pct, shareholding.pledged_pct_of_promoter

### P18 ONC — `r15/battery/diffs/P18_ONC.json`

- mismatches (4, **bold** = subtle tier): market_cap, pe_forward, shareholding.insider_ownership_pct (nearest US equivalent to promoter_pct), shareholding.institutional_ownership_pct
- no source truth (7): week52.high_date / week52.low_date, shareholding.promoter_pct, shareholding.fii_pct, shareholding.dii_pct, shareholding.public_pct, shareholding.pledged_pct_of_promoter, consolidated_vs_standalone

### P19 AMAL — `r15/battery/diffs/P19_AMAL.json`

- mismatches (22, **bold** = subtle tier): identity.legal_name, identity.isin, identity.bse_code, identity.board / exchange tier, identity.sector / identity.industry, price.last_close, market_cap, pe_ttm, pb, roe (ttm), debt_to_equity, revenue_ttm, net_profit_ttm, revenue_growth_yoy, eps_ttm, book_value_per_share, dividend.last_declared_per_share, dividend.paid_trailing_12m_per_share, dividend.yield, **week52.high**, week52.low, last_3_announcements
- no source truth (4): identity.nse_symbol, roce, shareholding.quarter / promoter_pct / fii_pct / dii_pct / public_pct, shareholding.pledged_pct_of_promoter

### P1 JNPR — `r15/battery/diffs/P1_JNPR.json`

- raw findings: 5 findings (DAT-P1-1..5): 2 high (shareholding/announcements/results endpoint failure + institutional-holding mismatch; eps_ttm/pe_ttm internal inconsistency), 2 medium (book_value_per_share/pb internal inconsistency; roe/roce null despite derivable inputs), 1 low (52-week high/low as-of dates not surfaced).
- mismatches (4, **bold** = subtle tier): pb, eps_ttm, book_value_per_share, shareholding.institutions_combined (fii_pct+dii_pct, cross-checked against the app's fundamentals proxy)
- no source truth (4): identity.former_names.rename_date, dividend.record_date, dividend.ex_date, shareholding.pledged_pct_of_promoter

### P20 SMR — `r15/battery/diffs/P20_SMR.json`

- mismatches (21, **bold** = subtle tier): identity.legal_name, identity.former_names, identity.isin, identity.bse_code, identity.sector, identity.industry, price.last_close, market_cap, pe_ttm, pb, roe, debt_to_equity, revenue_ttm, net_profit_ttm, eps_ttm, book_value_per_share, dividend.paid_trailing_12m_per_share, dividend.yield, **week52.high**, week52.low, last_3_announcements
- no source truth (7): roce, shareholding.promoter_pct (latest filed quarter), shareholding.fii_pct, shareholding.dii_pct, shareholding.public_pct, shareholding.pledged_pct_of_promoter, shareholding.as_of_quarter

### P2 DAL — `r15/battery/diffs/P2_DAL.json`

- mismatches (7, **bold** = subtle tier): price.last_close (as_of date), market_cap (as_of date), pe_ttm, revenue_ttm (fundamentals endpoint), revenue_ttm / net_profit_ttm (income-statement endpoint), eps_ttm, week52.low
- no source truth (2): corporate_actions_2026, consolidated_vs_standalone

### P3 CHTR — `r15/battery/diffs/P3_CHTR.json`

- mismatches (4, **bold** = subtle tier): pe_ttm, revenue_growth_yoy, eps_ttm, financial_statements (income/balance/cashflow)
- no source truth (4): identity.listing_date, dividend.record_date, dividend.ex_date, shareholding.pledged_pct_of_promoter

### P4 SAFE — `r15/battery/diffs/P4_SAFE.json`

- mismatches (5, **bold** = subtle tier): identity.sector_and_industry, roe, revenue_ttm (income-statement endpoint), net_profit (income-statement endpoint), shareholding.insiders_pct (/fundamentals main endpoint, held_percent_insiders)
- no source truth (5): roce, face_value, shareholding.dii_pct (Sep-2025), shareholding.pledged_pct_of_promoter, consolidated_vs_standalone

### P5 CSL — `r15/battery/diffs/P5_CSL.json`

- mismatches (1, **bold** = subtle tier): revenue_ttm / net_profit_ttm via /fundamentals/{symbol}/income and /cashflow (statement lines, not the scalar fields above)
- no source truth (3): identity.listing_date, shareholding.promoter_and_promoter_group_detail (held_percent_insiders cross-check), consolidated_vs_standalone

### P6 ICON — `r15/battery/diffs/P6_ICON.json`

- mismatches (4, **bold** = subtle tier): pe_ttm, eps_ttm, last_3_announcements[0].headline, fundamentals.income/balance/cashflow statements (bonus, non-pack field)
- no source truth (5): identity.isin, identity.industry, shareholding.pledged_pct_of_promoter, last_3_announcements[2].url_guid, consolidated_vs_standalone

### P7 JUMBO — `r15/battery/diffs/P7_JUMBO.json`

- mismatches (2, **bold** = subtle tier): eps_ttm, book_value_per_share
- no source truth (6): identity.former_names, identity.board, identity.listing_date, dividend.last_declared_per_share, shareholding.fii_pct, shareholding.pledged_pct_of_promoter

### P8 NAPEROL — `r15/battery/diffs/P8_NAPEROL.json`

- mismatches (5, **bold** = subtle tier): identity.sector, identity.industry, dividend.last_declared_per_share, shareholding.promoter_pct (fundamentals/held_percent_insiders, yfinance), shareholding.institutions_pct (fundamentals/held_percent_institutions, yfinance)
- no source truth (8): identity.listing_date, roce, face_value, shares_outstanding, dividend.record_or_ex_date, dividend.paid_trailing_12m_per_share, shareholding.pledged_pct_of_promoter, latest_results.filing_date

### P9 AMAL — `r15/battery/diffs/P9_AMAL.json`

- mismatches (6, **bold** = subtle tier): identity.exchange_venues (NSE second listing), shareholding.promoter_pct (fundamentals held_percent_insiders, yfinance-sourced), shareholding.dii_pct (fundamentals held_percent_institutions, yfinance-sourced), income statement (all line items), balance sheet (all line items), cash flow statement (all line items)
- no source truth (4): identity.former_names, revenue_growth_yoy, shareholding.fii_pct, shareholding.pledged_pct_of_promoter

### S1 DHOOTTRANS — `r15/battery/diffs/S1_DHOOTTRANS.json`

- mismatches (7, **bold** = subtle tier): price.change / change_percent (implied previous_close), pe_ttm, pb / book_value_per_share, earnings_growth (same growth_basis='mrq_yoy'), eps_ttm, every fundamentals field's as_of (systemic), shareholding (fallback: fundamentals.held_percent_insiders / held_percent_institutions)
- no source truth (2): dividend.last_declared_per_share / paid_trailing_12m_per_share, consolidated_vs_standalone basis disclosure

### S2 SMR — `r15/battery/diffs/S2_SMR.json`

- mismatches (3, **bold** = subtle tier): pe_ttm, eps_ttm, financials_detail (income/balance/cashflow statements)
- no source truth (3): pb, book_value_per_share, shareholding.pledged_pct_of_promoter

### S3 VERTEX — `r15/battery/diffs/S3_VERTEX.json`

- mismatches (5, **bold** = subtle tier): shares_outstanding, book_value_per_share, pb, eps_ttm, shareholding.promoter_pct (fundamentals.held_percent_insiders)
- no source truth (7): revenue_growth_yoy, face_value, dividend.last_declared_per_share, shareholding.fii_pct, shareholding.pledged_pct_of_promoter, corporate_actions_2026 (rights issue), consolidated_vs_standalone

### S4 TTC — `r15/battery/diffs/S4_TTC.json`

- mismatches (4, **bold** = subtle tier): shareholding.promoter_pct (fundamentals/held_percent_insiders, yfinance), shareholding.institutions_pct (fundamentals/held_percent_institutions, yfinance), latest_results.quarter / filing_date / reporting_regime, latest_results.annual_figures_inr_crore / half_yearly_figures_inr_crore (income statement)
- no source truth (5): dividend.last_declared_per_share, shareholding.pledged_pct_of_promoter, corporate_actions_2026.dividends, corporate_actions_2026.splits_bonus_rights, consolidated_vs_standalone_note

