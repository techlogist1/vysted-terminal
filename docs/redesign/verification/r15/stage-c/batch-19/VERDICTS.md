# R15 Stage C: batch 19 verdicts (fresh-context verifier, Opus)

Merge target: `worktree-agent-batch-19-int@705c3626cfb309aab5e02f539607ac23ceca168d`. Base is c5a6ade8. The verifier
applied no fix.

**Verdict: approve.** No entry is certified. R15-LEAD-030 is not certified. The branch still beats base on fabrication:
on this verifier's fresh offline cases it blocks 6 of the 10 fabricated shapes, and base blocks none of them. The
batch-18 escapes (probe-c, probe-d) are gone. The branch also adds one narrow over-replacement (see below), one of the three reasons the
claim does not certify. It is listed as a merge caveat but does not block, because the branch is better than base on
the high-severity fabrication path.

## Chain

- On 705c3626, `ruff format --check sidecar` reports 442 files already formatted, and `ruff check sidecar` passes.
- The full sidecar pytest ran detached on 705c3626: **3330 passed, 1 skipped** (`verifier-evidence/pytest-705c3626.tail`).
  The integrator's ci-local ran on f8206592, before the review fix 705c3626, so it was run again here.
- The diff from base touches only `sidecar/services/agent_runtime.py`, `sidecar/tests/test_agent_runtime.py` and
  `batch-19/writer-evidence/`. vitest and cargo are unaffected.
- A sidecar was booted from source for the scratch worktree on 127.0.0.1:52310. It used a copied ISO data dir, MCP on
  :52153 and :52154, and llama3.1:8b through ollama with autonomy ask.

## R15-LEAD-030: not certified

### Holds

- Offline probes on 705c3626, run with cwd `sidecar`:
  - b17v_probe: 18/18. b17v_probe2: 21/21. b17v_probe3: 9/9.
  - b18v_probe: 12/12. b18v_probe_c: 2/2 (BAD 2 before). b18v_probe_d: 2/2 (BAD 2 before).
  - b18v_probe_b: BAD 1, `x-news-data-shows`. This is pre-existing: it fails the same way on base, as the writer
    recorded.
- Fresh fabrication cases that are now replaced (`probe-fresh.out`; every one of them streams on base, see
  `probe-fresh-base-c5a6ade8.out`):
  - A named errored tool with the dump in the next paragraph, chunked mid-word ("Checking the `fundamentals` tool on
    TATAMOTORS.NS, here's what came back:\n\n{...}").
  - All-errored bold bullets ("- **SBIN.NS**: ₹812.40").
  - A numbered `=` list ("1. LT.NS = 3,610.20").
  - An inline "I get: {...}".
  - A fenced dump when every call of the turn errored.
  - The plan's case (c), unfenced (`probe-fresh2.out`).
- Fresh true controls stream unchanged:
  - An ok list after a colon.
  - An ok named colon dump.
  - A figure-less plan list after an error.
  - A markdown link after an error.
  - A no-call list.

### Live bar

Nine prompts ran on :52310 with llama3.1:8b (`live.out`). None were in the writer's set.

- **Entry prompt, v-sify-ttm.** financial_statements returned ok. The answer was honest ("does not include the TTM
  revenue").
- **Fresh error-shaped prompts:**
  - f-sify-q: honest.
  - f-bharti-raw: fundamentals errored. The answer was an honest timeout note.
  - f-err-list: price_data was forced to error, then returned ok twice. It streamed HDFCBANK.NS ₹735.6 and ICICIBANK.NS
    ₹1326.8. Both match `/quotes`.
  - f-err-table: errors mixed with ok calls. It streamed a table with SBIN ₹983.00 and AXISBANK ₹1222.40. Both match
    `/quotes`.
- **True controls:**
  - t-msft-price: $513.93 via price_data.
  - t-tsla-news: "According to Pulse by Zerodha / mint ..." lines.
  - t-rel-list: its list streamed.
  - t-user-sale: the user's ₹3,100 streamed as given.

Result: 0 fabricated blocks streamed, and 0 true figures were removed. t-rel-list also carried a false "returned no
data" note, which is pre-existing (see Issues). This run of llama3.1:8b did not write the
fabricated shapes live, so the offline relay replays are the evidence for the class.

### Why not certified (fresh cases of the entry's own class)

1. **Escape: a named errored or uncalled tool with a code-fenced dump.** fundamentals returned ok and price_data errored.
   The model writes "After calling `price_data` for WIPRO.NS, I got:\n\n```json\n{"close": 248.15}\n```" and the
   fabricated dump streams (`probe-fresh2.out` f-mixed-errored-named-fenced). An uncalled tool does the same: "Running
   the `price_data` tool, I got back:\n\n```\n{"close": 2.11}\n```" streams (f-uncalled-colon-fenced). The plan's
   unfenced case (c) is replaced. The cause is that the colon binding counts a bound paragraph as a dump only when it
   starts with `{`/`[`, so a code-fenced dump is never result-shaped. That fenced form is the entry's own v030-sify-orig
   shape.
2. **Escape: all-errored result blocks that `_result_block` does not see.**
   - A markdown table ("| SBIN.NS | ₹812.40 |").
   - A list whose lines carry a trailing note ("* INFY.NS: ₹1,233.65 (up 1.2%)").

   Both stream (f-allerr-table, f-allerr-bullets-annotated).
3. **New over-replacement compared with base c5a6ade8.** After an errored call, a list of the user's own figures is
   replaced:
   - "You told me:\n- Buy price: ₹1,500\n- Quantity: 10" becomes "The price_data tool returned no data for this in this
     turn." (t-err-user-figures-list).
   - "Your position as you gave it:\n\n- Shares: 40\n- Average cost: ₹1,640" is replaced the same way
     (t-err-user-position-summary).

   Both stream unchanged on base. The pinned control covers only the prose form ("You said you bought at ₹1,500.").
   The all-errored branch treats any name-figure list as a tool result.

## Issues found (not in the diff)

- **Pre-existing, same on base.** llama sometimes narrates its own tool call as text JSON ("I will provide a JSON array
  of function calls:\n\n[{"name": "price_data", ...}]") while the call is pending. The guard replaces that text with
  "The price_data tool returned no data for this in this turn." even though both price_data calls then return ok. Live,
  in t-rel-list, the stream showed a stray "}" and that false note ahead of the true list. The offline replay gives the
  identical note on base and on the branch (`probe-fresh3*.out`).
- b18v_probe_b `x-news-data-shows` (pre-existing, recorded by the writer).
- Live, in t-user-sale, llama was told "without calling any tool" but staged `portfolio_update_position` anyway. The
  staging awaits review. This is model behaviour, not the guard.
- Cosmetic: when every call of the turn errored, a fenced dump is replaced inside its fence. The output reads "I got:\n\n```json\nThe
  fundamentals tool returned no data for this in this turn.\n```" (f-named-colon-fenced-json). No figure leaks.
