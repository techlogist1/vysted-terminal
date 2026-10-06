# R15 Census — World sweep: agent-harness TOOLS, EVALS, PROVIDER QUIRKS (state of the art, Sept 2026)

Worker model id: `claude-opus-5[1m]`
Date of sweep: 2026-09-19
Topic: `harness-tools` — tool design (few deep tools, namespacing, response-format control,
token-efficient results, error messages that steer, idempotency), evals (scenario harnesses,
programmatic + LLM-judge scoring, regression suites, trajectory checks, pass^k), and
provider-quirk handling (tool-call formats, reasoning params, streaming, capability gating).
Read-only sweep. No repo files changed except this one. **No code claims are made here** — this
file is outside-truth only; the `-COMPARE` pass is where it meets `file:line`.

## Evidence conventions

- Every claim below carries a **URL + verbatim quote**. Quotes are from the page fetched on
  2026-09-19 unless noted.
- Distinct sources used: **19**.
- Honest disclosure of what failed this sweep:
  - `WebSearch` was unavailable: the session had exhausted its search budget
    (`200 of 200 WebSearch calls`). Every source below was reached by **direct WebFetch of a
    known primary URL**, so this sweep is deep on primary docs and thin on
    practitioner-blog discovery. That is a real coverage limit, stated rather than hidden.
  - `openrouter.ai/docs/features/tool-calling` and `openrouter.ai/docs/use-cases/tool-calling`
    both returned **HTTP 404**. No OpenRouter-specific claim is made below — the
    multi-provider-router quirks section rests on first-party provider docs only.
  - `modelcontextprotocol.io/specification/2025-11-25/schema` did not surface `ToolAnnotations`
    in the fetched excerpt; the annotation semantics were taken instead from the **canonical
    schema source** on GitHub (source 16), which is stronger evidence, not weaker.

---

## 1. Tool design — the shape of a good tool

### T-1. Tools are a first-class interface, not glue. Budget design effort accordingly

> "One rule of thumb is to think about how much effort goes into human-computer interfaces
> (HCI), and plan to invest just as much effort in creating good _agent_-computer interfaces
> (ACI)."
> — https://www.anthropic.com/engineering/building-effective-agents

> "While building our agent for SWE-bench, we actually spent more time optimizing our tools
> than the overall prompt."
> — https://www.anthropic.com/engineering/building-effective-agents

This is the load-bearing claim of the whole topic: tool surface is where agent quality is won
or lost, ahead of prompt wording.

### T-2. Few DEEP tools beat many shallow ones — consolidate whole workflows

> "Tools can consolidate functionality, handling potentially _multiple_ discrete operations (or
> API calls) under the hood."
> "Instead of implementing a `list_users`, `list_events`, and `create_event` tools, consider
> implementing a `schedule_event` tool which finds availability and schedules an event."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

> "Combine functions that are always called in sequence"
> — https://developers.openai.com/api/docs/guides/function-calling

The failure mode of the opposite approach is named directly:

> "One of the most common failure modes we see is bloated tool sets that cover too much
> functionality or lead to ambiguous decision points about which tool to use."
> "If a human engineer can't definitively say which tool should be used in a given situation, an
> AI agent can't be expected to do better."
> "Tools should be self-contained, robust to error, and extremely clear with respect to their
> intended use."
> "Curating a minimal viable set of tools for the agent can also lead to more reliable
> maintenance and pruning of context over long interactions."
> — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### T-3. There is now a published number for "too many tools"

> "Aim for fewer than 20 functions available at the start of a turn at any one time, though this
> is just a soft suggestion."
> — https://developers.openai.com/api/docs/guides/function-calling

> "Claude's ability to pick the right tool degrades once you exceed 30–50 available tools."
> "A typical multiserver setup (GitHub, Slack, Sentry, Grafana, and Splunk) can consume ~55k
> tokens in definitions before Claude does any work."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

The same page gives the explicit trigger to switch strategies:

> "Use tool search when any of the following apply: You have 10 or more tools available. Your
> tool definitions consume more than 10k tokens. Tool selection accuracy drops as your toolset
> grows. You aggregate multiple MCP servers (200+ tools). Your tool library grows over time."
> "Standard tool calling, without tool search, is a better fit when you have fewer than 10
> tools, every tool is used in every request, or your tool definitions are small (less than 100
> tokens total)."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

### T-4. Namespacing is the cheap disambiguator

