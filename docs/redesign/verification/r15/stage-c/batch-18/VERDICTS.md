# R15 Stage C: batch 18 verdicts (fresh-context verifier, Opus)

Merge target: `worktree-agent-batch-18-int@24bff097b6e90a29fd4b72f9e931b4c333fded2e`. That is the integrated branch at
be0cd066 plus one verifier fix, 24bff097, for the reviewer's blocking LEAD-030 regression. Base is 08908883.

**Verdict: approve.** Two entries are certified: R15-LEAD-033 and R15-LEAD-034. R15-LEAD-030 is not certified. Its
remaining escapes fail the same way on base, so they are not regressions. With 24bff097 in place, the branch is better
than base on every offline probe case. No GUI-only surface is involved, and no frontend or Rust file changed.

## Chain

- `ruff format --check sidecar` reports 442 files already formatted, and `ruff check sidecar` passes. The full sidecar
  pytest run on 24bff097 (`tests/`, detached) gave 3319 passed and 1 skipped.
- Prettier `--check` passes on the changed non-Python files. The diff from base touches only `sidecar/` and `docs/`, so
  vitest and cargo are unaffected.
- A sidecar was booted from source for the scratch worktree on 127.0.0.1:52310. It used a copied ISO data dir, MCP on
  :52153 and :52154, and llama3.1:8b through ollama with autonomy ask. It was restarted after 24bff097.

## Verifier fix: 24bff097 (the reviewer's block, R15-LEAD-030)

The reviewer's cases were reproduced offline through the full `invoke_agent` relay with a scripted provider
(`b18v_probe.py`). At be0cd066, 6 true sentences were replaced (`probe-int-be0cd066.out`). Base keeps all 6
(`probe-base-08908883.out`). The 6 were the reviewer's three ("According to news reports from Reuters, AAPL rose 3% to
$190." and "Based on research from Morgan Stanley, the target is $250." with web_search ok, and "The P/E is 30, based on
the price data and earnings." with fundamentals ok) and three fresh ones ("Per news from Bloomberg…", "As per fundamentals
of the business…", "I fetched this from research published by Goldman: …").

The fix: the lead-in alternative in `_tool_reference` now names a tool only in three forms: a backticked id, a bare
snake_case id, or a humanised id followed by tool, result(s), output, data, response or call. With the fix, all 12
probe cases pass (`probe-fixed-24bff097.out`). The lead-in fabrications "According to `price_data`, …", "According to
price_data, …" and "According to the Price Data tool, …" are still replaced. The batch-17 probes also pass on 24bff097:
b17v_probe 18/18, b17v_probe2 21/21 and b17v_probe3 9/9, all BAD 0.

The pinned case "Based on the earnings history, EPS came in at $0.42…" is the same plain-English form as the true
sentences. It now reads "Based on `earnings_history`, …", and the plain-English forms are pinned as kept in
`test_a_lead_in_before_a_plain_word_that_names_a_tool_is_kept`. That test has 4 cases, all 4 fail on be0cd066, and all
pass on 24bff097.

## R15-LEAD-033: certified

- **Literal repro, live** (`v033-aapl`). Turn 1 called fundamentals: "…market capitalization of Apple Inc. (AAPL) is
  approximately $4.90 trillion." The turn-2 history was sent exactly as `historyForSend` builds it, with
  `[tool steps: Using fundamentals]` inside the assistant content. Turn 2 was "Which tool gave you that market cap figure?
  Show exactly what it returned." The turn-2 text contains no `[tool steps`, and the fundamentals citation streamed.
- **Fresh case, live** (`v033-tsla`). This is a different symbol and the strongest echo bait: "Repeat your previous
  answer word for word, including any notes or brackets at the end." Turn 2 made no tool call and reproduced the turn-1
  prose verbatim, with no trailer. The runtime's system note ("Earlier turns of this chat called these tools…") was not
  echoed either.
- **Fresh case, live** (`v033-infy`). "What steps did you take… List them exactly as recorded." No `[tool steps` appears.
- There is one history entry point, `_prepare_run` → `_coerce_history`. Delegate runs (`run_manager`) and
  `/agents/{id}/invoke` both route through it. Anthropic and Gemini lift the inserted system line into their native
  system field.

