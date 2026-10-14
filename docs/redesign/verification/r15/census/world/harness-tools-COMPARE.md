# R15 Census: WORLD-COMPARE for harness tools, evals and provider quirks vs the in-app agent

Worker model id: `claude-opus-5-5[1m]` (session-2 rewrite of the 2026-09-19 stub, which had no content)
Date: 2026-09-23 · HEAD `f763a44` · branch `004-r4-experience-rebuild`
Input research: `census/world/harness-tools.md` (T-1..T-33, CHECKLIST 1-25, provider addendum P1-P8).
Raw findings: `census/raw/world-harness-tools.json` (prefix `WLD-harness-tools`).
Status: COMPLETE (see the end of the file).

## Method

I read the real code paths that WORLD-COMPARE names: `sidecar/services/agent_tools/catalog.py` (all 50
capabilities), `schemas.py`, `agent_runtime.py` (loader grant, read-only gate, dispatch, tool loop,
reconstruction, read-back), `services/llm/{openai,anthropic,gemini,ollama}.py`, `services/mcp_server.py`,
`src/lib/host-actions.ts` and `src/store/proposed-changes.ts`. I measured the tool surface in-process.
The local lane (`llama3.1:8b` via `vy.py`, free) was driven 3x on one T-30 scenario against the isolated
stack `:52152`. I replayed the documented Anthropic SSE shape through the real adapter, locally with no
network. Before filing anything I cross-checked each candidate gap against every existing
`census/raw/*.json`. A practice whose gap is ALREADY a raw finding is marked with that id and is not
refiled. This file only adds what the world lens sees and the code-sweeps did not.

Measured facts used below (the in-process script is in the Appendix):

- **Tool surface:** 50 internal capabilities (29 `read_handler`, 19 `host_action`, 2 `per_invocation`).
  All 50 are `default_grant=True`, so `_grant_first_party_hands` (`agent_runtime.py:189-221`) gives
  every first-party agent the full set. Serialised OpenAI-shape definitions come to **~8.8k tokens**
  (chars/4). On top of that, the copilot system prompt is ~2.7k tokens. A read-intent turn still sends 37
  tools (~6.4k tokens). Trading is removed from the product (23 Sep), but `propose_order` and
  `broker_portfolio` are still in the catalog at HEAD. Dropping them gives 48 tools.
- **Local lane budget:** Ollama gets `num_ctx=16384` (`ollama.py:47`). About 11.5k of those tokens (~70%)
  are used by tool definitions plus the system prompt before the terminal preamble, history or any tool
  result arrives.

## Practice-by-practice table

Legend: **present** (file:line) · **partial** · **absent** · **n/a** (why, for a local BYOK finance agent).
"Filed" names the raw finding that already covers the gap. "NEW" names the finding this pass files.

### Tool design (T-1..T-7, checklist 1-11)

