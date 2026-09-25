# RC1 fix round 2 — triage plan

Triage lead: rc1-fix-r2-triage (Opus). Base `b0f2b256`. Code was read in the rc1-cand worktree.
In-process probes used the candidate venv on the seed copy `rc1-data-rc1-fix-r2-triage`, and my
own sidecar ran on `:52332` (now stopped). Evidence is in `fix-r2/evidence/`. Working log:
`../logs/rc1-fix-r2-triage.md`.

These are the three keys whose round-1 fixes did not close them: rc1-fix-r1-recheck:1-3. All three
are **real**. They split into 3 file-disjoint writer sets. **0 rejected.** **1 partly deferred**:
the first-brief half of rc1-battery-4:1, recorded as DECISIONS_FOR_OPERATOR §4.1.

## W1 statements-currency (opus): rc1-scenarios:5

Files: `sidecar/services/agent_tools/fundamentals.py`, `sidecar/services/agent_tools/research.py`,
`sidecar/services/agent_runtime.py` (only `_FUNDAMENTALS_TOOLS` / `_model_facing_content`),
`sidecar/tests/test_fundamentals_tool.py`, `sidecar/tests/test_agent_runtime.py`.

- **Mechanism (confirmed by code read and the recheck evidence).** `_financial_statements`
  (agent_tools/fundamentals.py:240-287) returns raw statement floats with no currency key.
  `_model_facing_content` projects only `fundamentals` and `compare_symbols`
  (agent_runtime.py:714, 976). As a result, SIFY's income `total_revenue 44877000000.0` (INR)
  reached llama3.1:8b bare, and the model said "$44.877 billion". This is the third sibling of the
  R15-AGENT-001 class.
- **Fix.** The handler fetches `provider_registry.get_fundamentals(symbol)` concurrently with the
  statement. It adds `currency` = `financial_currency or currency`, the same statement currency that
  EquityOverviewPanel.tsx:833 uses. If that lookup fails, it sets `currency: null` and adds a note
  saying the reporting currency is unknown.
  Add `financial_statements` to `_FUNDAMENTALS_TOOLS`. `fundamentals_content` then renders each
  money line's period values with `display_value(v, "currency", currency)`. A line stays raw when
  its lower-cased label tokens (split on non-alphanumerics) include `eps`, `share`, `shares` or
  `rate`. Those are per-share values, share counts and tax rates. `shareholders` is a money token.
  When `currency` is null, every line stays raw.
- **Tests.**
  - A SIFY-shaped income result with `currency: "INR"`: the model-facing `total_revenue` reads
    `₹4,488 cr`, while `Basic EPS` and `Diluted Average Shares` stay numeric.
  - A case the fix was not written against: an AAPL-shaped USD cash-flow statement, where
    `Free Cash Flow` renders as `USD …B`.
  - Handler: fundamentals `{currency: USD, financial_currency: INR}` gives `currency: "INR"`.
    A raising fundamentals call gives `currency: null` plus the note, and the statement is still ok.
- **Not fixed (model capability, as in round 1).** The ADR-ratio half. No product source carries an
  ADR ratio, and copilot.json rule 2 already forbids inventing figures.
- **Why opus.** This class has now escaped twice at the model-facing boundary. The writer must also
  confirm that no other tool in `agent_tools` hands the model statement-size money without its
  currency (the earnings estimate is the known exception, filed as rc1-fix-r2-triage:1).

## W2 leaked-call-tail (opus): rc1-drive-onboarding-stranger:1

Files: `sidecar/services/llm/tool_call_rescue.py`, `sidecar/services/llm/ollama.py`,
`sidecar/services/llm/openai.py`, `sidecar/tests/test_tool_call_rescue.py`,
`sidecar/tests/test_llm_ollama.py`, `sidecar/tests/test_llm_openai.py`.

- **Mechanism (confirmed by code read).** ollama.py:221-227 yields every content delta while it
  streams, and only then runs `rescue_leaked_tool_call` at stream end (:257-264). openai.py has
  the same shape (:735-770, for the gated `_CONTENT_LEAK_PROVIDERS`). So when a leaked call is
  rescued, the user has already seen the call text and the model's hand-typed "result" that
  follows it. In the original finding, that was "current_price 164.4 … As per the live data,
  Zomato's stock price is currently ₹164.4". The same text also enters the history, where the next
  round reads it.
