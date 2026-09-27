# batch-10/W3-fundamentals-bse-cache (rc1-battery-1, round-5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar `127.0.0.1:52341`,
data dir `rc1-round-5-recheck-data-rc1-battery-1`. Raw output: `raw/set-42/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-048 | `GET /fundamentals/RELIANCE.NS`, `/CREST.NS`, `/AMAL.NS`, `roce` + `field_meta.roce` | roce RELIANCE 0.08993784539668614, CREST 0.03686193809422806, AMAL 0.22332467349866908 — matches cert (0.0899/0.0369/0.2233) exactly to 4 decimals. `field_meta.roce.provider="derived"`, `basis_note="annual EBIT / (total assets - current liabilities)"` on all three, matching the fix's derivation. | holds |
| R15-DATA-054 | Same fetches + ELCIDIN.NS, `basis` and `field_meta.basis` | RELIANCE `basis:"consolidated"`, `field_meta.basis:{status:"ok",provider:"exchange-filings"}`. CREST same. AMAL `basis:null` (no field_meta.basis probed separately — consistent with "no filing states"). ELCIDIN `basis:null`, `field_meta.basis:{status:"unavailable",provider:"exchange-filings",reason:"no NSE/BSE filing states a basis"}` — the router-stamped filings leg from fix `f4ef5673` is present and gives a stated reason beside the null value, matching the two-tests-pinned fix (`status`/`provider`/`reason` populated instead of a bare unexplained null). | holds |
| R15-DATA-096 | Two sequential `GET /fundamentals/AAPL/income`, timed, diffed | cold 0.825 s, warm (repeat) 0.012 s, byte-identical body — cache hit confirmed (same order-of-magnitude speedup and byte-identical payload as the cert's 2.54 s -> 0.01 s capture; absolute cold time differs with this run's cache/network state, not a regression signal). | holds |
| R15-LEAD-024 | `GET /macro/WEO%2FUSA.NGDP_RPCH.A?provider=imf`, `GET /macro/WEO%2FIND.PCPIPCH.A?provider=imf` | USA: 2023 2.934535/false, 2024 2.793116/false, 2025 2.11733/true, 2026 2.323695/true, ... through 2031 all true — exact match to cert (2.93/2.79/2.12/2.32, is_projection pattern identical). Fresh case IND.PCPIPCH.A: 2024 4.639051/false, 2025 2.090859/true, 2026 4.714761/true — matches cert's "2024 false, 2025+ true" pattern. vitest MacroChart dashed-segment rendering not re-run here (owned by the heavy/vitest lane). | holds |

**Set result: 4/4 holds.**

Evidence: `raw/set-42/R15-DATA-048-{reliance,crest,amal}.json`,
`raw/set-42/R15-DATA-054-elcidin.json` (basis cross-checked on the same
`R15-DATA-048-{reliance,crest}.json` files), `raw/set-42/R15-DATA-096.txt`,
`raw/set-42/R15-LEAD-024-{usa,ind}.json`.

COVERAGE: 4/4 ids raw; no raw: none.
