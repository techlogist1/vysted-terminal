# R15-LEAD-022 (rc1-verifier:4) — refutation audit round 4, group data

Verdict: **partial**. The entry's named examples (BHP.AX, 0700.HK, 7203.T, VOD.L) are fixed; the class the fix_shape names (every non-Indian exchange suffix passes through in dot form) is not: any Yahoo suffix outside the 37-entry allowlist is still dash-rewritten. Severity: high (kept).

Audited 06:57 IST on own sidecar :52400 + in-process with sidecar/.venv. Code tree == 01015033 (see data-R15-DATA-003.md header).

## Entry
- repro: quote any non-US, non-IN foreign listing (e.g. BHP.AX, 0700.HK, 7203.T, VOD.L) -> dash rewrite -> 'possibly delisted' -> 404 'check the symbol'.
- fix_shape: scope the dash rewrite away from exchange suffixes; pass every other recognised exchange suffix through unchanged; pin one symbol per suffix.
- batch-9 certified on BHP.AX, 0700.HK, 7203.T, VOD.L, SAP.DE, BRK.B only.

## 1. In-process _yahoo_symbol at HEAD (region US)
```
BHP.AX       -> BHP.AX
0700.HK      -> 0700.HK
7203.T       -> 7203.T
VOD.L        -> VOD.L
2222.SR      -> 2222-SR
SAP.F        -> SAP-F
GGAL.BA      -> GGAL-BA
OPAP.AT      -> OPAP-AT
BMW.BE       -> BMW-BE
SIE.MU       -> SIE-MU
EQB.NE       -> EQB-NE
CEZ.PR       -> CEZ-PR
QNBK.QA      -> QNBK-QA
COMI.CA      -> COMI-CA
SQM-B.SN     -> SQM-B-SN
BRK.B        -> BRK-B
BF.B         -> BF-B
RELIANCE.NS  -> RELIANCE.NS
is_us_symbol BRK False
is_us_symbol BRK.B False
is_us_symbol BRK-B True
is_us_symbol BF False
is_us_symbol BF-B True
is_us_symbol 2222 False
is_us_symbol SAP True
is_us_symbol GGAL True
is_us_symbol OPAP False
suffix count 37
```

## 2. Live /quotes at HEAD (entry examples + verifier's refutation symbols) — sh l022.sh
```
HEAD b06f4f70 06:50 IST

### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/BHP.AX
{"symbol":"BHP.AX","price":60.720001220703125,"change":-0.2999992370605469,"change_percent":-0.49164083056373936,"volume":6511835.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"AUD","market_state":null,"timestamp":"2026-09-25T06:13:02Z","provider":"yfinance","freshness":"eod"}
[HTTP 200 0.364244s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/0700.HK
{"symbol":"0700.HK","price":436.6000061035156,"change":-1.79998779296875,"change_percent":-0.4105811628714953,"volume":9113746.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"HKD","market_state":null,"timestamp":"2026-09-25T08:08:12Z","provider":"yfinance","freshness":"eod"}
[HTTP 200 0.488969s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/7203.T
{"symbol":"7203.T","price":2989.5,"change":11.5,"change_percent":0.38616521155137673,"volume":21084000.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"JPY","market_state":null,"timestamp":"2026-09-25T06:30:00Z","provider":"yfinance","freshness":"eod"}
[HTTP 200 0.441208s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/VOD.L
{"symbol":"VOD.L","price":125.80000305175781,"change":0.5000030517578153,"change_percent":0.3990447340445453,"volume":52512523.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"GBp","market_state":null,"timestamp":"2026-09-25T16:18:24Z","provider":"yfinance","freshness":"eod"}
[HTTP 200 0.391755s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/2222.SR
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
[HTTP 404 2.327480s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/SAP.F
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
[HTTP 404 2.377351s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/GGAL.BA
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
[HTTP 404 1.453696s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/OPAP.AT
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
[HTTP 404 1.650165s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/quotes/BRK.B
{"symbol":"BRK-B","price":505.4800109863281,"change":-0.21998901367186363,"change_percent":-0.04350188128769303,"volume":2992300.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"USD","market_state":null,"timestamp":"2026-09-25T20:00:03Z","provider":"yfinance","freshness":"eod"}
[HTTP 200 0.301494s]

```

## 3. Yahoo directly (yfinance in sidecar/.venv), dot vs dash form
```
2222.SR    rows=4 last_close=25.78
2222-SR    rows=0 last_close=None
SAP.F      rows=5 last_close=185.2
SAP-F      rows=0 last_close=None
GGAL.BA    rows=5 last_close=6290.0
GGAL-BA    rows=0 last_close=None
OPAP.AT    rows=0 last_close=None
OPAP-AT    rows=0 last_close=None
BMW.BE     rows=0 last_close=None
BMW-BE     rows=0 last_close=None
BHP.AX     rows=5 last_close=60.72
BHP-AX     rows=0 last_close=None
```

## 4. Provider-level probe: HEAD vs the proposed rule (dash only when the dashed form is a US-master ticker)
```
HEAD       2222.SR -> ERR ProviderError yfinance quote failed for '2222.SR': $2222-SR: possibly delisted; no price data found  (period=5d) (
HEAD       SAP.F -> ERR ProviderError yfinance quote failed for 'SAP.F': $SAP-F: possibly delisted; no price data found  (period=5d) (Yaho
HEAD       GGAL.BA -> ERR ProviderError yfinance quote failed for 'GGAL.BA': $GGAL-BA: possibly delisted; no price data found  (period=5d) (
PROPOSED   2222.SR -> 2222.SR 25.780000686645508 SAR
PROPOSED   SAP.F -> SAP.F 185.1999969482422 EUR
PROPOSED   GGAL.BA -> GGAL.BA 6290.0 ARS
PROPOSED   BRK.B -> BRK-B 505.4800109863281 USD
```

## Code at HEAD
sidecar/services/yfinance_provider.py:220-258 _YAHOO_EXCHANGE_SUFFIXES (37 entries: no SR, F, BA, AT, BE, MU, DU, HM, HA, SG, NE, CN, PR, BD, QA, KW, CA, SN, IL, ...); :318-322 any dotted symbol whose suffix is not in that set takes s.replace('.', '-').

## Reasoning
The verifier's claim holds with one correction. 2222.SR, SAP.F and GGAL.BA are real Yahoo listings (dot form returns SAR 25.78, EUR 185.2, ARS 6290; dash form returns nothing), yet _yahoo_symbol dashes them and /quotes answers 404 not_found 'check the symbol', telling the user a valid symbol is wrong. OPAP.AT is a bad example: Yahoo has no data for OPAP.AT in either form (BMW.BE likewise), so it proves only the mapping, not a lost quote. The fix replaced a universal rewrite with a finite allowlist, so the defect class (a foreign exchange suffix rewritten into a symbol Yahoo does not serve) still covers every exchange the list forgot, including Saudi Tadawul and Frankfurt. The US share-class quirk can be recognised positively instead: symbol_resolver.is_us_symbol('BRK-B') and ('BF-B') are True, so dashing only when the dashed form is a US-master ticker keeps BRK.B -> BRK-B (probe section 4) and passes every foreign suffix through.

Severity kept at high: quoting is a core flow and it is broken for every listing on an unlisted exchange, with a misleading 'check the symbol' message; the major markets in the entry's own examples work.

## Certification failures
Baseline 0: no 'certification failures so far' clause in the register note; not in any stage-c not_certified list (batch-9 certified); no earlier REFUTATION_AUDIT regression_confirmed/partial verdict. Plus this partial verdict = 1.
