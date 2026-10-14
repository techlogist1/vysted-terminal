# R15 Census — World sweep: agent-harness CONTEXT, MEMORY and RECOVERY (state of the art, Sept 2026)

Worker model id: `claude-opus-5[1m]`
Date of sweep: 2026-09-19
Topic: `harness-context` — context engineering (compaction, just-in-time retrieval, tool-result
clearing, structured note-taking / memory files, sub-agent isolation), memory (episodic /
semantic, user-scoped stores, claims ledgers), recovery (retries, checkpoints, resumable runs,
budget guards, loop detection, fallback models).
Read-only sweep. No repo files changed except this one.

## Evidence conventions

- `[FETCHED]` = primary doc fetched this sweep and quoted verbatim. Everything below is
  `[FETCHED]` unless marked otherwise.
- Honest disclosure: **`WebSearch` was unavailable for this sweep** (the session's 200-call
  search budget was already spent by earlier R15 workers). Every source below was reached by
  direct `WebFetch` on a known primary URL. Consequence: this sweep is strong on
  vendor-primary docs and well-known practitioner posts, and weaker on discovering *new*
  Sept-2026 write-ups that only a search would have surfaced. Two things were found anyway
  because primary docs linked them: Anthropic's `effective-harnesses-for-long-running-agents`
  and the `compact_20260112` server-side compaction beta.
- 21 distinct sources. Every claim carries URL + quote.

### Source list

| # | Source | URL |
|---|---|---|
| S1 | Anthropic — Effective context engineering for AI agents | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| S2 | Anthropic — How we built our multi-agent research system | https://www.anthropic.com/engineering/multi-agent-research-system |
| S3 | Anthropic — Effective harnesses for long-running agents | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| S4 | Anthropic — Building effective agents | https://www.anthropic.com/engineering/building-effective-agents |
| S5 | Claude blog — Context management (memory tool + context editing) | https://claude.com/blog/context-management |
| S6 | Claude docs — Context editing (`clear_tool_uses_20250919`) | https://platform.claude.com/docs/en/build-with-claude/context-editing |
| S7 | Claude docs — Compaction (`compact_20260112`) | https://platform.claude.com/docs/en/build-with-claude/compaction |
| S8 | Claude docs — Memory tool (`memory_20250818`) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool |
| S9 | Claude docs — Agent SDK: subagents | https://code.claude.com/docs/en/agent-sdk/subagents |
| S10 | Claude docs — Agent SDK: how the agent loop works | https://code.claude.com/docs/en/agent-sdk/agent-loop |
| S11 | Claude docs — Citations | https://platform.claude.com/docs/en/build-with-claude/citations |
| S12 | Manus — Context engineering for AI agents: lessons from building Manus | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus |
| S13 | Cognition — Don't build multi-agents | https://cognition.com/blog/dont-build-multi-agents |
| S14 | LangChain — Context engineering for agents | https://www.langchain.com/blog/context-engineering-for-agents |
| S15 | 12-Factor Agents (humanlayer) | https://github.com/humanlayer/12-factor-agents |
| S16 | 12-Factor Agents — Factor 3: own your context window | https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md |
| S17 | LangGraph — Persistence / checkpointers | https://docs.langchain.com/oss/python/langgraph/persistence |
| S18 | OpenAI Agents SDK — Running agents | https://openai.github.io/openai-agents-python/running_agents/ |
| S19 | LangMem — Conceptual guide (memory taxonomy) | https://langchain-ai.github.io/langmem/concepts/conceptual_guide/ |
| S20 | OpenRouter — Provider routing / Auto router | https://openrouter.ai/docs/features/provider-routing , https://openrouter.ai/docs/features/model-routing |
| S21 | Papers — MemGPT (arXiv 2310.08560), Generative Agents (arXiv 2304.03442), Chroma "Context Rot" (https://www.trychroma.com/research/context-rot) |

---

## 1. The frame: context is a budget, not a container

The single idea every 2025–2026 primary source now agrees on is that a bigger window does not
mean more usable context.

- S1: *"Context, therefore, must be treated as a finite resource with diminishing marginal
  returns."* and *"LLMs have an 'attention budget' that they draw on when parsing large volumes
  of context."*
- S1 names the phenomenon: *"studies on needle-in-a-haystack style benchmarking have uncovered
  the concept of context rot"*.
- S21 (Chroma) is the empirical backing: *"model performance varies significantly as input
  length changes, even on simple tasks"*; *"models do not use their context uniformly; instead,
  their performance grows increasingly unreliable as input length grows"*. Their study covered
  18 models. Three findings that matter to a finance harness:
  - **Semantic distance hurts.** *"performance degrades more quickly in input length with lower
    similarity needle-question pairs"* — i.e. an answer phrased unlike the question (a number
    buried in a filing table vs. a plain-English question) is the first thing lost.
  - **Distractors are not benign.** *"Adding four distractors compounds this degradation
    further"*; Claude models showed *"the lowest hallucination rates"*, GPT *"the highest rates
    of hallucination"* under distractors. Stuffing five near-miss quote candidates into context
    measurably raises the odds of the wrong one being cited.
  - **Coherent context can be worse.** *"models perform worse when the haystack preserves a
    logical flow of ideas. Shuffling the haystack and removing local coherence consistently
    improves performance."*
