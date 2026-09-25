# unplanned-6

Candidate 4097dac4. Own sidecar :52346. Raw output: `raw/set-51/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-071 | Read `sidecar/models/market.py:66-71` | `OHLCVSeries` now carries `partial: bool = False` and `coverage_start: date \| None = None`, comment cites R15-DATA-071 directly — a truncated series is now labeled, not silently presented as full | holds |
| R15-DATA-078 | `grep -n "alpha_vantage\|R15-DATA-078" docs/BLUEPRINT.md` | `docs/BLUEPRINT.md:266-267`: "yfinance fallback (no API key needed for basic use; R15-DATA-078 — alpha_vantage was never built and is dropped from this list, not just unimplemented)" — the doc no longer promises a provider that doesn't exist | holds |
| R15-DATA-079 | `curl :52346/quant/option/chain/RELIANCE` | Full real options chain: 78 contracts across multiple expiries with real `open_interest`/`strike`/`last_price`/`settle_price`/`volume`, provider `nse-fo-bhavcopy`; `open_interest: float \| None` present in `sidecar/models/market.py:102` and mirrored in `types/data.ts:92` — a working options-chain capability now exists end to end | holds |
| R15-DOCS-018 | Read `docs/CURRENT_STATE.md:93`, `sidecar/services/provider_registry.py` docstring | Docs now describe "resolves by standard model key + [preference order]" matching the actual resolver code ("dispatch is no longer a hardcoded if asset_class switch — it is a resolver keyed by a STANDARD MODEL KEY... PREFERENCE ORDER") — doc and code agree | holds |
| R15-LEAD-010 | Read `sidecar/services/sec_filings_provider.py:582-604` (`get_filing`) | Docstring cites R15-LEAD-010 directly: the lookup runs over the form-filtered list first when a form-type hint is given, then falls back to the unfiltered list on a miss; each pass opens with a 40-row window widening to 100 only when a full window misses | holds |
| R15-LEAD-013 | In-process python: loaded `sidecar/services/screener_universes/sp500.json` (503 symbols), checked the register's 14 named delisted tickers and 3 named missing tickers | All 14 delisted tickers (MMC, FI, ANSS, CTLT, DAY, DFS, HES, HOLX, IPG, JNPR, K, MRO, WBA, CTRA) absent; all 3 missing tickers (BXP, NVR, UDR) present | holds |
| R15-LIFECYCLE-026 | `ps -o time=,%cpu=,etime= -p 19284` (own sidecar worker) sampled 3x across a 291s window with zero curl/HTTP activity to the sidecar in between | Instantaneous 0.1% CPU at the final sample; window-average ~4.75% (includes settling right after a prior curl burst) — far below the register's ~60% buggy baseline and in line with the fix_shape's <5%-over-idle bound | holds |

Summary: 7 holds. No regressions.
