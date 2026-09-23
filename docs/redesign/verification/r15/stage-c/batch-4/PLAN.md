# R15 Stage C: Batch 4 Plan (high, plus same-root-cause mediums and lows)

- **Base:** branch `004-r4-experience-rebuild` at `1999844a7d3fac7261928bdbf5745685ec127033` (batch 3 merged, L23). D81 is merged: nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** batch planner (Opus). I opened the code at each cited line before writing a row. Each mechanism follows the corrected verdict (refuter correction, batch-3 reopen note), not the raw claim.
- **Queue at base:** 522 open: 0 critical, 64 high, 250 medium, 208 low.
- **Selection:** 50 open entries = 40 highs + 10 mediums/lows that share a root cause with a selected high.
  - Every selected high is in at least one of the four named areas except `LEAD-007` and `LEAD-008` (area `agent-llm`: the Gemini and xAI agent lanes are dead end to end, which is agent-chat for those users).
  - Class rule: a class is a shared root cause, not a shared `defect_class` label. Joined as class-mates: `DATA-049` (with 047), `DATA-082` (with 034), `DATA-093` (with 029's canonicalisation gap, screener side), `UI-025` (with 009), `CODE-AGENT-002` and `DATA-083` (with `LIFECYCLE-005`), `CODE-PLATFORM-037` and `AGENT-029` (the SSE client's one-terminal-callback invariant, with the frontend half of `LIFECYCLE-005`), `CODE-PLATFORM-016` (with `CODE-FRONTEND-006`), `CODE-FRONTEND-020` (with `UI-003`). §5 lists the label-mates not taken and why.
  - The 24 open highs not taken are in §4 with reasons (feature-size lanes, Tier-4 files, GUI-only proof, capacity).
- **proposed_not_defect:** none. Every selected entry reproduces as corrected at base. No entry in the four areas is adjudicated away.

---

## 0. The 50 entries

| # | Entry | Sev | Root-cause class | Writer |
|---|---|---|---|---|
| 1 | R15-AGENT-008 | high | context budget: full schema set every round, uncapped tool results, nothing counted against the window | W1 |
| 2 | R15-AGENT-009 | high | context budget: uncapped tool result (screener skip ledger) | W1 |
| 3 | R15-AGENT-006 | high | Gemini thought signature dropped between rounds | W1 |
| 4 | R15-LEAD-007 | high | Gemini tools projected into the OpenAPI `parameters` subset instead of JSON Schema | W1 |
| 5 | R15-LEAD-008 | high | xAI native search still on the retired Live Search API | W1 |
| 6 | R15-RESEARCH-005 | high | engine `degraded_reason` not copied into the execution record (remaining half) | W1 |
| 7 | R15-DATA-041 | high | compare_symbols ranks incomparable windows | W1 |
| 8 | R15-DATA-046 | high | World Bank bare id defaults to USA for every region | W1 |
| 9 | R15-AGENT-011 | high | agent-started backtest promised in a panel no code fills (sidecar half W1, frontend half W2) | W1 + W2 |
| 10 | R15-AGENT-015 | high | node contract drift (Invoke Agent `prompt` vs `prompt_template`) | W2 |
| 11 | R15-CODE-PLATFORM-002 | high | node contract drift (7 of 10 built-ins) | W2 |
| 12 | R15-AGENT-016 | high | workflow agent node: no creds threaded, failure laundered to ok | W2 |
| 13 | R15-CODE-PLATFORM-003 | high | workflow agent node: failure laundered to ok | W2 |
| 14 | R15-CODE-FRONTEND-006 | high | two SSE consumers for the workflow wire; the one feeding notifications is dead | W2 |
| 15 | R15-CODE-PLATFORM-016 | med | same as 14 | W2 |
| 16 | R15-DATA-040 | high | partially failed backtest universe reported clean | W2 |
| 17 | R15-DATA-029 | high | India symbol mapping lives only in `_yahoo_symbol`; three lanes keep their own normaliser | W2 |
| 18 | R15-DATA-030 | high | news tagging matches the raw request string | W2 |
| 19 | R15-DATA-032 | high | proxy statistics written into typed estimate fields | W2 |
| 20 | R15-CODE-FRONTEND-002 | high | one live transcript buffer overwritten by two space stores mid-stream | W3 |
| 21 | R15-AGENT-013 | high | Delegate output never delivered (no collectable output) | W3 |
| 22 | R15-AGENT-029 | med | SSE client does not guarantee one terminal callback (pre-stream rejection) | W3 |
| 23 | R15-CODE-PLATFORM-037 | low | same invariant (consumer throw relabelled; EOF without done) | W3 |
| 24 | R15-LIFECYCLE-005 | high | MCP transport failure escapes as BaseException; health flags stay green | W3 |
| 25 | R15-CODE-AGENT-002 | med | same (reconnect except-tuple too narrow) | W3 |
| 26 | R15-DATA-083 | med | same (health flags set only on the happy path) | W3 |
| 27 | R15-DATA-038 | high | SEC parsers expect shapes sec-edgar-mcp does not send; empty cached | W3 |
| 28 | R15-DATA-039 | high | SEC form type is a closed Literal; rows dropped after the upstream limit | W3 |
| 29 | R15-DATA-015 | high | 52w pair is a single-venue Yahoo scalar with no witness on /fundamentals | W4 |
| 30 | R15-DATA-016 | high | 52w pair and chart built on zero-volume forward-filled bars | W4 |
| 31 | R15-DATA-047 | high | dividend paid-TTM leg runs only in research | W4 |
| 32 | R15-DATA-049 | med | same | W4 |
| 33 | R15-DATA-034 | high | a served path skips the correctness gate (v7 batch); duplicated yield bound | W4 |
| 34 | R15-DATA-082 | med | a served path skips the gate (crypto exemption); ccxt fabricates 0.0 | W4 |
| 35 | R15-LIFECYCLE-004 | high | exchange parsers substitute close / 0.0 for a missing O/H/L/V | W4 |
| 36 | R15-DATA-035 | high | BSE empty marker written before publication, never expires | W4 |
| 37 | R15-DATA-036 | high | whole-market bhavcopy parsed per day to read one row | W4 |
| 38 | R15-DATA-020 | high | cross-exchange dedup is an exact prefix hash (batch-3 reopen) | W4 |
| 39 | R15-UI-090 | high | freshness calendar from the session region, not the instrument (sidecar half W4, Portfolio cue W5) | W4 + W5 |
| 40 | R15-UI-004 | high | per-symbol catch erases the failure the panel needs | W5 |
| 41 | R15-UI-005 | high | no-data total published as a numeric 0 | W5 |
| 42 | R15-UI-009 | high | browser-only primitive in the webview (Blob + `<a download>`) | W5 |
| 43 | R15-UI-025 | med | browser-only primitive in the webview (`window.prompt`) | W5 |
| 44 | R15-UI-006 | high | server cuts at limit by market cap; client sorts the page; no matched count | W5 |
| 45 | R15-UI-007 | high | preset writes criteria only; old group and formula still ride | W5 |
| 46 | R15-DATA-044 | high | NULL non-enrichment field silently fails the criterion | W5 |
| 47 | R15-DATA-093 | med | screener custom symbols looked up by the literal typed key | W5 |
| 48 | R15-UI-003 | high | Agent Builder hand-copies the sidecar's tool and provider vocabularies | W5 |
| 49 | R15-CODE-FRONTEND-020 | med | same (the test asserts the UI against its own constants) | W5 |
| 50 | R15-LIFECYCLE-007 | high | bare `docker` resolved through launchd's minimal PATH | W5 |

---

## 1. File ownership: five disjoint sets

A file belongs to exactly one writer. A writer that needs a change in another writer's file does not make it; it goes to `issues[]` with the exact line. "Import only" means read the symbol, never edit the file.

