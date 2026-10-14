# Set 90 — lows-P2/screener (candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-019 | live POST /screener/run with an OR group on :52353 | HTTP 200, 2 rows, row keys carry no matched_criteria | holds |
| R15-CODE-DATA-020 | live POST unknown universe / bad formula + handler source | 422 / 422; handler only catches FormulaError, comment says other errors stay 500 | holds |
| R15-DATA-107 | in-process india_symbol_meta (.NS, bare, .BO) | correct scrip_code/isin/group; lookup values are _BseRow named rows | holds |
| R15-DATA-108 | in-process repeat sector_map_generated/coverage | _sector_master cache hits=100 misses=1; 100 calls 0.01 ms | holds |
| R15-LEAD-029 | grep stale "5,156" + docstring + india-all size | no stale count in file; india-all = 5891 symbols | holds |

COVERAGE: 5/5 ids raw