> "Namespacing (grouping related tools under common prefixes) can help delineate boundaries
> between lots of tools."
> "For example, namespacing tools by service (e.g., `asana_search`, `jira_search`) and by
> resource (e.g., `asana_projects_search`, `asana_users_search`), can help agents select the
> right tools at the right time."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

> "Use consistent namespacing in tool names: prefix by service or resource (for example,
> `github_`, `slack_`) so one search matches the whole group."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

MCP now pins the legal character set, which matters for anyone projecting an internal registry
onto an MCP surface:

> "The following **SHOULD** be the only allowed characters: uppercase and lowercase ASCII
> letters (A-Z, a-z), digits (0-9), underscore (\_), hyphen (-), and dot (.)"
> "Tool names **SHOULD** be between 1 and 128 characters in length (inclusive)."
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

### T-5. Schemas should make the wrong call unrepresentable (poka-yoke)

> "[Poka-yoke](https://en.wikipedia.org/wiki/Poka-yoke) your tools. Change the arguments so that
> it is harder to make mistakes."
> — https://www.anthropic.com/engineering/building-effective-agents

> "Use enums and object structure to prevent invalid states"
> "Make the functions predictable and intuitive"
> "Pass the intern test"
> "Don't make the model fill arguments you already know. For example, if you already have an
> `order_id` based on a previous menu, don't include an `order_id` parameter."
> — https://developers.openai.com/api/docs/guides/function-calling

### T-6. Descriptions carry real, measurable weight

> "Put yourself in the model's shoes. Is it obvious how to use this tool, based on the
> description and parameters, or would you need to think carefully about it?"
> "A good tool definition often includes example usage, edge cases, input format requirements,
> and clear boundaries from other tools."
> — https://www.anthropic.com/engineering/building-effective-agents

> "Bad tool descriptions can send agents down completely wrong paths, so each tool needs a
> distinct purpose and a clear description."
> — https://www.anthropic.com/engineering/multi-agent-research-system

> "Explicitly describe the purpose of the function and each parameter (and its format), and what
> the output represents."
> "Use the system prompt to describe when (and when not) to use each function. Generally, tell
> the model _exactly_ what to do."
> — https://developers.openai.com/api/docs/guides/function-calling

Worked example inputs are now a measured lever, not a nicety:

> "Tool use examples improved accuracy from 72% to 90% on complex parameter handling"
> — https://www.anthropic.com/engineering/advanced-tool-use

### T-7. Names and identifiers in the RESULT matter as much as in the schema

> "Tool implementations should take care to return only high signal information back to agents."
> "Agents also tend to grapple with natural language names, terms, or identifiers significantly
> more successfully than they do with cryptic identifiers."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

---

## 2. Token-efficient results — the second half of tool design

### T-8. Let the AGENT choose the verbosity: `response_format`

> "You can enable both by exposing a simple `response_format` enum parameter in your tool,
> allowing your agent to control whether tools return `"concise"` or `"detailed"` responses."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

### T-9. Pagination / filtering / truncation with sane defaults — and SAY you truncated

> "We suggest implementing some combination of pagination, range selection, filtering, and/or
> truncation with sensible default parameter values."
> "If you choose to truncate responses, be sure to steer agents with helpful instructions."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

> "It's extremely important that tools promote efficiency, both by returning information that is
> token efficient and by encouraging efficient agent behaviors."
> — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### T-10. The big 2026 shift: stop routing every intermediate result through the model

> "Every intermediate result must pass through the model. In this example, the full call
> transcript flows through twice."
> "agents can filter and transform results in code before returning them"
> "The agent sees five rows instead of 10,000."
> "This reduces the token usage from 150,000 tokens to 2,000 tokens—a time and cost saving of
> 98.7%."
> — https://www.anthropic.com/engineering/code-execution-with-mcp

Measured again, on the product feature built from it:

> "Average usage dropped from 43,588 to 27,297 tokens, a 37% reduction"
> "Eliminate 19+ inference passes"
> "Reduce token consumption from 200KB of raw expense data to just 1KB"
> — https://www.anthropic.com/engineering/advanced-tool-use

### T-11. Load tool definitions just-in-time, not all up front

> "in cases where agents are connected to thousands of tools, they'll need to process hundreds
> of thousands of tokens before reading a request."
> "Presenting tools as code on a filesystem allows models to read tool definitions on-demand,
> rather than reading them all up-front."
> — https://www.anthropic.com/engineering/code-execution-with-mcp

> "85% reduction in token usage while maintaining access to your full tool library"
> "Opus 4 improved from 49% to 74%, and Opus 4.5 improved from 79.5% to 88.1%"
> — https://www.anthropic.com/engineering/advanced-tool-use

