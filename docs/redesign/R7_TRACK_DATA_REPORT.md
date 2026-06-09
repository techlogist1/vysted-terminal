# R7 Track D — Data track report (worktree-agent-r7-data)

## Component 1 — BSE completed (real scrip master + scrip-code routing)

### What shipped

- `sidecar/services/resolver_masters/regenerate_bse_master.py` — hardened
  regeneration tooling: `curl_cffi` Chrome TLS impersonation primary
  (`_fetch_once`, line 71) with an `httpx` desktop-UA fallback, 4 retry
  attempts with exponential backoff + jitter (`fetch_records`, line 111), and a
  1,000-row sanity floor (`build_master`, line 138) so a WAF refusal page can
  never overwrite the good committed master. Output rows are
  `[SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN, STATUS]`, market-cap ordered
  (prominence, mirroring the SEC ordering of `us_instruments.json`), one
  canonical row per ticker, emitted one-row-per-line with a dated header.
- `sidecar/services/resolver_masters/bse_instruments.json` — the REAL master,
  regenerated live once on 2026-06-09 (UTC) from a scratch invocation:
  **4,873 rows, every equity group incl. SME** (`_groups` census in the file
  header: B 1621, X 1296, A 724, XT 399, **M 327**, T 205, **MT 155**, Z 67,
  P 57 + small MS/ZP/TS/IP/Y/R tails). 412 KB. Carries `_generated`,
  `_source` and `_note` header keys.
- `sidecar/services/bse_provider.py` — scrip-code routing completed:
  - `get_history` (line 374) resolves ticker → numeric code from the master and
    locates each bhavcopy day's row by `FinInstrmId` via `_match_scrip`
    (line 406), ticker-string fallback only when the master carries no code.
  - `get_quote` (line 462) routes `getScripHeaderData` by the code (already
    did) and now threads the code into the bhavcopy fallback
    (`_quote_from_bhavcopy`, line 537) too.
  - Bhavcopy cache stays per-day; cold downloads stay bounded
    (`_MAX_COLD_DOWNLOADS = 8`); EQ-series preference retained
    (`_pick_equity_row`, line 247).
- Tests: `sidecar/tests/test_regenerate_bse_master.py` (new — script parsing/
  ordering/dedupe/sanity-floor/retry + shipped-master integrity incl. the
  ICONIKSPEV acceptance), `sidecar/tests/test_bse_provider.py` (rewritten
  around the REAL observed bhavcopy shape + code-routing/ticker-fallback
  cases), `test_provider_registry_region.py` / `test_history.py` moved off the
  fabricated TIRUPATI seed row (not in the live master) onto ICONIKSPEV.

### Observed endpoint shapes (live probes, 2026-06-09/10 IST, curl_cffi impersonate="chrome")

**ListOfScripData** —
`https://api.bseindia.com/BseIndiaAPI/api/ListOfScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active`
returns HTTP 200, ~1.7 MB, a bare JSON **list** (not `{"Table": [...]}`) of
4,873 records. One empty `Group=` call covers ALL groups incl. SME M/MT.
Observed record:

```json
{
  "SCRIP_CD": "511260",
  "Scrip_Name": "Iconik Sports And Events Ltd",
  "Status": "Active",
  "GROUP": "X",
  "FACE_VALUE": "10.00",
  "ISIN_NUMBER": "INE088P01015",
  "INDUSTRY": null,
  "scrip_id": "ICONIKSPEV",
  "Segment": "Equity",
  "NSURL": "https://www.bseindia.com/stock-share-price/iconik-sports-and-events-ltd/iconikspev/511260/",
  "Issuer_Name": "ICONIK SPORTS AND EVENTS LIMITED",
  "Mktcap": "145.83"
}
```

Group distribution observed: `{'B': 1621, 'X': 1296, 'A': 724, 'XT': 399,
'M': 327, 'T': 205, 'MT': 155, 'Z': 67, 'P': 57, 'MS': 6, 'ZP': 5, 'TS': 5,
'IP': 3, 'Y': 2, 'R': 1}`. No duplicate `scrip_id`s, no empty `scrip_id`s,
262 records without `Mktcap` (sorted to the tail).

**BhavCopy** —
`https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_20260609_F_0000.CSV`
returned HTTP 200, 829 KB, **plain CSV (not ZIP-wrapped)**, 4,856 data rows.
Header (34 cols):

```
TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,
FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,
LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,
TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4
```

Observed ICONIKSPEV row (2026-06-09): `FinInstrmId=511260, ISIN=INE088P01015,
TckrSymb=ICONIKSPEV, SctySrs=X, Opn=44.99, Hgh=44.99, Lw=42.31, Cls=43.09,
LastPric=43.48, PrvsClsgPric=44.44, TtlTradgVol=5757`. Note `SctySrs` carries
the GROUP (`X`) for non-EQ tiers — the EQ-preference falls back to the (unique)
code-matched row, as designed.

