# APOSD critique — llm-adapters

Worker model: `claude-opus-5-5[1m]`. This is the **verify-and-finish** pass (PROMPT_code_s2.md). The
critique stage for this subsystem was never finished: raw findings
(`../raw/code-llm-adapters.json`, 13, prefix `COD-llm-adapters-`) and their refute verdicts
(`../refute/code-llm-adapters.json`, 13) were already on disk. Sections 1-6 below are written
**from those 13 findings as the refute stage corrected them**. The one refuted finding is not
presented as live, and every downgrade is reflected. Section 7 covers the fresh hunt: 7 new
findings in `../raw/code-llm-adapters-2.json` (prefix `COD-llm-adapters-2-`). The refute stage has
not reviewed them yet, and they are labelled as such wherever they appear.

Skill `aposd-critique` was loaded and followed (two personas, 18 principles, specificity gate).
Assessment independence: **degraded (sequential)**. This worker has no sub-agent tool, so the
Strategic Thinker pass was finished before the Tactical Tornado pass started. Snapshot
persistence to `.aposd/critique/` was skipped because it would write an unrequested file into
the repo. Scope: all 20 owning files in CODE_PARTITION (`services/llm/*` x10, `model_registry.py`
+ JSON, `routers/llm.py`, `models/llm.py`, `types/ai.ts`, the 4 frontend stores,
`lib/model-options.ts`). Callers were read where a promise depends on them: `agent_runtime.py`
native-search gate, tool loop and ack read-back, `action_ledger.py`, `routers/agents.py` ack
route, `host-actions.ts` `ackHostAction`, `KeyEntryDialog.tsx`, `streaming.ts` event decode,
`budget_guard.py`, `config.get_effective_research_tier`. I also read the installed SDK sources
for anthropic 0.100.0, ollama and google-genai.

Refute outcome of the original 13 (carried into this document):

- 3 admitted as stated: `-6`, `-8`, `-12`.
- 9 admitted with a correction: `-1` high→medium, `-2` high→low, `-3` high→low, `-4`
  high→medium, `-5` medium→low, `-9` medium→low, `-10` medium→low, `-11` medium→low. `-7`
  stayed medium but its scope was widened.
- **1 refuted: `-13`.**

Final severities: **0 high, 5 medium (`-1`, `-4`, `-6`, `-7`, `-8`), 7 low**.

## 1. Tactical Tornado verdict: MEDIUM risk (original 13), HIGH once the -2 findings are counted

The package has one strong seam: `LLMProvider` (`base.py:77-130`) with `stream_chat` /
`validate_key` / `list_models` and a discriminated event union. The adapters behind it grew
unevenly. `OpenAIProvider` received all the strategic investment: argument validation, a
repair round, a content-leak rescue, header-aware retry, and the gpt-5 reasoning-effort repair
(`openai.py:80-86,447-654`). Its four siblings stayed at first-draft level. The most damning
pattern is the **"NEVER a silent coerce to {}" invariant**. `openai.py:84-86` states it as an
absolute. The same package breaks it in `groq.py:47-48` and `ollama.py:108-109`, and
`gemini.py:161` never checks at all (`COD-llm-adapters-1`, medium after refute). The rule
belongs to the whole layer, but only one adapter enforces it.

Red flags confirmed by refute:

- Information leakage x3: base URLs held by a prose "must match" comment (`-6`), the registry
  hand-copied into two TS tables (`-7`), and option filtering done two different ways (`-4`).
- Consistency breaks x4: tool-argument integrity (`-1`), `/keys/validate` bypassing humanize
  (`-9`), two transports for the key (`-10`), and `except X: raise` clauses that do nothing
  (`-12`).
- A parameter that lies (`-5`, `get_provider(base_url=)` is ignored for gemini and groq).
- A swallowed exception (`-2`).
- A network call with no timeout plus repairs with no cap (`-8`).
- A magic id, `leaked-0` (`-11`).

The fresh hunt found the pattern goes deeper than the original critic saw. The capability
tables that drive behaviour are hand-asserted truths that three adapters contradict
(`-2-2`, `-2-3`). The Anthropic adapter loses every tool argument, and a test fixture shaped
unlike the real API hides it (`-2-1`).

## 2. Design principles score: 2 pass / 13 at-risk / 3 violate (2/18)