Mechanically, the shipped form is a deferred-loading flag plus a search tool, with two
operational constraints worth copying:

> "Keep your 3–5 most frequently used tools non-deferred so Claude can call them without
> searching first."
> "At least one tool, normally the tool search tool itself, must stay non-deferred."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

...and prompt-cache preservation is designed in, which is the reason it is cheap:

> "Internally, the API excludes deferred tools from the system-prompt prefix. ... The prefix is
> untouched, so prompt caching is preserved."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

---

## 3. Errors that steer, and behavioural metadata

### T-12. An error is a prompt. Write it as one

> "If a tool call raises an error (for example, during input validation), you can
> prompt-engineer your error responses to clearly communicate specific and actionable
> improvements, rather than opaque error codes or tracebacks."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

MCP formalises the distinction between "the model can fix this" and "the model cannot":

> "**Tool Execution Errors** contain actionable feedback that language models can use to
> self-correct and retry with adjusted parameters. **Protocol Errors** indicate issues with the
> request structure itself that models are less likely to be able to fix."
> "Clients **SHOULD** provide tool execution errors to language models to enable self-correction."
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

And the spec's own example error is the template — it names the violated rule AND the current
state the model needs in order to retry:

> "Invalid departure date: must be in the future. Current date is 08/08/2025."
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

### T-13. Declare read-only / destructive / idempotent / open-world — but never trust the hint

Canonical schema semantics (verbatim doc-comments and defaults):

> `readOnlyHint` — "If true, the tool does not modify its environment. Default: false"
> `destructiveHint` — "If true, the tool may perform destructive updates to its environment. If
> false, the tool performs only additive updates. (This property is meaningful only when
> `readOnlyHint == false`) Default: true"
> `idempotentHint` — "If true, calling the tool repeatedly with the same arguments will have no
> additional effect on its environment. (This property is meaningful only when
> `readOnlyHint == false`) Default: false"
> `openWorldHint` — "If true, this tool may interact with an 'open world' of external entities.
> If false, the tool's domain of interaction is closed. For example, the world of a web search
> tool is open, whereas that of a memory tool is not. Default: true"
> — https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2025-11-25/schema.ts

Note the defaults are **pessimistic**: a tool that says nothing is assumed writing, destructive,
non-idempotent and open-world. Silence is not safety.

The security rule is unambiguous — annotations are display/UX metadata, never an authorisation
mechanism:

> "For trust & safety and security, clients **MUST** consider tool annotations to be untrusted
> unless they come from trusted servers."
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

> "For trust & safety and security, there **SHOULD** always be a human in the loop with the
> ability to deny tool invocations."
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

### T-14. Declare an output schema; return structured content

> "If an output schema is provided: Servers **MUST** provide structured results that conform to
> this schema. Clients **SHOULD** validate structured results against this schema."
> "For backwards compatibility, a tool that returns structured content SHOULD also return the
> serialized JSON in a TextContent block."
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

An easily-missed trap for anyone writing a tool with no arguments:

> "For tools with no parameters, use one of these valid approaches:
> `{ "type": "object", "additionalProperties": false }` - **Recommended** ... `{ "type": "object" }`
> - accepts any object"
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

---

## 4. Evals — how the state of the art actually measures a tool-using agent

### T-15. Start absurdly small; ~20 real queries beats a big suite you never run

> "We started with a set of about 20 queries representing real usage patterns. Testing these
> queries often allowed us to clearly see the impact of changes."
> — https://www.anthropic.com/engineering/multi-agent-research-system

> "Prioritize volume over quality: More questions with slightly lower signal automated grading is
> better than fewer questions with high-quality human hand-graded evals."
> "Be task-specific: Design evals that mirror your real-world task distribution. Don't forget to
> factor in edge cases!"
> "Automate when possible: Structure questions to allow for automated grading (for example,
> multiple-choice, string match, code-graded, LLM-graded)."
> — https://platform.claude.com/docs/en/test-and-evaluate/develop-tests

### T-16. Grade the END STATE, not the trajectory — trajectory checks are a second, weaker lens

> "Instead of judging whether the agent followed a specific process, evaluate whether it achieved
> the correct final state."
> — https://www.anthropic.com/engineering/multi-agent-research-system

BFCL v3 built exactly this into a public benchmark, and it is the cleanest published statement
of the two grading modes:

> "**State-based evaluation** compares 'the backend system's state after all function calls are
> executed at the end of each turn'"
> "**Response-based evaluation** uses 'subset-matched' checking, where 'the model result is
> considered correct if it contains the ground truth as a subset, even if it contains additional
> function calls.'"
> — https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html

