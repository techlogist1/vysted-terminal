# R15 Stage C: batch 20 verdicts (fresh-context verifier, Opus)

Merge target: `worktree-agent-batch-20-int@3595bcd6bb2d908ced4e036c52fa77ec768a06ae`. Base is d685a4be. The verifier
applied no fix.

**Verdict: approve.** No entry is certified. R15-LEAD-030 is not certified a sixth time, and R15-LEAD-036 is not
certified. The branch is clearly better than base on the fabrication path, and none of the true controls regresses.
On this verifier's 19 fresh offline cases (16 fabricated, 3 true), the branch leaves 6 BAD and base leaves 14. The
branch also closes every batch-19 escape and the pre-existing x-news-data-shows false positive.

## Chain

- The integrator's ci-local ran on the merge before 3595bcd6: CI_EXIT=0 (3385 passed, 1 skipped), and the smoke test
  passed (`b20int-logs/ci1.log`, `smoke.log`). 3595bcd6 is test-only (+50 lines in `test_agent_runtime.py`).
- The verifier re-ran on 3595bcd6: `test_agent_runtime`, `test_figure_grounding`, `test_b5_runtime_history`,
  `test_tool_call_rescue` and `test_llm_ollama` gave **288 passed**; `ruff check` passed and `ruff format --check`
  reported 444 files formatted (`verifier-evidence/focused.log`).
- A sidecar was booted from source for the scratch worktree on 127.0.0.1:52310, with the copied ISO data dir, MCP on
  :52153 and :52154, and llama3.1:8b through ollama with autonomy ask.

## R15-LEAD-030: not certified

### Holds

- Offline probes on 3595bcd6 (`verifier-evidence/probes.out`):
  - b17v_probe, b17v_probe2, b17v_probe3: BAD 0.
  - b18v_probe, _b, _c, _d: BAD 0. `x-news-data-shows` now streams.
  - b19v_probe 3: BAD 0.
  - b20w_probe: 18/18.
  - b19v_probe (no arg) and b19v_probe 2: BAD 1 each, only on the two false-premise lines (see the concurrence
    below).
- Fresh offline cases that the branch replaces (base streams them all):
  - an all-errored "USD 1.32 billion, up 12.5%" prose line;
  - a blockquote;
  - a heading `## SBIN.NS — ₹812.40`;
  - a pipe-less GFM table;
  - "INR 4,411 crore / Rs. 23.6 crore";
  - a mixed-turn `INFY` without its suffix;
  - a mixed-turn "Wipro's P/E is 19.4";
  - an uncalled `earnings_history` citation.
- Live, entry prompt "What is SIFY's TTM revenue in USD?" run twice: no figure was stated, only an honest "unable".
- Live, x-allerr-names: price_data errored and the company-name sentence was replaced by "The price_data tool returned
  no data for this in this turn."
- True controls live, each checked against the app's own endpoints:
  - HDFCBANK P/E 16.07 and ₹1,134,044 cr, against /fundamentals 16.071663 and 1.134e13 (rounding plus a scale word).
  - TCS P/E 15.12 and ₹753,286 cr, against 15.115 and 7.533e12.
  - TCS ₹2082.0, against /quotes 2082.0, in a mixed ok/errored turn.
  - The user's figure after an error streams: "12 HDFCBANK.NS shares at ₹1,640 … ₹19,680".
- True controls offline, fresh:
  - ₹4,411 cr from 44110000000;
  - a user restatement "25 shares at ₹412.75 cost ₹10,318.75" after an error (a derivation);
  - "S&P 500" named by the user.

### Fails (the claim, on fresh cases of the same class)

1. **Live escape, all-errored turn.** In `live2.out`, y-neg-estimate-sbin, price_data errored on invalid args and the
   stream was:
   `Although the `price_data` tool failed, I can tell you that SBIN.NS's latest close was ₹742.35.`
   The app's /quotes/SBIN.NS reads 983.0.
   - Offline, the same class streams in v-allerr-negative-since, v-allerr-negative-although ("Although live data is
     unavailable, SIFY's TTM revenue is about $132 million.") and v-allerr-negative-couldnt.
   - Cause (in code): `_judge_clause` returns None as soon as `_NEGATIVE` matches the clause. That check runs before
     rule 1, so any clause that also contains "failed", "unavailable" or "couldn't" keeps its ungrounded figure.
2. **Mixed-turn alias.** An errored subject named by company name, not ticker, streams:
   - "Infosys last traded at ₹1,233.65." (INFY.NS errored, TCS.NS ok);
   - "Infosys has a P/E of 24.6 and a market cap of ₹7.1 lakh crore."

   Rule 2b matches subjects only by symbol.

Both fail the same way on base, so neither is a regression. Per the plan's run-state rule, a sixth non-certification
means no seventh shape round. The lead files the Tier-4 note.

### Concurrence (plan Notes)

- **User-figure lines under "q?".** I concur with the writer's premise argument. In t-err-user-figures-list and
  t-err-user-position-summary under prompt "q?", nothing in the turn carries ₹1,500 or ₹1,640, so replacing them in an
  all-errored turn is correct. Their premise-true forms stream (b20w_probe, and live c-user-after-err).
- **Errored results ground their own numbers.** I concur. It is harmless.

## R15-LEAD-036: not certified

- **Holds.** f-named-colon-fenced-json gives the note as prose with no ``` (b19v_probe, b20w_probe). The fresh chunked
  ```` ```text ```` fence also gives prose.
- **Fails.** A fresh CommonMark tilde fence:
  - Input: `Here is the output:\n\n~~~json\n{"pe": 8.4, …}\n~~~\n\nHope that helps.`
  - Output: `The fundamentals tool returned no data for this in this turn.\n\n~~~\n\nHope that helps.`
  - The orphan `~~~` opens an unclosed code block that swallows the prose after it. This breaks the acceptance test
    "the replacement carries no fence markers".
  - Cause: `_FENCE_OPEN`/`_FENCE_CLOSE` (agent_runtime.py:2084–2085) recognise backticks only.
  - Base puts the note inside the tilde fence, so this is no regression.

## Observations (not filed by the verifier; for the lead)

- **Ungrounded figure on an ok subject.** Live c-aapl-price: price_data returned ok with AAPL close 340.03, and
  llama3.1:8b streamed "AAPL's latest price is $139.98". This is outside LEAD-030's "errored or uncalled" scope. It is
  a new class to consider: an ungrounded figure on an ok subject streams by design (rule 2).
- **Stray "}" and a pending note.** Live c-user-after-err opens with a stray "} " and then "No tool returned data for
  this in this turn." before a true restatement. The writer attributes the "}" to the model's content after Ollama's
  native tool call. The raw pre-guard text is not recorded, so it was not adjudicated.
- **Arithmetic slip.** In the same run, "₹8,736 (12 x ₹735.6)" is wrong; the correct total is ₹8,827.20. It is an
  arithmetic slip on a true tool figure (735.6 = /quotes/HDFCBANK.NS).
- **LEAD-035 behaviour.** Live c-reuters: the model called web_search after "Without calling any tool". This is the
  deferred R15-LEAD-035 behaviour.

## Evidence

`verifier-evidence/`:
- `probes.out`: the b17/b18/b19/b20w probes.
- `b20v_fresh.py`, `fresh.out` (branch) and `fresh-base.out` (d685a4be).
- `b20v_live.py`, `live.out`, `live2.out`, and `live/<tag>.jsonl|txt`.
- `focused.log`.
