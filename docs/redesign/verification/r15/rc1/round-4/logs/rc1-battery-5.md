# rc1-battery-5 — regression battery shard 5, gate round 4

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad confirmed at start
(`git rev-parse HEAD` on the scratch worktree). Own sidecar booted from
source on :52345 against a copy of the seed data (`rc1-round-4-data-battery-5`),
sleep pid 74767 / worker pid 74770. Sets covered: batch-7/W3-unattended-chart-workspace
(set-27, 10 ids), batch-9/W2-research-search-news (set-36, 4 ids),
batch-16/W1-one-writer-set (set-67, 2 ids).

## Method
- Read each register entry (repro + evidence) and the certifying batch's VERDICTS.md
  ("Per-entry evidence") before re-running.
- Entries certified only through a permanent, repo-tracked vitest/pytest file are
  verdict `ci_pinned` naming the test (never ran vitest/pytest suites, per role rules):
  R15-UI-020, R15-UI-023, R15-UI-031, R15-CODE-FRONTEND-017, R15-UI-026,
  R15-CROSS-PLATFORM-002.
- Everything else was re-run live: curl against my own sidecar (workspace corrupt/quarantine,
  507 permission, __autosave__ exposure, quant process-pool offload, the workflow scheduler +
  webhook end-to-end with a local receiver on :52999, NewsAPI fake-key rejection), or an
  in-process python call against the candidate's sidecar venv with only the network transport
  monkeypatched (adr_ratio.lookup miss-caching, simulating an unreachable EDGAR).
- R15-AGENT-090 (batch-16) required the shared Ollama lane: took the lock
  (`mkdir /tmp/vysted-r15-ollama.lock`), ran the exact original prompt through
  `scripts/r15/vy.py` against llama3.1:8b on my sidecar, released the lock via a trap on exit.

## R15-AGENT-090 note
The re-run's guard held on its core claim (no fabricated "1:1"/"1:2" ratio, no false
tool-attribution framing) but left a trailing "6 ordinary shares." fragment with no ok tool
call behind it (the tool called was `financial_statements`, not `fundamentals`, which the
AGENT-090 guard specifically covers). This is the same class as R15-LEAD-030/037/038
("the local model states a figure for a subject with no ok tool call behind it"), blocked_tier4
per DECISIONS 4.9-4.12 and the round-4 lead note's explicit standing rule for that class:
filed as a concurrence note (in `battery/raw/set-67/R15-AGENT-090.txt` and `battery/set-67.md`),
not to findings[], not a regression, not a fix-round candidate.

## Result
16/16 ids covered, all holds/ci_pinned, 0 regressed, 0 needs_gui, 0 blocked_env.
0 findings (no register-worthy regressions or new defects surfaced).

COVERAGE: 16/16 ids raw; no raw: (none).