- S14 gives the failure taxonomy practitioners use: *"Context Poisoning: When a hallucination
  makes it into the context"*, *"Context Distraction: When the context overwhelms the
  training"* (plus confusion and clash).

**Consequence for a harness:** every token admitted to the window must earn its place, and the
harness — not the model — is responsible for the admission policy. S15 states this as Factor 3,
*"Own your context window"*, with S16: *"Everything is context engineering. LLMs are stateless
functions that turn inputs into outputs."* and *"You don't necessarily need to use standard
message-based formats for conveying context to an LLM."*

---

## 2. Compaction — summarize the transcript, keep the state

Compaction is now a *first-class, configurable* mechanism rather than a panic button.

**Definition (S1):** *"Compaction is the practice of taking a conversation nearing the context
window limit, summarizing its contents"*, and the hard part is stated plainly: *"The art of
compaction lies in the selection of what to keep versus what to discard."*

**Server-side compaction (S7, `compact_20260112`)** — the Sept-2026 state of the art:

- Default trigger **150,000 input tokens**, configurable, *"Must be at least 50,000 tokens"*.
- Mechanics: detect → generate summary → emit a `compaction` block → continue. *"On subsequent
  requests, the API automatically drops all content blocks prior to the `compaction` block."*
- The default summarization prompt is itself instructive about what a good compaction preserves:
  *"Write down anything that would be helpful, including the state, next steps, learnings etc."*
- `instructions` **completely replaces** the default prompt — a documented footgun if you pass
  a narrow instruction and lose state you needed.
- `pause_after_compaction: true` stops the response after the summary so the harness can inject
  its own content (re-seed invariants) before continuing. This is the hook for "re-assert the
  rules the summary just dropped".
- Billing trap: *"Top-level `input_tokens` and `output_tokens` do **not** include compaction
  iteration usage. Sum across all `usage.iterations` entries to calculate total tokens consumed
  and billed."* A budget guard that reads only top-level usage **under-counts a compacting run**.
- Model trap: on Fable 5.1 / Mythos 5.1, *"Thinking blocks from before a `compaction` block
  aren't carried forward—the summary is all the model has"*.
- Compaction can fire more than once per request: *"Compaction might occur multiple times within
  a single request"*.

**Harness-side compaction (S10, S14):** Claude Code auto-compacts near the limit and emits a
`compact_boundary` system message. Two rules come out of it:

- S10: *"Compaction replaces older messages with a summary, so specific instructions from early
  in the conversation may not be preserved. Persistent rules belong in CLAUDE.md ... because
  CLAUDE.md content is re-injected on every request."* **Invariants must live somewhere that is
  re-injected, never only in turn 1.**