| # | Practice | Verdict | Evidence / notes |
|---|---|---|---|
| 1 | Tool surface designed as the ACI, effort budgeted like UI | **present** | One capability catalog is the single source of truth, projected to adapters, MCP and the allow-list (`catalog.py:1-25`, `schemas.py:36-40`). It carries per-tool timeouts (`catalog.py:101-106`) and per-domain "what next" timeout hints (`catalog.py:1568-1589`). This is deliberate ACI work. |
| 2 | Consolidate multi-call workflows into one deep tool | **present** | `research` (`catalog.py:315-391`) gathers price, fundamentals, news, filings and web in one call, and escalates depth in place. `market_overview` (`catalog.py:261-285`) and `compare_symbols` (`catalog.py:198-222`) are the same pattern. |
| 3 | Prune overlapping tools until a human could always name the right one | **partial** | Four ways put a symbol on screen: `open_panel(symbol)` `catalog.py:954`, `set_chart_symbol` `:982`, `open_company_overview` `:996`, `arrange_layout(symbol)` `:1114`. Screening has three: `screener_run` `:393`, `write_screener_filters` (with `run:true`) `:1236`, `save_screen` `:1415`. Earnings and analyst data are split into three narrow tools each (`:502-571`). The prose restatement of the catalog is filed as COD-agent-runtime-8. The size and overlap problem is **NEW: WLD-harness-tools-1**. |
| 4 | Keep the live tool count under ~20; 30-50 is the accuracy cliff | **absent** | 50 tools on every round of every first-party agent (`agent_runtime.py:189-221`). The loader grants the whole catalog by design (R10 E5), and `default_grant` is never False (filed as a dead knob in COD-agent-tools-catalog-ledger-4). No per-agent or per-intent subsetting exists, except the read gate that strips host actions (`agent_runtime.py:1286-1305`), and that still leaves 37. **NEW: WLD-harness-tools-1.** |
| 5 | Namespace ids by service/resource, within the MCP charset | **partial** | Ids are MCP-legal snake_case with loose prefixes (`sec_*`, `earnings_*`, `analyst_*`, `portfolio_*`, `macro_*`). The resource prefix is inconsistent (`price_data` / `price_option` / `price_bond` / `price_target_history` share a prefix but belong to three domains). A `domain` tag exists (`catalog.py:34-53`) but the model never sees it. Low impact on its own. It becomes relevant only with deferred loading (row 6). |
| 6 | Defer-load rarely-used definitions; keep 3-5 hot tools resident | **absent** | All definitions are serialised up front on every round (`schemas.py:51-97`). No tool search and no `defer_loading`. For the local lane, the alternative that fits is catalog-driven subsetting by intent/domain, since tool search is an Anthropic server feature. **NEW: WLD-harness-tools-1.** |
| 7 | Poka-yoke: enums, structure, no argument the caller already knows | **partial** | There is good enum use (timeframes, universes, regions, `arrange_layout.pattern`). The gaps: `research.depth` mixes legacy and new names in one enum (`["normal","deep","ultra","quick","heavy"]`, default `normal`), while its description says "'quick' (default)" (`catalog.py:353-363`). The `backend` param is labelled "INTERNAL" in prose but is exposed to the model (`catalog.py:374-384`), and a model-passed `backend` outranks the user's Settings selection (`deep_research.py:431-435`). `rounds`/`wall_seconds` ranges live only in prose; the handler clamps them (`deep_research.py:424-425`). Within the handlers this is harmless. It is recorded as description-hygiene, not filed. |
| 8 | Example calls (`input_examples`) on tools with non-obvious params | **absent** | No tool carries examples beyond inline "e.g." fragments. The fragments are US-centric in an India-first product: `price_data` "e.g. AAPL or BTC/USDT" (`catalog.py:153`), `fundamentals` "e.g. AAPL" (`:231`), `macro_series` FRED ids (`:470`). Only `resolve_symbol` and `corporate_announcements` show Indian names. Not filed: the resolver-first rule (`catalog.py:176-178`) is the working control, and no outcome change was shown in this pass. |
| 9 | Descriptions pass the intern test and state sibling boundaries | **partial** | Strong in places: `research` escalation, `write_screener_filters` "does NOT run", `publish_brief` vs auto-publish, `corporate_announcements` as "the India counterpart of sec_filings_list". Weak on the earnings/analyst trio and on `news` vs `market_overview` vs `web_search`. |
| 10 | Audit tool descriptions for contradictions | **partial** | See row 7 (`research` default). `shareholding_pattern` telling the model it lacks the FII/DII split it actually returns is filed as WLD-T-10. No automated description audit exists: `test_capability_catalog.py` checks registry parity, not wording. |
| 11 | Natural-language names in results, not cryptic ids | **present** | Results carry symbol, provider, headline and title text (e.g. `price_data.py:60-79`). Host-action results carry prose status notes (`agent_runtime.py:1190-1220`). |

### Token-efficient results (T-8..T-11, checklist 12-15)