| Writer | Model | Source files | Tests |
|---|---|---|---|
| **W1 `agent-runtime`** | opus | `sidecar/services/agent_runtime.py`, `sidecar/services/agent_tools/catalog.py`, `agent_tools/schemas.py`, `agent_tools/screener_tools.py`, `agent_tools/compare_symbols.py`, `agent_tools/research.py`, `agent_tools/run_custom_backtest.py` (docstring only), `sidecar/models/llm.py`, `sidecar/services/llm/base.py`, `llm/gemini.py`, `llm/ollama.py`, `llm/native_search.py`, `llm/openai.py`, `sidecar/services/macro/world_bank_provider.py`, `sidecar/services/macro/macro_router.py` | `test_agent_runtime*.py`, `test_capability_catalog.py`, `test_mcp_catalog_parity.py` (run; edit only for a derived change), `test_llm_gemini.py`, `test_gemini_multiround.py`, `test_native_search.py`, `test_llm_openai.py`, `test_screener_tools.py`, `test_compare_symbols.py`, `test_research_execution_record.py`, `test_research_tools.py`, `test_macro_providers.py`, `test_macro_router.py`, new `test_b4_runtime_*.py` |
| **W2 `workflow-backtest-feeds`** | opus | `sidecar/services/workflow_nodes/builtin.py`, `workflow_nodes/__init__.py`, `sidecar/services/workflow_engine.py`, `sidecar/models/workflow.py`, `sidecar/routers/workflow.py`, `types/workflow.ts`, `src/modules/node-editor/node-registry.ts`, `NodeEditorPanel.tsx`, `graph-state.ts` (only if needed), `src/store/workflow.ts`, `src/lib/desktop-notification.ts` (only if needed), `sidecar/services/bar_loader.py`, `sidecar/services/backtest_engine.py`, `src/store/backtest.ts`, `src/modules/backtest/BacktestPanel.tsx` (only if needed), `src/lib/host-actions.ts`, `sidecar/services/earnings_provider.py`, `sidecar/services/analyst_ratings_extended.py`, `sidecar/services/news_provider.py`, `sidecar/routers/news.py`, `types/earnings.ts`, `src/modules/earnings/EpsEstimateGrid.tsx` | `test_workflow_*.py`, `test_bar_loader.py`, `test_backtest_engine.py`, `test_earnings_provider.py`, `test_analyst_ratings_extended.py`, `test_news.py`, `test_news_tool.py`, new `sidecar/tests/fixtures/workflow_node_types.json`, co-located vitest for the owned TS files |
| **W3 `chat-runs-mcp`** | opus | `src/store/chat-history.ts`, `src/store/agent-spaces.ts`, `src/store/research-spaces.ts`, `src/lib/workspace.ts` (research-space switch call sites only, only if needed), `src/modules/chat/ChatSidebar.tsx`, `src/modules/chat/streaming.ts`, `src/lib/sidecar-client.ts` (only if needed), `src/lib/delegate-runs.ts`, `src/modules/chat/AgentsRail.tsx`, `sidecar/services/run_manager.py`, `sidecar/services/runs_store.py`, `sidecar/routers/runs.py`, `sidecar/models/run.py`, `sidecar/services/mcp_client.py`, `sidecar/services/openbb_mcp_provider.py`, `sidecar/services/sec_filings_provider.py`, `sidecar/models/sec.py`, `types/sec.ts` | `test_mcp_client.py`, `test_openbb_mcp_provider.py`, `test_sec_filings_provider.py`, `test_sec_filings_router.py`, `test_run_manager.py`, `test_runs_store.py`, `test_runs_router.py`, vitest: `streaming.test.ts`, `ChatSidebar.test.tsx`, `chat-history.test.ts`, `agent-spaces.test.ts`, `research-spaces.test.ts`, `delegate-runs.test.ts` |
| **W4 `market-data-gate`** | opus | `sidecar/services/correctness_gate.py`, `sidecar/services/yfinance_provider.py`, `sidecar/services/research/range_check.py`, `sidecar/services/research/fast.py`, `sidecar/services/dividend_history.py`, `sidecar/routers/fundamentals.py` (only if needed), `sidecar/services/yahoo_batch_provider.py`, `sidecar/services/provider_registry.py`, `sidecar/services/ccxt_provider.py`, `sidecar/services/nse_provider.py`, `sidecar/services/bse_provider.py`, `sidecar/services/nse_bhavcopy.py` (only if the class sweep finds the same substitution), `sidecar/models/fundamentals.py`, `sidecar/models/market.py` (only if needed), **`types/data.ts` (sole owner)**, `sidecar/services/corporate_disclosures.py`, `sidecar/routers/quotes.py`, `sidecar/routers/history.py`, `sidecar/services/locale.py` | `test_correctness_gate.py`, `test_fundamentals*.py`, `test_range_check.py`, `test_dividend_history.py`, `test_provider_registry*.py`, `test_nse_provider.py`, `test_bse_provider.py`, `test_nse_bhavcopy.py`, `test_corporate_disclosures.py`, `test_quotes.py`, `test_history.py`, `test_locale.py`, new `test_b4_*.py`, fixtures under `sidecar/tests/fixtures/{nse,bse}/` (add only) |
| **W5 `panels-screener`** | sonnet | `src/modules/portfolio/api.ts`, `PortfolioPanel.tsx`, `metrics.ts`, `src/lib/csv.ts`, `src/lib/export-artifact.ts` (only if a text-save variant is missing), `src/modules/watchlist/WatchlistPanel.tsx`, `src/modules/notes/NotesToolbar.tsx`, `eslint.config.mjs`, `sidecar/services/screener.py`, `sidecar/services/screener_formula.py` (only if needed), `sidecar/models/screener.py`, `types/screener.ts`, `src/store/screener.ts`, `src/modules/screener/ScreenerPanel.tsx`, `ScreenerResultsTable.tsx`, `ScreenerPresets.tsx`, `src/modules/agent-builder/form.tsx`, `AgentBuilderPanel.tsx`, `sidecar/routers/custom_agents.py`, `sidecar/services/searxng_manager.py` | `test_screener*.py` (not `test_screener_tools.py`), `test_custom_agents_router.py`, `test_searxng_manager.py`, co-located vitest (`PortfolioPanel.test.tsx`, `metrics.test.ts`, `csv.test.ts`, `notes.test.ts`, `screener.test.ts`, `ScreenerPanel.test.tsx`, `ScreenerResultsTable.test.tsx`, `agent-builder.test.tsx`) |

No writer edits `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/`, `CHANGELOG.md` or the register. Unowned files used as imports only: `sidecar/config.py`, `sidecar/services/research/semantics.py`, `sidecar/services/symbol_resolver.py`, `sidecar/services/witness.py`, `src/store/proposed-changes.ts`, `src/store/brief*.ts`, `src/lib/brief-ingest.ts`, `src/lib/market-session.ts`, `src/components/DataBadges.tsx`, `src/store/model-selection.ts`, `src/lib/keychain.ts`.

### 1.1 Cross-writer contracts

- **C1 agent-started backtest (W1 to W2, `AGENT-011`).**
  - W1 adds an optional `run_id` string to `open_panel`'s `input_schema` (catalog): "For panel=backtest: the run id a run_custom_backtest call returned, to display that run".
  - After a `run_custom_backtest` call returns `ok` with a `runId`, the runtime yields one synthetic `LLMToolUseEvent(name="open_panel", input={"panel": "backtest", "run_id": <runId>}, tool_call_id=f"auto-backtest-{<orig id>}")`, exactly like `_auto_publish_event` does for research. It is never dispatched back to the model.
  - W2's `open_panel` handler in `host-actions.ts` (describe and apply switches, `:655` and `:953`): `panel === "backtest"` with a `run_id` calls `useBacktestStore.getState().loadRun(run_id)` (new: `GET /backtest/runs/{run_id}`, the existing route at `routers/backtest.py:180-186`) and sets `activeRunId`. It rides the normal gate (panel kind: AUTO applies, ASK stages).
  - Wire names are exactly `open_panel`, `panel: "backtest"`, `run_id`.
- **C2 `types/data.ts` has one owner: W4.** W4 mirrors any `sidecar/models/fundamentals.py` or `market.py` change in the same commit. Preferred: no new fields; the 52w and dividend witnesses speak through `field_meta` (status + reason), which already exists.
- **C3 `yfinance_provider._yahoo_symbol` is frozen** (name, signature, behaviour) for this batch. W4 owns the file and must not change it. W2 (`DATA-029`) and W5 (`DATA-093`) import it.
- **C4 screener result names** (W5 to W1). W5 adds `matched_count` to `ScreenerResult` and `sort_by`/`sort_dir` to `ScreenerRequest`; it must not rename `skip_details` or `skipped_count`. W1's `AGENT-009` aggregation in `screener_tools.py` reads them and does not edit `models/screener.py`.
- **C5 v7 gate interplay** (W4 and W5). W4 validates inside `yahoo_batch_provider.fundamentals_from_v7`, so a withheld v7 yield arrives at the screener as `None` with `field_meta` status `withheld`. W5's `DATA-044` itemizes a NULL criterion field as `missing_field:<field>`, so a withheld yield itemizes instead of silently failing. W4 does not edit `screener.py`; W5 does not edit `yahoo_batch_provider.py`.
- **C6 `LLMToolUseEvent.provider_meta` is runtime-internal** (W1): `Field(default=None, exclude=True)`, so it never rides the SSE wire and needs no TS mirror. `streaming.ts` (W3) is unaffected.
- **C7 workflow run creds** (W2). `WorkflowRunRequest` gains optional `provider`, `model`, `api_key` (alias `apiKey`), the same names and body placement as `AgentInvocationRequest` (`routers/agents.py:98-100`). Mirrored in `types/workflow.ts` in the same commit. Never persisted, never logged.
- **C8 one terminal callback** (W3). After W3, every `streamChat` / `streamAgentInvocation` call ends in exactly one `onDone` or `onError`. `ChatSidebar` settles only there.
- **C9 research files.** W1 edits `agent_tools/research.py` only; W4 edits `research/fast.py` and `research/range_check.py`. Neither edits `research/semantics.py` or `research/deep.py`.
- **C10 `locale.py` is W4's.** W2 (`DATA-030`) imports `strip_exchange_suffix` only.

---

## 2. Per-writer entries (mechanism, then fix, test and files)

### W1: `agent-runtime` (opus, 9 entries)

