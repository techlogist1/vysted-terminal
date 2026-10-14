# R15-DATA-043 refutation audit (group data) at HEAD 6741387b

Sidecar on 127.0.0.1:52360 (scratch data dir). Script: scratchpad/refaudit-data/scr.py POSTs /screener/run.

## Entry's own repro
```
{"universe":"custom","custom_symbols":["AAPL","RELIANCE.NS"],"criteria":[],"sort_by":"market_cap","sort_dir":"desc"}
  rows [('RELIANCE.NS','INR',16483904126976.0,1219.2), ('AAPL','USD',4902477103104.0,335.92)]
  matched 2 result 2 coverage 'screened 2 of 2 — 0 unavailable · spans INR, USD — ranked within each currency'
```
The default-limit (200) result is currency-grouped and says so. The criteria-builder unit labels were certified by vitest in batch 2. `pytest tests/test_screener.py -k currency` -> 2 passed. The stated repro holds.

## Verifier's refutation (rc1-verifier:7)
```
{"custom_symbols":["RELIANCE.NS","AAPL"],...,"limit":1}
  rows [('RELIANCE.NS','INR',16483904126976.0,1219.2)]
  matched 2 result 1 coverage 'screened 2 of 2 — 0 unavailable'
{"custom_symbols":["AAPL","RELIANCE.NS","MSFT","TCS.NS"],...,"sort_by":"market_cap","sort_dir":"desc","limit":2}
  rows [('RELIANCE.NS','INR',1.648e13,1219.2), ('TCS.NS','INR',7.49e12,2087.0)]
  matched 4 result 2 coverage 'screened 4 of 4 — 0 unavailable'
```
Reproduces. A "top 2 by market cap" of a list that includes AAPL and MSFT returns RELIANCE and TCS. The INR group sorts first because 'INR' < 'USD', and the cut drops the whole USD group. The note that would warn the user is gone, because it is computed over the served page, not over the matched set.
Code: sidecar/services/screener.py:423-429 sorts by `(_currency_sort_key(currency), missing, sign*value)`. :815 `rows = matched[:limit]` cuts that grouped order. :845-847 `served_currencies = sorted({r.currency for r in rows ...})` looks only at the page. Reachability: the agent screener tool defaults to limit=50 (services/agent_tools/screener_tools.py:59) and passes a caller limit through, and the UI's "Show more" pages at 200 (src/store/screener.ts:34).

## Classification: partial
The fix holds for the entry's repro (a full mixed-currency page). A stated part of the same defect class does not hold: the ranking is still read as one cross-currency ranking, via the top-K cut, and now with no disclosure. It is not a regression, because the limit path was never covered.

## Adjacent (already filed by the verifier as rc1-verifier:15, confirmed here)
```
{"custom_symbols":["MANIKA.NS","RELIANCE.NS","TCS.NS"],...,"sort_by":"market_cap","sort_dir":"desc"}
  rows [('MANIKA.NS','INR',None,41.46), ('RELIANCE.NS','INR',1.648e13,...), ('TCS.NS','INR',7.49e12,...)]
```
A row whose Fundamentals.currency is None sorts under key '' ahead of 'INR' (screener.py:424 `currency=fundamentals.currency`, :426 sort key), so a null-market-cap row ranks first. The row's currency is re-stamped from the store only after the cut (:820-822). This is a separate defect and should be registered separately.
