# rc1-battery-11 — REGRESSION BATTERY shard 11 (Sonnet)

Candidate sha: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via
`git rev-parse HEAD` in the candidate worktree before any work).

Sets: batch-4/W2-workflow-backtest-feeds (set-12.md, 8 ids),
batch-2/W3-research-integrity (set-2.md, 5 ids),
batch-12/W8-design-token-gate (set-61.md, 2 ids),
batch-25/W6-sonnet (set-72.md, 1 id). 16 ids total.

## Setup

- Data dir: copied `rc1-round-5-recheck-seed-data` -> `rc1-round-5-recheck-data-battery-11`.
- Sidecar: booted from the candidate worktree's `sidecar/` source on `:52351`
  (own data dir, `VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154`
  pointing at the shared read-only stack), detached via
  `nohup sh -c "sleep 86400 | ./.venv/bin/python3 main.py ..." &`.
  Sleep-wrapper pid 78805; worker pid 78808. `/health` returned `ok` in <5s.
- Stopped at end of shard: killed sleep pid 78805, then worker pid 78808
  directly (the sleep pid alone left the worker orphaned and still serving
  `/health`; this is my own :52351 port, not another owner's, so the direct
  kill is in-scope cleanup, not a blanket kill).

## Method per set

- **set-12 (workflow/backtest)**: live `POST /workflow/run` /
  `POST /backtest/run` / market-data GETs against my own sidecar, building
  graphs directly from the palette's own specs
  (`node-registry.ts` `BUILT_IN_NODE_SPECS` / `BUILT_IN_NODE_CONFIG_FIELDS`)
  so the probe exercises the exact port/config-key wiring the entries are
  about. One live LLM call (`ai.agent_invoke` on the keyless `copilot`
  agent / local Ollama, R15-AGENT-015) ran under the shared local-model
  lock: acquired via `mkdir /tmp/vysted-r15-ollama.lock`, released
  automatically by a `trap ... EXIT` wrapper around the detached curl call
  (~30s to complete). Two entries (R15-CODE-FRONTEND-006,
  R15-CODE-PLATFORM-016) are frontend-wiring defects with no sidecar
  surface — verified by reading `NodeEditorPanel.tsx` / `store/workflow.ts`
  at this sha plus the live SSE shape from the palette run.
- **set-2 (research integrity)**: all five entries are pure-logic fixes
  (marker parsing, claim extraction, append-only source numbering,
  bibliography stripping, citation-preference indexing) with no dependency
  on live model output for the defect itself, so each was re-checked with a
  fresh in-process Python call importing the actual fixed function
  (`_reflect_says_complete`, `_split_claims`, `_Findings.all_sources`,
  `strip_model_bibliography`/`strip_invalid_markers`, `priority_note`) from
  `sidecar/.venv` on the candidate worktree, fed sample input matching each
  entry's own stated repro figures/text. No live ULTRA/DEEP research run
  was needed or done (would have cost 10+ minutes each per lock/time
  constraints, for no additional certainty over exercising the exact fixed
  function directly).
- **set-61 (design-token gate / SEC filings)**: R15-RELEASE-007 via a
  direct `node scripts/audit-design-tokens.mjs` run plus `package.json`
  grep (not via `pnpm ci-local`, which the heavy lane owns).
  R15-LEAD-010 via live `GET /sec/filings` + `GET /sec/filings/{accession}`
  against my sidecar, reaching the shared read-only sec-edgar-mcp for real
  SEC EDGAR data (AAPL 10-Ks, including one from 2021 — outside the
  unfiltered 40-recent-filing window the entry's root cause names).
- **set-72 (agent tool-arg coercion)**: in-process Python call importing
  `services.agent_runtime` + `models.llm.LLMToolUseEvent` directly and
  calling `_normalise_tool_args` with the register's own named scenarios
  (nested numeric string, stringified array, integral-float string) plus a
  negative control. Not a pytest run — a standalone script exercising the
  same function pytest's `test_b3_runtime_tool_args.py` also covers.

## Result

All 16 ids: **holds**. No regressions, no new defects, no chain failures, no
gate8-relevant findings in this shard's scope. `findings/rc1-battery-11.json`
is `[]`.

COVERAGE: 16/16 ids raw; no raw: none.
