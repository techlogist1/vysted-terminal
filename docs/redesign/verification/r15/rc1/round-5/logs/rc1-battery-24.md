# rc1-battery-24 — REGRESSION BATTERY shard 24 (batch-9/batch-10/batch-29)

Candidate sha 9bc600ece2ce6343a6aa48f130d7620b1466bb98 (worktree
`rc1-round-5-cand`, verified via `git rev-parse HEAD` before starting).

Own sidecar booted from candidate source on `127.0.0.1:52364`, data dir
`rc1-round-5-data-rc1-battery-24` (copied from the round-5 seed profile).
Sleep pid: 69264 (killed at end of run).

Sets covered:
- batch-9/W4-market-lanes-errors-quant (set-37.md): DATA-062, DATA-065,
  DATA-066, DATA-073, LIFECYCLE-021, UI-051, UI-053 — all hold (2 ci_pinned:
  DATA-062, UI-051, both frontend-only fixes confirmed at source + pinned
  vitest names, execution not run per role scope).
- batch-10/W5-chat-search-workflow (set-43.md): AGENT-063, AGENT-082,
  AGENT-088, CODE-RESEARCH-004, RESEARCH-028, UI-027 — all hold (2 ci_pinned:
  AGENT-088, UI-027, frontend-only).
- batch-29/W2-sonnet (set-81.md): DATA-063, LEAD-004 — both hold.

Notable technique: LIFECYCLE-021 and AGENT-063/LEAD-004's fresh-case shapes
were re-verified with small in-process Python scripts against the candidate's
own venv (mirroring the original certifying test's technique — monkeypatched
provider failures via FastAPI TestClient, or direct dataclass construction —
never `pytest` itself), since a live "dead NSE session" or synthetic filing
shape can't be forced through curl alone.

One observation logged (not a regression, not filed): live JONJUA fundamentals
now read a "quarterly-gap" TTM-basis reason instead of the "(a half-yearly
filer)" text the batch-29 certification recorded, consistent with JONJUA's
live exchange filings having gained a filed quarter since that run. The
in-process `cadence()` unit shapes (Jan-Mar-unfiled, complete-year,
pure-half-yearly x2, six-month-bridge-with-both-quarters-filed) all match the
certified table exactly, confirming the cadence logic itself is unchanged —
see set-81.md.

Zero regressions found across 15 entries. 0 findings filed.

COVERAGE: 15/15 ids raw; no raw: none.
