# R15-DATA-053 (rc1-verifier:8, with rc1-vshard-9:5 deduped in) — refutation audit round 4, group data

Verdict: **partial**. The headline repros hold (ICON and AMAL BSE quotes now carry volume and OHLC). Two stated parts of the same thin-quote class do not: the session volume the fix reads from BSE StockTrading is in lakh units for liquid scrips (a wrong figure, not a missing one), and the entry's own raw DAT-P13-4 (ELCIDIN, served by nse_direct) still has no day range. Severity: raised from medium to high.

Audited 07:01 IST on own sidecar :52400 + in-process with sidecar/.venv. Code tree == 01015033 (see data-R15-DATA-003.md header).

## Entry
- repro: /quotes/ICON volume null (DAT-P6-6); /quotes/AMAL volume null on the bse lane (DAT-P9-8); ELCIDIN price.bse_day_range / nse_day_range (OHLC) absent (DAT-P13-4).
- fix_shape: fetch session volume from BSE StockTrading (or the bhavcopy row) and add open/high/low/prev_close to Quote + types; pin with ICON/AMAL header fixtures.
- register note (batch-13): '/quotes/500325.BO reports volume: 2.19 for RELIANCE on BSE, looks like a lakh/unit artifact in the bse lane', folded into this entry as a possible residual.
- batch-10 (f407107) certified. That diff touched bse_provider.py, models/market.py, types/data.ts, yfinance_provider.py; nse_provider.py was not touched.

## 1. Entry repros + verifier refutation, live — sh d053.sh
```
HEAD b06f4f70 06:52 IST

### curl http://127.0.0.1:52400/quotes/ICON?asset_class=equity
{"symbol":"ICON","price":64.45,"change":0.0,"change_percent":0.0,"volume":1200.0,"open":64.45,"high":64.45,"low":64.45,"prev_close":63.06,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-24T00:00:00Z","provider":"bse","freshness":"eod"}
[HTTP 200 0.233664s]


### curl http://127.0.0.1:52400/quotes/AMAL?asset_class=equity
{"symbol":"AMAL","price":674.4,"change":-13.25,"change_percent":-1.926852323129499,"volume":13368.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"nse_direct","freshness":"eod"}
[HTTP 200 5.165656s]


### curl http://127.0.0.1:52400/quotes/ELCIDIN?asset_class=equity
{"symbol":"ELCIDIN","price":103800.0,"change":-1030.0,"change_percent":-0.9825431651244874,"volume":8.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"nse_direct","freshness":"eod"}
[HTTP 200 6.010493s]


### curl http://127.0.0.1:52400/quotes/INFY.BO
{"symbol":"INFY","price":1000.95,"change":-8.149999999999977,"change_percent":-0.8076503815280921,"volume":8.12,"open":1000.0,"high":1003.6,"low":991.75,"prev_close":1009.1,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
[HTTP 200 0.516126s]


### curl http://127.0.0.1:52400/quotes/INFY.NS
{"symbol":"INFY","price":1000.2,"change":-14.299999999999955,"change_percent":-1.4095613602759935,"volume":10240700.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"nse_direct","freshness":"eod"}
[HTTP 200 5.457783s]


### curl http://127.0.0.1:52400/quotes/RELIANCE.BO
{"symbol":"RELIANCE","price":1226.0,"change":7.0,"change_percent":0.5742411812961444,"volume":5.28,"open":1215.0,"high":1227.2,"low":1214.0,"prev_close":1219.0,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
[HTTP 200 0.448059s]


### curl http://127.0.0.1:52400/quotes/500325.BO
{"symbol":"RELIANCE","price":1226.0,"change":7.0,"change_percent":0.5742411812961444,"volume":5.28,"open":1215.0,"high":1227.2,"low":1214.0,"prev_close":1219.0,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
[HTTP 200 0.473554s]


### curl http://127.0.0.1:52400/quotes/AMAL.BO
{"symbol":"AMAL","price":673.05,"change":-15.050000000000068,"change_percent":-2.1871820956256456,"volume":5406.0,"open":689.0,"high":694.95,"low":665.0,"prev_close":688.1,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
[HTTP 200 0.881739s]


### curl http://127.0.0.1:52400/quotes/ICON.BO
{"symbol":"ICON","price":64.45,"change":0.0,"change_percent":0.0,"volume":1200.0,"open":64.45,"high":64.45,"low":64.45,"prev_close":63.06,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-24T00:00:00Z","provider":"bse","freshness":"eod"}
[HTTP 200 0.757788s]

```