| #   | Principle                     | Grade   | Evidence (file:line: pattern)                                                                                                                                                                                                                                                                                           | Consequence                                                                                                                                                                                                                                                          |
| --- | ----------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Strategic over tactical       | at-risk | `openai.py:80-86,495-654` has ~200 lines of WS8 argument validation and repair, while `groq.py:36-49`, `ollama.py:96-111` and `gemini.py:161` coerce or pass through (`-1`)                                                                                                                                             | Hardening happened per incident, in the adapter where the incident showed up. Each new adapter starts at the tactical baseline.                                                                                                                                      |
| 2   | Deep modules                  | pass    | `base.py:85-130`: one `stream_chat(messages, model, api_key, **kwargs)` hides eight SDKs, three wire shapes and seven event taxonomies behind `LLMStreamEvent` (`base.py:33-41`). `__init__.get_provider` (`:72-100`) hides the OpenAI-shaped dispatch.                                                                    | Callers (`agent_runtime`, `oneshot`, router) never touch an SDK. This is the subsystem's real asset.                                                                                                                                                                  |
| 3   | Information hiding            | at-risk | The adapter-kwarg allowlist `_ADAPTER_OPTION_KEYS` lives in `agent_runtime.py:97-107`, not in `services/llm`. `routers/llm.py:126-130` has to know the same thing another way (`-4`, medium).                                                                                                                              | Which kwargs an adapter accepts is adapter knowledge held by its callers. Every new caller must rediscover it.                                                                                                                                                        |
| 4   | Information leakage           | violate | `__init__.py:36-47`: three base URLs guarded by a "must match the registry" comment in a module that already imports the registry (`-6`, medium). `llm-providers.ts:40-113` + `model-selection.ts:26-61` are copies of `model_registry.json`, and the drift test compares only the two copies (`-7`, medium, scope widened: `resolveModel` uses the static default even when the sidecar is up). | A JSON-only model or URL edit ships split-brain: the served catalog and runtime dispatch disagree, and every user without an override gets a stale default. See also `-2-2`/`-2-3` (pending refute): the native-search capability table is a third hand-asserted truth that has already drifted. |
| 5   | General-purpose modules       | at-risk | `get_provider(provider_id, base_url)` honours `base_url` on 6 of 8 branches (`__init__.py:88-91`, `-5`, low). `oneshot.complete` has no `base_url` at all (`oneshot.py:46-53`, `-3`, low).                                                                                                                                | Not reachable from any shipped UI today (refute), but the general interface is narrower than its signature claims. The first proxy or self-hosted feature will hit it.                                                                                              |
| 6   | Different layer, different abstraction | at-risk | The tool-argument invariant (parse, schema-validate, sentinel) is implemented in one adapter (`openai.py:153-220`) instead of the layer every adapter feeds (`-1`).                                                                                                                                                 | The runtime cannot assume a valid tool input from the adapter layer as a whole.                                                                                                                                                                                      |
| 7   | Pull complexity downward      | at-risk | `oneshot.complete` offers `timeout` specifically for the ~600 s SDK default (`oneshot.py:61-67`), but the in-adapter repair call omits it (`openai.py:626-631`, `-8`, medium). `native_search.py:195-197` defines its own 90 s constant for the same shape.                                                                 | Each caller of the one-shot seam must remember the hazard. The one caller inside the hot stream loop forgot.                                                                                                                                                          |
| 8   | Better together or apart      | at-risk | `oneshot.complete._drive` (`oneshot.py:77-92`) and `native_search_oneshot._drive` (`native_search.py:240-255`) are the same "drive stream_chat, join deltas, stop on done/error" loop with separate timeout and error policies.                                                                                           | Two copies of the "one completion" abstraction, each with its own gaps (`-3` affects both).                                                                                                                                                                         |
| 9   | Define errors out of existence | violate | The denylist at `routers/llm.py:126-130` is the design that already shipped a TypeError once (`-4`, medium). `ollama.py:170-171` uses `except Exception: stream = None` with no log (`-2`, low: only construction errors reach it, and the retry-without-tools fallback is effectively dead). `routers/llm.py:107` returns `detail=f"transport error: {exc}"` (`-9`, low). | Error classes are handled after the fact, one at a time, instead of being made impossible (an allowlist) or surfaced consistently (humanize).                                                                                                                         |
| 10  | Design it twice               | at-risk | `routers/llm.py:60-64` says the key goes "in a header, never the body/query/log" 30 lines above two routes that put it in the body (`models/llm.py:256,268`, `-10`, low).                                                                                                                                                | The key transport was decided twice, differently, in one file. The next route has no rule to follow.                                                                                                                                                                  |
| 11  | Comments describe the non-obvious | at-risk | `openai.py:746-750`: the "Accumulate DeepSeek-reasoner reasoning_content" comment sits above an unrelated boolean. **`-13` was REFUTED**: the behaviour it describes exists, one layer up (`agent_runtime.py:1428-1442,1528-1529`), so the comment is misplaced, not false. `anthropic.py:171-172` is the only one of four `except X: raise` clauses whose comment explains itself (`-12`, low). | Minor. Comments are mostly accurate and dense. The misplaced one costs a reader a detour, not a wrong belief.                                                                                                                                                         |
| 12  | Comments first                | pass    | Module docstrings state the contract before the code: `base.py:1-12`, `native_search.py:1-23`, `openai.py:53-86` (every retry and leak constant carries a *why*), `ollama.py:35-47` (num_ctx derivation with measured VRAM).                                                                                              | Design intent can be recovered without git archaeology.                                                                                                                                                                                                              |
| 13  | Choosing names                | at-risk | `leaked-0` stands in for identity (`openai.py:323`, `-11`, low). `OpenAIProvider`'s docstring calls `provider_id` "informational" (`openai.py:415-417`), yet it drives the xAI/OpenRouter/OpenAI request branches (`:427,690-722`) and the leak gate (`:821`).                                                              | A reader trusting the docstring misses that the one adapter is really four behaviours.                                                                                                                                                                              |
| 14  | Modifying existing code       | at-risk | The `research_depth` TypeError (commit 7ad0b79) was fixed by adding names to a denylist (`routers/llm.py:122-130`) rather than removing the class of bug (`-4`).                                                                                                                                                      | The fix made the symptom go away and left the trap in place.                                                                                                                                                                                                         |
| 15  | Consistency                   | violate | Tool-argument integrity: 1 of 4 adapters (`-1`). Error humanization: 6 sites, 1 bypass (`-9`). Key transport: header vs body (`-10`). Dead `except X: raise` in 4 adapters (`-12`, low).                                                                                                                                  | Five near-identical adapters differ in the details that matter. Learning one does not predict the others.                                                                                                                                                             |
| 16  | Code should be obvious        | at-risk | `get_provider` documents `base_url` as "takes precedence over the dispatch default" and then drops it for gemini/groq (`__init__.py:80-81,88-91`, `-5`). Ollama silently retries without tools (`ollama.py:156-171`, `-2`).                                                                                               | Behaviour contradicts the local reading. Refute found both latent rather than live, hence low.                                                                                                                                                                       |
| 17  | Design for the future         | at-risk | The repair and native-search one-shots rebuild adapters with no `base_url` (`openai.py:626`, `native_search.py:241`, `-3`, low). `get_provider` drops `base_url` (`-5`, low).                                                                                                                                             | These are the seams a proxy or self-hosted-endpoint feature will depend on. Latent today, per refute.                                                                                                                                                                |
| 18  | Performance as design         | at-risk | Serial, uncapped repair rounds inside the open SSE stream, with no timeout, and their tokens stay invisible to `LLMDoneEvent.usage` and so to the BudgetGuard (`openai.py:526-589,795-800`, `-8`, medium).                                                                                                                | A rare trigger (a schema miss), but when it fires the stream stalls silently and the spend is unmetered.                                                                                                                                                             |

