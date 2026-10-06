# R15-DATA-113 / rc1-verifier:7: partial

Refutation audit round 2, group data. Own sidecar :52360 (pid 4861) from source at HEAD a3275f64. The code tree equals candidate 4c6dfe8c (the non-docs diff is empty). Written 18:23 IST.

## Entry's own repro (GET /earnings/WIT/estimates) and fresh cases
```
18:19 IST
== GET /earnings/WIT/estimates
{'symbol': 'WIT', 'currency': 'USD', 'revenue_currency': 'INR', 'eps_estimate_mean': 0.035, 'revenue_estimate_mean': 244747656810.0, 'detail': None}
== GET /earnings/INFY/estimates
{'symbol': 'INFY.NS', 'currency': 'INR', 'revenue_currency': 'USD', 'eps_estimate_mean': 19.61527, 'revenue_estimate_mean': 491654926200.0, 'detail': None}
== GET /earnings/INFY.NS/estimates
{'symbol': 'INFY.NS', 'currency': 'INR', 'revenue_currency': 'USD', 'eps_estimate_mean': 19.61527, 'revenue_estimate_mean': 491654926200.0, 'detail': None}
== GET /earnings/INFY/estimates -H X-Vysted-Region:US
    return loads(fp.read(),
        cls=cls, object_hook=object_hook,
        parse_float=parse_float, parse_int=parse_int,
        parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)
    return _default_decoder.decode(s)
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
== GET /earnings/TSM/estimates
{'symbol': 'TSM', 'currency': 'USD', 'revenue_currency': 'TWD', 'eps_estimate_mean': 4.4614, 'revenue_estimate_mean': 1454935426950.0, 'detail': None}
== GET /earnings/HDB/estimates
{'symbol': 'HDB', 'currency': 'USD', 'revenue_currency': 'INR', 'eps_estimate_mean': 0.388, 'revenue_estimate_mean': 475224862000.0, 'detail': None}
== GET /earnings/WIPRO.NS/estimates
{'symbol': 'WIPRO.NS', 'currency': 'INR', 'revenue_currency': 'INR', 'eps_estimate_mean': 3.21409, 'revenue_estimate_mean': 244747656810.0, 'detail': None}
== GET /earnings/TCS.NS/estimates
{'symbol': 'TCS.NS', 'currency': 'INR', 'revenue_currency': 'INR', 'eps_estimate_mean': 37.98309, 'revenue_estimate_mean': 723442230480.0, 'detail': None}
== GET /earnings/AAPL/estimates
{'symbol': 'AAPL', 'currency': 'USD', 'revenue_currency': 'USD', 'eps_estimate_mean': 1.98124, 'revenue_estimate_mean': 113624521680.0, 'detail': None}
```
The `INFY -H X-Vysted-Region:US` line failed only because of shell quoting. It was re-run with correct quoting:
```
curl -s -H 'X-Vysted-Region: US' :52360/earnings/INFY/estimates
-> symbol INFY, currency USD, revenue_currency USD, eps_estimate_mean 0.20543, revenue_estimate_mean 491654926200.0
```

## Scale check (own sidecar)
```
INFY.NS  fundamentals: currency INR, financial_currency USD, revenue_ttm 1,845,820,000,000
         income statement (financialCurrency): Reconciled Cost Of Revenue FY2026 = 14,079,000,000   <- USD-sized
WIT      financial_currency INR, revenue_ttm 949,680,013,312; income CoR FY2026 = 635,443,000,000   <- INR-sized
WIPRO.NS revenue_estimate_mean 244,747,656,810 (the same figure as WIT, labelled INR)
```
Infosys files its statements in USD, so Yahoo's financialCurrency is USD. Its quarterly revenue is about USD 5 billion. Yahoo's revenue estimate of 491.65B is INR-sized, about INR 49,165 crore for the quarter. Labelling it USD overstates it by about 95x. The same 491.65B is served for INFY.NS and for the INFY ADR, labelled USD both times.

## Code
sidecar/services/earnings_provider.py:101-108: `_revenue_currency` returns `payload.get("financial_currency") or payload.get("currency")`. It is used at :418 (estimates) and :521 (history and surprises). The fix assumes Yahoo states revenue estimates in financialCurrency. That holds for WIT, TSM and HDB but not for INFY, whose financialCurrency (USD) differs from the currency of its estimates (INR, the home market). On INFY.NS the old trading-currency label (INR) was correct, and the fix made it wrong.

## Verdict: partial
The entry's own WIT repro holds: revenue_currency is INR. The defect class the entry names is a currency mislabel on statement-size estimate revenue. That class is not closed: INFY and INFY.NS revenue estimates are INR-sized but labelled USD. The verifier's refutation reproduces exactly at the candidate.

Failure count: 1 (this gate refutation). No batch not_certified listing and not in round 1.