## 2. BSE StockTrading raw payload (in-process bse_provider._api_json('StockTrading/w', ...))
```
500209 INFY {'TTQ': '8.12', 'TTQin': '(Lakh)'} | all keys: ['CktLimit', 'ExDate', 'MktCapFF', 'MktCapFull', 'TTQ', 'TTQin', 'Turnover', 'Turnoverin', 'TwoWkAvgQty', 'TwoWkAvgQtyin', 'WAP', 'blockdttm'
500325 RELIANCE {'TTQ': '5.28', 'TTQin': '(Lakh)'} | all keys: ['CktLimit', 'ExDate', 'MktCapFF', 'MktCapFull', 'TTQ', 'TTQin', 'Turnover', 'Turnoverin', 'TwoWkAvgQty', 'TwoWkAvgQtyin', 'WAP', 'blockd
506597 AMAL {'TTQ': '5406', 'TTQin': ''} | all keys: ['CktLimit', 'ExDate', 'MktCapFF', 'MktCapFull', 'TTQ', 'TTQin', 'Turnover', 'Turnoverin', 'TwoWkAvgQty', 'TwoWkAvgQtyin', 'WAP', 'blockdttm']
539221 ICON? {'TTQ': '8852', 'TTQin': ''} | all keys: ['CktLimit', 'ExDate', 'MktCapFF', 'MktCapFull', 'TTQ', 'TTQin', 'Turnover', 'Turnoverin', 'TwoWkAvgQty', 'TwoWkAvgQtyin', 'WAP', 'blockdttm']
```

## 3. The product's own BSE history bars for INFY.BO (GET /history/INFY.BO?range=5d)
```
provider bse
2026-09-23T00:00:00Z close 1019.2 volume 407318.0
2026-09-24T00:00:00Z close 1009.1 volume 835779.0
2026-09-25T00:00:00Z close 1000.95 volume 811562.0
```

## 4. The entry-time ELCIDIN quote was already nse_direct (battery/collected/P13_ELCIDIN.json 'calls.quote')
```
{"url": "http://127.0.0.1:52152/quotes/ELCIDIN?asset_class=equity", "status": 200, "body": {"symbol": "ELCIDIN", "price": 105130.0, "volume": 13.0, "provider": "nse_direct", "freshness": "eod"}}
```

## Code at HEAD
- sidecar/services/bse_provider.py:630 quote.volume = the raw TTQ of the StockTrading/w payload, ignoring its TTQin unit field ('(Lakh)' for INFY 500209 and RELIANCE 500325, '' for AMAL 506597 and 539221).
- sidecar/services/nse_provider.py:597-628 _quote_from_history already computes prev and bars=_rows_to_bars([last]) (which carry open/high/low) but builds Quote without open/high/low/prev_close; :563-594 _quote_from_payload reads priceInfo.previousClose but likewise leaves them unset.
- tests/test_bse_provider.py:357-378 pins volume only on two small caps whose TTQin is empty, so the lakh case is unpinned.

## Reasoning
Primary repro fixed: ICON (bse) volume 1200 with open/high/low/prev_close; AMAL.BO (bse) volume 5406 with the day range. Bare AMAL is now served by nse_direct with volume 13368, so DAT-P9-8's volume-null no longer shows.

Residual A, the verifier's and rc1-vshard-9:5's BSE volume units. This is the fix's own volume lane. StockTrading states its unit in TTQin, and for liquid scrips that unit is lakh: INFY.BO shows volume 8.12 while the product's own BSE bhavcopy bar for the same 2026-09-25 session shows 811,562 shares, and RELIANCE.BO (and 500325.BO) show 5.28. The register had already folded this lakh artifact into this entry (batch-13 note), and it sits inside the fix_shape's 'fetch session volume from BSE StockTrading'. So it is a partial on this entry, not a new defect.

Residual B, the entry's own raw DAT-P13-4. At entry time ELCIDIN's quote came from nse_direct (section 4). At HEAD it is still nse_direct with open/high/low/prev_close null, and so are bare AMAL and INFY.NS. The fix_shape added the fields to Quote but filled them only on the bse lane.

The verifier's claim holds on both counts.

Severity raised to high. A liquid scrip's BSE volume is served 100,000 times too low as a plain number: the research brief renders quote.volume as 'Volume' (src/modules/research/brief-blocks.tsx:340-398) and the agent reads it. That happens on every .BO large cap, and on the bse fallback whenever the NSE lanes fail. It is not critical because the figure is implausible on sight and no valuation metric derives from it. The NSE OHLC gap alone would be low: no frontend code reads quote open/high/low/prev_close.

## Certification failures
Baseline 0: no 'certification failures so far' clause in the register note; not in any stage-c not_certified list (batch-10 certified); no earlier REFUTATION_AUDIT regression_confirmed/partial verdict. Plus this partial verdict = 1.
