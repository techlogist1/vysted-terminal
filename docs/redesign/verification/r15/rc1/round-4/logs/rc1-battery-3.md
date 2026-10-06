# rc1-battery-3 — regression battery shard 3 (batch-5 W5, batch-10 W2, batch-13 W3)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` — verified via
`git -C <cand-worktree> rev-parse HEAD` before starting.

Own sidecar booted from the candidate's `sidecar/` source on `127.0.0.1:52343`,
data dir `rc1-round-4-data-battery3` (copied from the keyless isolated seed).
Sleep-wrapper pid 60830, worker pid 60833. `/health` green within ~5s of boot.
Stopped both pids at the end of the shard; `/health` then connection-refused
(confirmed).

## Sets run

- `set-19.md` (batch-5/W5-screener-earnings-sec, 11 entries) — all 11 holds/ci_pinned,
  no regressions. Highlight: R15-DATA-110 live cold sp500 screen now evaluates
  478/503 (4.97% skip, under the 5% target) via the new seeded snapshot basis,
  vs. the pre-fix 100%-skip/0-evaluated failure the register described.
- `set-41.md` (batch-10/W2-catalog-hostactions, 4 entries) — all 4 holds/ci_pinned.
  Highlight: R15-RESEARCH-030 re-invoked the transcript tool live (in-process,
  no LLM needed) and got the same KPITTECH transcript batch-10 certified against.
- `set-65.md` (batch-13/W3-docs-017-india-universe-counts, 1 entry) — holds;
  live universe counts (nse-all 3506, bse-all 5042, india-all 5891, sp500 503)
  match the doc and the batch-13 cert exactly.

## Verdict mix and why

Most screener-UI entries (UI-055, UI-056, CODE-DATA-006, UI-045, AGENT-084)
verdict `ci_pinned` rather than `holds`: their original certification rendered
the React tree live or drove a live LLM tool-use turn; this shard's mandate
excludes running vitest/pytest, and I did not spin up a browser or an Ollama
run for a frontend-only rendering check. For each I read the shipped code
(the exact fix mechanism the register/PLAN.md described) and named the pinned
vitest test that encodes the behaviour, rather than asserting `holds` on code
reading alone for something a test suite is the actual arbiter of.
Sidecar-observable entries (DATA-110, CODE-DATA-004, LIFECYCLE-017/020,
DATA-028/032/067, CODE-AGENT-013, RESEARCH-030, CODE-PLATFORM-021, DOCS-017)
were probed live against the running candidate sidecar and verdict `holds`.

## New defect found

`rc1-battery-3:1` (low, new_defect): `docs/CURRENT_STATE.md:356-358` still
describes the pre-fix earnings behaviour (`fiscal_period` "inferred from
calendar month", EPS stddev "an approximation (high−low)/4") that the merged
DATA-032/DATA-067 fix removed — live probe in set-19 shows both fields are now
`null`. Filed as new_defect since it is outside R15-DOCS-017's own scope
(a different section of the same doc file) and is not itself a register entry.

COVERAGE: 16/16 ids raw across all three sets; no raw: none.
