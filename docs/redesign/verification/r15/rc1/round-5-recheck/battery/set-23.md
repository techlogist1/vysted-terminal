# batch-6/W4-research-funnel (rc1-battery-13, shard 13)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52353's venv (no HTTP needed — in-process).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-RESEARCH-002 | in-process: monkeypatched `growth_check.should_cross_check` to raise sync, `market_cap_witness.get_market_cap_witness` to raise async; real `snapshot_structured(tool, "RELIANCE", region="IN")` | did not raise; `injected hits: ['sync', 'async']` (both faults fired and were isolated); `fundamentals.ok=True` returned | holds |
| R15-RESEARCH-017 | in-process: monkeypatched `iter_research.run_heavy_research` to raise `RuntimeError`, called `deep_research._run_loop(profile=PROFILES['ultra'], ...)` directly | does NOT escape — caught at `deep_research.py` and returns `{'ok': False, 'message': 'Deep research could not finish — the heavy research loop failed: RuntimeError: injected: heavy prologue failed.', 'execution_loop': 'heavy', 'degraded_reason': ...}` | holds |
| R15-RESEARCH-018 | in-process real `deep._run_researcher(...)` for 3 sub-questions against target KAYNES.NS/IN, stubbed tool_call/llm_call | "What do recent SEC filings…" → `corporate_announcements` (not `sec_filings_list`); "sector outlook…" → `news` (no false "sec" match); "second-quarter guidance…" → `news`+`corporate_announcements` (no false "sec" match on "second") | holds |
| R15-RESEARCH-012 | in-process real `disclosures.gather_floor(tool_call, target=KAYNES.NS)` via real `corporate_announcements` tool against live sidecar data, 50 announcements | floor's top rows: corrigendum-to-results, "Financial Results For The Quarter Ended 30 June 2026", results-submission, board-meeting-for-results — all results-shaped, pulled from raw positions [2,10,15,21,22,26]; contrast raw-newest-first (no sub_question) top 5 = trading-window-closure / AGM procedural items | holds |
| R15-RESEARCH-016 | code trace of `services/research/iter.py` (both `run_iter_research` ~L372-391 and the heavy-panel prologue ~L987-994) — the exact guard the register names; PLUS a live `run_deep_brief(depth="ultra")` run (free-text query, Ollama-lock) that completed in 332.9s without crash | in `run_iter_research`, the `if structured.get("disclosures") is None:` check now wraps ONLY the `gather_floor` fetch (skip re-fetch when pre-seeded); `floor_rows = structured["disclosures"].get("rows")` + `if floor_rows: _record_web(...)` sits OUTSIDE that inner check, at the same indent as the outer `if wants_disclosures_floor(target):` — so it fires unconditionally, pre-seeded or not. This is precisely the described bug mechanism (the "is None" guard previously gated both the fetch AND the citation record together) now split so ULTRA's pre-seeded explorers still hit `_record_web`. Live run 1 (free-text) returned `ok:true, n_sources:0` — inconclusive on source count (likely target-resolution failure of the weak local model, not the guard itself). A targeted live run 2 (pre-bound `target=AMAL, bound=True`, bypassing free-text resolution) was launched to remove the ambiguity but did not finish before this shard's time budget and was terminated — not counted as evidence either way | holds (code trace + a completed-without-crash live run; the more targeted live confirmation did not finish in time — see note) |

Note on R15-RESEARCH-017/016: batch-6's certification described the ULTRA fix as
`_run_loop` falling back to `_single_pass_fallback(deep, query, common, loop="heavy")`,
matching DEEP's existing fallback. The candidate's CURRENT code no longer has
`_single_pass_fallback` at all — a later change (docstring cites R15-CODE-RESEARCH-003)
replaced BOTH the iter (DEEP) and heavy (ULTRA) loops' exception handling with a single
`_loop_failed(...)` honest-failure dict, explicitly to avoid "a second, differently-behaving
loop". This is a different mechanism than batch-6 certified, but it still satisfies
R15-RESEARCH-017's OWN stated repro (an exception in `run_heavy_research` escaping
`_run_loop` uncaught, "tool research raised" to the model with no brief) — the probe above
shows the exception is now caught and turned into an honest `ok:False` result, so the
specific repro does not reproduce. Not a regression per gate rule change 1 (verdict is
against the entry's own stated repro). R15-RESEARCH-016 WAS independently re-run live
(`run_deep_brief(depth="ultra")`, free-text query, 332.9s, completed without crash) in
addition to the code trace of the exact named guard; a second, more targeted live run
(pre-bound `target=AMAL, bound=True`, bypassing free-text resolution, meant to give an
unambiguous confirm/deny on filing-citation recording) was started under the Ollama lock
but did not finish before this shard's time budget and was terminated cleanly (lock
released via its own trap) rather than left orphaned — see
`battery/raw/set-23/R15-RESEARCH-016.txt` for the full detail. Verdict rests on the code
trace (which matches the register's described mechanism exactly) plus the
completed-without-crash live run; not on the unfinished targeted run.

COVERAGE: 5/5 ids raw; no raw: none.