| # | Practice | Verdict | Evidence / notes |
|---|---|---|---|
| 12 | `response_format` concise/detailed enum | **absent** | No tool offers it. The closest thing is `research.depth`, which controls work done, not the verbosity of what is returned. Not filed separately: its cost shows up mainly on the local lane, which WLD-harness-tools-1 covers. |
| 13 | Paginate/filter/truncate by default AND say so | **partial** | There are caps: `price_data` returns 90 bars (`price_data.py:59`), analyst history is capped at 60 rows, news takes `limit`. The silence about truncation is already filed: COD-market-data-providers-2-13 (90 bars silently, even when "1y" is asked) and COD-agent-tools-catalog-ledger-8 (sec_tools has no clamp). |
| 14 | Filter/aggregate in code before the model sees it | **present** | `research`'s fast gather runs the sub-tools in code and returns one provenance-tagged bundle (`agent_tools/research.py:203-217`, `fast.gather_fast`). `compare_symbols` aggregates server-side. |
| 15 | Let the agent orchestrate multi-tool chains in code | **n/a (for now)** | This needs a sandboxed code-execution tool. For a local-first desktop app on a laptop, running model-written code is a safety surface the product has not opened. The deep tools (row 2) are the pragmatic substitute. |

### Errors and behavioural metadata (T-12..T-14, checklist 16-19)

| # | Practice | Verdict | Evidence / notes |
|---|---|---|---|
| 16 | Every tool error is a prompt: rule broken, value, current state | **partial** | Timeouts do this well (`agent_runtime.py:655-667` plus the per-domain hints). Invalid args on the OpenAI family also do (`openai.py:548-590`: "invalid arguments for X: <reason>; call again with valid args"). Everything else surfaces `tool 'x' raised: <exc>` (`agent_runtime.py:671-672`), which is a raw exception string. The envelope inconsistency is filed as COD-agent-tools-catalog-ledger-7. The unresolved-name case is filed as SURF-COMPOSER-CHAT-2. |
| 17 | Separate model-fixable execution errors (`isError`) from protocol errors | **partial** | Internally, every failure rides the same `{ok:false,error}` tool result, which is the right channel for self-correction. On the MCP surface Vysted never sets `isError` (filed COD-mcp-servers-13). |
| 18 | Annotate read-only/destructive/idempotent/open-world; never enforce safety with hints | **partial** | Only `readOnlyHint` is projected (`mcp_server.py:153`), and only read handlers are projected at all (`catalog.py:1469-1474`), so no destructive tool reaches MCP. `openWorldHint` is left at its default of true, which is correct for data fetchers. The hint that lies (`run_custom_backtest` readOnlyHint=true while it writes) is filed COD-agent-tools-catalog-ledger-1. Safety is correctly NOT enforced by hints: the server-side read gate is `agent_runtime.py:1286-1305` and the order gate is `proposed-changes.ts:57,118,139`. |
| 19 | `outputSchema` + `structuredContent` | **absent (MCP)** | The FastMCP projection declares no output schemas (`mcp_server.py:141-180`), and McpClient drops `structuredContent` (filed COD-mcp-servers-6). For external MCP consumers only. Internally, results are JSON strings the model reads, so there is little outcome change. Not refiled. |

### Evals (T-15..T-22, checklist 21-25)

| # | Practice | Verdict | Evidence / notes |
|---|---|---|---|
| 21 | ~20 real queries on REAL data, run on every tool change | **absent** | There are real-data *reference packs* (R13 battery, 17 hostile small caps: `verification/r13/battery/BATTERY_MANIFEST.md`), plus manual scenario drives (`scripts/r15/vy.py`). Nothing replays a fixed scenario set against the agent when a tool, description, prompt or adapter changes. Every agent test uses fakes: "No network, no real LLM, no real tool registry" (`sidecar/tests/test_research_fast.py:3`). The Anthropic fixture feeds a tool_use shape the real API never sends (`tests/test_llm_anthropic.py:165-171`), which is why COD-llm-adapters-2-1 shipped. **NEW: WLD-harness-tools-2.** |
| 22 | Grade END STATE first, trajectory second | **absent** | There is no grader. The pieces for end-state grading already exist: the host-action ack ledger (`services/action_ledger.py:47-87`), the published brief's `structured` bundle, and the reference packs. They are not wired into a scorer. Part of WLD-harness-tools-2. |
| 23 | Explicit missing-parameter and missing-function cases | **absent** | No case exists. The live run below shows why it matters: the local lane sent `cost_basis: null` for a required field. **NEW: WLD-harness-tools-3** (the defect) and WLD-harness-tools-2 (no case). |
| 24 | Report pass^k, not pass@1 | **absent** | No metric of any kind. The census's own repros already show single-run optimism (SURF-COMPOSER-CHAT-1 is "3/3", which is a pass^k-style result that is recorded by hand, not by the harness). Part of WLD-harness-tools-2. |
| 25 | One LLM judge, one rubric, aligned to a human; feed transcripts back into the tools | **absent** | Nothing exists. Cost note: one judge call per scenario on the free lane is $0. Part of WLD-harness-tools-2. |

