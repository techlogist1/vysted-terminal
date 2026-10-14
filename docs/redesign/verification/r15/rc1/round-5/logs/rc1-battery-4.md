# rc1-battery-4 — regression battery shard 4 (gate round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar booted from candidate
source on :52344 against a fresh copy of the round-5 seed data
(`rc1-round-5-data-rc1-battery-4`), openbb-mcp/sec-edgar-mcp shared read-only on
:52153/:52154.

Sets: batch-5/W5-screener-earnings-sec (set-19, 10 ids), batch-10/W2-catalog-hostactions
(set-40, 4 ids), batch-6/W1-india-exchange-data (set-20, 1 id), batch-14/W1-agent-runtime
(set-62, 1 id). 16 ids total, all re-run against the fresh candidate build.

Method: read each register entry + the certifying batch's VERDICTS.md "per-entry evidence",
then re-ran the same class of probe (curl against the live sidecar, an in-process python call
against the candidate's venv, or — for R15-AGENT-084 / R15-RESEARCH-030, whose original repro
is "ask the agent" — a live llama3.1:8b invoke via `scripts/r15/vy.py` under the Ollama lock).
Entries certified only through a pinned vitest/pytest test (never run here; heavy lane owns
suites) are graded `ci_pinned`, citing the exact test name/line after grepping it present and
reading its assertions against the entry's invariant.

Findings: none. All 16 ids hold or are confirmed ci_pinned with the pinned test intact.

Notable: R15-DATA-017's SHANTIINOR announcement count is 3 here vs 2 at batch-6
certification time — NSE published one more real filing since (Sep 26 "General Updates"),
not a regression; the SME-index routing and promoter percentages match certification
exactly. SUMAX, which 502'd at the exact certification instant (noted as a live NSE
transport flake, not the bug), returned all 7 rows cleanly this run.

COVERAGE: 16/16 ids raw; no raw: none.
