# Set: batch-8/W4-resolver-exchange-lanes (set-33) — candidate ace7dd76, sidecar :52344

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-003 | MCP resolve_symbol (GUJGASLTD, fuzzy 'Marico Kaya limited') vs GET /resolve | resolved + candidates dicts equal; rename block (effective 2026-07-01 + note) present in tool; confidences equal to 4 places | holds |
| R15-UI-039 | GET /resolve/autocomplete GUJGAS / GUJGASLTD / GUJEN; /resolve GUJGASLTD | retired GUJGASLTD never offered as a pick; GUJGASLTD -> GUJENERGY with former_name, ISIN INE844O01030, bse 539336 | holds |
| R15-DATA-051 | GET /resolve SMR, CREST | SMR board=SME group=M fv=10; CREST mainboard B fv=10 (/fundamentals does not echo them: plan scope, documented in batch-8 Issues 7) | holds |
| R15-DATA-058 | GET /resolve?q=Sify Technologies Ltd (ADR) | candidates now end with SIFY US 0.913 (was 6 Indian rows only); bare SIFY 1.0 | holds |
| R15-CODE-DATA-002 | live repeat /resolve timing | 'hdfc bank limited results' 1.08 s -> 0.002 s; 'infosys' 0.309 s -> 0.0016 s | holds |
| R15-LIFECYCLE-019 | in-process MockTransport: ConnectTimeout first, live NSE symbolchange second | attempts 1 lane False -> after backoff attempts 2 lane True; GUJGASLTD->GUJENERGY; live route rename_lane=available | holds |
| R15-LIFECYCLE-022 | in-process MockTransport, UDiFF 404: (a) legacy live (b) both hosts 404 | (a) fallback tried, 2,934 rows live, 0 empty markers; (b) None, WARNING 'has the archive path moved?', only marker is 2026-10-02 (Gandhi Jayanti, a table holiday) | holds |
| R15-AGENT-045 | MCP compare_symbols [COCHINSHIP, MAZAGONDOCK] and by names | invented ticker -> "unresolved name: 'MAZAGONDOCK' is not a known ticker..."; names -> COCHINSHIP + MAZDOCK quotes | holds |
| R15-DATA-084 | in-process openbb stub payload value 0.0 | [('2021-01-04', 0.0), ('2021-01-05', 0.07)] | holds |
| R15-DATA-085 | GET /macro/NY.GDP.MKTP.CD?provider=world-bank | title 'GDP (current US$) — IND' | holds |
| R15-DATA-086 | in-process: socket.getaddrinfo forced down, macro_router.search('unemployment','world-bank'), then restored | down -> ProviderError kind=network (not curated rows); restored -> 25 real hits | holds |

COVERAGE: 11/11 ids raw; no raw: none