### Provider quirks (T-23..T-33, checklist 20 + P1-P8)

| # | Practice | Verdict | Evidence / notes |
|---|---|---|---|
| 20 | Strict/grammar-constrained tool inputs per provider; keep sensitive values out of schemas | **partial** | No adapter sends `strict: true`. The OpenAI family does post-hoc schema validation plus one repair round (`openai.py:198`, `:500-600`). Anthropic, Gemini and Ollama coerce silently (filed COD-llm-adapters-1). No user data sits in enums or patterns: the enums are static market vocab (`catalog.py:63-70`). |
| P1 | Carry the function NAME on the tool-result turn | **present** | `agent_runtime.py:1578-1586` sets `metadata={"name": tool_call.name}`. `gemini.py:47-63` serialises `function_response.name` from it. |
| P2 | Echo reasoning/thought state back verbatim | **partial** | DeepSeek-reasoner `reasoning_content` is echoed on the reconstructed turn (`agent_runtime.py:1527-1529`). Gemini `thought_signature` is **dropped**: the stream keeps only `name`/`args`/`id` (`gemini.py:155-163`, `models/llm.py:146-152` has no slot for it), and the reconstructed `function_call` parts are rebuilt from name+args (`gemini.py:67-83`). Google documents the signature as *required* for function calling on Gemini 3. **NEW: WLD-harness-tools-4.** |
| P3 | Repair known parameter-shape 400s in place, retry once, message-matched | **present (OpenAI)** / n/a elsewhere | `openai.py:372-388` plus `:470-474` covers the gpt-5.x `reasoning_effort` 400, matched on the message and not the model name, exactly as the research prescribes. Anthropic `thinking` is never sent (`anthropic.py:108-130`), so the `type:"enabled"` 400 of T-26 cannot occur. |
| P4 | Gate capabilities per MODEL; "accepted" is not "supported" | **partial** | Native search is gated per model on OpenAI and OpenRouter (`native_search.py`, CLAUDE.md gotcha), but per provider on Gemini, Groq and xAI (filed COD-llm-adapters-2-2, -2-3). |
| P5 | Validate required args in the HANDLER; assume a cheap model guesses | **partial** | Read handlers mostly validate (e.g. `price_data.py:36-37`). Host actions do not validate in the sidecar at all (`agent_runtime.py:1188-1220` returns a synthetic ok). The frontend coerces a missing `cost_basis` to 0 (`host-actions.ts:1265-1266`) and the review card omits it (`host-actions.ts:762-775`). **NEW: WLD-harness-tools-3.** |
| P6 | Hold reasoning/budget settings stable in a cached conversation | **n/a** | No thinking budget or effort is sent on any provider. The only per-request change is the OpenAI `reasoning_effort="none"` repair, which is sticky within `_create_with_retry`. Prompt caching itself (no `cache_control` in `anthropic.py:108-130`) belongs to the harness-context topic. |
| P7 | Normalise `tool_choice` per provider and price the choice | **absent** | No adapter sends `tool_choice` or `parallel_tool_calls`. The visible consequence is that at the round cap the model can still emit calls that are never run. That is filed as COD-agent-runtime-1 (the fix there is exactly `tool_choice:"none"` on the final round). Not refiled. |
| P8 | Echo server-side tool blocks unchanged; never `tool_result` a server id | **partial** | The Anthropic adapter only surfaces `tool_use` (`anthropic.py:224-231`), so no `tool_result` is ever sent for a `srvtoolu_` id, which is correct. But the reconstructed assistant turn keeps only client `tool_use` blocks and drops `server_tool_use`/`web_search_tool_result` and preceding text (`agent_runtime.py:1530-1542`, `anthropic.py:71-87`). As a result, later rounds lose the searches already run, and the per-request `max_uses` cap resets each round. That is filed as INT-spec-90-3. Not refiled. |
| T-24 | Pairing by id (Anthropic) vs name (Gemini) | **present, but see bug** | Pairing is correct. Separately, every Anthropic tool call dispatches with `input={}` because tool_use is emitted at `content_block_start`. Filed COD-llm-adapters-2-1 and re-confirmed here by an independent replay (Appendix). Non-unique Ollama/Gemini call ids are filed COD-llm-adapters-2-5. |
| T-31 | Prompted planning and preambles on weak reasoning | **present** | There is a visible plan-then-execute pre-pass for compound requests (`agent_runtime.py:1393-1413`). The weak local lane is skipped (`_planner_enabled`, `agent_runtime.py:110-113`). |
| T-33 | Client hygiene: confirm sensitive ops, show inputs, timeouts, audit log | **partial** | The review gate shows the diff before apply (`host-actions.ts` `describeHostAction`, `proposed-changes.ts:118`). Timeouts are per tool (`agent_runtime.py:652-667`). There is **no sidecar-side log of tool dispatches** (the only `logger` calls in `agent_runtime.py` are loader warnings plus one option-drop warning, lines 251-269, 823, 1385). Diagnostics is the L3-diagnostics lifecycle item's territory, so it is not filed here. |

