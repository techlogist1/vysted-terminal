# set-87 — unplanned-2 (rc1-battery-21)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-023 | source read `sidecar/services/screener_universe_india.py:1-15` module docstring + `sidecar/models/screener.py:25-40` comment; grep for the old stale counts (`2,675`/`2.7k`/`4.9k`) in both files | both comments now describe composition only ("every NSE master row (EQ + ETF + SM/NSE Emerge)", "BSE master rows with STATUS==Active", "the union, NSE listing preferred") with no hardcoded counts; grep for the old stale numbers in either file returns 0 matches. (The register's own note already carves the `_nse_lookup` docstring residual at `screener_universe_india.py:95` out to a separate entry, R15-LEAD-029 — out of this entry's scope, not probed here) | holds |

Raw: `battery/raw/set-87/R15-CODE-DATA-023.txt`

COVERAGE: 16/16 ids raw; no raw: none.
