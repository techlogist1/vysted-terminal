# R15-DATA-059 / rc1-verifier:10: partial

Refutation audit round 2, group data. Own sidecar :52360 (pid 4861) from source at HEAD a3275f64. The code tree equals candidate 4c6dfe8c. Written 18:23 IST.

## Entry's own repro (/resolve?q=ONC, SIFY) plus the former-name cases
```
18:17 IST
== GET /resolve?q=ONC
{"ok":true,"query":"ONC","region":"IN","resolved":{"symbol":"ONC","name":"BeOne Medicines Ltd.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"ONC","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":"BeiGene, Ltd.","board":null,"exchange_group":null,"face_value":null},"needs_disambiguation":false,"candidates":[{"symbol":"ONC","name":"BeOne Medicines Ltd.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"ONC","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":"BeiGene, Ltd.","board":null,"exchange_group":null,"face_value":null}],"rename_lane":"available"}
HTTP 200
== GET /resolve?q=SIFY
{"ok":true,"query":"SIFY","region":"IN","resolved":{"symbol":"SIFY","name":"SIFY TECHNOLOGIES LTD","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"SIFY","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":"SIFY LTD","board":null,"exchange_group":null,"face_value":null},"needs_disambiguation":false,"candidates":[{"symbol":"SIFY","name":"SIFY TECHNOLOGIES LTD","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"SIFY","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":"SIFY LTD","board":null,"exchange_group":null,"face_value":null}],"rename_lane":"available"}
HTTP 200
== GET /resolve?q=BeiGene
{"ok":true,"query":"BeiGene","region":"IN","resolved":null,"needs_disambiguation":true,"candidates":[{"symbol":"ONC","name":"BeOne Medicines Ltd.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"ONC","confidence":0.97,"isin":null,"bse_code":null,"industry":null,"former_name":"BeiGene, Ltd.","board":null,"exchange_group":null,"face_value":null},{"symbol":"BEIGF","name":"BeOne Medicines Ltd.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"BEIGF","confidence":0.97,"isin":null,"bse_code":null,"industry":null,"former_name":"BeiGene, Ltd.","board":null,"exchange_group":null,"face_value":null},{"symbol":"TNMG","name":"TNL Mediagene","exchange":"US","region
```
## US master row shape
```
python3 -c "json.load(open('sidecar/services/resolver_masters/us_instruments.json'))['instruments'][:3]"
-> [['NVDA', 'NVIDIA CORP'], ['GOOGL', 'Alphabet Inc.'], ['AAPL', 'Apple Inc.']]
```
sidecar/services/symbol_resolver.py:1378 `if inst.exchange not in ("NSE", "BSE"): return inst` skips identity enrichment for every US instrument, and the master has no ISIN or CUSIP column.

## Is the batch-12 "could-not" (no free ticker-keyed ISIN source) true?
An installed dependency, called from the repo venv:
```
sidecar/.venv/bin/python -c "import yfinance as yf; print(yf.Ticker('SIFY').isin, yf.Ticker('ONC').isin, yf.Ticker('AAPL').isin)"
-> SIFY US82655M2061 | ONC - | AAPL US0378331005
```
The SIFY value matches the entry's outside truth (US82655M2061). So a keyless ticker-keyed ISIN source already ships with the sidecar, though it misses some tickers (ONC returns '-').

## Verdict: partial
The former-name half of the entry's repro holds: ONC gives former_name 'BeiGene, Ltd.', SIFY gives 'SIFY LTD', and BeiGene brings back ONC and BEIGF as candidates. The Toss the Coin query now binds TTC. The entry's repro and fix_shape also name `isin=null` for US instruments ("add ISIN/CUSIP to the US master"), and that part is still unmet: SIFY and ONC resolve with isin null. Batch 12 accepted a could-not whose premise the probe above refutes for SIFY and AAPL. Board and listing_date now exist as schema fields (null for US). The refuter scoped those as product-wide gaps, so they are not counted here.

Failure count: 2 (rc1 refutation audit round 1 = regression_confirmed; this gate refutation = partial).