### T-17. Test the two failure modes nobody writes cases for: missing parameter, missing function

> The **missing-parameter** category "tests the model's ability to recognize when essential
> information is missing from the user request." The **missing-function** category "requires the
> model to identify that no available function can fulfill the user request."
> — https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html

And the observed failure shapes are worth writing regression cases against directly:

> LLMs "struggle with breaking down tasks and making the correct implicit calls", fail to
> "explore the current state before performing actions", and can "overthink and negatively
> influence their planning."
> — https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html

### T-18. Measure RELIABILITY, not best-of-n: pass^k

> "state-of-the-art function calling agents (like gpt-4o) succeed on <50% of the tasks"
> "a new metric (pass^k) to evaluate the reliability of agent behavior over multiple trials"
> "pass^8 <25% in retail"
> — https://arxiv.org/abs/2406.12045 (τ-bench)

This is the single most under-adopted practice in the field: a tool surface that passes once in
eight tries is, for a money-relevant product, broken — and a `pass@1` dashboard hides that
completely.

### T-19. An LLM judge works — as ONE call, ONE rubric, ONE numeric score plus pass/fail

> "We used an LLM judge that evaluated each output against criteria in a rubric... a single LLM
> call with a single prompt outputting scores from 0.0-1.0 and a pass-fail grade was the most
> consistent."
> — https://www.anthropic.com/engineering/multi-agent-research-system

The judge itself must be aligned against a human before it is trusted:

> "This information allowed me to iterate on the prompt of the critique model to make it
> sufficiently aligned with Phillip over time."
> — https://hamel.dev/blog/posts/evals/

### T-20. Three tiers, and assertions come from real traces — not imagination

> "There are three levels of evaluation to consider: Level 1: Unit Tests, Level 2: Model & Human
> Eval, Level 3: A/B testing."
> "If you have trouble thinking of assertions, you should critically examine your traces and
> failure modes."
> "Doing all three activities well creates a virtuous cycle differentiating great from mediocre
> AI products."
> — https://hamel.dev/blog/posts/evals/

Grading-method ladder, simplest first (use the cheapest rung that discriminates):

> "1. Exact match evaluation ... 2. Cosine similarity evaluation ... 3. ROUGE-L evaluation ...
> 4. LLM-based Likert scale ... 5. LLM-based binary classification ... 6. LLM-based ordinal scale"
> "Most use cases need multidimensional evaluation along several success criteria."
> — https://platform.claude.com/docs/en/test-and-evaluate/develop-tests

### T-21. Evals must run against REAL data, and humans still find what evals miss

> "Prompts should be inspired by real-world uses and be based on realistic data sources and
> services... avoid overly simplistic or superficial 'sandbox' environments."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

> "People testing agents find edge cases that evals miss. These include hallucinated answers on
> unusual queries, system failures, or subtle source selection biases."
> — https://www.anthropic.com/engineering/multi-agent-research-system

### T-22. Close the loop: feed the eval transcripts back and let the agent rewrite the tool

> "You can even let agents analyze your results and improve your tools for you. Simply
> concatenate the transcripts from your evaluation agents and paste them into Claude Code."
> — https://www.anthropic.com/engineering/writing-tools-for-agents

> "This process for improving tool ergonomics resulted in a 40% decrease in task completion time
> for future agents using the new description, because they were able to avoid most mistakes."
> — https://www.anthropic.com/engineering/multi-agent-research-system

> "Test how the model uses your tools: Run many example inputs in our workbench to see what
> mistakes the model makes, and iterate."
> — https://www.anthropic.com/engineering/building-effective-agents

---

## 5. Provider-quirk handling — where a multi-provider BYOK harness actually breaks

### T-23. Schema conformance is now a provider FEATURE — turn it on, per provider

> "Setting `strict` to `true` will ensure function calls reliably adhere to the function schema,
> instead of being best effort."
> "We recommend always enabling strict mode."
> — https://developers.openai.com/api/docs/guides/function-calling

> "Without strict mode, Claude might return incompatible types (`"2"` instead of `2`) or omit
> required fields, breaking your functions and causing runtime errors."
> "Tool `input` strictly follows the `input_schema` ... Tool `name` is always valid (from
> provided tools or server tools)"
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use

Two caveats that only appear in the fine print, both of which bite a BYOK/regulated app:

