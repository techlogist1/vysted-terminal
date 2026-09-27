# rc1-battery-9 — regression battery shard 9

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, worktree
`rc1-round-5-cand` (confirmed via `git rev-parse HEAD` before starting).

Sidecar: from source on `:52349`, data dir `rc1-round-5-data-battery-9` (copied
from the ISO seed at `rc1-round-5-seed-data`). Sleep pid 50733 (worker 50736).
`VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154` (shared,
read-only). Stopped at end of shard via `kill 50733`.

Sets: batch-7/W3-unattended-chart-workspace (set-26, 9 ids), batch-9/W1-agent-runtime
(set-34, 4 ids), batch-10/W8-plugins-dock (set-46, 3 ids). 16 ids total.

## Method

For every id: read the register entry (repro/evidence) and the batch's `VERDICTS.md`
"Per-entry evidence" for how it was certified. Where certification was a live sidecar
probe, re-ran the identical repro against the candidate sidecar (curl / in-process
python / `vy.py`). Where certification cited a vitest test (committed, register-id-
tagged), confirmed the test still exists in the candidate source and cited it —
verdict `ci_pinned` — rather than running vitest (heavy lane's job per the brief).

Local-model calls (`vy.py --provider ollama`) held `/tmp/vysted-r15-ollama.lock` for
the duration of each call (acquired on first attempt each time, released via a
`trap ... EXIT` in the detached shell).

## Notable repro corrections made in-flight

- **R15-UI-046**: my first probe hit the raw sidecar HTTP endpoints directly
  (`POST /workspace`, `DELETE /workspace/{name}`), which do **not** carry the
  reserved-name guard — that guard lives client-side in `src/lib/workspace.ts`
  (`saveWorkspace`/`deleteWorkspace`), confirmed by reading the guard's call sites.
  Corrected to cite the pinned test (`workspace.test.ts:1389`) instead of a false
  "regressed" read from testing the wrong layer.
- **R15-CODE-PLATFORM-018**: needed the `OptionPricingRequest` schema fields
  (`exercise`, `payoff`, `dividend_yield`, `valuation_date`, `expiry_date`) — the
  register evidence's field names (`option_type`, `time_to_expiry`) don't match the
  current Pydantic model; read `sidecar/models/quant.py` directly to get a valid
  request body.
- **R15-AGENT-023**: the schedule (`everyMinutes:5`) took ~6 min to fire rather
  than exactly 5 — the sidecar's own boot-time BSE-symbol-master yfinance warmup
  (visible in the sidecar log, 14:58–15:03) was still running when the schedule
  was created, delaying the first eligible tick slightly. Confirmed genuinely
  unattended (no interaction with the schedule between creation and the fire) and
  matches the certified mechanism exactly once it fired.
- **R15-CODE-AGENT-008**: the re-run got `sources:[]` where the certified run got
  6 — this scratch sidecar has no web-search backend wired (`execution.backend:
  null`), not a regression in the payload-decode mechanism the entry is about (all
  5 `structured` keys were present, undecoded correctly).

## Result

0 regressed, 0 new_defect, 0 chain, 0 gate8. 9 holds (live-reconfirmed), 7 ci_pinned.

COVERAGE: 16/16 ids raw.