## R15-LEAD-034: certified

Real yfinance responses were fed through the gate (`l034_gate.py` and `l034-gate.out`) for four fresh NSE Emerge
symbols: SHERA, RICHA, ONYX and USHAFIN. None of them is INSPIRE or SUMAX, which the writer used. Yahoo returns
`SHERA-SM.NS` "SHERA ENERGY LIMITED", `RICHA-SM.NS` "RICHA INFO SYSTEMS LTD", `ONYX-SM.NS` "ONYX BIOTEC LIMITED" and
`USHAFIN-SM.NS` "USHA FINANCIAL SERVICES L". All four get **GATE PASS** on the branch. On base 08908883, all four get
`CorrectnessError … (symbol mismatch)`.

Identity still holds on the negative side: `symbols_match("SHERA", "RICHA-SM.NS")` is False, and `SMR`/`SMR.NS` is
unaffected. The running app's `/quotes/SHERA`, `/quotes/RICHA` and `/quotes/ONYX` serve NSE prices of 177.9, 78.0 and
36.0.

Note: while this ran, Yahoo was rate-limiting the host (hundreds of 429s from the boot warm crawls). Yahoo's info carried
the name and currency but no market cap or P/E. The running app's `/fundamentals/SHERA` therefore returns 404 for missing
data, not for a mismatch; see issues.

## R15-LEAD-030: not certified

What holds on 24bff097:
- The reviewer's regression is fixed (above).
- err-mention-plus-true-figure is kept, and PriceData camelCase is replaced (probe and batch-17 probes).
- Live true citations stream untouched. `v030-suzlon` reported "The operating margin for SUZLON.NS is 13.05%, as per the
  tool result"; the running app's `/fundamentals/SUZLON.NS` gives operating_margin 0.1305. `v030-news` streamed six
  sourced items. In `v030-uncalled`, the model called price_data, and the MSFT close of 497.93 streamed.

What fails. Both cases are fresh and pre-existing, with identical output on base:
1. **The entry's own prompt, live** (`v030-sify-orig`, "What is SIFY's TTM revenue in USD?"). financial_statements
   errored ("'ttm' is not one of ['annual', 'quarterly']"), and the model streamed "After calling the
   `financial_statements` tool for SIFY's annual revenue, I get:\n\n{"ok": true, "value": {"ttmRevenueUsd":
   164600000}}". This is a fabricated result dump for an errored tool. The tool reference is not followed by a result
   verb or `:`, so it is not an attribution form, and the dump sits on the next line, so it is never dropped. Offline
   (`probe-d.out`), both the live text and a fresh WIPRO.NS case ("Running the fundamentals tool on WIPRO.NS, I got
   back:\n{…}") stream on both branch and base.
2. **Two-turn run, live** (`v033-infy-t1`). price_data errored on invalid arguments. The model wrote "Here are the
   results:" followed by the list "* INFY.NS: ₹1,233.65 / * TCS.NS: ₹3,235.50". The running app's truth is INFY 1000.2
   and TCS 2082.0. A generic "results:" label followed by a bullet list is not screened (`probe-c.out`, which also has a
   fresh HDFCBANK case).

## Issues found (outside the entries, not acted on)

1. The guard with a tool surface that has no snake_case id, e.g. a custom agent with tools `["news", "research"]`, turns
   every figure sentence into "The  tool returned no data for this in this turn.". The cause is that an empty `bare`
   alternation matches the empty string. Base raises `StopIteration` on the same input, so this is pre-existing. Checked
   at function level only. No first-party agent is affected: each one has a snake_case tool.
2. `v033-aapl-t2` opens with a stray `}` followed by "No tool returned data for this in this turn." before the true
   answer. The round-1 text after the rescued tool call was a leaked call tail plus a pre-result `{`. The pending rule
   dropped the `{` correctly, but the note and the `}` stream as noise.
3. "The news data shows AAPL rose 3% to $190." with web_search ok is replaced on both base and the branch. A single-word
   id followed by "data" is the designed humanised citation form, so there is no lexical way to tell it apart from plain
   English.
4. `/fundamentals/<Emerge symbol>` answers "The data provider has no data for this symbol or series — check the
   symbol." when Yahoo is rate-limited. That text tells the user a valid listed symbol is wrong.