> "The computer use and browser use toolset entries ... don't accept `strict: true`; a request
> that sets it on either entry is rejected."
> "Tool schemas are temporarily cached for up to 24 hours since last use."
> "Do not include PHI in `input_schema` property names, `enum` values, `const` values, or
> `pattern` regular expressions."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use

The generalisable rule: **the schema is not private the way message content is.** Never put
user-identifying or sensitive values into enums or patterns.

### T-24. Tool-result pairing differs by provider — by ID on one, by NAME on another

Anthropic pairs by `tool_use_id`:

> "`{type: "tool_result", tool_use_id: $tool_use_id, content: $weather}`"
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

Gemini requires the function NAME on the response, alongside the call id:

> "Function responses must be paired to function calls using three fields: `name`: The function
> name (matching the original call); `call_id`: The unique identifier from the original
> function_call step; `result`: The execution result as text content"
> — https://ai.google.dev/gemini-api/docs/function-calling

A harness that normalises to one shape and drops `name` on the result turn will multi-round fine
on one provider and silently break on the other. This is the canonical cross-provider bug.

### T-25. Reasoning-model state must be echoed back verbatim, and the rules differ by model

> "For stateless mode, preserve all model-generated steps including `thought` steps exactly as
> received in conversation history."
> — https://ai.google.dev/gemini-api/docs/function-calling

> "Thinking block preservation changes too: Claude Opus 4.5 and models numbered 4.6 and higher
> keep prior turns' thinking blocks in context and bill them as input, where Claude Sonnet 4.5,
> Claude Haiku 4.5, and earlier models stripped them"
> — https://platform.claude.com/docs/en/build-with-claude/extended-thinking

### T-26. Reasoning PARAMETERS are a moving target that 400s across a model generation

This is the clearest single example in the corpus of why a pinned slug rots:

> "Extended thinking (`thinking.type: "enabled"` with `budget_tokens`) is deprecated on the
> Claude 4.6 models (requests using it still succeed). Claude 4.7 and later models do not support
> it and reject requests that use it, returning a 400 error."
> "You need to migrate off `type: "enabled"` if: ... You are moving to Claude Opus 4.7, Claude
> Opus 4.8, Claude Opus 5, Claude Sonnet 5, Claude Fable 5.1, Claude Mythos 5.1, Claude Fable 5,
> or Claude Mythos 5, where `type: "enabled"` returns a 400 error."
> "The mapping is small: remove `budget_tokens`, set `thinking: {type: "adaptive"}`, and control
> reasoning depth with `output_config: {effort: ...}` instead of a token budget."
> — https://platform.claude.com/docs/en/build-with-claude/extended-thinking

The takeaway for a harness: **repair the known 400 in place and retry once**, rather than
surfacing a raw provider error — the failure is a parameter-shape mismatch the harness can fix,
not a user error. A model-name allow-list would be the wrong fix; the docs describe the break by
parameter, across a whole generation.

### T-27. "Accepted" is not "supported" — capability gating must be per-model, not per-provider

> "Claude Haiku 4.5 does not support interleaved thinking. On the Claude API, the beta header is
> accepted but ignored."
> "Acceptance is not the same as effect: on models that reject `type: "enabled"` (4.7 and later)
> or lack manual-mode interleaving (Claude Opus 4.6), the header has no manual-mode effect"
> "Partner-operated platforms (Amazon Bedrock and Google Cloud) likewise accept the header on any
> model without returning an error, and ignore it on models that don't support"
> — https://platform.claude.com/docs/en/build-with-claude/extended-thinking

Same shape on the tool-search feature — per-model support tables, plus a platform carve-out:

> "Claude Opus 4.1 and earlier models don't support the tool search tool."
> "On Amazon Bedrock, server-side tool search is available only through the InvokeModel API, not
> the Converse API."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

A harness that gates a feature on `provider == "anthropic"` rather than on the model id will
either 400 or, worse, **silently no-op**.

### T-28. Cache invalidation is a provider quirk with a measurable bill

> "changing `budget_tokens` between requests invalidates cache breakpoints, just as switching
> thinking modes does, because the budget value is rendered into the prompt."
> "In practice, pick a budget and hold it stable for the life of a cached conversation."
> "A tool with `defer_loading: true` can't also carry `cache_control`: the API returns a 400. Put
> the cache breakpoint on a non-deferred tool."
> — https://platform.claude.com/docs/en/build-with-claude/extended-thinking and
> https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

### T-29. Tool *invocation policy* is a first-class knob, and it is spelled differently everywhere

