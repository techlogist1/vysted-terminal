# R15 Stage C: batch 17 verdicts (fresh-context verifier, Opus)

Merge target: `worktree-agent-batch-17-int@a340ad7b34dcec85f347c64813e6a135af9903ae`. The branch holds W1 commits 4b6acb6b
(LEAD-030) and ede02247 (LEAD-031) on base 5d4ca99c.

**Verdict: approve.** One entry is certified (R15-LEAD-031). R15-LEAD-030 is not certified, because its "no true citation
is replaced" claim fails on a fresh case. That case fails identically on base, so it is not a regression. On every probe,
the branch is strictly better than base: 9 of the offline probes fail on base, and only 2 fail here, both pre-existing
(`probe2-base.out` compared with `probe2.out` and `probe3.out`). There is no GUI-only surface, and no frontend file changed.

## Chain

- The integrator's `pnpm ci-local` exited 0, with pytest reporting 3294 passed and 1 skipped (`b17int-logs/ci1.log`). The
  smoke test exited 0 (`smoke.log`).
- The verifier re-ran the focused files (test_agent_runtime, test_tool_call_rescue, test_llm_ollama, test_llm_openai) in
  the scratch worktree: 240 passed.
- A sidecar was booted from source for the scratch worktree on 127.0.0.1:52310. It used a copied ISO data dir, MCP on
  :52153 and :52154, and llama3.1:8b through ollama with autonomy ask. `/quotes/SIFY` returned 13.41 USD, which is the
  ground truth for price-fabrication checks.

## R15-LEAD-030: not certified

What holds:
- **Live original prompt, 3 runs** ("What is SIFY's TTM revenue in USD? Cite the tool you got it from.";
  `lead030-{1,2,3}`). No fabricated citation or dump streamed in any of them. In run 2, `financial_statements` errored on
  `'ttm'`. The model then fabricated "According to price_data, Sify Technologies Ltd.'s TTM revenue is ₹ 8.2 billion."
  (price_data was never called). The guard caught it live (`sidecar-guard-lines.log`), and the stream carried "The
  price_data tool returned no data for this in this turn." None of the 3 runs sent a `{"name` fragment.
- **Live two-turn follow-up, with history sent as `historyForSend` sends it, trailer included**
  (`followup-aapl-history.json`, `followup-notool-{1,2}`). Turn 2 made no tool call. "The tool that gave me the market cap
  figure was `fundamentals`. It returned a value of $4.90T …" streamed untouched in both runs, as did the bulleted
  "`fundamentals` … Returned value: `market_cap`: $4.90T". (In `followup-aapl`, `-aapl-2` and `-msft`, the model re-called
  the tool in turn 2, and the true citations streamed.)
- **Offline relay through the full `invoke_agent` with a scripted provider** (`b17v_probe.py`, output in `probe.out`,
  13/13 pass). Every case below is fresh, meaning the writer's tests do not use it:
  - The title-case same-line dump "Earnings History: {… "$0.42"}" is replaced, and no dump streams.
  - The next-line dump "The Analyst History output:\n{\n "target": "$25.00"…" is replaced, the dump is dropped, and
    "Consensus is buy." is kept.
  - The hyphenated "Per price-data results, the close was $2.11." (price_data errored) is replaced.
  - The array dump "Corporate Actions = [\n …]" is replaced, and the prose after it is kept.
  - The true humanised "Financial Statements returned revenue of ₹4,411 cr." is kept, and so is the true backtick dump
    "`price_data` returned:\n{…13.41}".
  - Pre-call "I'm about to check the earnings history data for SIFY." is kept. So is "Next I'll pull the financial
    statements data …", which comes after another tool returned ok.
  - "Let me check: `news` data shows revenue of $5 bn." is replaced.
  - A history seeded by the fixed label "Reading your portfolio" keeps a get_portfolio citation, and a seed of "Using
    resolve symbol; Using price data" keeps "The Price Data tool returned …".
  - A history seeded only with financial_statements still gets "The price_data tool … $2.11" replaced with the "in this
    turn" wording.
  - "I don't have price data for SIFY yet …" is kept.
  - "According to the fundamentals tool, TTM revenue is $1320 m." is replaced (probe3).
  - Base 5d4ca99c fails 7 of these cases (`probe2-base.out`).

What fails (the reason it is not certified):
1. **A true citation is replaced (over-replacement), fresh case, in the entry's own scenario.** fundamentals errors and
   financial_statements returns ok. The model writes "The fundamentals tool returned an error, so I used financial
   statements, which shows revenue of ₹4,411 cr." The streamed text is "The fundamentals tool returned no data for this
   in this turn.", so the user loses the correct, ok-sourced figure (`probe2.out` `err-mention-plus-true-figure`). The
   guard replaces any sentence that names an untraced tool next to a cue word or figure. It does not check whether the
   value is attributed to that tool. The same fact written as two sentences ("…returned an error. Financial statements
   show ₹4,411 cr.") is kept. Base behaves the same, so this is pre-existing, but it fails the claim to certify ("no true
   citation is replaced").
2. **A camel-cased humanised name escapes (minor).** "PriceData returned a close of $2.11." streams when price_data was
   never called (`probe3.out` `fab-camelcase`). The fix handles humanised names with spaces or hyphens, but not
   concatenated ones.

Fix shape for next time: replace a sentence only when a figure or dump is attributed to the untraced tool, for example
when the untraced reference is the subject of the result verb. When an ok tool is also named, keep the sentence, or
replace only the clause about the untraced tool. Let `[\s_-]?` stand between the parts of a humanised id so that camel
case also matches.

## R15-LEAD-031: certified

The claim is that a guard's replacement no longer splices onto a leaked text-form tool-call fragment. That splice needs a
partial marker to reach the client, and none now does.
- **orig-2's shape, re-driven through the real `OllamaProvider` with a fake client** (`b17v_031.py`,
  `lead031-adapter.out`). The chunks were `…'.\n\n', '{"', 'name', '":', ' "', 'fund', 'amentals', '", "parameters"…'`.
  The deltas stop at `'.\n\n'`, and the call is rescued as `fundamentals {"symbol": "SIFY"}`. On base, the same input
  streamed `{" name ": " fund amentals` (`lead031-adapter-base.out`).
- **Fresh cases:**
  - JSON with no spaces and a split `{`, `"na`, `me":"`, `pri`, `ce_d…`: nothing shows after "Checking.\n". Base leaked it.
  - Call syntax `price`, `_da`, `ta(symbol=…)`: nothing of `price` shows. Base leaked it.
  - An abandoned prefix (`'The ', 'price', ' moved; ', '{"', 'note', '": 1}'`): replayed chunk for chunk with nothing
    lost.
  - LeakHold direct (`probe.out` `031/*`): the unoffered `screener_run` JSON is replayed as the same chunks, and the benign
    "The pri|ce is up." is replayed whole.
- **Live:** none of the 3 lead030 runs or the 8 follow-up turns streamed a `{"name` fragment.

## Not-a-defect / out-of-scope proposals

None were proposed this batch.

## Issues observed (outside the entries, not acted on)

- `followup-aapl-2-t2`: llama3.1:8b echoed the client's history trailer "[tool steps: Using fundamentals]" into its own
  answer text. The trailer format is visible to the model and can leak into prose.
- During the MSFT run, the sidecar log showed a sweep of fundamentals calls for `*-SM.NS` symbols (INSPIRE-SM.NS,
  IPHL-SM.NS, ISHAN-SM.NS) that failed the correctness gate. This looks like background warming, not the agent. It was
  not investigated.
