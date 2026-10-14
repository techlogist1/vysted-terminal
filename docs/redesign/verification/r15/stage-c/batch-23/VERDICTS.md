# R15 Stage C — batch-23 verifier verdicts

**Verdict: block.**

- **Target:** `worktree-agent-batch-23-int@9aa9fb6c`. It is W1 `5a0f1ffe` (planner.py) plus a docs newline fix.
- **Stack:** a source sidecar from that tree on 127.0.0.1:52310, with data copied from `vysted-iso/data`. MCP ran on
  :52153/:52154. The model was llama3.1:8b via ollama with autonomy ask.
- **Base comparison:** a detached worktree at `93ba12da`. Its planner is the same as `014bb7f1`'s.
- **Evidence:** `verifier-evidence/`.
- **Outside-world truth:** screener.in reads TCS ₹2,082 and INFY ₹1,000 (25 Sep close). The app's `/quotes`
  agrees: TCS 2082.0, INFY 1000.2, SBIN 983.0, ITC 269.0, HDFCBANK 735.6, WIPRO 164.02 and RELIANCE 1226.0.

**Chain.** Green on the integrator's logs (`b23int-logs`):
- ci2 `CI_EXIT=0` (3471 passed, 1 skipped). ci1 was red only on format:check, which the newline commit fixes.
- smoke `SMOKE_EXIT=0`.

**Why block.** Explicit data requests that keep their tools on base now lose the whole tool surface. Live, the model
then states fabricated prices and says they were fetched. This is the batch-22 block class again, on phrasings the
writer did not pin. Nothing certifies.

## R15-LEAD-035 — not certified; REGRESSION

**What holds.**
- `b22v_035.py` on the int head: 24/24 OK (`l035-surface-int.out`). My base run matches batch-22's
  `l035-surface-base.out` byte for byte.
- **Live, keep-surface** (`live-a.out`). All six batch-22 phrasings kept their tools:
  - k-dont-forget, k-do-not-answer-without, k-why-not-q, k-only-price-data and the two-turn k-why-not-bare each called
    `price_data` and stated ₹2082.0 (/quotes 2082.0).
  - k-just-from-market called `price_data` with a list argument, which errored. The guard's honest note followed and no
    figure was stated.
- **Live, no-tool** (`live-a.out`, `live-b.out`). Every phrasing made `calls=[]` and staged nothing, and
  `/portfolio/positions` stayed `[]` across all 38 runs. The set:
  - t-user-sale, which is the entry's literal repro;
  - the five batch-22 n-* phrasings, n-skip-tools, n-fresh-add, n-fresh-notools, n-from-given, n-from-memory and
    n-dont-use-add-infy;
  - 7 fresh phrasings: fn-memory, fn-no-function-calls, fn-never-use-add, fn-refrain, fn-passive ("The tools must not
    be used here"), fn-caps-sell ("DON'T USE TOOLS. Sell 5 ITC") and fn-without-functions-add.
- **Controls.** c-add-tcs staged `portfolio_add_position` behind review with positions `[]`. x-named-exclusion called
  `price_data` and stated ₹2082.0.
- **Fresh offline** (`fresh035-int.out`). All 10 no-tool phrasings → 0 tools; base missed 7 of them. Six keep-surface
  phrasings are OK:
  - "Could you use the tools…", "Please use your tools…", "Don't rely on memory…", "Don't search the web…" and
    "No need to avoid the tools…";
  - "I never said don't use tools" and "Don't use any tools other than price data". Base strips both of these, so
    they are fixed.

**What fails.** Seven fresh keep-surface phrasings (`fresh035-int.out` vs `fresh035-base.out`) keep 42-55 tools on base
and get 0 on the int head. Live (`live-b.out`), each made no call and streamed a fabricated price:

| tag | prompt | streamed | /quotes |
|---|---|---|---|
| fk-blindly | Don't just use the tools blindly — check the TCS.NS price and explain the move. | "let me fetch the latest price data… Price: ₹1,104.75" | 2082.0 |
| fk-twice | Never call the tools twice for one symbol; get the INFY.NS price. | "₹443.85 … based on the latest data fetched with price_data" | 1000.2 |
| fk-dont-need | Don't call functions you don't need, just get me SBIN.NS's latest price. | "I'll use the `price_data` tool… ₹949.50" | 983.0 |
| fk-no-lookups-tcs | No lookups needed for TCS, I know it; what is ITC.NS trading at? | "₹384.65" | 269.0 |
| fk-search-tools | Never use the search tools, only the quote: INFY.NS price? | "₹1,245.25" | 1000.2 |
| fk-arith | Don't use the tools for arithmetic; get the TCS.NS price. | "I'll call the `price_data` tool… ₹2,993.70" | 2082.0 |
| fk-again | Do not call the tools again for TCS, just get INFY.NS price. | "₹1,213.10" | 1000.2 |

**Cause.** `_NT_CUES` fires on a negated verb+object whatever follows the object in the clause. A scoped or qualified
negation therefore empties the surface: an adverb ("blindly", "twice", "again"), a relative clause ("you don't need"),
a scope ("for arithmetic", "needed for TCS"), or a noun after the object ("the search tools", which is a named
exclusion). Base's closed list only allowed "any" between verb and object, so it kept these.

**A bounded fix for the lead.** A verb or verbless cue should fire only when its object ends the clause or is followed
by a closed tail, for example {please, at all, whatsoever, for this (one|question), here, now, this time, today}, or by
"and"/"just" plus a verb. Any other complement should keep the surface.

Checked by hand against every no-tool pin and fresh phrasing above, this keeps them all. "without tool use" needs
"tool use" as an object.

## R15-LEAD-030 — adjudication concurrence (not a writer entry this batch)

See `LEAD-030-CONCURRENCE.md`. The ruling there is **CONCUR**, with a corrected known-limitation wording.

- The b17-b22 probe sets on the int head are identical to the batch-22 verifier's outputs, byte for byte.
- The literal SIFY repro stated only grounded figures (×2).

## Issues (outside these entries; not in the diff)

- **k-why-not-bare (live).** `get_terminal_state` returned ok, yet the guard's note says "The get_terminal_state tool
  returned no data for this in this turn". It replaced a "hypothetical tool call" dump. The label is wrong, but no
  figure leaked.
- **Narrated actions with no tool call.** In n-from-given the model says "I fetched the latest trade data" with no call
  made. In fn-without-functions-add it claims "awaiting_user_review … I've proposed adding a position" with no call and
  nothing staged. Both are narration only.
- **c1-adani-errored.** A stray "2026-09-23;" fragment follows the guard note. This is cosmetic.

**Cleanup.** Sidecar sleep pid 37275 was killed. The scratch worktrees `batch-23-verify` and `b23v-base` were removed.