> "Three modes control model behavior via `tool_choice`: **auto** (default) ... **any**: 'Model is
> constrained to always predict a function call' ... **none**: 'Model is prohibited from making
> function calls'"
> — https://ai.google.dev/gemini-api/docs/function-calling

> "The `tool_choice` parameter supports 'auto' (default), 'required', forced specific functions,
> or `allowed_tools` for restricting callable subsets. Set `tool_choice` to `"none"` to imitate
> the behavior of passing no functions."
> — https://developers.openai.com/api/docs/guides/function-calling

> "`tool_choice: {type: "auto", disable_parallel_tool_use: true}`" — "Ask for at most one tool
> call per turn."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

Note that Anthropic's `any`/`tool` choice is not free — it changes the injected system prompt
size, per model:

> "Claude Opus 5 | `auto`, `none`***`any`, `tool` | 286 tokens***406 tokens"
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

### T-30. Missing-required-argument behaviour differs BY MODEL TIER — the small model guesses

> "If the user's prompt doesn't include enough information to fill all the required parameters
> for a tool, Claude Opus is much more likely to recognize that a parameter is missing and ask for
> it. Claude Sonnet might ask, especially when prompted to think before outputting a tool request.
> But it might also infer a reasonable value."
> "This behavior is not guaranteed, especially for more ambiguous prompts and for less capable
> models."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

For a finance app this is the money-relevant quirk in the whole sweep: a cheap or local model
**invents** the missing argument rather than asking, and the fabricated argument then looks like
a real, sourced value downstream. Validation belongs in the handler, not in the prompt.

### T-31. Steering eagerness and narrating the plan are prompt-side controls with published shapes

> "Switch to a lower `reasoning_effort`. This reduces exploration depth but improves efficiency
> and latency."
> "You can even set fixed tool call budgets...The budget can naturally vary based on your desired
> search depth."
> "Provide the model with an escape hatch that makes it easier to satisfy a shorter context
> gathering step."
> "GPT-5 is trained to provide clear upfront plans and consistent progress updates via 'tool
> preamble' messages."
> "Steer the frequency, style, and content of tool preambles...from detailed explanations to
> brief plans."
> "Prompted planning is more important at minimal reasoning, as the model has fewer reasoning
> tokens."
> — https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide

And the anti-pattern that a tool description is unusually good at introducing:

> "Poorly-constructed prompts containing contradictory or vague instructions can be more damaging
> to GPT-5."
> "Carefully review prompts for poorly-worded instructions...removing them drastically streamlined
> performance."
> — https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide

A tool description that says "use this for any price question" while a sibling says "always use
this for quotes" is exactly that contradiction, shipped in the tool layer where nobody reviews it.

### T-32. Streaming and server-side tools change the transcript shape you must echo back

> "On the next request, pass the assistant's content back unchanged, including the
> `server_tool_use` and `tool_search_tool_result` blocks."
> "Never return a `tool_result` for its `srvtoolu_...` ID." / "Don't return a `tool_result` for
> the `srvtoolu_...` ID: the API rejects the request."
> "A search that matches nothing returns a `tool_search_tool_search_result` with an empty
> `tool_references` array, not an error."
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

Also note the failure taxonomy this feature publishes — a good model for any tool that can fail
for operational rather than logical reasons:

> "`invalid_tool_input` ... `unavailable` ... `too_many_requests` ... `execution_time_exceeded`"
> — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

### T-33. Client-side hygiene the spec asks for, which harnesses routinely skip

> "Clients **SHOULD**: Prompt for user confirmation on sensitive operations; Show tool inputs to
> the user before calling the server, to avoid malicious or accidental data exfiltration; Validate
> tool results before passing to LLM; Implement timeouts for tool calls; Log tool usage for audit
> purposes"
> — https://modelcontextprotocol.io/specification/2025-11-25/server/tools

---

## CHECKLIST — 25 concrete practices

Each line: the practice, a one-line rationale, and its source.