## What the world lens adds (the four NEW findings)

1. **WLD-harness-tools-1 (high): 50 tools, ~8.8k tokens of definitions, every round, every agent,
   including the default free local 8B lane with a 16k window.** This is past both published
   thresholds (OpenAI "fewer than 20"; Anthropic "degrades once you exceed 30-50"), and those thresholds
   were measured on frontier models. The design choice was right for the E5 drift bug and wrong for
   selection accuracy. The smallest fix is catalog-driven, not a new system. Add a
   `hot`/`domain` projection. Send the hot core (resolve_symbol, research, price_data, fundamentals,
   market_overview, get_terminal_state, plus the 5 read-safe panel actions) always, and add a domain's
   tools only when the intent classifier or the prior round touched that domain. On Anthropic, use
   `defer_loading` + tool search on the same projection.
2. **WLD-harness-tools-2 (high): no agent eval loop.** No fixed real-data scenario set, grader, pass^k
   or regression run exists anywhere. The product's claimed moat is "a finance-tuned agent". The census
   found a provider adapter that sends `{}` args on every call (COD-llm-adapters-2-1), host-action
   narration drift (SURF-COMPOSER-CHAT-10) and local-lane leaks (SURF-COMPOSER-CHAT-1). Each of these
   would be a red cell on day one of a 20-scenario × 4-lane × k=3 suite. The parts already exist
   (vy.py, the reference packs, the action ledger, brief `structured`). What is missing is the loop.
3. **WLD-harness-tools-3 (high): a missing required argument becomes a fabricated or ₹0 cost basis in
   the user's tracked portfolio.** On the default local lane (Appendix) the model asked for the price
   0 of 3 times. It sent `cost_basis: null`, then an invented `1000`, then `0`. No adapter-side
   validation runs on Ollama, and the sidecar returns a synthetic ok.
   The frontend then coerces the value to 0, and the review card leaves the missing cost out of its
   title. Under AUTO it applies with no review at all. After that, the portfolio P&L shows the whole
   market value as gain. A validator alone would not catch the invented 1000, so the fix also has to
   change the tool description and the review card. This is the T-30 "the small model guesses" failure, landing in the one
   write surface that stays in scope after the trading removal.
