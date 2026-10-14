# DS-1 — US/India ticker collisions (investor adversary, head d38b5d1a)

Stack: candidate built binaries (final-cand/src-tauri/binaries), main :52810 on a clean stranger profile,
openbb-mcp :52811, sec-edgar-mcp :52812. Targets unchanged since 6bc6d378: sidecar/routers/fundamentals.py
(`/{symbol}`, `/income|balance|cashflow`), sidecar/routers/quotes.py, sidecar/app.py `_RegionMiddleware` (:216), sidecar/routers/resolve.py.

## Commands
- `python3 scratchpad/inv/ds1.py` — for DAL CHTR SAFE CSL ICON AMAL SMR TTC x X-Vysted-Region {IN, US}:
  GET /resolve?q=S, /quotes/S, /fundamentals/S, /fundamentals/S/income (Origin http://localhost:5173).
  Raw: raw/investor/ds1.json, summary raw/investor/ds1-summary.txt.
- `python3 scratchpad/inv/ds1b.py` — exchange-qualified DAL.BO CHTR.BO AMAL.NS AMAL.BO SMR.BO TTC.BO CSL.BO ICON.BO SAFE.BO
  under BOTH regions (quote, fundamentals, income/balance under the US header). Raw: raw/investor/ds1b.json.

## Outside world
- screener.in (raw/investor/ds1-screener.json): https://www.screener.in/company/<bse_code>/ for 539681 (Dynamic Archistructures,
  "Market Cap ₹ 25.0 Cr. Current Price ₹ 49.9"), 544546 (Chatterbox, Mar 2025 revenue 59.13 Cr, Mar 2026 84.22),
  544257 (Sodhani, 3.55 / 3.65), 538868 (Continental Sec, Mar 2026 3.94), 544426 (Icon Facilitators 58.06 / 64.22),
  506597 / AMAL consolidated (Amal Ltd, "Market Cap ₹ 868 Cr.", "Current Price ₹ 702", Mar 2025 135, Mar 2026 240),
  544774 (SMR Jewels, Mar 2024 125, Mar 2025 263), 544303 (Toss The Coin, 8.63 / 14.67).
- SEC EDGAR https://www.sec.gov/files/company_tickers.json: DAL=DELTA AIR LINES (CIK 27904), CHTR=CHARTER COMMUNICATIONS,
  SAFE=Safehold Inc., CSL=CARLISLE COMPANIES, ICON=Icon Energy Corp, AMAL=Amalgamated Financial Corp., SMR=NUSCALE POWER, TTC=TORO CO.
- BSE api (api.bseindia.com getScripHeaderData 539681) answered Akamai "Access Denied" from this host; screener used instead.

## Read-back (excerpt of ds1-summary.txt)
Under IN every bare symbol resolves to the BSE/NSE company and quote/fundamentals/income are that company's, in INR, at
crore scale matching screener (e.g. CHTR IN income 2025-03-31 591,258,000 = 59.1 Cr; ICON IN 580,639,000 / 642,427,000;
SMR IN 1,244,698,000 / 2,632,469,000; AMAL.NS income 2026-03-31 2,393,708,000 = 239 Cr consolidated). Under US every bare
symbol resolves to the SEC registrant (Delta 52.67 bn, Charter 51.36 bn, Toro 4.51 bn ...), USD. Exchange-qualified
.BO/.NS under the US header stay Indian (DAL.BO US -> Dynamic Archistructures INR; AMAL.NS US -> Amal Ltd INR).
Quotes match screener within the as-of skew (CHTR 33.01 vs 33.0, CSL 21.97 vs 22.0, SMR 93.05 vs 93.0, AMAL 702.4 vs 702).
DAL IN (no trade since 2025-03-12): quote freshness "stale" with timestamp 2025-03-12; 52w high/low withheld "no trades in
52 weeks (last trade 2025-03-12)"; P/E 5.60 status "flagged" with the reason quoting the 24.5 the filing implies; EPS served
from the BSE filing (2.05). No cross-company figures anywhere: R15-DATA-001 / R15-CODE-DATA-001 hold.
Bare AMAL under IN binds NSE Amal with needs_disambiguation false although a US AMAL candidate at confidence 1.0 is listed:
that is R15-DATA-002 (blocked_tier4, bare-ticker region binding) — attached, not new.

## Defect found: investor:1 (medium) — regression of R15-DATA-048
GET /fundamentals/AMAL (X-Vysted-Region IN; the default bind, AMAL.NS) and GET /fundamentals/AMAL.NS:
`market_cap: null`, field_meta.market_cap `{"status":"unavailable","reason":"provider did not publish this field"}`,
`shares_outstanding: null` (same reason) — while the SAME company's BSE listing in the same sidecar,
GET /fundamentals/AMAL.BO, serves `market_cap 8,690,951,168` (₹869 Cr, screener ₹868 Cr) and `shares_outstanding 12,362,662`,
both rows carrying ISIN INE841D01013 in /resolve. The NSE payload also holds eps 24.02 and net_income_ttm 297,070,016
(shares = NI/EPS = 12.37 M). sidecar/services/yfinance_provider.py:749-752 derives market cap only from the Yahoo
`shares_outstanding` of the same listing; nothing reuses the sibling listing's share count or NI/EPS. R15-DATA-048 (fixed,
f407107) named exactly this: "market cap ... stay 'unavailable' whenever Yahoo omits them, though the app already holds the
ingredients (... price, master share count)". A ₹868 Cr NSE company — the default listing a stranger in IN gets — shows no
market cap. Severity medium (R2: a gap a demanding owner hits in normal use; blank with a stated reason, never wrong).

VERDICT DS-1: finding investor:1
