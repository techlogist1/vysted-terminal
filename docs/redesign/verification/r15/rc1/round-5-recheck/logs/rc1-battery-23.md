# rc1-battery-23 — regression battery shard 23 (stage-c batch-9/10/11/13)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via `git rev-parse HEAD` in the shared scratch worktree).
Own sidecar: `127.0.0.1:52363`, source cwd `<cand>/sidecar`, data dir `rc1-round-5-recheck-data-rc1-battery-23` (cp'd from the seed), sleep-wrapper pid `3994`.
MCP env: `VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154` (shared read-only stack).

## Sets

- **set-38** (batch-9, W4-market-lanes-errors-quant): DATA-066, DATA-062, LIFECYCLE-021, UI-053, DATA-065, DATA-073, UI-051 — all 7 holds, curl/in-process probes only.
- **set-44** (batch-10, W5-chat-search-workflow): AGENT-082, AGENT-088, UI-027, RESEARCH-028, AGENT-063, CODE-RESEARCH-004 — 5 holds (AGENT-082 via live `vy.py`+ollama, AGENT-088/CODE-RESEARCH-004/AGENT-063/RESEARCH-028 via curl + source), UI-027 ci_pinned (pure client-side keybinding-conflict logic, no sidecar route, no GUI this run — source trace corroborates but the only executable repro is the vitest suite, which the battery role is barred from running).
- **set-51** (batch-11, W3-agent-eval): AGENT-007 — bounded live re-run of `scripts/agent_eval/run.py` (k=1, 5 of the 16 scenarios, `--max-minutes 14`, ollama llama3.1:8b, under the Ollama lock) rather than the full k=3×16-scenario 45-min harness the batch-11 verifier ran; see set-51.md for the scoping rationale and results.
- **set-62** (batch-13, unassigned): DOCS-017 — holds, live universe counts byte-identical to the doc and the certification.

## Ollama lock usage

Three holds, all wrapped `trap 'rmdir /tmp/vysted-r15-ollama.lock' EXIT INT TERM HUP` so the lock releases on completion or failure, all acquired on the first `mkdir` attempt (no contention observed): `agent082-vy.log`/`agent082-events.jsonl` (AGENT-082 live spend_usd check, ~56s); `agent007-run.log` (first agent-eval attempt, failed fast on a harness mistake — ran with system `python3` instead of the sidecar's venv, so `services.agent_tools.catalog`'s `pydantic` import failed; not a product defect); `agent007-run2.log`/`agent007-out/` (the corrected re-run with `sidecar/.venv/bin/python3`, ~4.5 min for 5 scenarios).

## Coverage

15/15 ids in my sets have a raw file under `battery/raw/set-{38,44,51,62}/`. Full detail: see each `battery/set-*.md`.

COVERAGE: 15/15 ids raw; no raw: none.
