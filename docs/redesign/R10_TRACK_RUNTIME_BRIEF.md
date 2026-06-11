# R10 Track RUNTIME — depth truth, lifecycle honesty, capability, robustness

Branch: `worktree-agent-r10-runtime`. Read first: `verification/R10_DEFECT_CATALOGUE.md`
(E2, E3.3, E5, E6, E7), DECISIONS D38/D39/D41/D42/D45, the contracts commit
(ResearchExecution in research/models.py; BriefExecution in types/brief.ts;
data-write/settings kinds in types/proposed-change.ts).

## Files you own (exclusive)

`sidecar/services/agent_tools/research.py`, `sidecar/services/agent_runtime.py`,
`sidecar/services/agent_tools/catalog.py`, `sidecar/agents/*.json`,
`sidecar/services/run_manager.py`, `sidecar/services/runs_store.py`,
`sidecar/services/action_ledger.py` (new), `sidecar/routers/agents.py`,
and tests (`test_toolbelt_integrity.py` new, `test_backtest_agent_parity.py` new,
`test_research_execution_record.py` new, `test_agent_runtime.py`,
`test_capability_catalog.py`, `test_runs_*`, `test_agents_router.py`).
Do NOT touch symbol_resolver/target/fast/iter/deep/deep_research (Team RESOLVE),
screener files (Team SCREENER), src/ (frontend teams), services/llm/ (Team ERRORS).

## 1. Execution record (E2 dead) — `agent_tools/research.py`