- **Fix.** Add `leak_start(text, offered) -> int | None` to tool_call_rescue.py. It returns the
  index of the first `{"name": "<offered>"` or `<offered>(` marker, taken from the start of that
  marker's line, and from a preceding ```` ``` ```` fence line if there is one. Only names offered
  this round count.
  In both adapters, once a marker is found (on the text joined so far), stop yielding content
  deltas from `max(leak_start, already_streamed)`. At end of stream there are two cases. If the
  rescue fires, drop the held text and yield the tool_use. Otherwise, yield the held text as one
  delta, so no text is ever lost. Thinking events are unaffected.
- **Tests.**
  - The Zomato round (Ollama): no yielded delta contains `164.4`, and exactly one
    `price_data {"symbol": "ZOMATO.NS"}` tool_use follows.
  - A case the fix was not written against: an openai-adapter gated provider (deepseek or
    openrouter) leaking a JSON call followed by a fake result, with the same outcome.
  - Prose that mentions a non-offered call, or no call, streams byte-identical text.
  - `test_leaked_text_tool_call_is_rescued` asserts the old visible-leak kinds
    `["delta","delta","tool_use","done"]`. Update it to the new behaviour (the leaked call text is
    not shown), and log why in the commit. `test_leaked_json_for_a_tool_not_offered_stays_text`
    must pass unchanged.
- **Not fixed (model capability).** In recheck run 6 and in the Tata Motors variant, the model
  invented a price in prose without writing any call, so there is nothing to rescue. The session
  preamble ("you MUST call a tool … do not invent specifics") and the copilot grounding rule
  already exist, and 5 of 6 runs were honest. Recorded as an issue, not fixed.
- **Why opus.** This changes the streaming path of every hosted content-leak lane and Ollama. A
  hold that never flushes would lose the user's answer.

## W3 overlay-cache (sonnet): rc1-battery-4:1 (repeat-run half)

Files: `sidecar/services/exchange_financials.py`, `sidecar/tests/test_b7_exchange_financials.py`.

- **Mechanism (profiled, `evidence/battery4-leg-profile.jsonl`).** For an uncached Indian name,
  the `fundamentals` leg takes about 10.7 s even in a warm process. openbb takes 0.8 s and yfinance
  2.3 s. Then `apply_exchange_financials` takes 7.0 s: the NSE filings list plus 5 XBRL
  archives, each paced at about 1 req/s. In a warm process, `snapshot_structured` returned price ok
  and fundamentals "timed out after 6s — dropped" (SBIN).
  `get_filed_periods` (exchange_financials.py:361-377) writes `_cache` only in the coroutine after
  `await asyncio.to_thread(_fetch, key)`. When the 6 s box cancels the leg, the worker thread still
  finishes, but its result is discarded. The next call then repeats the whole paced fetch (a
  re-fetch after the dropped leg took 18.9 s: `evidence/battery4-redo-probe.json`). So every FAST
  brief for that name drops fundamentals again.
- **Fix.** Store a successful result inside the worker: `to_thread` runs a small function that
  calls `_fetch` and writes `_cache`. A cancelled caller's fetch then still lands. The TTL and the
  never-raises contract stay unchanged.
- **Test.** Stub `_fetch` to block on a `threading.Event`. `asyncio.wait_for(get_filed_periods
  ("X.NS"), 0.05)` times out. Release the event and join the worker. The next
  `get_filed_periods("X.NS")` returns the stubbed periods, and `_fetch` was called exactly once.
- **Deferred: the first-brief half** (DECISIONS_FOR_OPERATOR §4.1). Six paced requests cannot fit
  FR-070's 6 s core-leg box. The fix is either a larger FAST budget or serving values before the
  overlay with a flag. Both are product and spec calls.

## Issues outside the entries (not in any diff)

- **rc1-fix-r2-triage:1 (new finding).** The earnings estimate labels WIT's INR-sized revenue
  estimate (244,246,846,490) as USD (earnings_provider.py sets `currency` from the trading
  currency; EpsEstimateGrid.tsx:111 formats it in that currency). This is the same class on a
  data model, its `types/` mirror, and a panel. It goes to the next round.
- **nse_provider `_lock` is held across `session.get`.** A stalled quote-equity request (15.4 s
  in the redo probe) therefore blocks every other nse_direct caller. `get_archive_text` (:747-749)
  and `_SessionHolder.ensure` (:261) also pace inside `_lock` (noted in round 1, still open).
- **The prose-only price fabrication by llama3.1:8b** (W2 note), and **the SIFY ADR-ratio
  fabrication** (W1 note). Both are model-capability limits.
