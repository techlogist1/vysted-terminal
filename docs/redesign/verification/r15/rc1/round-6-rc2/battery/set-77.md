# Set 77 — lows-P2/disclosures-witnesses (candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-007 | in-process get_shareholding with NSE lane raising KeyError | falls through to BSE lane, count 1; both lanes failing -> ProviderError (not raw KeyError) | holds |

COVERAGE: 1/1 ids raw
