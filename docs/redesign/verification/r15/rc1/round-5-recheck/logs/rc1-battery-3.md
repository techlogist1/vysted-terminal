# rc1-battery-3 — regression battery shard 3

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via `git rev-parse HEAD`
in the scratch worktree before starting). Sets: batch-8/W4-resolver-exchange-lanes
(set-33, 11 ids), batch-10/W7-panels-marketplace (set-46, 4 ids),
batch-17/W1-one-writer-set (set-65, 1 id). 16 ids total.

## Sidecar

Booted once for the whole shard from the candidate's `sidecar/` source on `:52343`,
data dir `rc1-round-5-recheck-data-battery-3` (cp -R of the seed). Sleep-wrapper pid
59012, worker pid 59015 — both killed at the end (confirmed dead via `ps`).
`VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154` (shared stack).
`/health` returned ok with `openbb-mcp: available` before any probe.

## Method

For each id: read the register entry's own repro + the batch verifier's certification
note, then re-ran that exact repro — `curl` against the own sidecar for HTTP-surfaced
entries (resolver/data/UI-marketplace), or an in-process Python call against the
candidate's `sidecar/.venv` for pure-function/internal-mechanism entries (memoization
timing, mock-transport retry/backoff, macro provider stubs, the streaming leak-hold).
No vitest/pytest suite was run; source was read to confirm wiring, then a live/in-process
probe was run to confirm behavior (never judged from the diff alone).

Per gate rule change 1: verdicts are against each entry's OWN stated repro only. Three
entries (R15-DATA-051, R15-UI-032, R15-UI-018) carry a "not certified"/"stays open" note
describing a BROADER class claim beyond the entry's own repro (fundamentals echoing
board/face_value; the original SEC-search-dead-end shape; ScreenerPanel/Marketplace
delete sites) — those broader claims were not re-probed as regressions since they are
outside the entry's own stated repro; the entry's own repro was re-run and held in each
case.

## Results summary

All 16 ids: **holds**. No regressions, no new defects, no ci_pinned, no needs_gui, no
blocked_env. Two entries (R15-AGENT-045, R15-UI-028) had their batch's "not certified"
residual note explicitly re-probed too (the two-symbol compare_symbols case; the Rho
unit label) and both are now fixed as well — noted in the set tables but not filed as
separate findings since the register status is already "fixed" and these are confirmations,
not new information.

## Notable source anchors

- `sidecar/services/symbol_resolver.py:329` `instrument_payload()` — single shared wire
  shape, comment: "the ONE wire shape ... both project through it" (R15-CODE-DATA-003).
- `sidecar/services/symbol_resolver.py:1164` `_scan_names` `@lru_cache(maxsize=256)`
  (R15-CODE-DATA-002).
- `sidecar/services/nse_symbol_change.py:465` `_refresh_guarded` — `_refreshed_on` set
  only on success, backoff retry (R15-LIFECYCLE-019).
- `sidecar/services/nse_bhavcopy.py:335` `_fetch_day` — fallback tried on primary 404
  (R15-LIFECYCLE-022).
- `sidecar/services/agent_tools/compare_symbols.py:253` — per-symbol error carried into
  the `ok:false` payload (R15-AGENT-045, closes the batch-7 residual too).
- `sidecar/services/openbb_mcp_provider.py:280` `_first_present` (R15-DATA-084).
- `sidecar/services/macro/world_bank_provider.py:196,231` (R15-DATA-085, R15-DATA-086).
- `src/modules/quant/units.ts` `toMarketUnits` — vega/theta/rho all convert+label now
  (R15-UI-028, closes the batch-9 Rho residual too).
- `src/lib/marketplace.ts:204` `INDIA_DATA_LANES`, wired in `MarketplacePanel.tsx:129`
  (R15-DATA-077).
- `sidecar/services/llm/tool_call_rescue.py:159` `LeakHold` — holds a partial marker
  whole until it resolves or stops matching (R15-LEAD-031, commit ede02247).

COVERAGE: 16/16 ids raw across set-33 (11/11), set-46 (4/4), set-65 (1/1); no raw
files missing.
