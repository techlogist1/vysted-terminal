# R15 Census — WORLD-COMPARE: harness context / memory / recovery vs the in-app agent

Worker model id: `claude-opus-5-5[1m]` (session-2 rewrite of the 2026-09-19 stub)
Date: 2026-09-23
Input research: `census/world/harness-context.md` (CHECKLIST 1-20 + 2 supporting practices,
sources S1-S21). Code read at HEAD of `004-r4-experience-rebuild`.
Raw findings: `census/raw/world-harness-context.json` (prefix `WLD-harness-context`).
Status: COMPLETE.

Verdict key: **present** (file:line) / **partial** / **absent** / **n/a** (why, for a local BYOK
finance agent). "Covered by" = an existing census raw finding already owns the defect, so no
duplicate raw is filed here.

## The harness in one paragraph (what was actually read)

One foreground turn = `invoke_agent` (`sidecar/services/agent_runtime.py:1229-1631`): it composes
`[persona system prompt + TERMINAL_CAPABILITIES_PREAMBLE, session preamble (date/locale), terminal
preamble, ≤10 prior text turns, user prompt]` (`_compose_messages`, :506-521; history cap
`_coerce_history` :469-482 and the frontend's own `.slice(-10)` at
`src/modules/chat/ChatSidebar.tsx:749-753`), sends the agent's FULL allow-list of tool schemas
every round (:1273, :1434-1440; the copilot ships 50 tools), and loops up to `_MAX_TOOL_ROUNDS = 6`
(:543). Tool results are `json.dumps(payload)` appended verbatim as `role="tool"` messages
(:576-587, :619-676). Host actions get an ack-ledger read-back that rewrites the tool result from
the panel's real outcome (:1065-1145, :1615-1625). Delegate runs (`run_manager.py`) wrap the same
loop in a `BudgetGuard` (`budget_guard.py`) and persist a digest-shaped checkpoint in
`runs_store.py`. Cross-session memory = research-space transcripts + a claims ledger held in the
frontend workspace blob (`src/store/research-spaces.ts`, rendered into the preamble at
`agent_runtime.py:389-404`). There is no compaction, no tool-result clearing, no token accounting,
and no prompt caching anywhere in the loop.

## Practice-by-practice table