**Summary: 2 pass, 13 at-risk, 3 violate (2/18 pass).**

## 3. Overall impression

The abstraction is right: one neutral event stream over eight vendors, and a JSON registry as
the declared source of truth. The execution of both is uneven. Everything the refute confirmed
is one of two kinds. Either a truth is written down twice (URLs, registry tables, option keys,
key transport), or an invariant is enforced in one adapter instead of the layer (tool
arguments, humanized errors). Refute took most of the teeth out of the original 13: nothing
confirmed is high, and several are latent traps with no user-reachable path yet. The fresh hunt
(section 7) shows why that is not reassuring. The same two root causes produce **live**
high-severity defects the first critic missed. The biggest single opportunity is to make the
adapter layer own its invariants: a shared tool-call normalizer (arguments, ids), a per-model
capability truth used by both the runtime gate and the adapter, and an allowlist of adapter
kwargs.

## 4. What's working

- **The event union is a deep interface.** `LLMStreamEvent` (`base.py:33-41`, mirrored in
  `types/ai.ts:151-194` and decoded in one place, `streaming.ts:275-357`) lets the runtime, the
  one-shot helpers and the SSE router ignore vendor shapes completely. New event kinds
  (`research_step`, `agent_plan`) were added without touching an adapter.
- **The registry is loaded fail-loud.** `model_registry._load` (`model_registry.py:44-68`)
  raises on a missing file, invalid JSON or a malformed row, and names the PyInstaller
  `--add-data` cause. That avoids the silent-`agents/` failure class this repo already paid for
  once.