### Live smoke (scratch invocation — the once-only live run)

```
history: bse ICONIKSPEV bars: 7
   2026-06-05 44.2 45.68 44.2 45.1 1327.0
   2026-06-08 44.2 45.5 42.85 44.44 18221.0
   2026-06-09 44.99 44.99 42.31 43.09 5757.0
quote: ICONIKSPEV 43.09 -1.35 -3.04 INR bse
```

`/history/ICONIKSPEV`-class requests now return real EOD bars from the bhavcopy
cache via scrip-code 511260; the quote rides `getScripHeaderData?scripcode=511260`
with the bhavcopy fallback. The provider's `httpx` + UA/Referer hardening was
sufficient live for both the bhavcopy CSV and the header JSON endpoints.

### Verification (offline)

```
pytest tests/test_bse_provider.py tests/test_regenerate_bse_master.py
       tests/test_symbol_resolver.py tests/test_provider_registry_region.py
       tests/test_history.py tests/test_provider_registry.py -q
61 passed in 1.24s
```

Full sidecar pytest after the change: `1485 passed, 1 skipped in 31.99s` (exit 0).

### NEEDS-MANUAL-CHECK

- The seed master's TIRUPATI/AUROLAB rows were fabricated and are gone from the
  regenerated file; any external doc referencing them as examples is stale.
- `_generated` is the UTC date of the scratch run (2026-06-09); rerun
  `python -m services.resolver_masters.regenerate_bse_master > bse_instruments.json`
  periodically (quarterly is plenty — codes are stable, listings drift slowly).

## Component 2 — NSE exchange-direct (anti-bot lane)

### What shipped

- `sidecar/services/nse_provider.py` (new, commit 4256dc1) — the curl_cffi
  Chrome-impersonated direct lane:
  - cookie dance: `_SessionHolder.ensure` (line 250) warms a fresh session on
    `https://www.nseindia.com/` before its first API call; `_new_session`
    (line 237) is the test seam;
  - throttle: `_Throttle` (line 153) — ~1 req/s + jitter in [0, 0.4]s across
    ALL NSE traffic, warm-ups included, injectable clock/sleep;
  - rotation: `_get_json` (line 295) discards + re-warms the session on
    401/403 and retries ONCE; a second block raises so the registry falls
    through;
  - circuit breaker: `_CircuitBreaker` (line 190), PER PATH via `_breaker_for`
    (line 278) — 3 consecutive post-rotation blocks open a 300 s cooldown with
    fast-fail, half-open re-probe after. Per-path because the edge was
    OBSERVED blocking `quote-equity` while serving `historicalOR` on the same
    session;
  - `get_history` (line 454) — EOD from `api/historicalOR/cm/equity`, 90-day
    windows bounded at 9 (wider ranges raise → jugaad serves them), weekly/
    monthly resampled, intraday honestly refused;
  - `get_quote` (line 479) — `api/quote-equity` when served (defensive
    `priceInfo` parse, line 501) with the historicalOR-derived EOD fallback
    (`_quote_from_history`, line 535: close + official
    `CH_PREVIOUS_CLS_PRICE`);
  - Component 3 raw fetchers: `get_corporate_announcements` (line 583),
    `get_results_calendar` (line 596), `get_shareholding_master` (line 605).
- `sidecar/services/provider_registry.py` — `nse_direct` declared at rank 15
  (line 149): the IN chain is now `nse_direct(15) → nse/jugaad(20) → bse(25) →
yfinance(50)`, gated on `nse_provider.is_available()` (curl_cffi import).
- `scripts/smoke-test-sidecars.mjs` — `_probeNseDirectNoSla()` (line 253),
  warn-only live probe of `historicalOR/cm/equity` through the sidecar venv's
  python + curl_cffi (Node fetch has the wrong TLS fingerprint for NSE's
  Akamai edge); wired into `main()` next to the BSE probe.
- Tests: `sidecar/tests/test_nse_provider.py` (23 tests — cookie dance,
  observed-shape parses, rotation, per-path breaker, throttle pacing, EOD
  fallback, registry ranking) + `test_provider_registry_region.py` updated for
  the four-deep IN chain. Fixtures: `sidecar/tests/fixtures/nse/` — VERBATIM
  trims of the live captures, including the observed Akamai
  `quote_equity_access_denied.html`.
- `docs/redesign/INTEGRATION_NOTES_R7.md` (new) — no router/app.py wiring
  needed; notes the deliberate sync-`Session`-instead-of-`AsyncSession`
  deviation (the registry's quote/ohlcv seam is synchronous; identical
  anti-bot surface).

