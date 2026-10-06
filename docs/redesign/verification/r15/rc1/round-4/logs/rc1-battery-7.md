# rc1-battery-7 (regression battery shard 7)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (verified via `git rev-parse HEAD` in
`rc1-round-4-cand`).

Sidecar: own instance on `127.0.0.1:52347`, cwd `<cand>/sidecar`, data dir copied from
`rc1-round-4-seed-data` to `rc1-round-4-data-battery-7`. Boot wrapper shell pid `74910`
(`sh -c 'sleep 86400 | ./.venv/bin/python3 main.py ...'`), python worker pid `74913`.
`/health` confirmed ok before any probe.

Sets (per task assignment — note: my assigned entry ids did NOT match the stale
`r15/rc1/battery/set-{11,43,69}.md` files already in the repo from an earlier gate round;
those are round-3 files at candidate `4c6dfe8c`/`01d6920a`, out of scope per the harness
rule, referenced only to pull the batch verifier's original repro shape):

- set-11 = batch-4/W2-workflow-backtest-feeds: R15-AGENT-015, R15-CODE-PLATFORM-002,
  R15-AGENT-016, R15-CODE-PLATFORM-003, R15-CODE-FRONTEND-006, R15-CODE-PLATFORM-016,
  R15-DATA-040, R15-DATA-029, R15-DATA-030 — 7 holds, 2 ci_pinned (frontend SSE-wiring
  entries verified by source read since vitest is the heavy lane's).
- set-43 = batch-10/W4-screener-routes-statedocs: R15-DATA-061, R15-DATA-087,
  R15-RESEARCH-025, R15-CROSS-PLATFORM-003, R15-DATA-095, R15-DOCS-016 — 6/6 holds.
- set-69 = batch-18/W1-agent-runtime-citation-guard: R15-LEAD-033 — live two-turn
  ollama/llama3.1:8b run under the local-model lock, port 52347.

Method: register `repro` field for the original defect + batch VERDICTS.md "Per-entry
evidence" for what the fix looks like, then re-ran the same probe in-process (candidate
venv) or live (curl against :52347) against 1006c6da. Never ran pytest/vitest suites.

Ollama lock: acquired (`mkdir /tmp/vysted-r15-ollama.lock`) immediately (no contention),
held via a `trap ... EXIT` wrapper around the LEAD-033 two-turn script so it releases on
success or failure; released automatically at script end.

Full per-set tables: `battery/set-11.md`, `battery/set-43.md`, `battery/set-69.md`.
Raw probe output: `battery/raw/set-11/`, `battery/raw/set-43/`, `battery/raw/set-69/`.

Sidecar stopped at end of shard: killed wrapper pid 74910, then worker pid 74913 (both
confirmed gone; `/health` on 52347 refused after).

Result: 15 holds (7 set-11 direct + 2 ci_pinned + 6 set-43 + 1 set-69 (LEAD-033, live
two-turn ollama/llama3.1:8b under the lock)), 0 regressions, 0 new defects, 0 needs_gui,
0 blocked_env.

COVERAGE: 16/16 ids raw; no raw: none.

Other agents' concurrent ollama traffic was visible on other ports (52344, 52326, etc.)
during my lock hold — noted, not a defect of this shard; the lock was free when I
acquired it and released automatically (trap) at script end.