- **The OpenAI retry path is well-designed.** `max_retries=0` makes the adapter the single
  retry authority (`openai.py:432-445`). It honours both `Retry-After` forms and never retries a
  deterministic 4xx (`:390-409`). It is the template the siblings should follow.

## 5. Priority issues (existing findings, corrected severities)

- **[P1] Tool-argument integrity is an adapter-local invariant (`COD-llm-adapters-1`, medium).**
  Principle: different layer, different abstraction / consistency. Symptom: unknown unknowns.
  `groq.py:47-48` and `ollama.py:108-109` return `{}` on bad JSON, and `gemini.py:161` does not
  validate, while `openai.py:84-86` forbids exactly that. Refute: symbol-keyed tools
  self-validate (`price_data.py:35-37`), so the model does get an error. Optional-argument tools
  still run on defaults. Fix: move `_drain_tool_buffers` / `_validate_tool_args` / the sentinel
  into `base.py` (or `tool_args.py`) and call it from all adapters. The repair round can stay
  OpenAI-only.
- **[P1] Denylist vs allowlist for adapter kwargs (`COD-llm-adapters-4`, medium).**
  Principle: define errors out of existence. Symptom: change amplification. `routers/llm.py:126-130`
  strips four names, while `agent_runtime.py:97-107` allowlists six, and `wireOptions` forwards
  everything (`streaming.ts:124-130`). No shipped caller sends options on `/llm/chat` today
  (refute), so this is a trap waiting for one. Fix: promote `_ADAPTER_OPTION_KEYS` into
  `services/llm/__init__.py` and filter against it in both places.
- **[P1] Registry copies with a drift test on the wrong pair (`COD-llm-adapters-7`, medium).**
  Principle: information leakage. Symptom: change amplification. The TS tables are not just an
  offline fallback: `resolveModel` returns the static default whenever there is no override
  (`model-selection.ts:119`), and untrusted restores are pruned against the static list (`:76`).
  Fix: one vitest that imports `sidecar/config/model_registry.json` and asserts both TS tables
  equal it.
- **[P2] Repair rounds with no timeout, no cap and no metering (`COD-llm-adapters-8`, medium).**
  Principle: performance as design / pull complexity down. `openai.py:626-631` passes no
  timeout, `:526-589` repairs every failing call serially, and `:795-800` usage excludes repair
  tokens. Fix: pass a timeout, cap at 1-2 repairs per round and fall straight to the sentinel
  past the cap, and add repair usage to the round's usage.
- **[P2] Base URLs held by prose (`COD-llm-adapters-6`, medium).** Principle: information
  leakage. `__init__.py:36-47`. Fix: add `model_registry.default_base_url_for(provider)` and
  derive the three constants from it.

Low, confirmed, not priority: `-2` (swallowed Ollama construction error), `-3` (one-shots drop
`base_url`), `-5` (`get_provider` drops `base_url` for gemini/groq), `-9` (raw exception text in
the key dialog), `-10` (two key transports), `-11` (`leaked-0`, whose missing consumer
`-2-5` now supplies), `-12` (dead `except X: raise`). **Refuted: `-13`**. The reasoning echo is
implemented in the runtime; only the comment placement is off.

## 6. Persona walkthrough

**Tactical Tornado.** Given the next incident, "Groq 400s on a truncated tool call" say, the
Tornado copies another 60 lines of `_drain_tool_buffers` into `groq.py`, just as `openai.py`
grew its own. On the next "unknown option killed the stream" report, they add a fifth name to
`routers/llm.py:129`. A new provider gets a new `elif self._provider_id == ...` branch in
`openai.py:690-723` and a new row in `PROVIDER_LEVEL_NATIVE_SEARCH` (`native_search.py:62`),
asserted and never tested against what the adapter actually sends. `-2-2` shows that already
happened for groq and xai.