| # | Practice (research CHECKLIST) | Verdict | Evidence in Vysted | Gap / note |
|---|---|---|---|---|
| 1 | Context is a budget with an admission policy; measure tokens-in-window per turn (S1, S21) | **absent** | No token counting anywhere in the loop (`grep count_tokens\|tiktoken` over `sidecar/services` → nothing). Admission is only "last 10 text messages" (`agent_runtime.py:482`, `ChatSidebar.tsx:752`) + a 12-claim preamble cap (:331). Ollama window is fixed at `DEFAULT_NUM_CTX = 16384` (`services/llm/ollama.py:47`, set at :141-143) while the copilot's fixed overhead measured this pass is **35,227 chars of tool schemas (~8.8k tok) + 10,964 chars of system prompt (~2.7k tok)** — ~11.5k of 16.4k tokens before the date/terminal preambles, history, user prompt, any tool result or the answer. | **Gap → WLD-harness-context-1.** The default lane (copilot `defaultProvider: ollama`, `agents/copilot.json:58`) has ~4.8k tokens for everything that matters, and nothing notices when it is exceeded. |
| 2 | Invariants re-injected every request, never only turn 1 (S10) | **present** | The whole system block (persona + capabilities preamble + session preamble + terminal preamble) is rebuilt from the spec on every call (`_compose_messages`, `agent_runtime.py:506-521`); the "never invent figures / fetch live" rules live there (:437-440, :493-503), not in history. | — |
| 3 | Compact on a configured trigger with a STATE-shaped summary (S7, S1) | **absent** | No compaction. Overflow policy is truncation: the 11th-oldest message is silently dropped (`agent_runtime.py:482`). The only "summary" is `summarizeTranscript` (`src/store/research-spaces.ts:33-45`) = the user's last 3 questions, 120 chars each — narrative of what was ASKED, never what was FOUND (figures, conclusions, open questions). | **Gap → WLD-harness-context-2** (conversation window) and **-3** (memory content). |
| 4 | Archive the full transcript before compaction (S10) | **n/a (partially moot)** | There is no compaction to precede. The live transcript is in-memory only (`src/store/chat-history.ts:1-12`); research-space transcripts persist capped at `RESEARCH_SPACE_TRANSCRIPT_CAP` (`research-spaces.ts:47-56`). Once a compactor exists this becomes load-bearing. | Rides on -2's fix. |
| 5 | Every compression restorable: drop payload, keep identifier (S12) | **partial** | Good where it exists: the brief carries `execution.run_id` + source URLs (`agent_runtime.py:906-927`), and claims carry symbol/metric/statedAt (:344-373). But cross-turn history drops every tool call and result outright (`_coerce_history` keeps only `role in (user, assistant)` with string content, :478-481) — no placeholder, no identifier of what was fetched. | Folded into **-2**. |
| 6 | Clear stale tool RESULTS separately from compaction; keep last N (S5, S6) | **absent** | Every tool result stays in `messages` for the rest of the turn and is re-sent on every subsequent round (`agent_runtime.py:1587`, loop :1426-1631) — up to 7 provider requests carry every prior result. No per-result size cap either (`web_search.py:219-235`, `sec_tools.py:107-110` return whole payloads; one `/disclosures/announcements?symbol=RELIANCE` payload measured 21,558 bytes ≈ 5.4k tokens this pass). | Part of **-1**. |
| 7 | Cleared result → placeholder telling the model it was removed (S6) | **absent** | Nothing is ever cleared, and history truncation (:482) leaves no marker. | Part of **-2**. |
| 8 | Gate cache-invalidating edits; keep context append-only; stable prefix (S6, S12) | **partial** | Within a turn the message list IS append-only (good — :1530-1587 only appends; the one in-place edit is the host-action read-back rewrite at :1624-1625, which mutates an already-sent tool result and so breaks any cache from that point). But: the Anthropic adapter sets **no `cache_control` at all** (`services/llm/anthropic.py:104-150`; grep → none), and it concatenates persona + date + the per-turn terminal preamble into one `system` string (:39-94), so even a cached system block would change every turn. For a BYOK Anthropic user every round re-bills ~11.5k tokens of schemas+prompt uncached. | **Gap → WLD-harness-context-5.** |
| 9 | Mask unavailable tools, don't remove them mid-run (S12) | **present** | The tool list is fixed per invocation: read-only stripping and native-search withholding happen once before the loop (`agent_runtime.py:1286-1340`); rounds reuse the same `tool_ids`. | — |
| 10 | Defer tool/MCP schemas, load on demand (S10) | **absent** | First-party agents are unioned with the FULL catalog grant at load (`_grant_first_party_hands`, `agent_runtime.py:189-220`) and all schemas ship every round (:1434-1440). 50 tools / ~8.8k tokens on the copilot. The adapter comment admits this is what broke the local lane at 4096 (`ollama.py:35-39`); the fix raised the window instead of shrinking the admission. | Part of **-1**. |
| 11 | Carry identifiers, not payloads, across boundaries (S1, S2) | **partial** | Research auto-publish ships the execution record + source list, not the model transcript (:795-932) — good. The research engine returns a bundle to the loop, not its trace. But turn→turn and session→session carry prose only (see #5), and the delegate checkpoint stores `"[tool_use NAME]"` placeholders with no args/results (`run_manager.py:161-167`). | Delegate side covered by COD-runs-durable-delegate-2/-9. |
| 12 | Durable, per-user-namespaced store the agent reads FIRST and updates as it goes (S8, S19) | **partial (write-only)** | The agent can WRITE durable memory — `write_note` with a per-symbol `scope` (`agent_tools/catalog.py:1373-1395`) — but no tool, preamble line or terminal snapshot ever READS notes back (`src/modules/chat/context-provider.ts` carries no notes; catalog has no read-notes capability; per-invocation reads are only `get_terminal_state`/`get_portfolio`, `agent_runtime.py:1179-1188`). Research-space memory is read, but it is question-history (#3) and research spaces cannot currently be saved (COD-workspace-layout-2). | **Gap → WLD-harness-context-3.** |
| 13 | Harden that store: traversal, size caps, expiry, secret stripping (S8) | **n/a today** | Notes/workspace blobs are app-owned, keyed by scope strings in the workspace blob, not filesystem paths; no traversal surface. Size caps exist for research memory (`RESEARCH_SPACE_TRANSCRIPT_CAP`, `RESEARCH_SPACE_CLAIMS_CAP`). Becomes load-bearing the moment -3 gives the agent a read path. | — |
| 14 | Initializer session: progress log + checklist before substantive work (S3, S8) | **n/a** | A coding-agent pattern (multi-context-window app builds). The finance analogue — a per-symbol research space that opens with prior state — exists in shape (`agent_runtime.py:389-404`) and is judged under #3/#12. | — |
| 15 | Flip "done" only after verification; mark a capped run PARTIAL (S3, S8, S9) | **partial** | Verification half is a genuine strength: host actions are grounded from the ack ledger before the model narrates (`_grounded_host_action_result`, :1083-1145; `_publish_divergence_notices`, :991-1048), and the capabilities preamble forbids claiming "dispatched" as done (:170-178). Partial half is absent: at the round cap the last round's tool calls are streamed but never dispatched and the turn ends with no answer and no "partial" marker (:1472-1497). | Covered by COD-agent-runtime-1 (high). |
| 16 | Sub-agents only for read-only fact-returning subtasks; decisions single-threaded (S9, S1, S13) | **present** | The only delegated sub-loop is the `research` tool's engine, which is read-only (`catalog.is_read_only`), returns a structured bundle, and never drives the host; all host decisions stay in the single main loop. The planner pre-pass is advisory only (:1387-1413). | — |
| 17 | Pass everything the sub-agent needs; sanitize instruction-shaped patterns in what re-enters the trusted context (S9) | **partial** | Inside the research engine, web evidence is fenced as untrusted (`services/search/scrub.py`, used at `research/deep.py:789-795`, `verify.py:175-185`, `iter.py:800`). But the MAIN loop splices raw tool output unfenced: `web_search` returns attacker-controlled `title`/`snippet`/`excerpt` verbatim (`agent_tools/web_search.py:219-235`), `news`, `corporate_announcements` and the research bundle's markdown likewise, straight into `role="tool"` content (`agent_runtime.py:576-587`, :671-676). That loop holds mutating host actions — including `portfolio_delete_position`, `portfolio_update_position`, `write_note`, `remove_from_watchlist` — which under `autonomy="auto"` dispatch without review (`agent_runtime.py:1201-1212`; frontend auto-applies every non-order kind, `src/store/proposed-changes.ts:115-118`). | **Gap → WLD-harness-context-4.** |
| 18 | Checkpoint to durable storage; resume handle on every run incl. failed (S17, S9, S10) | **partial** | Delegate runs persist to SQLite (`runs_store.py:55-69`) and expose `/runs/{id}/resume` (`routers/runs.py:126-135`). But the checkpoint is lossy and written only at exit, resume drops provider/model/key, no UI calls resume, and a restart leaves zombie `running` rows. Foreground turns have no checkpoint at all (in-memory chat store). | Covered by COD-runs-durable-delegate-2, -6, -9, -10 (+ -1 for the lost answer). No duplicate filed. |
| 19 | Cap turns, spend, fan-out depth, concurrency in the harness; count all iterations in spend (S9, S10, S18, S4, S7) | **partial** | Turns: `_MAX_TOOL_ROUNDS = 6` (:543). Web searches: `_WEB_SEARCH_CAP = 5` (:548, :1551-1565). Per-tool wall timeouts (:612-617, :652-666) + research guard (:588-609). Spend/token/wall/steps ceilings: Delegate runs only (`budget_guard.py:106-162`, `run_manager.py:140-148`); foreground turns have none. Fan-out is fixed (one research engine), so depth/concurrency caps are moot. Research-engine LLM calls are not metered into any guard. | Metering gaps covered by INT-spec-135-143 / COD-research-extraction-synthesis-2 (research unmetered), COD-llm-adapters-2-6 (Gemini thinking tokens), COD-runs-durable-delegate-3/-11/-12. |
| 20 | Typed termination reason; name the model that actually answered when a fallback served it (S10, S18, S20) | **partial** | Typed errors exist (`LLMErrorEvent.code`, e.g. `content_filter` at :1485-1495; humanized adapter errors `openai.py:830-839`). The research lane's Tongyi fallback IS surfaced (`usingFallback`, per CLAUDE.md gotcha / `GET /system/deepresearch/probe`). Missing: `max_tokens`/`length` truncation shown as complete (COD-error-layer-2-3, COD-llm-adapters-2-7); round-cap end (COD-agent-runtime-1); Anthropic `stop_reason="refusal"` passes through as a bare `finish_reason` the runtime never maps (only `content_filter` is handled, :1485). And the curated `openrouter/auto` pick (`config/model_registry.json:71`, `src/store/model-selection.ts:59`) lets OpenRouter substitute any model while the adapter never reads the stream's served `model` field (`services/llm/openai.py:750-830` reads only choices/usage; `LLMDoneEvent` has no model field, `models/llm.py:213-217`). | **Gap → WLD-harness-context-6** (silent substitution). Other termination gaps covered by the cited raws. |
| S-a | Keep the wrong turns (compacted into a lesson) (S12, S15 F9) | **partial** | Within a turn, failed tool results stay in context as structured `{"ok": false, "error": ...}` (:642-676) and invalid-args are surfaced for self-correction (:638-647) — good. Across turns every failure is erased (history keeps prose only, :478-481), so the next turn retries the same dead provider path. | Folded into **-2**. |
| S-b | Repetitive uniform context is the loop signal (S12) | **absent (bounded)** | No repeated-call detection; the only guard is the 6-round cap, which ends the turn with no answer (COD-agent-runtime-1). With the cap that small, a dedicated detector would change little on its own. | No separate raw. |

## Where Vysted is ahead of the research baseline

- **Ground-truth read-back for side effects** (#15 verification half). The ack-ledger rewrite of
  host-action results (`agent_runtime.py:1065-1145`) is exactly S4's "gain ground truth from the
  environment at each step", applied to UI side effects — a pattern none of the cited sources ship
  for their own tool calls.
- **Claims ledger as a structured field** (S11's "grounding is a structured field, not prose"):
  prior stated values ride as `{symbol, metric, value, statedAt}` and re-inject into every
  research-space turn (`agent_runtime.py:344-373`, recorded deterministically at
  `src/lib/brief-claims.ts:105`). Limited to research spaces and to brief publishes, but the
  shape is right.
- **Invariants live in the re-injected system block** (#2), including the anti-staleness date
  anchor.

## Gaps filed (raw)

| raw_id | severity | practice(s) | one line |
|---|---|---|---|
| WLD-harness-context-1 | high | 1, 6, 10 | Local lane: ~11.5k of a 16k window is fixed overhead; tool results are uncapped, never cleared and never counted |
| WLD-harness-context-2 | medium | 3, 5, 7, S-a | Conversation memory is a silent 10-message text window: no compaction, tool evidence and failures erased between turns |
| WLD-harness-context-3 | high | 12, 3 | Durable memory is write-only: `write_note` notes are never read back; research-space "memory" is the user's last 3 questions |
| WLD-harness-context-4 | high | 17 | Web/news tool output enters the main loop unfenced while that loop can auto-apply portfolio deletes/edits under AUTO |
| WLD-harness-context-5 | medium | 8 | No prompt caching on Anthropic; per-turn terminal preamble folded into the system block |
| WLD-harness-context-6 | medium | 20 | `openrouter/auto` is a curated pick but the served model is never read or shown |

Cross-referenced, not re-filed: COD-agent-runtime-1 (#15/#20), COD-runs-durable-delegate-1/-2/-3/
-6/-9/-10/-11/-12 (#18/#19), COD-error-layer-2-3 + COD-llm-adapters-2-7 (#20 truncation),
COD-llm-adapters-2-6 + COD-research-extraction-synthesis-2 + INT-spec-135-143 (#19 metering),
COD-workspace-layout-2 (#12 research spaces unsaveable).

## Live evidence

- **Measured (in-process, no LLM):** copilot = 50 tool schemas, 35,227 chars (~8.8k tokens) +
  system prompt 10,964 chars (~2.7k tokens), against `num_ctx = 16384`.
- **Measured (isolated stack `:52152`, GET):** `/disclosures/announcements?symbol=RELIANCE` =
  21,558 bytes (~5.4k tokens) for one tool payload.
- **Local-lane drive (free, `vy.py --provider ollama --model llama3.1:8b`, tag
  `wld-harness-context`):** "For RELIANCE: fetch the latest corporate announcements, the
  shareholding pattern, and the fundamentals…" → one real `corporate_announcements` call, then the
  model leaked the other two calls as text and wrote "The shareholding pattern for RELIANCE is not
  available" without calling the tool. Final-round usage `input_tokens=4143` — Ollama's
  `prompt_eval_count` counts only non-cached tokens, so the usage the harness receives cannot show
  how full the window is (supports -1: the overflow signal is invisible even in telemetry).
  Evidence: `census/world/harness-context-evidence/local-lane-drive1.{jsonl,log}`. (The tool-call
  leak itself belongs to the harness-tools compare, not this topic.)
- **NOT TESTED (cost):** Anthropic cache-miss billing (-5) and `openrouter/auto` substitution
  (-6) need paid keys (Anthropic lane is unfunded for this run; openrouter/auto is not a `:free`
  slug). A single 4-round Anthropic Sonnet turn would cost ~$0.20 to demonstrate; one
  openrouter/auto answer ~$0.01-0.05. Both findings rest on code evidence.
- **NOT TESTED (needs a hostile page):** -4's injection path is mechanism-verified in code only.
