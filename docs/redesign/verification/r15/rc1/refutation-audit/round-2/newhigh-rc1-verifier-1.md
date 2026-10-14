# newhigh / rc1-verifier:1 — BSE-only shareholding 502 (SHP index over plain httpx, BSE 403s it)

Auditor: refutation audit round 2, group newhigh. Written 18:20 IST. Candidate code tree 4c6dfe8c (confirmed: `git diff --name-only 4c6dfe8c HEAD | grep -v '^docs/'` printed nothing at a3275f64).
Own sidecar: `sidecar/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 52365`, VYSTED_DATA_DIR=<scratchpad>/refaudit2-newhigh/data.

**Verdict: new_defect_confirmed (high).**

## 1. Verifier's claim and evidence (read)
Finding rc1-verifier:1; evidence r15/rc1/verifier/g2/spot-bse-shp.txt and spot-shareholding.txt: AMAL, DAL, NAPEROL, JUMBO and ELCIDIN return 502 provider_error; TCS, RELIANCE and JNPR (NSE lane) return 200. In-process, plain httpx on SHPQNewFormat returns 403 while `_api_json` (curl_cffi, impersonate=chrome) returns the Table.

## 2. Live repro on own :52365 (header X-Vysted-Region: IN)
```
for s in TCS AMAL DAL NAPEROL JUMBO ELCIDIN; do curl -s -H 'X-Vysted-Region: IN' "http://127.0.0.1:52365/disclosures/shareholding?symbol=$s"; done
```
```
== TCS
{"symbol":"TCS","count":20,"patterns":[{"symbol":"TCS","quarter_end":"2026-06-30","quarter_basis":null,"promoter_percent":71.77,"fii_percent":null,"dii_percent":null,"institutions_percent":null,"public_percent":28.23,"pu
HTTP 200
== AMAL
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
HTTP 502
== DAL
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
HTTP 502
== NAPEROL
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
HTTP 502
== JUMBO
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
HTTP 502
== ELCIDIN
{"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."}
HTTP 502
```
sidecar.log:
```
unexpected provider response: disclosures: every shareholding source failed for 'AMAL' (BSE: bse shareholding: index HTTP 403)
/disclosures/shareholding -> 502 provider_error: disclosures: every shareholding source failed for 'AMAL' (BSE: bse shareholding: index HTTP 403)
unexpected provider response: disclosures: every shareholding source failed for 'DAL' (BSE: bse shareholding: index HTTP 403)
/disclosures/shareholding -> 502 provider_error: disclosures: every shareholding source failed for 'DAL' (BSE: bse shareholding: index HTTP 403)
unexpected provider response: disclosures: every shareholding source failed for 'NAPEROL' (BSE: bse shareholding: index HTTP 403)
```

## 3. In-process transport comparison at the candidate (scrip 503681, the verifier's own)
```
plain httpx index: 403 <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD><BODY> <H1>
_api_json index: dict 118 June 2026 503681_177202615395_SHP.xml
plain httpx XBRL: 200 134782
curl_cffi XBRL: 200 134782
parse: {'promoter_percent': 75.0, 'public_percent': 25.0, 'public_non_institutional_percent': 24.94, 'dii_percent': 0.06, 'fii_percent': 0.0, 'institutions_percent': 0.06, 'promoter_pledged_percent': 0.0, 'promoter_pledge_basis': 'filed'}
```
Only the quarter INDEX (api.bseindia.com) is blocked for plain httpx. The per-quarter XBRL on www.bseindia.com still answers 200 over the same `_http_get`, and it parses (promoter 75.0 / public 25.0 / pledge filed 0). So the lane is dead at one call: the index fetch.

## 4. Root cause
- `sidecar/services/bse_provider.py:861-870` `_fetch_shp_index` fetches `_SHP_INDEX_URL` (`https://api.bseindia.com/BseIndiaAPI/api/SHPQNewFormat/w`, line 744) through `_http_get` (line 175, plain httpx). BSE's edge answers 403 "Access Denied" to that client.
- The same module already has the working lane: `_api_json` at line 1189 (curl_cffi `impersonate="chrome"`), whose own docstring says "the result endpoints 403 a plain httpx client". Every other api.bseindia.com call in the module (lines 614, 624, 1224, 1233, 1241) goes through `_api_json`. The SHP index is the one api.bseindia.com call left on httpx.
- batch-3 VERDICTS.md already recorded this 403 as a note ("BSE api.bseindia.com 403 (Akamai) for the SHP index … the lane degrades honestly"), but it was never registered as a defect. Unit tests stay green because `test_bse_provider.py` `_shp_http_stub` and `test_corporate_disclosures.py` monkeypatch `_http_get` for the index URL, so no test holds the transport choice.

## 5. Fix shape
Route the index through `_api_json`: `_fetch_shp_index(code)` becomes `_table(_api_json("SHPQNewFormat/w", {"scripcode": code}), "Table", "SHPQNewFormat/w")`. Keep the `ProviderError` wording that disclosures already expects. Leave the XBRL download (`_fetch_and_parse_shp_xbrl`, www.bseindia.com) on `_http_get`, which still answers 200. Update the SHP test stubs so the index is served through a monkeypatched `_api_json` and the XBRL through `_http_get`. Drop `_SHP_INDEX_URL` if nothing else uses it.

## 6. Acceptance test
- `sidecar/tests/test_bse_provider.py`: new `test_shp_index_rides_the_impersonated_lane`. Monkeypatch `_http_get` to raise AssertionError for any URL containing "SHPQNewFormat" and to serve the XBRL fixture for ".xml". Monkeypatch `_api_json` to return `_SHP_INDEX` for path "SHPQNewFormat/w". Assert `get_shareholding("BOMOXY-B1")` returns rows with promoter_percent 73.29. Also update `test_get_shareholding_index_failure_raises` so it fails through `_api_json` raising ProviderError("bse SHPQNewFormat/w: HTTP 503"), and the `test_corporate_disclosures.py` SMR stub the same way.
- Live re-proof: own sidecar, `for s in AMAL DAL NAPEROL JUMBO ELCIDIN SMR; do curl -s -o /dev/null -w "$s %{http_code}\n" -H 'X-Vysted-Region: IN' "http://127.0.0.1:<port>/disclosures/shareholding?symbol=$s"; done` → all 200 with count ≥ 1 and a non-null promoter_percent on the latest quarter. TCS stays 200.

## 7. Certification-failure count
id null (new) → 0, 'new'.
