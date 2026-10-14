# Refutation audit round 4 — datapack — R15-RESEARCH-017 (key rc1-battery-9:1)

Auditor: Opus, follow-up group `datapack`. Written 07:12 IST. HEAD 06a8535c. The code tree
equals 01015033 (checked as in the DATA-008 file).

## Verdict: not_a_defect (the verifier's concurrence stands). failure_count 0.

At HEAD, an injected `gather_floor` raise in the prologue gives the same result at both depths.
It does not escape. Both return the typed failure `ok:false` with
`degraded_reason: "the {iter|heavy} research loop failed: RuntimeError: ..."` and an
`execution_loop` that names the loop. Neither depth produces a brief. With the injection removed,
the same harness produces a brief at both depths (`ok:true`). The asymmetry the entry named is
gone: ULTRA losing the brief while DEEP degraded to a single-pass fallback. The single-pass
fallback the closure note describes no longer exists at either depth. R15-CODE-RESEARCH-003
deleted it on purpose (status fixed, 68bb7aa4 batch 8). Its fix shape: "Delete run_deep_research
(iter's abort->synthesize covers degradation)". The `_run_loop` docstring says: "never a second,
differently-behaving loop".

## Command and output (real user-facing chain, both engines)

Script: `<scratch>/research017_both.py`, run with the repo venv from the main worktree
(`cd sidecar && VYSTED_DATA_DIR=<scratch>/data ./.venv/bin/python <scratch>/research017_both.py`).
It drives `deep_research.run_deep_brief(query, depth=..., rounds=1, wall_seconds=30)` →
`_run_native` → `_run_loop` → `iter.run_iter_research` (DEEP) / `iter.run_heavy_research` (ULTRA).
It patches `services.research.disclosures.gather_floor` to raise
`RuntimeError("refaudit4 injected: gather_floor failed (battery rc1b9 shape)")`, the same seam
and exception type the battery shard used. Only network and LLM seams are stubbed:

- `config.get_llm_creds` → ollama stub
- `oneshot.complete_with_usage` → canned text
- `iter.resolve_target` → the bound India target KAYNES.NS, so `wants_disclosures_floor` fires
- `iter.snapshot_structured` → stub legs
- `agent_tools.invoke_tool` and `visit_for_research` → stubs

Nothing spends.

Results (`<scratch>/research017_both.results.jsonl`). The `depth` key was overwritten by the
result's own `depth` (null on failure), so `execution_loop` identifies the engine:
`iter` = DEEP, `heavy` = ULTRA.

```
gather_floor raises, DEEP : escaped false, ok false, execution_loop "iter",
  degraded_reason "the iter research loop failed: RuntimeError: refaudit4 injected: gather_floor failed (battery rc1b9 shape)",
  message "Deep research could not finish — the iter research loop failed: ...", has_markdown false
gather_floor raises, ULTRA: escaped false, ok false, execution_loop "heavy",
  degraded_reason "the heavy research loop failed: RuntimeError: refaudit4 injected: ...",
  message "Deep research could not finish — the heavy research loop failed: ...", has_markdown false
control (no raise), DEEP : ok true, execution_loop "iter",  mode "deep",  has_markdown true, n_sources 2
control (no raise), ULTRA: ok true, execution_loop "heavy", mode "heavy", has_markdown true, n_sources 2
```

Repo pin at HEAD: `sidecar/.venv/bin/python -m pytest -q tests/test_b6_research_funnel.py -k
honest_failure` → `1 passed`. `test_ultra_heavy_raise_is_an_honest_failure` asserts
`ok is False`, `execution_loop == "heavy"`, the reason carries the exception, and the iter loop
is never run as a second attempt.

## Code read

- `sidecar/services/agent_tools/deep_research.py:294-298`: the heavy branch has
  `try: run_heavy_research(...) except Exception as exc: return _loop_failed("heavy", exc)`.
- `:319-322`: the iter branch has the same wrap, `return _loop_failed("iter", exc)`.
- `:325-335`: `_loop_failed` returns `{ok: False, message, execution_loop, degraded_reason}`.
- `:415-418`: `run_deep_brief` passes the dict through with `execution_loop` set.
- `sidecar/services/research/iter.py:378-386` (DEEP) and `:986-995` (ULTRA): both prologues call
  `gather_floor` unguarded, so the same failure takes the same path at both depths.
- `sidecar/services/research/disclosures.py:152-156`: `gather_floor` guards its own feed call
  (`except Exception: # a feed miss is soft`). The injected raise therefore stands in for an
  unexpected internal bug, not a feed outage.

## Why the battery claim does not hold

The shard file `battery/raw/set-23/R15-RESEARCH-017.txt` starts with "heavy research loop raised"
and a traceback. That is the `logger.exception` line inside `_loop_failed`
(`deep_research.py:328`), not an exception reaching the caller. The shard's own second JSON block,
the user-facing equivalent, shows `ok:false` with the typed `degraded_reason`.

Its first block ("ESCAPED_run_heavy_research_itself") calls the inner function directly, outside
`_run_loop`, which by design has no guard. The shard's finding really means "ULTRA no longer
falls back to a single-pass brief". That is true, but DEEP no longer does either. The difference
between the closure note's "ok:true, loop:heavy, n_sources:14" fallback and today's typed failure
comes from the later R15-CODE-RESEARCH-003 fix. It is not a return of the depth asymmetry.

## Notes (not counted)

- The register closure note for R15-RESEARCH-017 is stale against HEAD. It still describes the
  batch-6 single-pass fallback, and its fix_shape pin ("still yields a published single-pass
  brief") is superseded by R15-CODE-RESEARCH-003. The register should cite 68bb7aa4 and the
  current pin, `test_ultra_heavy_raise_is_an_honest_failure`.
- Design question, not a defect of this entry's class: an unexpected prologue exception now
  costs the whole DEEP/ULTRA brief at both depths, with an honest typed message. Whether a
  prologue enrichment (the filings floor) should be fenced so the loop continues without it is
  an operator product call. It was taken implicitly by CODE-RESEARCH-003.
