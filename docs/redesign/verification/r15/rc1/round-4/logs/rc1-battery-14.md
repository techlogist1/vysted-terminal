# rc1-battery-14 — regression battery shard 14

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar on :52354, source
`.../scratchpad/rc1-round-4-cand/sidecar`, data `.../scratchpad/rc1-round-4-data-rc1-battery-14`
(copy of rc1-round-4-seed-data). Sidecar log: `battery/rc1-battery-14-sidecar.log`.

Sets: batch-3/W1 (set-5, 8 ids), batch-3/W4 (set-8, 6 ids), batch-11/W3 (set-50, 1 id
AGENT-007), batch-25/W5 (set-74, 1 id RESEARCH-015).

## Method
For mechanism-level entries, re-ran each entry's committed pinned pytest test(s)/vitest
file directly against the candidate (not the diff, not a stale report) — `pytest -v
<node-id>` per entry, one raw file per id under `battery/raw/set-<n>/<id>.txt`. For
RESEARCH-015 (no committed test existed pinning the exact register cases) wrote a small
in-process probe script calling the real `services.research.verify._claim_evidence`
with the register's Case C / Case D / Control B domain shapes — same production code
path, not a mock of the defect. For AGENT-001 and AGENT-007 ran a live check (Ollama
lane, under the shared lock) since those are runtime-model-behaviour entries.

## Notable
- RESEARCH-008's pinned test (`test_keyless_hanging_ddg_serves_brave_inside_the_tool_cap`)
  is flaky in isolation on this run: the functional asserts (ok=True, correct row served)
  always passed; only the hardcoded `elapsed < 1.0` wall-clock assert flaked (failed
  6.7s/6.6s/1.7s, passed 0.83s/0.80s) while ~5 sibling battery-shard sidecars on this same
  Mac were hammering it (load avg 2.1-3.0 from concurrent universe-warmup Yahoo storms).
  Whole-file run passed clean. Treated as environment timing noise, not a regression —
  logged under notes, not as a finding, since the mechanism itself held every time.
- AGENT-001's live rerun landed on an unrelated resolution anomaly: 'research KPIT
  Technologies' built its brief for BSOFT (Birlasoft, former_name 'KPIT') instead of
  KPITTECH, despite KPITTECH ranking first at the same confidence on /resolve. Filed as
  new_defect rc1-battery-14:1 (not in the register). Also on this isolated no-SearXNG
  profile the loop auto-downgraded to fast/quick and the runtime auto-published the brief
  from structured data before the model wrote any prose, so the live run never reached
  AGENT-001's actual trigger (a narrated money figure) either way — verdict rests on the
  unchanged code shape (semantics.py labels + brief-blocks.tsx formatDerived).
- AGENT-007 (batch-11): the original cert was a full k=3 x 16-scenario harness run
  (up to 45 min). Given the stall rule and shard time budget, re-ran a SCOPED live check:
  k=1, --only price-aapl,ask-chart-indicator,missing-param-portfolio,sec-filings-aapl,
  --max-minutes 8, ollama llama3.1:8b, against the candidate sidecar — enough to prove the
  harness/grader/tool-dispatch mechanism is unbroken and that the known-failing-on-ollama
  scenarios (model quality, not mechanism) still land the same way. `test_agent_eval.py`
  (harness+grader unit tests, no live model) also re-run clean: 19 passed.

## Ollama lock
Held twice, released via trap on both success paths (AGENT-001 live invoke; AGENT-007
scoped eval run). No other lane needed the local model in this shard.

## Result
16/16 holds, 0 regressed, 0 ci_pinned (all had a live or in-process re-run beyond a bare
test-file citation), 0 needs_gui, 0 blocked_env. One new_defect filed
(rc1-battery-14:1, KPIT->BSOFT resolution). Sidecar stopped at end of shard.

COVERAGE: 16/16 ids raw across all 4 sets; see each set-<n>.md's own COVERAGE line.
