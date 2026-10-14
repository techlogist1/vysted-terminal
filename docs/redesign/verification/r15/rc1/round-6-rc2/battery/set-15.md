# Set: batch-5/W1-india-disclosures-agent-surface (set-15) — candidate ace7dd76, sidecar :52340

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-020 | in-process _nse_row_to_announcement/_bse_row_to_announcement on the two RELIANCE fixtures + _dedup_key; live HDFCBANK announcements | keys equal ('RELIANCE','911b3457c59ed144','2026-06-09'), COLLAPSES: True; live merged feed 40 rows (33 NSE/7 BSE) | holds |
| R15-DATA-023 | GET /disclosures/shareholding DAL, CSL, ADANIENT | promoter_pledged_percent+basis: DAL 0.0 filed, CSL 0.0 filed, ADANIENT 0.79 filed (live route now serves it; raw R15-DATA-023.txt is a first probe with wrong key names, superseded by -live-* files) | holds |
| R15-DATA-024 | GET /disclosures/deals KOPRAN, ADANIENT, CCDL | KOPRAN 125 deals (bulk), ADANIENT 77 (bulk+block), CCDL 107 incl. BSE bulk | holds |
| R15-DATA-025 | GET /disclosures/corporate-actions JONJUA, ELCIDIN, AMAL | JONJUA bonus 7:24 rec 2026-09-04 + 5:40 rec 2026-01-23; ELCIDIN Rs25 dated, NSE+BSE deduped; AMAL Rs1.50 ex 2026-07-31 | holds |
| R15-DATA-056 | GET /disclosures/shareholding CREST, VERTEX, TTC | CREST dii 0.0 derived; VERTEX fii=dii=0.0 derived; TTC fii 0.0 derived | holds |
| R15-AGENT-060 | in-process shareholding_pattern CREST | no 'note' key; fii 1.71 / dii 0.0 / split_source BSE | holds |
| R15-AGENT-062 | in-process price_data AAPL | bars_returned 90, bars_available 125, window_start present | holds |
| R15-AGENT-058 | in-process market_overview with news_provider.fetch_news raising ProviderError | ok:true, headlines [], headlines_error 'news feed unavailable: all news sources failed' | holds |
| R15-CODE-RESEARCH-001 | depth profiles + deep_research._clamp(360,30,max(300,360),360) | deep 180, ultra 360, clamp returns 360 (was 300) | holds |
| R15-DATA-074 | in-process corporate_announcements tool x3 for RELIANCE counting get_announcements | 1 underlying fetch across 3 calls | holds |
| R15-DATA-026 | GET /fundamentals/DHANBANK/income?period=quarterly | periods 2026-06-30 (Q1 FY27) .. 2025-03-31 | holds |
| R15-AGENT-020 | in-process _build_local_tools read_notes + preamble; frontend half pinned by ChatSidebar.test.tsx:632 / context-provider.test.ts:323 | read_notes(BDL) returns the note; preamble names it. Frontend send half not run (no vitest in this lane) | holds |

COVERAGE: 12/12 ids raw; no raw: none