- S10: a `PreCompact` hook exists *"to archive the full transcript before summarizing"* — i.e.
  compaction is lossy and the harness should keep the pre-compaction transcript on disk.
- S14 records the threshold practitioners see: *"Claude Code runs 'auto-compact' after you
  exceed 95% of the context window"*.

**Compression must be restorable (S12):** *"compression strategies are always designed to be
restorable"* — Manus drops a web page's content but keeps its URL, drops a file's body but keeps
its path. Anything that can be re-fetched from a stable identifier can be safely dropped.

**Dedicated compressor (S13):** Cognition goes further: *"We introduce a new LLM model whose key
purpose is to compress a history of actions & conversation into key details, events, and
decisions."* Compaction quality is worth a separate, cheaper, purpose-prompted call.

---

## 3. Tool-result clearing — the cheapest win, with a cache caveat

Distinct from compaction: **surgically evict stale tool results** while leaving the reasoning
narrative intact.

S6, `clear_tool_uses_20250919`: *"Older tool results (like file contents or search results) are
no longer needed once Claude has processed them."* Mechanics and knobs:

| Knob | Default | Why it matters |
|---|---|---|
| `trigger` | 100,000 input tokens | When clearing starts (`input_tokens` or `tool_uses`) |
| `keep` | 3 tool uses | *"The API removes the oldest tool interactions first, preserving the most recent ones."* |
| `clear_at_least` | none | *"This helps determine if context clearing is worth breaking your prompt cache."* |
| `exclude_tools` | none | *"tool names whose tool uses and results should never be cleared"* |
| `clear_tool_inputs` | `false` | By default the **call** stays visible, only the **result** is cleared |

Two properties a harness must not get wrong:

1. *"The API replaces each cleared result with placeholder text indicating to Claude that it was
   removed."* The model is told it *had* a result and lost it — it can re-fetch rather than
   hallucinate. Silent deletion would not have this property.
2. *"Your client application maintains the full, unmodified conversation history. You do not need
   to sync your client state with the edited version."* Editing is server-side; the audit trail
   on the client stays complete.

Cache cost is explicit (S6): *"Tool result clearing: Invalidates cached prompt prefixes when
content is cleared ... You'll incur cache write costs each time content is cleared."*

**Measured payoff (S5):** *"combining the memory tool with context editing improved performance
by 39% over baseline. Context editing alone delivered a 29% improvement."* and *"context editing
enabled agents to complete workflows that would otherwise fail due to context exhaustion—while
reducing token consumption by 84%."*

---

## 4. Just-in-time retrieval — carry identifiers, not payloads

S1: *"Rather than pre-processing all relevant data up front, agents built with the 'just in time'
approach maintain lightweight identifiers ... and use these references to dynamically load data
into context at runtime."*

S2 shows the same move across an agent boundary: *"Subagents call tools to store their work in
external systems, then pass lightweight references back"*.

S8 states it as the design intent of the memory tool: *"Memory supports just-in-time context
retrieval. Rather than loading all relevant information up front, an agent records what it learns
in memory files and reads them back on demand."*

S14's taxonomy is the canonical four verbs: **Write** (save outside the window), **Select**
(pull in), **Compress** (retain only required tokens), **Isolate** (split across agents). It also
records that selection itself needs help at scale: applying RAG to tool descriptions *"improved
tool selection accuracy by 3-fold"*.

S10 confirms the same principle for schemas, not just data: MCP tool search *"defers MCP tool
schemas by default and loads them on demand. When tool search is off ... each MCP server adds
all its tool schemas to every request, so a few servers with many tools can consume significant
context before the agent does any work."*

---

## 5. Structured note-taking — the agent writes its own state to disk

S1: *"Structured note-taking, or agentic memory, is a technique where the agent regularly writes
notes persisted to memory outside of the context window."* — *"This strategy provides persistent
memory with minimal overhead."*

