# rc1-battery-6 — regression battery shard 6

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` verified at start (`git rev-parse HEAD` in
the scratch worktree). No prior round-4 files existed for this label/sets (checked
`battery/set-10.md`, `set-42.md`, `set-68.md` and `battery/raw/set-{10,42,68}/` before starting —
none present); started fresh.

Sidecar: own instance on `:52346`, seed data copied to
`rc1-round-4-data-rc1-battery-6`, `/health` confirmed ok before probing. Booted once, reused for
all three sets, stopped at end (sleep pid 74047 killed via `kill`, not a blanket kill).

Sets covered (writer sets from the task, per the task's exact id lists):
- batch-4/W1-agent-runtime → `battery/set-10.md` (9 ids)
- batch-10/W3-fundamentals-bse-cache → `battery/set-42.md` (6 ids)
- batch-17/W1-one-writer-set → `battery/set-68.md` (1 id)

Method per id: read the register entry (repro + evidence), then re-ran that repro — live curl
against the candidate's own isolated sidecar for anything hitting live data (macro World Bank
region routing, IMF WEO projection flag, BSE quote OHLC/volume, fundamentals ROCE/basis/dates),
or a direct code trace confirming the fix is present and wired into the live call path for
design-verified entries (context-budget mitigation, Gemini thought-signature round-trip, Gemini
schema serialization, xAI native-search gate, screener skip-ledger cap, compare_symbols window
guard, backtest run hydration). Two entries (R15-RESEARCH-005, R15-LEAD-031) whose original
register repro required either a live 60s+ local-model run or a specific raw-output shape from a
past drive were verified via each fix's own dedicated pinned regression test instead of a full
suite (`test_research_synthesis_timeout.py`, `test_tool_call_rescue.py`) — never vitest/pytest
suites in full, per the battery role's scope.

Result: 16/16 hold (14 direct `holds`, 2 `ci_pinned`). Zero regressions found in this shard.

COVERAGE: 16/16 ids raw; no raw: none.
