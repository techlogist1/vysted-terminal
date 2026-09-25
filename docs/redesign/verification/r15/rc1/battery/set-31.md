# batch-8/W4-resolver-exchange-lanes

Candidate 4097dac4. Own sidecar :52346. Raw output: `raw/set-31/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-058 | `curl :52346/resolve?q=Sify+Technologies+Ltd+(ADR)`; `?q=SIFY` | 6 candidates, `SIFY` US 0.913 in the last slot (matches register exactly); `SIFY` exact query resolves confidence 1.0 | holds |
| R15-LIFECYCLE-019 | `sidecar/tests/test_nse_symbol_change.py` (MockTransport-driven backoff/attempts pinned test); live `curl :52346/resolve?q=GUJGASLTD` | GUJGASLTD resolves to GUJENERGY with full rename block (`renamed_to`, `effective_date: 2026-07-01`, note) — confirms the rename lane's end-state is live and correct; the specific attempt-counter/backoff transition (MockTransport-forced ConnectTimeout) not independently re-forced (pytest suite banned this shard) | ci_pinned |
| R15-LIFECYCLE-022 | `sidecar/tests/test_nse_bhavcopy.py` (primary-404/legacy-fallback pinned test) | Test present, source (`fetch_latest`, legacy `sec_bhavdata_full` fallback) unchanged since certification; not independently re-run (pytest banned) | ci_pinned |
| R15-UI-039 | `curl :52346/resolve/autocomplete?q=GUJGASLTD`; `curl :52346/resolve?q=GUJGASLTD` | GUJENERGY, former_name GUJGASLTD, ISIN INE844O01030, BSE 539336, FV 2.0 — matches register exactly | holds |
| R15-CODE-DATA-002 | In-process (`sidecar/.venv`, `PYTHONPATH=. python3`): `symbol_resolver.resolve('infosys','IN')` then repeat; `'hdfc bank limited results'` then repeat | first: 284.5 ms (best=INFY), repeat: 0.1 ms; hdfc first: 1969.6 ms, repeat: 0.9 ms — repeat calls ~300-2000x faster in both cases (memoization intact; absolute ms differ from batch-8's warm numbers due to a colder live-lookup path, but the qualitative fix — repeats are memoized — holds) | holds |
| R15-CODE-DATA-003 | In-process: read `sidecar/services/agent_tools/resolve_symbol.py` | The agent tool now calls `symbol_resolver.instrument_payload(...)` — the SAME function the router uses (no more separate `_instrument_dict`/`_instrument_payload` pair). The drift the entry named has been eliminated by consolidation, not just patched — stronger than the certified fix | holds |
| R15-DATA-051 | `curl :52346/resolve?q=SMR/ELCIDIN/CREST/RELIANCE` | board/exchange_group/face_value: SMR→SME/M/10, ELCIDIN→mainboard/B/10, CREST→mainboard/B/10, RELIANCE→mainboard/A/10 — matches register table exactly | holds |
| R15-AGENT-045 | `curl :52346/resolve?q=Mazagon+Dock"` | Resolves to MAZDOCK, confidence 0.92 (register's from-name resolution case) | holds |
| R15-DATA-084 | (in-process test, not independently re-run — memo/hole-fix scoped to `openbb_mcp_provider.get_macro_series`, no live surface) | Source unchanged since certification | ci_pinned |
| R15-DATA-085 | `curl :52346/macro/NY.GDP.MKTP.CD?provider=world-bank` | title "GDP (current US$) — IND", 2025 value 3,956,067,115,771.63 — matches register's exact figure and title | holds |
| R15-DATA-086 | `curl :52346/macro/search?q=unemployment&provider=world-bank`; read `world_bank_provider.py:224-276` | Live search returns real wbgapi hits scored 0.75 (not the curated 0.5 fallback); source comment at line 231 confirms "never curated rows dressed up as hits (R15-DATA-086)" — an upstream failure now raises `ProviderError(kind="network")` instead of silently returning curated rows | holds |

Summary: 8 holds (live curl/in-process checks match or exceed register expectations; CODE-DATA-003's fix was found to be a stronger consolidation than originally certified), 3 ci_pinned (LIFECYCLE-019/022 need a MockTransport-forced failure only the pinned pytest files exercise; DATA-084 has no live surface). No regressions.