**R15-AGENT-008 and R15-AGENT-009 (one class: nothing bounds what enters the model's context).**
- **Mechanism.**
  - `_grant_first_party_hands` (`agent_runtime.py:192-223`) unions the full default grant into every first-party agent, and the loop sends every allowed schema every round (`:1552-1558`). Measured: 50 tools, about 35k chars of schemas, plus a ~11k-char prompt; a read turn still sends 37 tools.
  - The Ollama lane runs at `DEFAULT_NUM_CTX = 16384` (`llm/ollama.py:47`) and silently drops the head on overflow.
  - Every tool result is `json.dumps`ed whole (`_dispatch_tool`, `:634-689`) and becomes the model-facing message through `_model_facing_content` (`:754-772`) with no size cap; results are re-sent every later round; nothing estimates tokens.
  - `AGENT-009`: `screener_run` returns `result.model_dump()` whole (`screener_tools.py:67-70`, `"result": result.model_dump(mode="json")`), including `skip_details` (up to ~5,000 `{symbol, reason}` rows for india-all).
- **Fix: one admission policy in the runtime, with the catalog as its source.**
  1. **Window.** `LLMProvider.context_window(model) -> int | None` in `llm/base.py`, default `None` (hosted lanes: no admission change). Ollama returns its effective `num_ctx`.
  2. **Result cap** at the one model-facing seam, `_model_facing_content`: a result longer than its budget is cut with a marker naming the elided size and the next step ("…[N chars elided — call again with a narrower query or a smaller limit]"). Budget: a share of the window when one is known, else a fixed ceiling. The writer sizes the ceiling from the captured research payloads under `docs/redesign/verification/r15/surface/research-briefs/` so a normal hosted research result is never cut. The raw `result_str` still feeds auto-publish and the execution record.
  3. **Round estimate.** Before each round, estimate tokens as chars/4 of the schemas for `tool_ids` plus every message. When a window is known and the estimate exceeds it, replace the contents of the oldest tool-result messages with an elision marker until it fits (never the current round's results, never the user prompt).
  4. **Domain subsetting only on a window-bound lane.** When a window is known and schemas plus system prompt exceed half of it, send only the always-on domains (quotes, charts, indicators, research, fundamentals, news, terminal, workspace, portfolio) plus any specialist domain (screener, macro, earnings, analyst, filings, quant, agents, workflows) whose cue words appear in the prompt or the last user turns. The cue words live in `catalog.py` next to `Domain` (one source). The allow-list itself is unchanged (D21 intact); the subset is logged at debug. This replaces today's silent head truncation with a deliberate subset.
  5. **`AGENT-009`.** `screener_run`'s tool payload replaces `skip_details` with `skip_summary: {reason: count}` plus at most 5 `skip_examples`; `skipped_count` stays. The HTTP route and panel keep the full ledger.
- **Tests.**
  - Copilot on the Ollama lane with a two-tool turn: the round-1 and round-2 estimates stay under `num_ctx`, and `screener_run` is in `tool_ids` for "screen nse-all for P/E under 15" while `price_option` is not.
  - Same prompt on a hosted lane (window `None`): the full tool set is sent and nothing is elided.
  - `AGENT-009`: a partial india-all result with 5,000 skips yields a tool payload under a fixed byte budget carrying per-reason counts.
  - Class case not written against: a 40 KB `corporate_announcements` result on the Ollama lane reaches the model capped, with the marker, while the auto-publish/raw path is untouched.
- **Files.** `agent_runtime.py`, `catalog.py`, `llm/base.py`, `llm/ollama.py`, `screener_tools.py`.

**R15-AGENT-006 (Gemini thought signatures).**
- **Mechanism.** `gemini.py:155-163` reads only `fc.name`, `fc.id`, `fc.args`; `LLMToolUseEvent` (`models/llm.py:146-152`) has no slot; the runtime's `metadata["tool_calls"]` carries id/name/input only (`agent_runtime.py:1664-1673`); `_split_system_and_contents` (`gemini.py:67-84`) rebuilds `function_call` parts from name and args. `thought_signature` is a `types.Part` field in google-genai 2.5.0 (checked). Round 2 of a Gemini 3 tool turn replays calls without the signature Google documents as required.
- **Fix.** `provider_meta: dict[str, Any] | None = Field(default=None, exclude=True)` on `LLMToolUseEvent` (C6). Gemini stores `{"thought_signature": <bytes as base64 str>}` from the part; the runtime copies `provider_meta` into `metadata["tool_calls"][i]` (it must survive a Delegate checkpoint JSON dump, hence base64); `_split_system_and_contents` re-attaches the decoded bytes as `thought_signature` on the matching `function_call` part. Parts without a signature are not merged with parts that have one.
- **Test.** A wire-shape replay: a fake stream whose part carries `thought_signature=b"sig"` yields an event with the meta; after one runtime round, the round-2 `contents` built for Gemini carry `thought_signature == b"sig"` on that `function_call` part. Case not written against: two calls in one round, only one signed, stay separate parts with the signature on the right one.
- **Files.** `models/llm.py`, `llm/gemini.py`, `agent_runtime.py`.
- **Certification note.** Google's docs make this required on Gemini 3; no Gemini key is funded (D35), so the verifier certifies on the wire-shape test and records the live check as outstanding.

**R15-LEAD-007 (every Gemini turn fails before the request).**
- **Mechanism (reproduced at base).** `schemas.gemini_tools` puts the catalog's JSON Schema into `function_declarations[].parameters`, which google-genai validates as its OpenAPI-subset `Schema`: `coupons_per_year.enum` holds ints and `arrange_layout.panels.items.type` is a list, so `GenerateContentConfig` raises 8 validation errors. The same declarations under `parameters_json_schema` (a `FunctionDeclaration` field in 2.5.0) validate cleanly.
- **Fix.** Project Gemini declarations with `parameters_json_schema` (the raw catalog schema), not `parameters`. No per-schema coercion.
- **Test.** `types.GenerateContentConfig(tools=gemini_tools(<every internal id>))` constructs. Case not written against: monkeypatch `TOOL_SCHEMAS` with a schema using `oneOf` and a `["string","null"]` type, and it still constructs.
- **Files.** `agent_tools/schemas.py`.

**R15-LEAD-008 (xAI native search returns 410).**
- **Mechanism.** `native_search.PROVIDER_LEVEL_NATIVE_SEARCH` contains `xai` (`native_search.py:65`), so every xAI turn with native search on gets `search_parameters` (`openai.py:575-582`, `native_search.py:161-169`); xAI retired Live Search (live 410, batch-3 verifier).
- **Fix.** xAI has no native-search rung until it moves to the Agent Tools API: drop `xai` from `SUPPORTS_NATIVE_SEARCH` and `PROVIDER_LEVEL_NATIVE_SEARCH`, and remove the `search_parameters` injection. xAI keeps the local `web_search` tool.
- **Test.** `native_search_available("xai", None, "grok-4")` is False; the runtime keeps `web_search` in `tool_ids` for an xAI turn; the OpenAI adapter's xAI request kwargs carry no `search_parameters`. Case not written against: the one-shot cross-verify channel (`native_search_oneshot`) does not pick xAI.
- **Files.** `llm/native_search.py`, `llm/openai.py`.

**R15-RESEARCH-005 (remaining half).**
- **Mechanism.** Batch 3 made the deep engine stamp `out["degraded_reason"] = deep.SYNTHESIS_TIMEOUT_REASON` (`agent_tools/deep_research.py:420-422`) and fixed the thin-coverage copy and floor number formatting. `agent_tools/research.py` `_stamp_execution` (`:101-138`) builds the `ResearchExecution` from `_derive_loop` and the fast-loop rule only, so the engine's stated reason never reaches `execution.degraded_reason`.
- **Fix.** `_stamp_execution` uses the payload's `degraded_reason` when the engine stated one; the fast-loop degradation rule still applies when the loop is `fast`.
- **Test.** A deep-engine stub whose LLM call times out with web sources present: the tool result's `execution.degraded_reason == "synthesis_timeout"` and the brief carries no thin-coverage copy. Case not written against: an ULTRA (heavy loop) payload with the same stated reason.
- **Files.** `agent_tools/research.py`.

**R15-DATA-041 (compare_symbols windows).**
- **Mechanism.** `_return_pct_window` (`compare_symbols.py:28-43`) is `(last/first - 1) * 100` over whatever bars came back; per-symbol output carries only the float; best/worst rank across symbols regardless of window.
- **Fix.** Each symbol carries `bars`, `window_start`, `window_end`. Rank best/worst only across symbols whose `window_start` falls within a few trading days of the common start; otherwise `relative = {best: None, worst: None, note: "windows not comparable: <sym> has <n> bars since <date>"}`.
- **Test.** ESTABLISHED (6-month series) vs NEWLY_LISTED (2 bars): no best/worst, note names NEWLY_LISTED. Case not written against: a long-listed symbol whose provider history starts mid-window (a gap) is also excluded.
- **Files.** `compare_symbols.py`.

**R15-DATA-046 (World Bank default country).**
- **Mechanism.** `macro_router` routes IN to `world-bank` for its India series, but `world_bank_provider._parse_series_id` returns `_DEFAULT_COUNTRY = "USA"` for a bare id (`:41`, `:131-139`), and all 9 featured ids are bare.
- **Fix.** `_parse_series_id(series_id, region)`: a bare id takes the region's country (IN to IND; others unchanged). `macro_router` passes the request region.
- **Test.** IN-region featured GDP growth resolves to IND. Case not written against: a second featured id (CPI inflation) through the router.
- **Files.** `macro/world_bank_provider.py`, `macro/macro_router.py`.

**R15-AGENT-011 (sidecar half; C1).**
- **Mechanism.** The catalog tells the model the result "renders in the backtest panel" (`catalog.py:868-870`), and `run_custom_backtest.py:9-12` repeats it; no frontend code fetches an agent-started run (`grep 'backtest/runs' src/` hits only a comment).
- **Fix.** C1: the optional `run_id` param on `open_panel`, and the synthetic `open_panel` event after a successful `run_custom_backtest` (built next to `_auto_publish_event`). Keep the description; it becomes true once W2 lands.
- **Test.** A stub `run_custom_backtest` returning `{"ok": true, "runId": "bt-1"}` makes the runtime yield exactly one `open_panel` with `{"panel": "backtest", "run_id": "bt-1"}` and a unique id; a failed run yields none.
- **Files.** `catalog.py`, `agent_runtime.py`.

Run `test_capability_catalog.py` and `test_mcp_catalog_parity.py` after the catalog edits.

### W2: `workflow-backtest-feeds` (opus, 10 entries plus the frontend half of `AGENT-011`)

**R15-CODE-PLATFORM-002 and R15-AGENT-015 (one root cause: the node contract is hand-copied into TS with no parity check).**
- **Mechanism (refuter-corrected: 7 of 10 built-ins).** `graph-state.flowToSpec` copies handle ids and config keys verbatim (`graph-state.ts:99`); the engine wires `inputs[target_port] = upstream[source_port]`. Drift: `compute.indicator` config `indicator` vs `indicator_id` and out `values` vs `result`; `ai.agent_invoke` config `prompt` vs `prompt_template` (`node-registry.ts:457-462` vs `builtin.py:166-169`) and out `response` vs `content`; `logic.branch` in `condition` vs `value`, outs `true`/`false` vs `true_path`/`false_path`; `logic.compare` ins `left`/`right` vs `a`/`b`, op `ne` vs `neq`; `action.notify_desktop` in `message` vs `message_template`; `transform.json_path` `input`/`value` vs `value`/`extracted`; `flow.sleep` `duration_ms` vs `seconds`.
- **Fix.** The sidecar handlers are canonical. Declare each built-in's ports and config keys once in `workflow_nodes/__init__.py` next to its `register_node_type` call; correct the 7 TS specs to those names (no aliases: the old keys never worked, so no working saved graph depends on them). Pin parity with one checked-in fixture, `sidecar/tests/fixtures/workflow_node_types.json`: a pytest asserts it equals the declared specs, and a vitest asserts `node-registry.ts`'s built-ins match it. Either side drifting fails a test.
- **Tests.** The parity pair above. `AGENT-015`'s pin: a spec built by `flowToSpec` from the palette's Invoke Agent node with a typed prompt runs the handler with that prompt (stubbed `invoke_agent` records the prompt). Case not written against: a palette-built `transform.json_path` → `action.log` graph returns the extracted value.
- **Files.** `node-registry.ts`, `workflow_nodes/__init__.py`, `builtin.py` (docstrings only if needed), new fixture, tests.

**R15-AGENT-016 and R15-CODE-PLATFORM-003 (one root cause: the agent node has no creds and launders every failure).**
- **Mechanism.** The panel POSTs `{spec, mode}` only (`NodeEditorPanel.tsx:386-391`); `WorkflowRunRequest` has no credential fields (`models/workflow.py:66-74`); the documented `VYSTED_<PROV>_API_KEY` env fallback does not exist; `agent_invoke` catches every exception and `LLMErrorEvent`, substitutes `"(no provider key configured)"` and returns normally (`builtin.py:183-207`), so the engine records `ok` (`workflow_engine.py:367-386`). A config `api_key` is persisted plaintext in the saved spec.
- **Fix.** C7: the run request carries `provider`/`model`/`api_key`; the router publishes them for the run with `config.set_request_llm_creds` (reset in `finally`); `agent_invoke` uses node-config `provider`/`model` overrides, else the request creds (`config.get_llm_creds()`), and never reads a key from config or inputs. `agent_invoke` raises on an `LLMErrorEvent` or exception with the real message, so the engine records `error`. `WorkflowSpec` rejects any node config carrying `api_key` (covers REST save/run and MCP save_workflow, which validate through the model). The panel sends the current chat selection's provider, model and keychain key, the way `ChatSidebar.tsx:780-795` resolves them. Fix the docstring. Tests that asserted the sentinel encode the defect: fix them and say why in the commit.
- **Tests.** An adapter error yields node status `error` and run status `error` naming the node and the message; a spec with `config.api_key` is rejected on save and on run; with creds on the request, a stubbed `invoke_agent` receives that provider/model/key. Case not written against: an unknown `agent_id` also ends `error`, not `ok`.
- **Files.** `builtin.py`, `models/workflow.py`, `routers/workflow.py`, `types/workflow.ts`, `NodeEditorPanel.tsx`.

**R15-CODE-FRONTEND-006 and R15-CODE-PLATFORM-016 (one root cause: two SSE clients for one wire).**
- **Mechanism.** `NodeEditorPanel.tsx:386-431` runs a private `consumeSse` (`:937`) into local state; the store's `appendEvent` (`store/workflow.ts:203-220`), the only feeder of `pendingNotifications`, has no production caller; `useDesktopNotificationBridge` (`desktop-notification.ts:92-110`) therefore never fires while the node output reads `notified: true`.
- **Fix.** One consumer: the store's (it has tests, `workflow.test.ts:201-302`). The panel drives its server run through the store (`runWorkflow` plus the store's run log, or at minimum the store's frame parser feeding `appendEvent` for every server event) and its private `consumeSse` is deleted. Add an `AbortController` (unmount/Stop) and a terminal run-error row when the stream fails. Do not delete store tests.
- **Test.** A server stream containing a `notify_desktop` node-complete intent reaches `pendingNotifications` from the panel's Run. Case not written against: a stream that fails mid-run renders a run-error, not a green run.
- **Files.** `NodeEditorPanel.tsx`, `store/workflow.ts`.

**R15-DATA-040 (partial backtest universe).**
- **Mechanism.** `bar_loader._load_one_symbol` returns `[]` on `ProviderError` (`bar_loader.py:145-149`); `run_backtest` raises only when every symbol is empty (`backtest_engine.py:444`); `warnings` carry only skipped buys (`:471-476`).
- **Fix.** After loading, name every requested symbol with no bars (and its reason when known) in `warnings`, with "metrics cover N of M symbols".
- **Test.** One of three symbols raises `ProviderError`: warnings name it and the coverage. Case not written against: a symbol returning an empty series without an error is named too.
- **Files.** `bar_loader.py`, `backtest_engine.py`.

**R15-DATA-029 (India symbols in earnings, analyst and news lanes).**
- **Mechanism.** `earnings_provider._normalise_symbol` (`:79-81`) and `analyst_ratings_extended._normalise_symbol` (`:131-132`) turn `.NS`/`.BO` into `-NS`/`-BO`; `news_provider` formats the request symbol into the per-symbol Yahoo feed as is (`:94-99`), so bare `BDL` hits the US namesake. `_yahoo_symbol` (`yfinance_provider.py:97+`) already does the region-aware mapping.
- **Fix.** Import `yfinance_provider._yahoo_symbol` (C3) and use it before every Yahoo call in the three lanes; delete both local normalisers.
- **Test.** `RELIANCE.NS` stays `RELIANCE.NS` in earnings and analyst calls; bare `BDL` in an IN session builds the `BDL.NS` feed URL; `INFY` in IN resolves to `INFY.NS`, not the ADR. Case not written against: `532540.BO` passes through the analyst lane unchanged.
- **Files.** `earnings_provider.py`, `analyst_ratings_extended.py`, `news_provider.py`.

**R15-DATA-030 (news tagging).**
- **Mechanism.** `_tag_symbols` (`routers/news.py:62-74`) runs `\b<request string>\b` over title and summary and drops untagged items when symbols are requested; `RELIANCE.NS`, `HDFCBANK`, `SBIN` never appear in prose, and a 1-letter ticker matches the article "a".
- **Fix.** Tag against an alias set per symbol: the suffixed form, the bare form (`locale.strip_exchange_suffix`), and the resolved company name. Bare-ticker text matching needs 2+ characters; a 1-letter ticker matches by company name only. An item fetched from a symbol's own per-symbol feed is tagged to that symbol by provenance when the provider keeps that origin.
- **Test.** "Reliance Industries Q2 profit rises" tags `RELIANCE.NS`; "Nvidia unveils a new chip… A report" does not tag `A`. Case not written against: "State Bank of India raises rates" tags `SBIN`.
- **Files.** `routers/news.py` (and `news_provider.py` for provenance, same writer).

**R15-DATA-032 (fabricated estimate statistics).**
- **Mechanism.** `EarningsEstimateDetail` sets `eps_estimate_median = eps_mean`, `revenue_estimate_median = rev_mean`, stddev `(high - low) / 4`, and `revenue_analyst_count = analyst_count` read from the EPS row, with `analyst_count` defaulting to 0 (`earnings_provider.py:425-448`); every calendar event uses the same stddev proxy (`:245-270`).
- **Fix.** Leave median, stddev and revenue analyst count `None` unless upstream supplies them; `analyst_count` is `None` when missing, not 0. Correct the `types/earnings.ts` field docs; `EpsEstimateGrid.tsx` renders `null` as a dash, never 0.
- **Test.** A frame with no `numberOfAnalysts` and no median gives `None` for all four. Case not written against: the calendar `EarningsEvent` path carries no stddev proxy.
- **Files.** `earnings_provider.py`, `types/earnings.ts`, `EpsEstimateGrid.tsx`.

**R15-AGENT-011 (frontend half; C1).**
- **Fix.** `useBacktestStore.loadRun(runId)` fetches `GET /backtest/runs/{runId}` and stores the run as complete; the `open_panel` handler (describe and apply) loads it and sets `activeRunId` when `panel === "backtest"` and `run_id` is present.
- **Test.** A vitest: applying `open_panel {panel: "backtest", run_id: "bt-1"}` with a mocked fetch leaves the store with `runs["bt-1"]` complete and `activeRunId === "bt-1"`. Certify only after W1 merges.
- **Files.** `store/backtest.ts`, `host-actions.ts`.

### W3: `chat-runs-mcp` (opus, 9 entries)

**R15-CODE-FRONTEND-002 (transcript ownership mid-stream).**
- **Mechanism.** `chat-history.loadMessages`/`clear` null `streamingMessageId` unconditionally (`chat-history.ts:236-237`); `agent-spaces.newSpace/switchTo/closeSpace` (`agent-spaces.ts:43-80`) and `research-spaces.restoreSpace/switchSpace` (`research-spaces.ts:196-216`) call them with no stream check; the tab strip stays enabled while streaming (`ChatSidebar.tsx:1146-1167`). Deltas then hit an id no longer in `messages`, the archived partial stays `pending` forever, `streaming` reads false so the queue starts a second run. Separately, entering a research space replaces the live chat-tab transcript without archiving it into `agent-spaces`.
- **Fix.**
  - A space switch while a stream is in flight stops that run first through the Stop path (a registered abort in `chat-history`, called by every switch), finalizes the partial in its own thread as stopped, then switches. Deltas never land in another thread; no second run starts while one is live.
  - Entering a research space archives the live transcript under the active agent-space tab; leaving it restores that tab's transcript instead of `clear()`.
- **Tests.** Switch tab mid-stream: abort is called, the archived partial is not pending and is marked stopped, and no second run starts until the first settles. Case not written against: opening a research space mid-stream from `workspace.ts`'s entry point behaves the same, and a tab-2 conversation survives a research-space round trip.
- **Files.** `chat-history.ts`, `agent-spaces.ts`, `research-spaces.ts`, `ChatSidebar.tsx`, `workspace.ts` (only if its call sites need the stop).

**R15-AGENT-013 (Delegate output).**
- **Mechanism.** `_drive_run` keeps only delta text and `[tool_use name]` markers (`run_manager.py:164-181`), dropping `publish_brief`, host actions and progress; `_digest_transcript` truncates each message to 500 chars (`runs_store.py:184`); the rail renders running/paused only and a finished run vanishes (`AgentsRail.tsx:29-32`); the poller's terminal branch syncs status only (`delegate-runs.ts:176-179`); nothing fetches `GET /runs/{id}`. The launch copy promises review of proposed changes (`ChatSidebar.tsx:846-850`) with no channel.
- **Fix.**
  - The run row stores the final assistant text untruncated, the last `publish_brief` input, and the host-action `tool_use` events; `GET /runs/{id}` returns them (dual-case like today).
  - The launch records the originating chat thread (agent-space id). On the poller's terminal branch, fetch `GET /runs/{id}` once, append the answer to that thread (live or archived), publish the brief through the existing brief ingest path, and enqueue each host action through the normal proposed-changes gate (no new flag). Correct the launch copy to what the gate does.
- **Test.** A scripted delegate run emitting text over three rounds, a `publish_brief` and a `write_note`: `GET /runs/{id}` returns the full text (over 500 chars) and the brief; the poller test appends the answer to the originating thread, publishes the brief and enqueues the note. Case not written against: a run that ends in `error` after writing text still delivers its partial text with the error.
- **Files.** `run_manager.py`, `runs_store.py`, `routers/runs.py`, `models/run.py`, `delegate-runs.ts`, `AgentsRail.tsx`, `ChatSidebar.tsx`.

**R15-AGENT-029 and R15-CODE-PLATFORM-037, plus the frontend half of `LIFECYCLE-005` (one invariant: every stream call ends in exactly one terminal callback, C8).**
- **Mechanism.** `streamChat`/`streamAgentInvocation` await `getSidecarBaseUrl()` before `consumeSseStream`'s try (`streaming.ts:133-153`), so a not-ready sidecar rejects outside `onError`; `dispatchFrame` wraps parse, normalise and the consumer handler in one try and relabels a consumer throw "unparseable SSE frame" (`:251-269`); `consumeSseStream` does not track a terminal frame, so a clean EOF with no `done`/`error` leaves the message streaming (`:225-249`).
- **Fix.** Move the base-URL await inside the try; try only around parse/normalise and call the handler outside it; track `sawTerminal` and call `onError("The stream ended before the answer finished.")` after the read loop when false; `handleSend` wraps its stream call so any rejection settles the message.
- **Tests.** `getSidecarBaseUrl` rejecting calls `onError` once and clears `streamingMessageId`; a consumer throw surfaces its own message; EOF without `done` calls `onError` once. Case not written against: an agent-invocation stream (not chat) ending without `done`.
- **Files.** `streaming.ts`, `ChatSidebar.tsx`, `sidecar-client.ts` (only if needed).

**R15-LIFECYCLE-005, R15-CODE-AGENT-002 and R15-DATA-083 (one class: MCP failures escape the error path and health flags stay green).**
- **Mechanism.** A failed streamable-http open raises an anyio cancellation / cancel-scope `RuntimeError` that bypasses `except Exception` (`mcp_client.py:95-120`); `list_tools`/`call_tool` catch only `(TimeoutError, McpError, OSError)` (`:152-190`), so the next call after a dead child escapes as `CancelledError`; `openbb_mcp_provider` maps `Exception`, not `BaseException`, to `ProviderError` (`:239-248`), so the registry (`provider_registry.py:410`, catches `ProviderError` only) never falls through; `available` means "endpoint configured" (`:147-157`); both providers set their health flags only after `_decode_tool_result`, which raises first on an `isError` payload.
- **Fix.** In `McpClient`, run the open and each call so a transport failure (including an anyio cancellation that is not an outer-task cancellation: check `asyncio.current_task().cancelling()`) drops the session and raises `ProviderError`; a genuine outer cancellation still propagates. In both providers, one try covers call plus decode and sets `lastToolCallOk=false` and `lastError` on any failure; `available` reports false after a failed call until the next success.
- **Tests.** Parametrise `test_mcp_client.py` over `anyio.ClosedResourceError`, `httpx.ReadError` and a transport `CancelledError`: session dropped, `ProviderError` raised. A client pointed at a closed port makes `get_fundamentals` fall through to the next provider and status reports `available: false` with `lastError`. An outer `task.cancel()` still cancels. Case not written against: `sec_filings_provider` with a stub `isError` response sets its flags.
- **Files.** `mcp_client.py`, `openbb_mcp_provider.py`, `sec_filings_provider.py`.

**R15-DATA-038 (SEC sections and insider parsers).**
- **Mechanism.** `_sections_from_payload` (`sec_filings_provider.py:325`) accepts only a list; sec-edgar-mcp returns a dict of section strings. `_insider_rows_from_payload` (`:393`) skips rows without `transaction_date`/`trade_date` and reads the issuer from `issuer_name`/`company_name`, dropping every filing-level Form-4 row and the top-level `name`. The empty result is cached 24 h / 1 h.
- **Fix.** Accept the dict-of-sections shape and filing-level Form-4 rows (issuer from `name`); a success payload that parses to zero rows is logged as a parse error and not cached as an empty.
- **Test.** The captured sec-edgar-mcp payloads (from the verification evidence) parse to non-empty sections and 5 Form-4 rows. Case not written against: an unknown-shape success payload is not cached.
- **Files.** `sec_filings_provider.py`.

**R15-DATA-039 (SEC form types).**
- **Mechanism.** `FilingFormType` is a 7-form `Literal` (`models/sec.py:23`) used as `Filing.form_type` (`:35`); `_coerce_form_type` returns `None` for anything else and the row is skipped (`sec_filings_provider.py:217-236`, `:288-291`) after `limit` went upstream; no dropped count.
- **Fix.** `Filing.form_type: str` (the `Literal` stays only as the filter enum); rows are never dropped; when a form filter is applied after the upstream limit, the response reports `dropped_count`. Mirror `types/sec.ts`.
- **Test.** An INFY-shaped payload of 20-F/6-K rows lists them. Case not written against: `10-K/A` and `SC 13D` rows are listed for AAPL.
- **Files.** `models/sec.py`, `sec_filings_provider.py`, `types/sec.ts`.

### W4: `market-data-gate` (opus, 11 entries)

**R15-DATA-015 and R15-DATA-016 (one class: the served 52-week pair has no exchange witness on /fundamentals).**
- **Mechanism.**
  - The pair is Yahoo's `fiftyTwoWeekHigh`/`Low` passed through as `ok` (`yfinance_provider.py:467-469`); the gate only checks internal consistency (`correctness_gate.py:274-301`).
  - The exchange-direct witness (`research/range_check.py`) runs only in research, fetches one venue, and declines below 300 days/180 bars. ELCIDIN moved to NSE in April 2026, so Yahoo and the NSE series both start at the NSE listing and the BSE year is never consulted (`DATA-015`).
  - DAL.BO's Yahoo history carries zero-volume forward-filled bars at a 2023 print (1,238 bars, 33 with volume), so the 52w low and the chart are built from non-trades (`DATA-016`).
- **Fix.**
  - Add a 52w range witness to `correctness_gate.apply_witnesses` (cached through `_cached_witness`, like the batch-3 witnesses) for an Indian listing: exchange-direct daily history from every venue the instrument lists on (NSE and BSE), merged by date, reusing `range_check.compute_range`.
    - Exchange range diverges beyond tolerance: the provider pair is **flagged** (kept), the reason naming the exchange range, its venues and window start.
    - Merged history shorter than 52 weeks: the reason says "since <date>".
    - No trade in the trailing 52 weeks: the pair is **withheld** with "no trades in 52 weeks (last trade <date>)".
  - `yfinance_provider.get_history` drops forward-filled non-trade bars from an equity series: volume 0 and open = high = low = close = the prior close. Index and crypto series are untouched.
- **Tests.** An ELCIDIN two-venue fixture (NSE since 2026-04-20 plus the BSE year) flags the pair with the BSE low 87,003 in the reason; a DAL history fixture withholds with the last trade date; the forward-filled bars are gone from DAL's served history. Case not written against: an index series (volume 0 with moving OHLC) keeps every bar, and a dual-listed liquid name (RELIANCE) stays `ok` with no flag.
- **Files.** `correctness_gate.py`, `research/range_check.py`, `yfinance_provider.py`.

**R15-DATA-047 and R15-DATA-049 (one root cause: the dividend paid-TTM leg runs only in research).**
- **Mechanism.** `_apply_dividend_ttm` (`research/fast.py:207-235`) and the D56 paid-vs-declared cross-check exist only on the research path; `/fundamentals` leaves `dividend_per_share_ttm` null with no reason and serves Yahoo's `dividendRate` as `ok`; `dividend_history` returns `unavailable`, not affirmed zero, for an empty series even with 12+ months of price history; Yahoo's `trailingAnnualDividendRate` 0.0 is ignored.
- **Fix.** Move the leg into one shared function (in `dividend_history.py`) called by both `research/fast.py` and `apply_witnesses`: fill `dividend_per_share_ttm` with `field_meta`; flag `dividend_per_share` when it diverges from the paid TTM; affirmed zero gives `dividend_per_share_ttm = 0.0` and `dividend_yield = 0.0` with the reason; affirm zero when price history covers 12 months and the dividend series is empty; map `trailingAnnualDividendRate`.
- **Tests.** An ABBOTINDIA special-dividend fixture flags `dividend_per_share` on `/fundamentals`; a never-payer (DAL/ICON shape) reads an affirmed 0.00% with its reason. Case not written against: ELCIDIN's yield is served from the paid TTM, and research output is unchanged.
- **Files.** `dividend_history.py`, `research/fast.py`, `correctness_gate.py`, `yfinance_provider.py`.

**R15-DATA-034 and R15-DATA-082 (one class: a served path skips the correctness gate).**
- **Mechanism.** `yahoo_batch_provider.fundamentals_from_v7` is called directly (`screener.py:895`, `:1242`; `fundamentals_warm.py:180`), not through a `ProviderDeclaration`, so `validate_fundamentals` never runs; the yield bound exists as 2.0 in `yahoo_batch_provider.py:430` and in `yfinance_provider`, and 0.25 in the gate (`correctness_gate.py:50`). Crypto passes `validate=None` in `provider_registry.get_quote/get_history` (`:457`, `:470`), and `ccxt_provider._ticker_to_quote` substitutes 0.0 for a missing price (`:52`).
- **Fix.** Call `validate_fundamentals` inside `fundamentals_from_v7` (one site covers all three callers); delete the local 2.0 bounds so `_PLAUSIBLE_YIELD_FRACTION` is the only bound. Gate crypto quotes and series with only the session-staleness leg skipped; `_ticker_to_quote` raises `ProviderError` when no price field exists.
- **Tests.** A v7 row with yield 1.5 comes back withheld with `field_meta`; a screener run over that row (new test file, no `screener.py` edit) does not match `dividend_yield > 0.5`. Case not written against: a ccxt ticker with neither `last` nor `close` raises and the registry does not serve a 0.0 quote.
- **Files.** `yahoo_batch_provider.py`, `yfinance_provider.py`, `provider_registry.py`, `ccxt_provider.py`, `correctness_gate.py`.

**R15-LIFECYCLE-004 (parser field drift).**
- **Mechanism.** `nse_provider.py:405-409` and `bse_provider.py:240-244` substitute `close` for a missing open/high/low and 0.0 for missing volume; `validate_series` (`correctness_gate.py:149-174`) checks only emptiness, last close and symbol.
- **Fix.** A missing O/H/L/V key is a parse failure that raises `ProviderError` (the registry falls through); sweep every exchange parser (`nse_provider`, `bse_provider`, `nse_bhavcopy` and the jugaad lane) for the same substitution. `validate_series` also rejects a series in which every bar is flat with zero volume.
- **Tests.** Parametrised over O/H/L/V renamed in a captured NSE `historicalOR` window: `ProviderError`, never flat bars. Case not written against: the BSE bhavcopy parser with a renamed column, and a hand-built all-flat zero-volume series rejected by the gate.
- **Files.** `nse_provider.py`, `bse_provider.py`, `nse_bhavcopy.py` (only if the sweep finds it), `correctness_gate.py`.

**R15-DATA-035 (BSE bhavcopy poisoning).**
- **Mechanism (refuter-corrected).** Before publication BSE answers 200 text/html; `parse_bhavcopy` yields an empty frame and `bse_provider.py:319`/`:329-331` write a permanent `''` marker that `_bhavcopy_for` (`:275`) treats as no data forever.
- **Fix.** An HTML body is "not published yet", never an empty day. The empty marker is honoured only when it was written after its trading day (file mtime in IST later than that day); a marker written on or before its day is ignored and re-fetched, which also clears markers poisoned before this fix.
- **Test.** An HTML-200 fixture for today writes no honoured marker and a later fetch returns the day. Case not written against: a marker left on disk from before the fix (mtime equal to its day) is re-fetched.
- **Files.** `bse_provider.py`.

**R15-DATA-036 (BSE history parse cost).**
- **Mechanism (refuter-corrected numbers).** `_assemble_history` calls `_bhavcopy_for` → `parse_bhavcopy` for every day in range, building a whole-market DataFrame to select one scrip (`bse_provider.py:424-440`); a warm 1y chart of KSE took 8.7 s. The new 52w witness above makes this path hot on `/fundamentals`.
- **Fix.** Read only the requested scrip's row from each cached day file (stream the CSV, stop at the match) instead of parsing the whole market into a frame.
- **Test.** A timing-bounded test over 250 cached synthetic 5,000-row day files assembles a year for one scrip well under 1 s. Case not written against: the quote path over 14 days returns the same bars as before.
- **Files.** `bse_provider.py`.

**R15-DATA-020 (cross-exchange dedup; batch-3 reopen).**
- **Mechanism.** The batch-3 key `(symbol, sha1(normalised 120-char body prefix), IST day)` (`corporate_disclosures.py:317-333`) collides only on exact prefixes. Live: RELIANCE "Company executives participated" vs "the Company executives participated", "shareholder''s approval" vs "shareholders approval", INFY's BSE body is boilerplate ("Enclosed"), so dual-listed feeds still list most filings twice.
- **Fix.** Replace the exact key with cross-feed pairing in the merge loop (`:381-389`): an NSE item and a BSE item of the same symbol and IST day, disseminated within a short window of each other, pair when their normalised texts (body, or subject when the BSE body is boilerplate) are similar enough (token overlap, stdlib only). Within-feed exact duplicates still collapse. NSE wins a pair.
- **Tests.** Fixtures captured from the live feeds (add only): RELIANCE 2026-09-09 credit rating (NSE 20:35 / BSE 20:37), TCS 2026-09-05 HyperVault press release, INFY transcript with the "Enclosed" body: each pair collapses. Negative: two different same-day filings minutes apart stay separate. Case not written against: a HDFCBANK pair captured the same way.
- **Files.** `corporate_disclosures.py`.

**R15-UI-090 (sidecar half: calendar region from the instrument).**
- **Mechanism.** `_label_freshness` in `routers/quotes.py:30-48` and the series label in `routers/history.py:47` pass `config.get_region()` to `locale.freshness_for`, so a US quote read in an IN session during NSE hours is `live`.
- **Fix.** Both labels resolve the calendar region from the instrument (exchange suffix, provider lane, or `quote.exchange`), not the session.
- **Test.** Region IN, AAPL quote timestamped during NSE hours: freshness is not `live`. Case not written against: the AAPL history series under the same session.
- **Files.** `routers/quotes.py`, `routers/history.py`, `locale.py` (a helper, only if needed).

### W5: `panels-screener` (sonnet, 11 entries plus the Portfolio half of `UI-090`)

**R15-UI-004 and R15-UI-005 (one class: an unknown rendered or published as a value).**
- **Mechanism.** `fetchPositionQuote` catches every error to `null` (`portfolio/api.ts:23-32`), so the panel's failure banner and Retry (`PortfolioPanel.tsx:794-808`) never render. `metrics.ts:111-113` sums resolved rows from 0 and `mixedCurrencies` is false when `byCurrency` is empty, so no data publishes `totalValue: 0` (`PortfolioPanel.tsx:202`), which `context-provider.ts:53-61` forbids.
- **Fix.** `fetchPositionQuote` returns `{quote} | {error}` (a not-found is an unresolved symbol, not a failure); `fetchPositionQuotes` returns `{quotes, failed}`; `failed > 0` sets `quotesError`. No resolved quote publishes `totalValue: null` with note "no live quotes resolved" and renders "Market value: — (no live quotes)"; a partial total's note names the excluded holdings.
- **Tests.** `mockRejectedValue`: banner and Retry render. All-unresolved: `null` plus the note, never 0. Case not written against: one holding priced and one failing shows the partial note and the banner.
- **Files.** `portfolio/api.ts`, `PortfolioPanel.tsx`, `metrics.ts`.

**R15-UI-090 (Portfolio half).**
- **Fix.** Each Portfolio row shows the session/staleness cue from the quote's `freshness` and timestamp, using the existing `market-session.ts` helpers and the `StalenessBadge` the Watchlist uses (import only). No wire change.
- **Test.** An `eod` quote renders the cue. Certify with W4's sidecar half.
- **Files.** `PortfolioPanel.tsx`.

**R15-UI-009 and R15-UI-025 (one class: a browser-only primitive in the desktop webview).**
- **Mechanism.** `downloadCsv` clicks a Blob `<a download>` (`csv.ts:27-37`), the path `export-artifact.ts:4-8` documents as blocked; `NotesToolbar.tsx:146` uses `window.prompt`, which WKWebView does not implement.
- **Fix.** `downloadCsv` saves through `saveTextArtifact` (the Rust `write_text_atomic` path, `export-artifact.ts:78`) and returns the path or error; Watchlist and Portfolio show the saved path or the error. The Link button opens an inline URL popover. An ESLint `no-restricted-properties` rule bans `window.prompt`, `window.alert` and `window.confirm` in `src/`.
- **Tests.** `downloadCsv` invokes the Tauri write command (mocked) and never clicks an anchor inside Tauri; the Link popover applies the mark. Case not written against: the Watchlist export path.
- **Files.** `csv.ts`, `WatchlistPanel.tsx`, `PortfolioPanel.tsx`, `NotesToolbar.tsx`, `eslint.config.mjs`, `export-artifact.ts` (only if needed).

**R15-UI-006 (screener truncation).**
- **Mechanism.** `run_screener` sorts matches by market cap (`screener.py:407-413`) and cuts at `limit` (`:784-785`); `result_count = len(rows)` (`:841`); the panel always sends 200 (`store/screener.ts:315`) and a header click sorts only that page.
- **Fix.** `ScreenerRequest` gains `sort_by` (a screener field, default `market_cap`) and `sort_dir` (`asc`/`desc`), applied before the cut with `None` last; `ScreenerResult` gains `matched_count`. Mirror `types/screener.ts`. A header click re-runs with the new sort; the header reads "N matched · showing top K by <field>"; a Show more control raises the limit.
- **Tests.** Sidecar: `sort_by=pe_ratio asc` over a fixture where the lowest P/E is a small cap returns it first; `matched_count > result_count`. Panel: the header copy. Case not written against: `desc` on a field with NULLs keeps NULLs last.
- **Files.** `screener.py`, `models/screener.py`, `types/screener.ts`, `store/screener.ts`, `ScreenerResultsTable.tsx`, `ScreenerPanel.tsx`.

**R15-UI-007 (preset after a nested group).**
- **Mechanism.** `ScreenerPresets.apply` calls `setCriteria` only (`ScreenerPresets.tsx:125-131`); `runScreener` gives a nested tree precedence and ANDs the formula (`store/screener.ts:359-373`); `setCriteria` clears neither.
- **Fix.** A preset applies through the same reset as `resetCriteria`/`applyFilters` (group null, advanced false, formula empty) with its own criteria and universe.
- **Test.** Nested group plus formula, then a preset: the request carries exactly the preset's criteria. Case not written against: an "or" combinator set before the preset.
- **Files.** `ScreenerPresets.tsx`, `store/screener.ts`.

**R15-DATA-044 (NULL criterion field).**
- **Mechanism.** `_finalize` itemizes only `needed_fields` (`screener.py:731-737`), which `_enrichment_fields_needed` (`:447`, called at `:1064`) limits to v7-enrichable fields; `pe_ratio`, `dividend_yield`, `price_to_book` are not among them, and `_evaluate_criterion` returns False for `None`.
- **Fix.** Itemize on every field the criteria and formula reference, not only the enrichable ones.
- **Test.** `pe_ratio < 20` over rows with NULL P/E itemizes them as `missing_field:pe_ratio`. Case not written against: `price_to_book` under a nested group.
- **Files.** `screener.py`.

**R15-DATA-093 (custom universe keys).**
- **Mechanism.** Custom symbols are only stripped and uppercased (`screener.py:195-205`) and looked up by that literal key; bare `RELIANCE` misses the warm `RELIANCE.NS` row; the placeholder is "AAPL MSFT NVDA".
- **Fix.** Canonicalise each custom symbol with `yfinance_provider._yahoo_symbol` (C3) before the store lookup; the placeholder follows the session region.
- **Test.** Five bare IN names under an open Yahoo circuit evaluate from the warm `.NS` rows. Case not written against: a `.BO` code passes through.
- **Files.** `screener.py`, `ScreenerPanel.tsx`.

**R15-UI-003 and R15-CODE-FRONTEND-020 (one root cause: the builder re-declares the sidecar's vocabularies).**
- **Mechanism.** `form.tsx:16-54` hard-codes 20 tool ids and 7 providers; `validate()` filters tools to that list (`:139-141`); editing reconciles over it, so saving strips every other tool; an unknown provider falls back to `anthropic`. The test asserts the UI against the same constants.
- **Fix.** `GET /custom-agents/tool-ids` returns `sorted(agent_selectable_tool_ids())`, declared before the `/{agent_id:path}` route; the builder renders tools from it and providers from `GET /llm/providers`; form state keeps the agent's full tool set and provider, showing unknown ids as read-only chips; delete the `validate()` filter; the static arrays stay only as a fallback before the sidecar answers.
- **Tests.** Pytest: the route equals `agent_selectable_tool_ids()`. Vitest: edit and save round-trips an agent holding `research`, `web_search` and provider `openrouter` unchanged; the builder renders the mocked response, not the constants. Case not written against: a tool id the sidecar lists but the fallback array lacks is selectable.
- **Files.** `routers/custom_agents.py`, `form.tsx`, `AgentBuilderPanel.tsx`, `agent-builder.test.tsx`.

**R15-LIFECYCLE-007 (docker under a GUI launch).**
- **Mechanism.** `_run_docker` executes a bare `"docker"` (`searxng_manager.py:128-144`); launchd gives a Finder-launched app `PATH=/usr/bin:/bin:/usr/sbin:/sbin`.
- **Fix.** Resolve the docker binary once: `shutil.which("docker")`, then the known install locations (`/usr/local/bin`, `/opt/homebrew/bin`, `~/.orbstack/bin`, `/Applications/Docker.app/Contents/Resources/bin`); use the absolute path for every call.
- **Test.** `PATH=/usr/bin:/bin` with a fake docker in a probed location: `detect()` reports `cli_present: true`. Case not written against: `status` and `setup` also use the resolved path.
- **Files.** `searxng_manager.py`.

---

## 3. Integrator run order and gates

1. Work in a scratch worktree (`git worktree add <scratchpad>/b4-int 004-r4-experience-rebuild`), never in the main repo (it has uncommitted register and CLAUDE.md edits). Run `git branch --show-current` before every merge.
2. Audit each branch through `origin/worktree-agent-b4-<w1..w5>`: `git merge-base --is-ancestor 1999844 origin/<branch>` (a stale base means re-dispatch) and `git diff --stat 1999844..origin/<branch>` touching only its §1 files.
3. Merge `--no-ff` in this order:
   - **W4** (owns `types/data.ts` and the gate; W5's screener interplay C5 relies on it).
   - **W1** (the `open_panel.run_id` param and synthetic event, C1).
   - **W2** (consumes C1; imports `_yahoo_symbol`, C3).
   - **W3** (independent).
   - **W5** (screener contract; imports `_yahoo_symbol`).
4. Gates after all five merge:
   - `export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`
   - `ruff format --check sidecar && ruff check sidecar`
   - `pnpm format:check`, `pnpm lint` (the new restricted-properties rule)
   - `pnpm ci-local` in the background with the exit code recorded
   - `node scripts/smoke-test-sidecars.mjs`
5. Grep checks:
   - no `replace(".", "-")` normaliser left in `earnings_provider.py` or `analyst_ratings_extended.py`;
   - `"(no provider key configured)"` gone from `builtin.py`;
   - no `validate = None if asset_class == "crypto"` in `provider_registry.py`; no `or 0.0` price in `ccxt_provider.py`;
   - no local `2.0` yield bound in `yahoo_batch_provider.py` or `yfinance_provider.py`;
   - `search_parameters` no longer built in `openai.py`;
   - no `parameters"` key in `schemas.gemini_tools`;
   - no `window.prompt` in `src/`, no `a.download` in `csv.ts`;
   - `config.get_region()` gone from the freshness label paths in `routers/quotes.py` and `routers/history.py`;
   - `NodeEditorPanel.tsx` has no private `consumeSse`.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge; add D-B4-1 (window-bound tool subsetting) to `docs/redesign/DECISIONS_FOR_OPERATOR.md` for visibility. Writers do not edit docs.
7. Certify `AGENT-011` only after W1 and W2 merge; `UI-090` only after W4 and W5 merge. `AGENT-006` certifies on the wire-shape test with the live Gemini 3 check recorded as outstanding (no key, D35).

---

## 4. Deferred to the next batch (feature-size, Tier-4, GUI-only proof, or capacity)

- **Tier-4 (locked files): `RELEASE-001`, `RELEASE-002`, `RELEASE-003`, `RELEASE-004`.** Signing, a release pipeline, the updater artifacts and CI triggers all edit `.github/` and/or `src-tauri/tauri.conf.json`. Surface to the operator; no writer.
- **India data lanes (feature-size, one next-batch set): `DATA-023` (pledge), `DATA-024` (bulk/block/SAST), `DATA-025` (corporate actions), `DATA-026` (statement capabilities + quarterly route; its prerequisite `DATA-001` is fixed), `DATA-027` (exchange-derived IN fundamentals provider), `DATA-028` (market-wide India results calendar).** Each adds a lane, a route or a capability and a `types/data.ts` mirror; they collide with W4's disclosure and fundamentals files this batch.
- **`DATA-014` (DAL leg).** Needs an exchange-filed results witness (Yahoo's own statement agrees with the wrong TTM); feature-size; collides with W4.
- **`DATA-017`.** Resolver master refresh and NSE Emerge coverage; cross-cutting and feature-size.
- **`DATA-110`.** A persisted last-good valuation snapshot for throttled screener runs; feature-size.
- **`DATA-037`.** Crypto range buttons; capacity (its slot went to `AGENT-029`, which the class rule required). Standalone; first in line.
- **`AGENT-020`.** Agent memory read-back needs a new per-invocation capability plus a snapshot field; it pairs with `AGENT-040`/`AGENT-050` (memory and context carry-over) as one next-batch set.
- **`AGENT-007`, `AGENT-017`.** An eval loop and a default-model swap proven on it; process and live evidence, not a code fix this batch can pin. `AGENT-017` depends on `AGENT-007`.
- **`AGENT-023`.** A scheduler/trigger layer and an outbound action node; feature-size.
- **`LIFECYCLE-001`.** Moving the MCP joins off Tauri's main thread plus late MCP port binding in the sidecar; its proof is a real app launch (GUI), and it collides with W3 on `openbb_mcp_provider.py`.
- **`LIFECYCLE-008`.** Diagnostics log and support bundle; feature-size, outside the four areas.
- **`CODE-AGENT-001`.** Origin allow-list on the sidecar; outside the four areas and sidecar-boundary adjacent (possible Tier-4).
- **`CODE-PLATFORM-004` (+ `CODE-PLATFORM-019`), `CODE-PLATFORM-005`.** Workflow branch/skip semantics and the QuantLib global-date lock; outside the four areas; capacity.
- **`LEAD-001`.** MCP sidecar requirement pins (release area); capacity. The integrator keeps the batch-3 constraints workaround.

---

## 5. Label-mates and neighbours not taken (different root cause)

- **`AGENT-081`** (`promise-without-surface`): `open_company_overview.highlight` is never consumed by the panel; a different consumer gap from `AGENT-011`.
- **`CODE-PLATFORM-065`** (`stream-terminal-invariant`): the workflow router swallows spec-validation errors server-side; W3's invariant is the chat SSE client.
- **`AGENT-026`** (`done-treated-as-success`): a `done` frame with a bad `finish_reason`; W3's invariant is a missing or pre-stream terminal.
- **`CODE-FRONTEND-028`** (`archive-drops-message-status`): the research-space archive has no status field; W3 finalizes a stopped partial before archiving but does not add the persisted status or agent-space persistence.
- **`UI-079`** (`csv-injection`): formula cells in CSV output; a cell-escaping rule, not the save primitive.
- **`UI-036`** (`freshness-not-shown`): Portfolio prices never refresh; W5 adds the session cue (UI-090) but not the polling.
- **`CODE-AGENT-024`, `CODE-AGENT-025`**: the duplicated MCP discovery code and dropped `structuredContent`; W3 fixes the error path in both copies without the refactor.
- **`DATA-071`** (`silent-partial-result`): the cold BSE range cap of 8 downloads; a coverage-field mechanism, not the backtest warning.
- **`DATA-085`, `DATA-086`, `UI-053`**: World Bank title enrichment, search failure masking, IMF slash ids; distinct macro mechanisms.
- **`DATA-062`, `DATA-065`**: quote batch join and weekly-bar freshness; different freshness inputs.
- **`AGENT-045`, `AGENT-069`**: compare_symbols name resolution and `gather` exceptions.
- **`CODE-DATA-021`**: `compute_range`'s duplicated window predicate; W4 reuses `compute_range` as is.
- **`AGENT-046`**: non-unique tool-call ids; W1 gives its synthetic event a unique id only.
- **`CODE-FRONTEND-026`**: `drainNotifications` drops intents appended mid-send.
- **`UI-055`, `UI-056`, `CODE-FRONTEND-009`, `CODE-FRONTEND-010`**: other screener mechanisms (empty-vs-failed copy, error frame, agent save_screen/run).

---

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B4-1 Context admission.** A model-facing result cap with an elision marker (window-relative when the adapter reports a window); oldest tool results elided when a round's estimate exceeds the window; domain subsetting from catalog cue words only on a window-bound adapter (today only Ollama). The allow-list and D21 are unchanged: the subset replaces a silent head truncation.
- **D-B4-2 Gemini projection.** Tools go out as `parameters_json_schema`; thought signatures ride runtime-internal `provider_meta`, excluded from the SSE wire.
- **D-B4-3 xAI native search off** until moved to the Agent Tools API; xAI keeps the local `web_search` tool.
- **D-B4-4 Agent-started backtests** open through a synthetic `open_panel(backtest, run_id)` host action on the normal gate, mirroring research auto-publish.
- **D-B4-5 Workflow node contract.** Sidecar handler names are canonical; the palette follows; parity is pinned by one shared JSON fixture. No aliases for the old TS keys.
- **D-B4-6 Workflow creds.** The run request carries the foreground provider/model/key in the body like agent invoke (never persisted or logged); the agent node raises on failure; a spec carrying `config.api_key` is rejected.
- **D-B4-7 One workflow SSE consumer** (the store's); the panel's private parser is deleted.
- **D-B4-8 Delegate output.** Final text, the brief and host actions persist untruncated on the run row and are delivered once on the terminal poll: the answer to the originating thread, the brief through ingest, host actions through the normal gate.
- **D-B4-9 Mid-stream switch stops first.** A tab or research-space switch stops the live run, finalizes the partial as stopped in its own thread, then switches; a research space archives and restores the chat tab.
- **D-B4-10 MCP failures are ProviderErrors.** Transport failures (including non-outer anyio cancellations) drop the session and raise `ProviderError`; health flags record every failure; `available` is false after a failed call until the next success. The chat SSE client guarantees one terminal callback.
- **D-B4-11 SEC form type is an open string**; rows are never dropped; a zero-row parse of a success payload is an error, never a cached empty.
- **D-B4-12 52-week witness on /fundamentals.** Exchange-direct, all venues, merged: flag on divergence (never substitute, as D-B3-8 and range_check's contract); "since <date>" when shorter than a year; withhold when no trade in 52 weeks. Forward-filled non-trade bars are dropped from equity history.
- **D-B4-13 One dividend paid-TTM leg** shared by /fundamentals and research.
- **D-B4-14 The gate's yield bound is the only one**; the v7 path validates at its mapping; crypto is gated except for session staleness; ccxt never serves 0.0.
- **D-B4-15 A missing O/H/L/V is a parse failure**; `validate_series` rejects an all-flat zero-volume series.
- **D-B4-16 BSE empty markers** count only when written after their trading day (mtime); an HTML answer is "not yet published". History reads one scrip row per day file.
- **D-B4-17 Cross-feed announcement pairing** by same symbol and day, short dissemination gap and fuzzy text similarity.
- **D-B4-18 Freshness calendar from the instrument**, not the session region.
- **D-B4-19 Screener sorts server-side before the limit** and reports `matched_count`; presets reset the nested group and formula.
- **D-B4-20 No browser-only primitives in the webview**: CSV saves through the Rust text writer; `window.prompt/alert/confirm` are lint-banned.
- **D-B4-21 Agent Builder vocabularies come from the sidecar** (`GET /custom-agents/tool-ids`, `GET /llm/providers`).
- **D-B4-22 Portfolio unknowns are null with a note**; a quote failure raises the banner, a not-found does not.

---

## 7. Writer ground rules

1. Work in your own isolated worktree and branch (`worktree-agent-b4-<w1..w5>`). First run `git reset --hard 1999844a7d3fac7261928bdbf5745685ec127033` and confirm with `git log -1`. Push after each concrete deliverable.
2. One focused commit per entry or per root-cause group, conventional, no emojis, ending with the session's attribution trailer.
3. Tests only where the repo keeps them (`sidecar/tests`, `src/**/*.test.ts(x)`), one focused test per pinned behaviour; where a class is involved, pin the case the fix was not written against, as named above. Never delete, skip or weaken a test; if a test encodes the defect, fix it and give the reason in the commit body. Never special-case code to satisfy a test. Scratch scripts never become tests.
4. Before every Python commit: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`. Before every TypeScript push: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files. Export the PATH line from §3 first.
5. Touch only your §1 files. Honour C1 to C10 exactly: names, signatures and wire strings. A needed change elsewhere goes into `issues[]` with the exact line.
6. No refactoring beyond the entry, no flags or defensive code for cases that cannot happen. Anything odd outside your entries goes to `issues[]`.
7. Never re-add trading. Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/` or the register. Read no `R15_BRIEF*.md` and nothing under `r15/local/`. No GUI. Never print a secret.
8. Run long commands (pytest suites, `ci-local`) in the background; never pipe them through `head`/`tee` in the foreground.