**Strategic Thinker.** Keep `LLMProvider` as the one deep seam and give it the two things every
adapter currently re-derives. First, a `normalize_tool_calls(raw_calls) -> list[LLMToolUseEvent]`
in `base.py` that owns JSON parsing, schema validation, the sentinel, and a guaranteed-unique
`tool_call_id` (fixes `-1`, `-11`, `-2-5`). Second, a per-adapter `capabilities(model) ->
{native_search: bool, accepted_kwargs: frozenset}` that the runtime gate reads *instead of* the
hand table in `native_search.py`. The adapter that injects the search affordance is then the
only thing that can claim to have one (fixes `-4`, `-2-2`, `-2-3`). I weighed an alternative:
centralise capabilities in `model_registry.json` per model. It was rejected because the
registry cannot see what the adapter code actually sends, which is exactly the drift that
bit here.

## 7. Verify-and-finish fresh hunt: 7 new findings (PENDING REFUTE)

File: `../raw/code-llm-adapters-2.json`. Each item was proved with a scratch script that runs
the real adapter code against the installed SDKs (no sidecar started), with a live probe, or
with a documentation quote. The refute stage has not reviewed them yet.

| raw_id                  | Sev    | Finding                                                                                                                                                                                                                                                                                                                                                  | Proof                                                                                                                                                                                                                                                            |
| ----------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| COD-llm-adapters-2-1    | high   | **Every Anthropic tool call arrives with `input={}`.** `_translate_event` emits `tool_use` on `content_block_start` (`anthropic.py:225-232`), where the API always sends `input:{}`. The argument JSON streams later as `input_json_delta`, which the translator drops. The unit test fakes a start block that already has arguments (`test_llm_anthropic.py:166-172`). | Real SDK + `httpx.MockTransport` replaying the documented SSE: `tool_use get_quote {}`. Docs: platform.claude.com streaming.md:935 shows `"input":{}` on start.                                                                                                     |
| COD-llm-adapters-2-2    | high   | **No web search at all on Groq, and probably none on xAI.** `PROVIDER_LEVEL_NATIVE_SEARCH` includes groq and xai (`native_search.py:62`), so the runtime removes the local `web_search` tool (`agent_runtime.py:1334-1340`, default tier_a). The Groq adapter pops the flag and injects nothing on non-Compound models, which are the only Groq models in the registry (`groq.py:109-117`). xAI sends the retired Live Search `search_parameters` (`openai.py:691-695`). | Captured Groq request: `['messages','model','stream','tools']`, tools `['price_data','news']`. xAI's old live-search URL now documents only the Responses-API `web_search` tool.                                                                                  |
| COD-llm-adapters-2-3    | high   | **Every Gemini agent round combines `function_declarations` with `google_search`** (`gemini.py:118-129`). Google documents that combination as "supported for Gemini 3 models only", and the registry default is `gemini-2.5-pro`. The replay also drops function-call signatures (`gemini.py:74-82`).                                                    | Captured config: `[['function_declarations'], ['google_search']]`. Doc quote from ai.google.dev tool-combination.md.txt:2. **Needs a live check** with a Gemini key to confirm reject vs silent drop.                                                             |
| COD-llm-adapters-2-4    | medium | **Key validation is wrong for 3 of 8 providers.** OpenRouter's `/models` is public, so `validate_key('not-a-real-key')` returns **True** and the dialog saves the bad key. Gemini (400 `API_KEY_INVALID`) and xAI (400 "Incorrect API key") surface a bad key as `transport error: ...`, and the stream-side humanize auth branch never fires for either.        | Live: OpenRouter adapter returns True. Gemini adapter raises `ClientError 400`. `curl api.x.ai/v1/models` with a fake key returns 400.                                                                                                                               |
| COD-llm-adapters-2-5    | medium | **Tool-call ids are not unique.** Ollama emits `''` because its SDK `ToolCall` has no id (`_types.py:333-352`). Gemini emits `name_index`, reset every round (`gemini.py:142,159`). The process-global ack ledger (`action_ledger.py:25-31`, 600 s TTL) is keyed on the id. Result: an Ollama host action can never be acked (`host-actions.ts:1457`, `agents.py:47`), and a Gemini host action can read a stale "applied" left by an earlier one. | Code path: `agent_runtime.py:1065-1080,1618-1625`. Ollama is the store's `defaultProviderId` (`llm-providers.ts:135`).                                                                                                                                             |
| COD-llm-adapters-2-6    | medium | **Gemini thinking tokens are not metered.** The adapter reports only `candidates_token_count` (`gemini.py:167-173`), not `thoughts_token_count` or `tool_use_prompt_token_count`, so the BudgetGuard under-counts Gemini 2.5 spend.                                                                                                                       | SDK `types.py:7826` defines the total as the sum of four parts. Google's doc says thinking tokens are billed as output.                                                                                                                                             |
| COD-llm-adapters-2-7    | medium | **Anthropic output is capped at 4096 tokens and truncation is silent.** `DEFAULT_MAX_TOKENS=4096` is the only value ever sent (`anthropic.py:37,110`). No layer acts on a `max_tokens`/`length` finish: oneshot ignores it (`oneshot.py:84-92`), the runtime checks only `content_filter` (`agent_runtime.py:1485`), and the UI never reads `finishReason`. A truncated synthesis renders as complete. | grep: no caller sets `max_tokens`. Decode at `streaming.ts:327-342`.                                                                                                                                                                                              |

