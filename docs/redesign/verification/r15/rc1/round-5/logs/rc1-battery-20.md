# rc1-battery-20 — regression battery shard 20 (gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, verified at start via
`git -C <cand> rev-parse HEAD`.

Sets: batch-3/W4-research-depth (set-8, 7 ids), batch-28/W6-sonnet (set-79, 7 ids),
batch-12/W4-research (set-58, 1 id), unplanned-1 (set-86, 1 id). No prior round-5 files for
this label existed at start (fresh shard).

## Approach

For each id, first read the register entry (repro + evidence) and the certifying batch's
VERDICTS.md "per-entry evidence". 15 of 16 ids now have a **pinned** test in the repo's own
test tree (`sidecar/tests/test_*.py`, `src/**/*.test.ts(x)`) whose docstring/describe/it names
the exact register id and asserts the exact original repro — including the 7 batch-28 entries
that were originally certified only via scratch vitest files that were deleted afterward
(VERDICTS.md: "All were deleted afterwards"); permanent pinned tests for those ids exist in the
candidate tree today. Per the harness's own rule ("Never run vitest or pytest suites... an
entry certified only through a pinned test → verdict ci_pinned naming the test"), these were
NOT executed — each was verified by reading the pinned test's source at the candidate sha and
confirming it covers the original claim, with the read captured as the raw evidence file.

R15-LEAD-043 (set-86) has no pinned test naming it, so it was re-run live: one sidecar boot on
:52360 (own copy of seed data), `vy.py invoke copilot "hi" --provider openai --model gpt-4o-mini
--mode agent --autonomy ask --no-key` — the register's own literal repro. Result: humanized
`auth` error ("No OpenAI API key is set — add it in Settings."), not the generic internal-error
frame. A parallel `--provider groq` attempt failed because `vy.py`'s own `--provider` choices
don't include `groq` (`{openrouter,openai,deepseek,ollama}` only) — noted as an environment
limitation of the harness script, not a product defect; the openai half is the register's
literal repro and reproduces fixed.

## Sidecar

Booted once for the whole shard (only needed for LEAD-043): main sidecar from
`<cand>/sidecar` on 127.0.0.1:52360, data dir
`.../scratchpad/rc1-round-5-data-rc1-battery-20` (copy of the round's seed data). `/health`
confirmed ok before the probe. Stopped at the end (killed its own worker pid after its sleep
wrapper's pid didn't cascade the kill fast enough; verified `/health` down; did not touch any
other owner's sleep/worker pid or port — several other roles' stacks were visibly running
concurrently on other ports and were left alone).

## Result

0 regressions. All 16 entries hold on the candidate.

COVERAGE: 16/16 ids raw; no raw: none.
