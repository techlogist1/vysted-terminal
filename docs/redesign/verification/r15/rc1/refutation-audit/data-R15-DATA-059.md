# R15-DATA-059 refutation audit (group data) at HEAD 6741387b

Sidecar on 127.0.0.1:52360 (scratch data dir, default region).

## Entry's own repro (verbatim: GET /resolve?q=ONC; DAT-P17-5/P17-4: /resolve?q=SIFY; DAT-S4-8: Toss the Coin)
```
## resolve q=ONC
{'symbol':'ONC','name':'BeOne Medicines Ltd.','isin':None,'former_name':None,'exchange':'US','bse_code':None} needs_dis False
resolved keys ['asset_class','board','bse_code','confidence','exchange','exchange_group','face_value','former_name','industry','isin','name','region','symbol','yahoo_symbol']
## resolve q=SIFY
{'symbol':'SIFY','name':'SIFY TECHNOLOGIES LTD','isin':None,'former_name':None,'exchange':'US'} needs_dis False
## resolve q=BeiGene
needs_dis True cands [('ONC','US','BeiGene, Ltd.',None), ('BEIGF','US','BeiGene, Ltd.',None), ('TNMG','US',None,None), ('TNMWF','US',None,None)]
## resolve q=Toss%20the%20Coin%20Private%20Limited
{'symbol':'TTC','name':'Toss The Coin Ltd','isin':'INE0XAY01012','former_name':None,'exchange':'BSE','bse_code':'544303'}
```
The bundled index has the data a ticker resolve fails to surface:
```
python3 -c "...former_names.json..." -> {'in': 1996, 'us': 4827}
ONC ['BeiGene, Ltd.']  SIFY ['SIFY LTD', 'SATYAM INFOWAY LTD']  TTC ['Toss the Coin Private Limited']
```
`pytest tests/test_symbol_resolver.py -k "former or BeiGene or beigene or toss"` -> 3 passed. These tests cover only the name-query direction.

## Verifier's refutation (rc1-verifier:10)
Same probe, same result: ONC and SIFY return isin null and former_name null. Only the 'BeiGene' name query shows the former name, on its candidates.

## Code
- sidecar/services/symbol_resolver.py:1377 `if inst.exchange not in ("NSE", "BSE"): return inst`. For a US instrument this returns before the former-name fallback at :1406-1411. That fallback only echoes `inst.former_name`, which only the name scan (:1064-1100) stamps. So a US ticker resolve never joins _former_names() (:469), even though ONC/SIFY are in it.
- US master sidecar/services/resolver_masters/us_instruments.json rows are `[ticker, name]` only (e.g. ['AAPL','Apple Inc.']). The fix_shape step "add ISIN/CUSIP to the US master" was not done, so isin is null for every US instrument.
- 'board' is now a key on every resolved instrument (null for US). listing_date is still absent from the resolve schema.

## Classification: regression_confirmed (never fixed for the entry's literal repro)
The entry's primary repro, /resolve?q=ONC -> isin null and former_name null, and the SIFY repros P17-4/P17-5 reproduce unchanged at HEAD. The certification (batch-11) tested only the name-query direction ('BeiGene', 'Toss the Coin Private Limited', Facebook, Zomato...), which does hold. So the fix covers half the title ("former names never resolve"). It does not cover the other half ("non-Indian identity stays empty"), which is where the entry's own repro lines sit. Scope caveat: the stage-B refuter said board/listing_date are product-wide schema gaps. The ISIN-leak guard at :1377 is deliberate for the BSE/sector-map join. It does not justify skipping the US-keyed former-name index, which is keyed per region ('us' vs 'in') and cannot leak across exchanges.