### Observed endpoint shapes (live probes, 2026-06-10 IST, curl_cffi impersonate="chrome", symbol RELIANCE)

- `GET /` warm-up → 200; cookies `AKA_A2`, `_abck`, `ak_bmsc`, `bm_sz`
  (Akamai). The get-quotes page adds `nsit`/`bm_sv`/`bm_mi`; `nseappid` never
  appeared.
- `api/historical/cm/equity` (legacy) → **503**. The live path is
  `api/historicalOR/cm/equity?symbol=&series=["EQ"]&from=DD-MM-YYYY&to=` →
  200, `{"data": [rows newest-first], "meta": {series, fromDate, toDate,
symbol}}`; row keys: `CH_SYMBOL, CH_SERIES, CH_TIMESTAMP "YYYY-MM-DD" (the
IST trading date directly — no UTC+5.5h decode, unlike jugaad),
CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, CH_TRADE_LOW_PRICE,
CH_CLOSING_PRICE, CH_PREVIOUS_CLS_PRICE, CH_LAST_TRADED_PRICE, VWAP,
CH_TOT_TRADED_QTY, CH_TOT_TRADED_VAL, CH_TOTAL_TRADES, CH_52WEEK_*`.
  30-day window → 21 rows.
- `api/corporate-announcements?index=equities&symbol=RELIANCE` → 200, bare
  list, **3,300 items / 2.8 MB (the FULL history — trim client-side)**; item
  keys incl. `an_dt, attchmntFile (nsearchives PDF), attchmntText, desc,
sm_isin, sm_name, sort_date, symbol, hasXbrl, seq_id`.
- `api/event-calendar?index=equities&symbol=RELIANCE` → 200, bare list (64):
  `{symbol, company, purpose, bm_desc, date "DD-Mon-YYYY"}`.
- `api/corporate-share-holdings-master?index=equities&symbol=RELIANCE` → 200,
  bare list (90 quarters): `{date "31-MAR-2026", pr_and_prgrp "50",
public_val "50", submissionDate, recordId, xbrl (SHP XML URL), …}`.
  FII/DII splits are NOT in the master — they live in the linked XBRL.
- `api/quote-equity?symbol=RELIANCE` → **403 Akamai "Access Denied" (path
  ACL) on EVERY variant**: chrome + safari impersonation, minimal/no headers,
  page-level warm-ups, cookie hops via `api/marketStatus` (200) — while
  `historicalOR` + the corporates endpoints served on the SAME session.
  `api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData` →
  200 (the NextApi lane is reachable; no equity-quote function is exposed:
  `getQuoteEquity` → 400 "Invalid function").
- `api/chart-databyindex?index=RELIANCEEQN` → 200 but empty off-session
  (`{closePrice: 0, grapthData: [], …}`) — not used.

### Live smoke (scratch invocation — the once-only live run)

```
history: nse_direct RELIANCE bars: 26
   2026-06-05 1304.5 1306.0 1288.0 1291.0 17785223.0
   2026-06-08 1277.0 1282.6 1259.2 1263.3 16494759.0
   2026-06-09 1269.0 1274.2 1257.5 1269.2 23620214.0
quote: RELIANCE 1269.2 5.9 0.47 INR nse_direct 2026-06-09
announcements: 3 | newest: 09-Jun-2026 19:45:31 | Updates
events: 64 | first: Demerger 05-Aug-2005
shareholding quarters: 90 | latest: 31-MAR-2026 promoter 50 public 50
```

The quote rode the EOD fallback exactly as designed (quote-equity blocked →
rotate → historicalOR-derived close + official prev close). The smoke-script
probe one-liner verified standalone: `WARMUP 200 / STATUS 200 / ROWS 7`.

### Verification (offline)

```
pytest tests/test_nse_provider.py tests/test_provider_registry_region.py
       tests/test_provider_registry.py tests/test_history.py
       tests/test_quotes.py tests/test_health.py -q
62 passed in 1.61s
```

Full sidecar pytest after the change: `1508 passed, 1 skipped in 31.42s`
(exit 0). Ruff format + check clean.

### NEEDS-MANUAL-CHECK

- `api/quote-equity` may serve from residential Indian IPs (the parser is
  ready); from this vantage it is hard-blocked at the edge. If a future probe
  captures a real 200 payload, add it to `tests/fixtures/nse/` and tighten
  `_quote_from_payload` to the observed shape.
- The breaker cooldown (300 s) and window budget (9×90 d) are first-cut
  tunings — revisit if real charts need >2y exchange-direct (jugaad currently
  serves those ranges).

## Components 3–4

Not yet in this run's completed scope. See `R7_TRACK_DATA_BRIEF.md`.