S12 is the most concrete version: *"treat the file system as the ultimate context in Manus:
unlimited in size, persistent by nature"*, and the recitation trick — *"when handling complex
tasks, it tends to create a todo.md file—and update it step-by-step"* — which exists to drag the
objective back into recent attention on a long run (a typical Manus task is *"around 50 tool
calls on average"*).

**The memory tool's own prompt (S8)** is the clearest statement of the contract the API itself
injects:

```
IMPORTANT: ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE.
...
ASSUME INTERRUPTION: Your context window might be reset at any moment, so you risk losing any
progress that is not recorded in your memory directory.
```

Mechanics worth copying even without the Anthropic tool: six commands (`view`, `create`,
`str_replace`, `insert`, `delete`, `rename`), a `/memories` prefix, *"The memory tool operates
client-side: Claude requests file operations, and your application executes them"*, and three
non-negotiable safeguards the docs put on the *implementer*:

- **Path traversal** — *"A malicious path such as `/memories/../../secrets.env` can reach files
  outside the `/memories` directory. Your implementation must validate every path in every
  command."*
- **Size caps** — *"Track memory file sizes and cap how large a file can grow."*
- **Expiry** — *"Periodically delete memory files that haven't been accessed in a long time."*
- Plus: *"Claude usually refuses to write sensitive information to memory files. For stronger
  guarantees, add validation that strips sensitive data before your handler writes the file."*

**The multi-session pattern (S8, S3)** is the production shape of this:

- S8: an *initializer session* creates *"a progress log ... a feature checklist ... and a
  reference to any startup or initialization script"*; each later session opens by reading them;
  each session updates the log before ending. Key principle: *"Mark a feature complete only after
  end-to-end verification confirms it works, not when the code is written."*
- S3 (the case study): *"The very first agent session uses a specialized prompt that asks the
  model to set up the initial environment: an `init.sh` script, a claude-progress.txt file"*,
  and the recovery discipline *"ask the model to commit its progress to git with descriptive
  commit messages and to write summaries of its progress in a progress file"*, *"This allowed the
  model to use git to revert bad code changes and recover working states of the code base"*.
- S3 is also blunt that compaction alone is not enough: *"compaction isn't sufficient. Out of the
  box, even a frontier coding model like Opus 4.5 running on the Claude Agent SDK in a loop
  across multiple context windows will fall short"*.

**Named failure modes from S3** (all of them are harness bugs, not model bugs):

| Failure | Quote | Harness countermeasure (from the same post) |
|---|---|---|
| One-shotting | *"the agent tended to try to do too much at once—essentially to attempt to one-shot the app"* | Work one feature at a time |
| False "done" | *"After some features had already been built, a later agent instance would look around, see that progress had been made, and declare the job done"* | Structured feature checklist with a `passes` field the agent only flips after testing |
| Premature completion | *"Claude marks features as done prematurely"* / *"Self-verify all features. Only mark features as 'passing' after careful testing"* | Verification gate before status change |
| Dirty handoff | *"Claude leaves the environment in a state with bugs or undocumented progress"* | *"Start the session by reading the progress notes file and git commit logs, and run a basic test on the development server to catch any undocumented bugs"* |

---

## 6. Sub-agent isolation — and the serious argument against it

**For (S1, S2, S9):**

- S1: *"Sub-agent architectures provide another way around context limitations ... specialized
  sub-agents can handle focused tasks with clean context windows"*, and *"Each subagent might
  explore extensively ... but returns only a condensed, distilled summary of its work"*.
- S2: *"Subagents facilitate compression by operating in parallel with their own context windows,
  exploring different aspects"*.
- S9 enumerates the four benefits precisely — **context isolation** (*"intermediate tool calls and
  results stay inside the subagent; only its final message returns to the parent"*),
  **parallelization**, **specialized instructions**, and **tool restrictions** (*"A `doc-reviewer`
  subagent might only have access to Read and Grep tools, ensuring it can analyze but never
  accidentally modify your documentation files"*).
- S9 is explicit that isolation is also an *ignorance* problem: *"The only content you pass from
  parent to subagent is the Agent tool's prompt string, so include any file paths, error messages,
  or decisions the subagent needs directly in that prompt."*
- S9 also records a **prompt-injection defense** at the subagent return boundary: Claude Code
  *"scans the final message for instruction-shaped patterns before the parent reads it"* —
  neutralizing control-tag imitation such as a `<system-reminder>` block and turn markers
  (`Human:` / `Assistant:`), while *"it never removes or rewords the subagent's text"*. A harness
  that splices untrusted tool output or worker output into a parent context needs this.

**Against (S13):** Cognition's position is that parallel subagents destroy shared assumptions:
*"The actions subagent 1 took and the actions subagent 2 took were based on conflicting
assumptions not prescribed upfront"*; the principle *"Actions carry implicit decisions, and
conflicting decisions carry bad results"*; the prescription *"Share context, and share full agent
traces, not just individual messages"* and *"The simplest way to follow the principles is to just
use a single-threaded linear agent"*. Their verdict: *"Running multiple agents in collaboration
only results in fragile systems. The decision-making ends up being too dispersed."*

**Reconciliation the sources support:** subagents are safe when the subtask is **read-only and
its result is a fact, not a decision** (search, scan, extract) — exactly S9's read-only
`["Read","Grep","Glob"]` shape. They are dangerous when two workers each decide something. S2's
own economics also caution against reflex delegation: *"agents typically use about 4× more tokens
than chat interactions, and multi-agent systems use about 15× more tokens"* — and *"upgrading to
Claude Sonnet 4 is a larger performance gain than doubling the token budget on Claude Sonnet
3.7"*, i.e. buy a better model before buying more fan-out.

---

## 7. Cache discipline — the constraint that shapes everything above

S12 is the only source that states this as the top metric: *"the KV-cache hit rate is the single
most important metric for a production-stage AI agent"*, with the arithmetic: *"cached input
tokens cost 0.30 USD/MTok, while uncached ones cost 3 USD/MTok—a 10x difference"*, on an
input-heavy workload — *"the average input-to-output token ratio is around 100:1"*.

The rules that follow:

- *"Make your context append-only. Avoid modifying previous actions or observations"* — because
  *"even a single-token difference can invalidate the cache from that token onward"*.
- Don't hot-swap the tool set mid-run: *"any change will invalidate the KV-cache for all
  subsequent actions and observations"*. Manus instead *"masks the token logits during decoding
  to prevent ... selection of certain actions"* — **mask, don't remove**.
- The same tension appears in Anthropic's own docs: S6's `clear_at_least` exists precisely so a
  clear only fires when it's *"worth breaking your prompt cache"*, and S7 recommends
  `cache_control` on the compaction block and at the end of the system prompt so *"cached system
  prompts"* aren't *"invalidated when compaction occurs"*.
- S10: content that is stable across turns (system prompt, tool definitions, CLAUDE.md) is
  *"automatically prompt cached"* — so a timestamp or a rotating preamble at the top of a system
  prompt is a self-inflicted cost.

---

## 8. Memory: types, scope, and the "keep the wrong turns" result

**Taxonomy (S19):** three kinds, three purposes:

- **Semantic** — *"Facts & Knowledge"*, as collections (searched at runtime) or profiles
  (structured, task-specific).
- **Episodic** — *"Past Experiences"*, preserving successful interactions as examples, *"capturing
  situation, reasoning, and outcomes"*.
- **Procedural** — *"System Behavior"*, encoding how the agent should respond, *"evolving through
  feedback and experience"*.

**Formation timing (S19):** hot-path extraction *"provides immediate updates but adds latency to
user interactions"*; background formation *"refers to the technique of prompting an LLM to reflect
on a conversation after it occurs ... without slowing down the immediate interaction."*

**Scoping (S19):** namespace templates like `("acme_corp", "{user_id}", "code_assistant")`, where
*"The `{user_id}` template variable populates at runtime"* — memory is keyed, never global. S8
says the same for the memory tool: *"The `/memories` path is a prefix that your handler maps onto
real storage, such as a per-user directory or keys in a database."*

**Theory (S21):** MemGPT's framing is still the cleanest — *"we propose virtual context
management, a technique drawing inspiration from hierarchical memory systems in traditional
operating systems that provide the appearance of large memory resources through data movement
between fast and slow memory"*, and it *"utilizes interrupts to manage control flow"*. Generative
Agents supplies the reflection half: an architecture that *"store[s] a complete record of the
agent's experiences using natural language, synthesize[s] those memories over time into
higher-level reflections, and retrieve[s] them dynamically to plan behavior."* S14 traces the
lineage: *"Reflexion introduced the idea of reflection following each agent turn and re-using
these self-generated memories"*.

**Errors are memory too (S12).** The most counter-intuitive well-sourced result of the sweep:
*"one of the most effective ways to improve agent behavior is deceptively simple: leave the wrong
turns in the context"*. Erasing a failed tool call erases the evidence that the approach doesn't
work. S15 makes it a factor — **Factor 9: "Compact Errors into Context Window"** — the synthesis
being: keep the *lesson* from the failure, compacted, not the raw stack trace, forever. S2 concurs
from the other direction: *"letting the agent know when a tool is failing and letting it adapt
works surprisingly well"*.

**Loop-shaped failure from memory (S12).** The flip side: *"Language models are excellent mimics;
they imitate the pattern of behavior in the context"* and *"the agent often falls into a
rhythm—repeating similar actions simply because that's what it sees"*. Uniform, repetitive context
*is* the loop-detection signal — and the stated mitigation is deliberate variation in
serialization, not just a counter.

**Claims ledgers / receipts (S11).** The mechanism the industry ships for "which source backs
this number" is citations: S11's own summary — *"Citations return the exact passages that support
each claim, so you can verify answers and surface sources to your users."* The harness pattern is
that grounding is a **structured field carried alongside the claim** (`cited_text` + document
index), not prose the model is asked to append — because prose citations are exactly the thing a
compaction or a tool-result clear will drop.

---

## 9. Recovery: checkpoints, resumable runs, durable execution

**Checkpoints (S2):** *"we built systems that can resume from where the agent was when the errors
occurred"*, and *"we combine the adaptability of AI agents built on Claude with deterministic
safeguards like retry logic and regular checkpoints"*. Determinism belongs in the harness; the
adaptability belongs to the model.

**Git as the checkpoint store (S3):** for code-shaped work, commits *are* checkpoints — *"This
allowed the model to use git to revert bad code changes and recover working states of the code
base"*. The generalization: a checkpoint must be a **restorable artifact**, not a log line.

**Thread-scoped persistence (S17):** *"Checkpointers persist a thread's graph state as
checkpoints. Use them for short-term, thread-scoped memory."*, listed use-cases including *"fault
tolerance"* and *"time travel"*. The gotcha the same page records: `MemorySaver` *"does not
persist between restarts"* — an in-process checkpointer is not durability, and this is a very easy
mistake to ship.

**Resumable sessions (S9, S10):** Claude Code exposes resume as a first-class flow: capture
`session_id` and the subagent's `agentId`, then *"pass `resume: sessionId` in the second query's
options"*. A resumed subagent *"retains its full conversation history, including all previous tool
calls, results, and reasoning"*. Crucially, a run that stops at its turn cap is **marked partial**:
*"When a subagent stops at its `maxTurns` limit, Claude Code marks the output in the Agent tool
result as partial, so Claude knows the run is unfinished."* An unfinished run that reads as
finished is the single worst recovery bug. S15 names the same requirement as **Factor 6:
"Launch/Pause/Resume with simple APIs"** and **Factor 12: "Make your agent a stateless reducer"**
— resumability is a consequence of statelessness plus an external state store (S15 Factor 5:
*"Unify execution state and business state"*).

**Budget guards (S9, S10, S18):** four independent caps, all of them in shipping SDKs:

| Cap | Mechanism | At the limit |
|---|---|---|
| Turns | `maxTurns` / `max_turns` (S10); S18's `max_turns` | S10: `ResultMessage` subtype `error_max_turns`. S18: *"If we exceed the `max_turns` passed, we raise a `MaxTurnsExceeded` exception."* |
| Spend | `maxBudgetUsd` / `max_budget_usd` (S9, S10) | *"refuses to spawn more subagents, returning `Budget limit reached`, stops background subagents that are still running, and ends the query with the `error_max_budget_usd` result subtype"* |
| Fan-out depth | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, default `3` (S9) | bottom-layer subagent *"does its delegated work itself"* |
| Concurrency | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, default `20` (S9) | *"Concurrent subagent limit reached"* returned as the tool result |

S9's rationale is worth quoting because it is a *model-behaviour* claim, not a cost one: *"Claude
decides on its own when to spawn a subagent and how many to spawn ... a subagent can spawn
subagents of its own, so one prompt can grow into a tree of agents."* And: *"Claude Opus 5
delegates to subagents more readily than earlier models, so the depth, concurrency, and spend
limits matter most on queries that run Opus 5."* Prompting alone is insufficient — *"Either
instruction only steers Claude, so set the limits as well."* S4 states the general principle:
*"It's also common to include stopping conditions (such as a maximum number of iterations) to
maintain control."*

**Typed termination, not a boolean (S10).** The result subtypes are the recovery contract:
`success`, `error_max_turns`, `error_max_budget_usd`, `error_during_execution`,
`error_max_structured_output_retries`. *"The `result` field holds the final text output and is
only present on the `success` variant, so always check the subtype before reading it."* Also:
*"All result subtypes carry `total_cost_usd`, `usage`, `num_turns`, and `session_id` so you can
track cost and resume even after errors."* — a failed run must still surrender its cost and its
resume handle. And crash accounting is called out explicitly: after a session crash the result
is `error_during_execution` *"whose cost fields may be zeroed and whose `stop_reason` is
`null`"*.

**Refusals and model misbehaviour are distinct states (S10, S18).** S10: *"To detect refusals,
check `stop_reason === 'refusal'`"*. S18: `ModelBehaviorError` occurs *"when the underlying model
produces unexpected or invalid outputs"* including malformed JSON. A harness that maps refusal,
malformed-tool-JSON, rate-limit and genuine tool failure onto one "error" frame cannot explain
itself to a user.

**Fallback models (S20).** The routing layer's answer: OpenRouter's default is *"Prioritize
providers that have not seen significant outages in the last 30 seconds. For the stable
providers, look at the lowest-cost candidates"*, with automatic fallback to *"the remaining
providers"*, `max_price` ceilings, `sort` by price/throughput/latency, and an explicit escape
hatch — `order` as *"list of provider slugs to try in order"* combined with `allow_fallbacks:
false` when substitution is unacceptable. The observability rule that makes fallback honest:
*"The response includes the `model` field showing which model was actually used"*. **A fallback
the user cannot see is a silent downgrade** — and in a finance product, a cheaper model silently
answering a valuation question is a trust failure, not a cost saving.

**Ground truth beats self-report (S4):** *"During execution, it's crucial for the agents to gain
'ground truth' from the environment at each step (such as tool call results or code execution) to
assess its progress."* S2 applies it to evaluation: *"break evaluation into discrete checkpoints
where specific state changes should have occurred"* and *"evaluate whether it achieved the
correct final state"* rather than validating every intermediate step.

---

## 10. What is load-bearing specifically for a local-first, BYOK finance agent

Not a build list — a steer for the WORLD-COMPARE pass. The sweep's practices divide unevenly:

- **Directly applicable, high value:** structured note-taking to disk (the app already owns a
  data dir), restorable compression (a filing URL + page anchor is the perfect lightweight
  identifier), typed termination subtypes, resume handles on every durable run, per-user memory
  namespacing, keeping the *lesson* of a failed tool call, citations-as-structured-fields.
- **Applicable with a twist:** cache discipline — a BYOK user pays their own provider, so an
  append-only, stable-prefix context is *their* money; and OpenRouter-style fallback must be
  **surfaced**, because a silently-substituted model answering about a company's pledged
  promoter holding is materially different from a refusal.
- **Weaker fit:** heavy multi-agent fan-out (S2's 15× token multiplier lands directly on a BYOK
  user's bill); server-side `compact_20260112` (vendor-specific — a multi-provider harness needs
  its own compactor, which is where S13's dedicated cheap compressor model is the right shape).

---

## CHECKLIST — 20 concrete practices

Each: the practice, the one-line reason, the source.

1. **Treat context as a budget with an explicit admission policy; measure tokens-in-window per
   turn.** Performance degrades non-uniformly with length, not just at the limit. — S1, S21
2. **Put invariants where they are re-injected every request, never only in turn 1.** Compaction
   drops early instructions: *"specific instructions from early in the conversation may not be
   preserved."* — S10
3. **Compact on a configured trigger, and make the summary prompt state-shaped** (state, next
   steps, learnings, decisions) rather than narrative. That is literally the default
   compaction prompt's instruction. — S7, S1
4. **Archive the full transcript before every compaction** (a `PreCompact`-equivalent hook).
   Compaction is lossy and irreversible in-context. — S10
5. **Make every compression restorable:** drop the payload, keep the identifier that can re-fetch
   it. *"compression strategies are always designed to be restorable."* — S12
6. **Clear stale tool RESULTS separately from compacting the conversation**, keeping the last N
   and excluding the tools whose results are load-bearing. 29% alone, 39% with memory, −84%
   tokens. — S5, S6
7. **Replace a cleared result with a placeholder that tells the model it was removed**, so it
   re-fetches instead of inventing. — S6
8. **Gate any cache-invalidating edit on a minimum token saving** (`clear_at_least`-style) and
   keep the context append-only otherwise — cached vs uncached is a 10× price difference. — S6, S12
9. **Mask unavailable tools, don't remove them mid-run.** Changing the tool block invalidates the
   cache for everything after it. — S12
10. **Defer tool/MCP schemas and load them on demand.** Un-deferred schemas *"consume significant
    context before the agent does any work."* — S10
11. **Carry lightweight identifiers, not payloads, across every boundary** (agent→agent,
    turn→turn, session→session). — S1, S2
12. **Give the agent a durable, per-user-namespaced file store it is prompted to read FIRST and
    update as it goes** — *"ASSUME INTERRUPTION."* — S8, S19
13. **Harden that store like a filesystem boundary:** reject `../` and encoded traversal, cap file
    size, expire unused files, strip secrets before write. — S8
14. **Run an initializer session that lays down the progress log + checklist + startup script
    before substantive work**, and end every session by updating it. — S3, S8
15. **Flip a task to "done" only after end-to-end verification, and mark a capped run as
    PARTIAL.** Both false-done modes are documented failures. — S3, S8, S9
16. **Use sub-agents for read-only, fact-returning subtasks with a restricted tool set; keep
    decisions single-threaded.** Isolation helps; dispersed decision-making doesn't. — S9, S1, S13
17. **Pass everything the sub-agent needs in its prompt, and sanitize instruction-shaped patterns
    in what it returns.** It inherits nothing, and its output re-enters a trusted context. — S9
18. **Checkpoint to durable storage (not an in-process saver) and expose a resume handle on every
    run, including failed ones.** `MemorySaver` *"does not persist between restarts."* — S17, S9, S10
19. **Cap turns, spend, fan-out depth and concurrency in the harness — prompting alone doesn't
    bound delegation — and count compaction iterations in the spend total.** — S9, S10, S18, S4, S7
20. **Terminate with a typed reason (success / max-turns / max-budget / refusal / model-behaviour
    / crash), and when a fallback model serves the request, say which model actually answered.**
    A silent downgrade is indistinguishable from a correct answer. — S10, S18, S20

Two supporting practices that didn't make the numbered cut but are well-evidenced:
**keep the wrong turns** (compacted into a lesson) rather than erasing failed attempts — S12, S15
Factor 9; and **treat repetitive, uniform context as the loop signal**, since the model *"falls
into a rhythm—repeating similar actions simply because that's what it sees"* — S12.