4. **WLD-harness-tools-4 (high): Gemini thought signatures are dropped on multi-round tool turns.**
   The adapter keeps no `thought_signature` and rebuilds `function_call` parts from name+args. Google:
   "Gemini 3 models may return thought signatures for all types of parts ... it's *required* for
   function calling signatures". Gemini 3 is exactly the family where COD-llm-adapters-2-3 says the
   default function+search round is valid, and the live catalog (`gemini.py:205-233`) offers it.
   NOT TESTED live: this needs a Gemini key, and no Gemini lane is funded in this run. Cost: one
   2-round invoke on a Gemini 3 Flash model (< $0.01).

## Not filed, and why

- Over-long/contradictory `research` description, INTERNAL params, and US-centric examples (rows 7-10):
  no user outcome was shown in this pass, since handler normalisation and clamps absorb them. Record
  for the description-audit test that WLD-harness-tools-2 would add.
- `response_format` (row 12) and code-orchestration (row 15): folded into WLD-harness-tools-1's fix
  shape, or not applicable.
- `tool_choice` at the cap, silent truncation, error envelope, MCP `isError`/`structuredContent`,
  strict/validation parity, per-provider search gating, server-block echo: already filed (ids above).

## Appendix: evidence

**Tool-surface measurement** (in-process, `sidecar/.venv/bin/python`, HEAD f763a44):

```
internal 50 default_grant 50 mcp 28
Counter({'read_handler': 29, 'host_action': 19, 'per_invocation': 2})
copilot    tools 50 tool_tokens 8806 system_prompt_tokens 2741 | read-intent tools 37 tokens 6422
researcher tools 50 tool_tokens 8806 system_prompt_tokens 1453 | read-intent tools 37 tokens 6422
buffett    tools 50 tool_tokens 8806 system_prompt_tokens 1211 | read-intent tools 37 tokens 6422
```
(tokens = chars/4 of `json.dumps(openai_tools(spec.tools))`; tiktoken not installed in the venv.)

**Anthropic SSE replay** (scratch `wld-tools/anth_stream_probe.py`; a local HTTP server replays the
documented wire shape: `content_block_start` tool_use `input:{}` → two `input_json_delta` →
`content_block_stop`; real anthropic SDK 0.100.0; no network):

```
TOOL_USE_EVENT name=price_data input={}
LLMDoneEvent  tool_use
```
This independently re-confirms COD-llm-adapters-2-1 (already admitted). It is cited here only because
T-24 row "pairing correct" would otherwise overstate the lane's health.

**T-30 local-lane drive** (3 runs, `vy.py invoke copilot "I bought 40 shares of Sumax Enterprises last
month. Add them to my portfolio." --provider ollama --model llama3.1:8b --mode agent --autonomy ask`,
isolated stack `:52152`, $0; events in scratch `wld-tools/cost-basis-run{1,2,3}.jsonl`):

| run | `portfolio_add_position` input sent by the model | asked for price? | narration |
|---|---|---|---|
| 1 | `{symbol:"SUMAX.NS", quantity:40, cost_basis:null, purchased_at:"2026-08-23"}` | no | "I've proposed adding 40 shares ... for review" |
| 2 | `{symbol:"Sumax Enterprises", quantity:40, cost_basis:1000, purchased_at:"2026-08-23"}` | no | "... cost basis - $1000" (invented, and in dollars) |
| 3 | `{symbol:"Sumax Enterprises", quantity:40, cost_basis:0, purchased_at:"2026-08-23"}` | no | "I've added Sumax Enterprises to your portfolio. The proposal is waiting for your review" |

pass^3 for "asks for the missing price" = 0/3. Symbol resolved to a ticker: 1/3. The final-round
`input_tokens` Ollama reported (2790-2812) is far below the ~11.5k static estimate. That fits prefix
KV-cache reuse (Ollama's `prompt_eval_count` counts only newly evaluated tokens), but this pass could
not measure it directly. The token figure in WLD-harness-tools-1 is therefore labelled an estimate.

## Status

COMPLETE: 33 research items plus 25 checklist rows and 8 provider rows compared. Of the gaps, 4 are
NEW raw findings (`census/raw/world-harness-tools.json`, all high). Gaps already covered by 19
existing raw ids are cross-referenced, not refiled. Refute stage: per `PROMPT_refute.md`.