Mint `run_id = uuid4().hex` at `_research` entry. After the engine returns, build
`ResearchExecution(run_id, requested_depth=depth, loop=<payload["execution_loop"]>,
backend=payload.get("backend"), started_at/finished_at, degraded_reason=…)` and set
`out["execution"] = record.to_dict()`. Team RESOLVE guarantees every engine return
carries `execution_loop` ∈ {fast, iter, heavy, research-model}; if absent, derive
from the legacy `mode` and set `degraded_reason="legacy engine payload"`. Degradation
rule: requested deep/ultra but loop=="fast" → `degraded_reason` MUST say why (use the
payload's note/web reason when present). Emit ONE synthetic begin step through the
step sink when dispatching any research tool: kind="engine",
detail=`research:begin {run_id} depth={depth} query={…}` — the frontend keys its
in-flight brief state on it (contract with Team FRONTEND-BRIEF).

## 2. Auto-publish from execution only — `agent_runtime.py`

In `_auto_publish_event`: DELETE `raw_mode = str(payload.get("mode") or "fast")`.
New rule: no `execution` in payload → return None (no auto-publish; log a warning).
With it: loop fast→mode "fast"/depth "quick"; iter→"deep"/"deep"; heavy→"deep"/"heavy";
research-model→per requested stop ("fast"/"quick" only when requested_depth=="normal").
Forward `execution` inside `brief_input` (snake_case, verbatim record) plus existing
fields. Also: handle the `needs_disambiguation` research result — synthesize a
publish_brief whose input is `{query, disambiguation: {query, candidates}, execution}`
and nothing else; the panel renders the chooser (Team FRONTEND-BRIEF).
Track `last_research_execution` per invoke; when the MODEL issues its own
publish_brief without `execution`, inject the tracked record before yielding the event.

## 3. Honest publish narration + ack ledger (E3.3 dead)

- `services/action_ledger.py` (new): in-memory TTL store keyed by tool_call_id:
  `record(tool_call_id, status, brief_meta)`, `get(tool_call_id)`, TTL ~10min,
  `reset_for_tests()`.
- `routers/agents.py`: `POST /agents/actions/ack` body `{tool_call_id, status:
"applied"|"kept_previous"|"failed", brief?: {run_id, created_at, symbol,
source_count}}` → ledger. (Also: route the router's last-resort exception guard
  through `services.errors.humanize` — Team ERRORS ships that module; until their
  branch merges, guard with a try/except ImportError fallback to today's str(exc).)
- In `_build_local_tools`' autonomy=auto synthesized result for publish_brief (and
  ALL host actions): replace "applied … past tense" with "dispatched to the panel —
  verify with get_terminal_state before claiming completion; panel state is
  authoritative." At end-of-stream, for each publish_brief tool_call this turn,
  check the ledger: status missing → yield a notice event (existing event vocab —
  reuse the step/notice channel) "The brief panel did not confirm the publish";
  kept_previous → "The panel kept the previous, richer brief." The frontend renders
  these as quiet system chips (their team).

## 4. Durable runs depth persistence

`runs_store.py`: add `options_json` column (additive migration: CREATE TABLE IF NOT
EXISTS path + ALTER TABLE guard). `create_run` persists non-secret options
(research_depth, region; NEVER keys). `resume_run`/`answer_run` re-merge persisted
options into the spawned `_drive_run` so the ContextVar floor is re-threaded.
Pin with a resume test.

## 5. Capability maximization (E5/E6 dead) — `catalog.py`

- `Capability` gains `default_grant: bool = True` and `timeout_seconds: float | None`.
- New projection `default_grant_tool_ids()`; `_grant_first_party_hands` unions
  `spec.tools` with it (replacing the host-actions+research union). Custom agents
  (agents_store) stay author-picked.
- NEW host_action capabilities (kind="host_action", read_only=False, with JSON
  schemas): `portfolio_add_position(symbol, quantity, cost_basis, asset_class?,
note?, purchased_at?)`, `portfolio_update_position(position_id, …same)`,
  `portfolio_delete_position(position_id)`, `write_note(scope, text, mode:
replace|append)`, `remove_from_watchlist(symbol)`, `save_layout(name?)`,
  `save_screen(name, criteria?, group?, formula?, universe?)`, `set_region(region:
US|IN|GLOBAL)`. Extend `write_screener_filters` schema with `formula?: string` and
  `run?: boolean`; extend both screener capability universe enums with
  nse-all/bse-all/india-all (coordinate text with Team SCREENER's models — the enum
  strings are already in the contracts commit).
- Read-intent strip: the new mutating tools must NOT be in `_READ_SAFE_PANEL_ACTIONS`.
- `agents/*.json`: update copilot.json to the full default-grant list (documentation
  parity — correctness no longer depends on it); leave persona JSONs as voice +
  specialty lists.
- §6.5 IS UNTOUCHABLE: do not modify propose_order, the order-kind exemption
  (agent_runtime.py:775–783 area), routeOrderProposal seams, audit log, kill switch.
  The integrity test must ASSERT autonomy/keys/broker/kill-switch settings have no
  agent capability.

## 6. Per-tool timeouts (E7 dead) — dispatch boundary

`catalog.timeout_for(tool_id)`; budgets: resolve/quotes/fundamentals 15s,
news/macro/earnings/analyst 20s, web_search 25s, filings/disclosures 30s, quant 30s,
broker_portfolio 20s, screener_run 150s, run_custom_backtest 120s, research = outer
guard `wall_seconds+90` computed from args. Wrap registry-tool invocation in
`_dispatch_tool` with `asyncio.wait_for`; on timeout return
`{"ok": False, "error": "timeout", "message": "<tool> timed out after <N>s — <hint>"}`
with a per-domain TIMEOUT_HINTS table in catalog.py. Host-action locals exempt.

## 7. Tests (the regression armor)

- `test_toolbelt_integrity.py`: every internal default_grant capability ∈ every
  first-party agent's EFFECTIVE list (this alone catches E5); named pins for
  run_custom_backtest + compute_greeks/price_option/price_bond/yield_curve_value in
  copilot's effective list; grep-extract `HOST_ACTION_NAMES` from
  `src/lib/host-actions.ts` and assert set-equality with catalog host_action ids
  (the frontend team lands their side in the same wave — write the test against the
  catalog's FINAL id set, listed in this brief, so it goes green at integration);
  assert NO capability exists for autonomy/keychain/broker-config/kill-switch.
- `test_backtest_agent_parity.py`: fixed synthetic bars → direct
  `backtest_engine.run_backtest` vs `invoke_tool("run_custom_backtest", …)` →
  results identical minus run_id; `backtest_summary` digest matches.
- `test_research_execution_record.py`: matrix (composer-options, model-arg
  escalation, resume-rethreaded, persona) × (normal/deep/ultra) → execution.loop +
  auto-publish mode/depth correct; payload without execution → NO auto-publish;
  disambiguation result → chooser publish.
- Timeout test: registered slow tool + tiny budget → honest message, loop continues.

## Gates before you push

ruff format/check clean; FULL pytest green (the grant change will move roster/parity
counts — update expectations with one-line why-comments). Granular commits, push at
each green milestone.
