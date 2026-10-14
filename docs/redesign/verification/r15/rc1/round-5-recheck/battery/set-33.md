# batch-8/W4-resolver-exchange-lanes (set-33.md)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Shard rc1-battery-3. Own sidecar
`:52343` (source, data dir `rc1-round-5-recheck-data-battery-3` copied from the seed).
Every id's original repro re-run live in-process against the candidate's venv, or via
`curl` against the shared/own sidecar. Raw output: `battery/raw/set-33/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-003 | Both `routers/resolve.py` and `agent_tools/resolve_symbol.py` now project through one shared `symbol_resolver.instrument_payload()` (grep + in-process call on GUJENERGY) | Single function, `confidence=round(score,4)` and the `rename` block shape identical at both call sites; source docstring: "the ONE wire shape ... both project through it" | holds |
| R15-UI-039 | `GET /resolve/autocomplete?q=GUJGASLTD` and `?q=GUJEN` (own sidecar) | Typing the retired ticker or a live prefix both return `GUJENERGY` with full `rename` provenance (`renamed_from/to`, `effective_date`, `note`) — autocomplete now runs through the same rename/enrichment stage as `/resolve` | holds |
| R15-DATA-051 | `GET /resolve?q=SMR` and `GET /fundamentals/CREST` (own sidecar) | `/resolve` identity now carries `board:"SME"`, `exchange_group:"M"`, `face_value:10.0` for SMR (matches outside BSE truth); `/fundamentals/CREST` still has no board/face_value key (matches the entry's own note: only the `/resolve` identity payload was certified fixed, `/fundamentals` was explicitly left open at closure) | holds |
| R15-DATA-058 | `GET /resolve?q=Sify+Technologies+Ltd+%28ADR%29` (own sidecar) | Top candidate is now `SIFY` (confidence 0.913), ahead of the IN-locale fuzzy rows that previously buried it under the 6-candidate cap | holds |
| R15-CODE-DATA-002 | In-process: `symbol_resolver.resolve("infosys","IN")` with `_live_lookup` stubbed, called 3x, `_scan_names.cache_info()` | First call ~293ms, repeat calls ~0.09ms; `CacheInfo(hits=2, misses=1, maxsize=256)` — `_scan_names` is `@lru_cache(maxsize=256)`, named for this entry in the source comment | holds |
| R15-LIFECYCLE-019 | In-process mock-transport: `_download_and_parse` fails once (Exception, non-empty `type(exc).__name__` logged) then returns a real `SymbolChange` row; ran `_refresh_guarded()` | 2 attempts total; `_refreshed_on` stayed `None` after the failed attempt and was stamped only after the retry succeeded; `_active_map` loaded | holds |
| R15-LIFECYCLE-022 | In-process mock-transport: primary UDiFF URL 404s, `sec_bhavdata_full` legacy fallback returns 200 + rows; ran `fetch_latest(max_lookback_days=1)` | Fallback host was requested on the primary 404 (both URLs in `calls`), `fetch_latest` returned the fallback's rows, no `{"empty": true}` marker was written to the cache | holds |
| R15-AGENT-045 | In-process: `_compare_symbols({"symbols": ["COCHINSHIP", "MAZAGONDOCK"]})` — the exact two-symbol case the batch-7 refuter flagged as still broken | `ok:false` with `MAZAGONDOCK` carrying `"error": "unresolved name: 'MAZAGONDOCK' is not a known ticker and matched no listing — retry with the company name or the exact exchange ticker"` in both the per-symbol entry and the top-level `message` — no longer reads as a bare "no quote available" | holds |
| R15-DATA-084 | In-process: `get_macro_series("EFFR")` with a stubbed `_call_tool` returning `value: 0.0` for the first row | `observations[0].value == 0.0` (preserved, not `None`); `_first_present()` replaced the `or`-based key fallback, comment names R15-DATA-084 | holds |
| R15-DATA-085 | In-process: `get_series("NY.GDP.MKTP.CD","USA")` with a fake wbgapi client whose `series.info(...).items` is a plain list (no `callable` guard) | `title == "GDP (current US$) — USA"`, not the raw indicator code; source comment names R15-DATA-085 and explains the old `callable(info.items)` guard never fired | holds |
| R15-DATA-086 | In-process: `world_bank_provider.search("unemployment")` with a client whose `series.list` raises; then `macro_router.search(..., provider="world-bank")` | `search()` now raises `ProviderError` instead of returning curated fallback rows scored as real hits; `macro_router.search` propagates the error and writes nothing to the cache (`written == {}`) | holds |

COVERAGE: 11/11 ids raw.