If refute confirms them, `-2-1` to `-2-3` are the headline of this subsystem. Two of the
product's first-class providers (Anthropic; Gemini on the default model) cannot run the agent
correctly, and two more (Groq, xAI) have no working search. The unit suite does not see any of
it: each adapter test fakes the SDK in the shape the adapter expects, not the shape the vendor
sends.

## 8. Minor observations (not raised as findings)

- `_resolve_tool_events` appends validated calls first and repaired or failed calls after
  (`openai.py:526-589`), so the model's emitted call order is not preserved. This is harmless
  for id-paired providers, but a sequence of host actions can apply out of order.
- `openrouter_catalog._derive_web_search` calls `float(pricing["web_search"])` outside the
  function's own try (`openrouter_catalog.py:72`). A non-numeric price aborts the whole live
  catalog, and the router falls back to the registry list.
- `OpenAIProvider.list_models` keeps responses-only ids (`*-codex`, `o*-pro`,
  `computer-use-*`) that 404 on chat-completions. `is_chat_model` filters by modality only
  (`base.py:48-74`).
- `model_registry.json` still lists `grok-3` / `grok-4` as xAI models. xAI retired `grok-3` and
  `grok-4-0709` on 2026-05-15 and redirects them to `grok-4.3` at different pricing
  (https://docs.x.ai/developers/migration/may-15-retirement), so the `grok` price row
  ($6/1M) no longer matches.
- `model-catalog.ts:62-84`: a forced refresh can race an in-flight fetch, and the last response
  to arrive wins, which may be the keyless one.

## 9. Questions to consider

- What if `tool_call_id` uniqueness and argument validity were guaranteed by `LLMToolUseEvent`
  itself (a default id factory plus a validated constructor), so no adapter could opt out?
- Should "does this adapter inject native search for this model?" be answered by the adapter,
  the only code that knows, rather than by a table in `native_search.py`?
- Why do the adapter unit tests build fake SDK events by hand instead of replaying recorded
  vendor SSE through the real SDK with `httpx.MockTransport`? A replay would have caught `-2-1`.

## 10. Run notes

- Target: `llm-adapters` (20 files, 4426 LOC per CODE_PARTITION). Slug and persistence were
  skipped (no repo writes beyond the two output files).
- Ignore list: none present.
- Assessment independence: degraded (sequential; no sub-agent tool).
- Proof scripts, in the session scratchpad: `anth_proof.py` (Anthropic tool input) and
  `search_proof.py` (groq/gemini request capture). Live probes used only fake keys (OpenRouter
  `/models` and `/key`, Gemini `models.list`, xAI/DeepSeek/Groq/OpenAI/Anthropic `/models`). No
  key was read from the keystore, no sidecar was started, and the operator's stack was not
  touched.
- Original 13 findings are untouched. New findings are only in `raw/code-llm-adapters-2.json`
  (7), for the `refute/code-llm-adapters-2.json` stage.