| # | Practice | Why | Source |
|---|---|---|---|
| 1 | Budget as much design effort on the tool surface as on the UI; treat it as the ACI. | "plan to invest just as much effort in creating good _agent_-computer interfaces (ACI)" — and SWE-bench work spent more time on tools than the prompt. | [building-effective-agents](https://www.anthropic.com/engineering/building-effective-agents) |
| 2 | Consolidate multi-call workflows into ONE deep tool (`schedule_event`, not list+list+create). | Each extra round trip is an inference pass and a chance to pick wrong. | [writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| 3 | Prune overlapping tools until a human engineer could always name the right one. | "If a human engineer can't definitively say which tool should be used ... an AI agent can't be expected to do better." | [effective-context-engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| 4 | Keep the model's live tool count under ~20, and treat 30–50 as the accuracy cliff. | Published thresholds, not folklore: "fewer than 20 functions"; "degrades once you exceed 30–50". | [openai function-calling](https://developers.openai.com/api/docs/guides/function-calling), [tool-search-tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) |
| 5 | Namespace tool ids by service and resource (`kite_positions_get`), within MCP's `[A-Za-z0-9_.-]`, ≤128 chars. | Prefixes both disambiguate selection and make one search match a whole group. | [writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents), [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |
| 6 | Defer-load rarely-used tool definitions; keep the 3–5 hottest always resident. | ~55k tokens of definitions before work starts; deferral cuts ~85% and lifts selection accuracy (49%→74%, 79.5%→88.1%). | [tool-search-tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool), [advanced-tool-use](https://www.anthropic.com/engineering/advanced-tool-use) |
| 7 | Poka-yoke the schema: enums, object structure, no argument the caller already knows. | "Change the arguments so that it is harder to make mistakes"; "Don't make the model fill arguments you already know." | [building-effective-agents](https://www.anthropic.com/engineering/building-effective-agents), [openai function-calling](https://developers.openai.com/api/docs/guides/function-calling) |
| 8 | Put example calls (`input_examples`) on any tool with non-obvious parameters. | Measured 72% → 90% accuracy on complex parameter handling. | [advanced-tool-use](https://www.anthropic.com/engineering/advanced-tool-use) |
| 9 | Write descriptions that pass the intern test and state boundaries against sibling tools. | "Bad tool descriptions can send agents down completely wrong paths." | [multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system) |
| 10 | Audit tool descriptions for contradictions the way you audit a system prompt. | "contradictory or vague instructions can be more damaging"; removing them "drastically streamlined performance". | [gpt-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide) |
| 11 | Return natural-language names/labels, not cryptic ids, in tool results. | "Agents also tend to grapple with natural language names ... significantly more successfully than ... cryptic identifiers." | [writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| 12 | Expose a `response_format` enum (`concise` \| `detailed`) so the agent picks its own verbosity. | Lets one tool serve both a cheap scan and a deep read without two tools. | [writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| 13 | Paginate/filter/truncate by default — and say in the payload that you truncated. | "be sure to steer agents with helpful instructions" when truncating. | [writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| 14 | Filter and aggregate in code BEFORE the result reaches the model. | "The agent sees five rows instead of 10,000" — 150,000 → 2,000 tokens, 98.7% saving. | [code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp) |
| 15 | Let the agent orchestrate multi-tool chains in code rather than one round trip per call. | 43,588 → 27,297 tokens (37%), "Eliminate 19+ inference passes". | [advanced-tool-use](https://www.anthropic.com/engineering/advanced-tool-use) |
| 16 | Make every tool error a prompt: name the rule broken, the offending value, and the current state. | Spec template: "Invalid departure date: must be in the future. Current date is 08/08/2025." | [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |
| 17 | Separate model-fixable execution errors (`isError: true`) from protocol errors, and feed only the former back for self-correction. | "Tool Execution Errors contain actionable feedback that language models can use to self-correct". | [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |
| 18 | Annotate every tool `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` — and never enforce safety with them. | Defaults are pessimistic (silence = destructive, non-idempotent); "clients MUST consider tool annotations to be untrusted". | [MCP schema.ts](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2025-11-25/schema.ts), [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |
| 19 | Declare `outputSchema` and return `structuredContent` (plus the serialized JSON text block). | Server MUST conform; clients SHOULD validate — turns a prose blob into a checkable contract. | [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |
| 20 | Turn on strict/grammar-constrained tool inputs per provider, and keep sensitive values OUT of schemas. | Kills the `"2"` vs `2` class of bug; schemas are cached up to 24h and not covered by message-content protections. | [strict-tool-use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use), [openai function-calling](https://developers.openai.com/api/docs/guides/function-calling) |
| 21 | Keep a scenario suite of ~20 real queries on REAL data, run on every tool change. | "about 20 queries representing real usage patterns" made change impact visible; sandbox data hides the failures that matter. | [multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system), [writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| 22 | Grade the END STATE primarily; use trajectory/subset matching as the secondary lens. | "evaluate whether it achieved the correct final state"; BFCL's state-based vs response-based split. | [multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system), [BFCL v3](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html) |
| 23 | Add explicit missing-parameter and missing-function eval cases. | These are the two categories BFCL had to add; they are also exactly where a weaker model invents a value. | [BFCL v3](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html) |
| 24 | Report pass^k (same scenario k times, all must pass), not pass@1. | τ-bench: "pass^8 <25% in retail" — single-run scores hide unreliability that a user meets on day one. | [τ-bench](https://arxiv.org/abs/2406.12045) |
| 25 | Use ONE LLM-judge call with ONE rubric → 0.0–1.0 + pass/fail, aligned against a human grader first; mine assertions from real traces; then feed eval transcripts back to rewrite the tools. | "a single LLM call with a single prompt ... was the most consistent"; tool-ergonomics rewriting gave a "40% decrease in task completion time". | [multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system), [hamel.dev evals](https://hamel.dev/blog/posts/evals/), [develop-tests](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) |

### Provider-quirk addendum to the checklist (gate per MODEL, never per provider)

| # | Practice | Why | Source |
|---|---|---|---|
| P1 | Carry the function NAME on the tool-result turn, not just the call id. | Gemini pairs `function_result` by `name` + `call_id`; an id-only normaliser breaks multi-round on Gemini while passing on Anthropic. | [gemini function-calling](https://ai.google.dev/gemini-api/docs/function-calling) |
| P2 | Echo reasoning/thought state back verbatim; expect preservation rules to differ by model. | "preserve all model-generated steps including `thought` steps exactly as received"; Claude 4.5-and-earlier stripped thinking blocks, 4.6+ keep and bill them. | [gemini function-calling](https://ai.google.dev/gemini-api/docs/function-calling), [extended-thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) |
| P3 | Repair known parameter-shape 400s in place and retry once, message-matched — don't surface the raw provider error. | `thinking.type:"enabled"` 400s on Opus 4.7+/Opus 5/Sonnet 5/Fable 5/Mythos 5; the fix is a small mechanical remap to `{type:"adaptive"}` + `output_config.effort`. | [extended-thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) |
| P4 | Gate capabilities on the MODEL ID, and remember "accepted" ≠ "supported". | The interleaved-thinking header is "accepted but ignored" on Haiku 4.5 and on partner platforms — a silent no-op, not an error. | [extended-thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) |
| P5 | Validate required arguments in the HANDLER; assume a cheaper model will guess rather than ask. | "Claude Sonnet might ask ... But it might also infer a reasonable value"; a guessed argument becomes a fabricated number downstream. | [tool-use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) |
| P6 | Hold reasoning/effort/budget settings stable inside a cached conversation. | Changing `budget_tokens` (or thinking mode) re-renders the prompt and invalidates cache breakpoints — measurable cost, invisible cause. | [extended-thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) |
| P7 | Normalise `tool_choice` per provider (`auto`/`any`/`none`/`required`/`allowed_tools`, `disable_parallel_tool_use`) and price the choice. | The spellings differ; and on Anthropic, `any`/`tool` costs ~120 more system-prompt tokens than `auto` (Opus 5: 286 → 406). | [gemini](https://ai.google.dev/gemini-api/docs/function-calling), [openai](https://developers.openai.com/api/docs/guides/function-calling), [tool-use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) |
| P8 | Echo server-side tool blocks back unchanged; never return a `tool_result` for a server tool id. | "the API rejects the request" — and an empty search result is a normal empty array, not an error to retry. | [tool-search-tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) |

---

## Sources (19 distinct)

1. https://www.anthropic.com/engineering/writing-tools-for-agents
2. https://www.anthropic.com/engineering/building-effective-agents
3. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
4. https://www.anthropic.com/engineering/code-execution-with-mcp
5. https://www.anthropic.com/engineering/advanced-tool-use
6. https://www.anthropic.com/engineering/multi-agent-research-system
7. https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
8. https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
9. https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
10. https://platform.claude.com/docs/en/build-with-claude/extended-thinking
11. https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
12. https://developers.openai.com/api/docs/guides/function-calling
13. https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide
14. https://ai.google.dev/gemini-api/docs/function-calling
15. https://modelcontextprotocol.io/specification/2025-11-25/server/tools
16. https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2025-11-25/schema.ts
17. https://modelcontextprotocol.io/specification/2025-06-18/server/tools (prior spec revision, for the error-model diff)
18. https://arxiv.org/abs/2406.12045 (τ-bench, pass^k)
19. https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html (BFCL v3, state-based grading)
20. https://hamel.dev/blog/posts/evals/

_(20 listed; #17 is the prior revision of #15 and is counted as one source family, hence "19
distinct" above.)_
