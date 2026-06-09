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
{"SCRIP_CD": "511260", "Scrip_Name": "Iconik Sports And Events Ltd",
 "Status": "Active", "GROUP": "X", "FACE_VALUE": "10.00",
 "ISIN_NUMBER": "INE088P01015", "INDUSTRY": null, "scrip_id": "ICONIKSPEV",
 "Segment": "Equity",
 "NSURL": "https://www.bseindia.com/stock-share-price/iconik-sports-and-events-ltd/iconikspev/511260/",
 "Issuer_Name": "ICONIK SPORTS AND EVENTS LIMITED", "Mktcap": "145.83"}
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

## Components 2–4

Not in this run's scope (Component 1 only). See `R7_TRACK_DATA_BRIEF.md`.
