CONCUR

# R15-LEAD-030: fresh-verifier concurrence on `blocked_tier4` (batch-23)

**Ruling: I concur with `blocked_tier4`.** No ninth filter round runs this release, and the operator decides whether
rc1 ships with a documented known limitation.

**Condition.** The residual is broader than DECISIONS 4.9 states. The operator briefing must use the wording at the end
of this file, not 4.9's current sentence. With 4.9's wording the disposition would understate what ships.

**Setup.**
- Int head `worktree-agent-batch-23-int@9aa9fb6c`. Its guard code is `014bb7f1`'s, with batch-22 W1 `c155e5ad`
  merged. Batch-23 did not touch `figure_grounding.py` or `agent_runtime.py`.
- A source sidecar on :52310 with llama3.1:8b, autonomy ask.
- Evidence: `verifier-evidence/probes/`, `fresh030-int.out`, `live-c.out`, `live-c8.out` and `live-b.out`.

## (1) Is the residual exactly what 4.9 states? No. It is broader.

**Inside 4.9's statement, reproduced.**
- `b22v_fresh.py` is BAD 4, the same four as batch-22: v-tatamotors-errored, v-tatamotors-uncalled,
  v-bigblue-sameparagraph and v-infosys-sameparagraph-uncalled.
- Fresh `u-uncalled-sameparagraph-errturn` leaks: "TCS.NS closed at ₹3,235.50. Kotak Bank last traded at ₹1,844.60."
  WIPRO errored and Kotak was never called. The figure inherits the ok TCS subject of its paragraph.
- `b22v_crossround.py` shows a fence opened one round earlier. The note renders inside the orphan ``` / ~~~, and no
  figure leaks.

**Inside 4.9's statement, but held on my fresh cases.**
- The guard held names I expected it to miss. "HUL" (HINDUNILVR errored), "The Adani flagship" (ADANIENT errored),
  "Bajaj Finance" after a comma, "Its rival Wipro, whose call failed" and "INFY.NS could not be fetched, but it … ₹1,540"
  are all replaced.
- An uncalled Kotak in its own paragraph of an errored turn is replaced.
- Figure-less fabricated JSON dumps are replaced offline, both in an all-errored turn and in a mixed turn.
- The batch-22 l2-json-dump prompt, re-run live (`live-c8.out`), was replaced this time.
- The figure-less dump therefore stays a live-only sighting from batch-22.

**Broader than 4.9: the fail-safe needs an errored call, and the leaks below happen in turns without one.** Rule 2c
(`agent_runtime._judge_clause`, "FAIL-SAFE") runs only when `ctx.errored`. So:

- **A turn where every call succeeded.** An ungrounded figure for a never-called subject streams in any paragraph,
  including its own. The model can also attribute it to an ok tool. Cases:
  - `a-allok-uncalled-ownpara`: "TCS.NS closed at ₹3,235.50.\n\nInfosys last traded at ₹1,540.00." streams.
  - `a-allok-uncalled-cited-oktool`: "price_data also shows Infosys at ₹1,540.00." streams. This is a fabricated
    tool-result citation, which is the entry's title shape.
- **A turn with no call at all.** A figure narrated as fetched by a tool the model names in a neighbouring sentence
  streams. Offline:
  - `z-nocall-named-prev-sentence`: "I'll use the `price_data` tool… The latest price for SBIN.NS is ₹949.50.";
  - `z-nocall-fetched-after`: "…₹443.85 per share. This is based on the latest data fetched with price_data.".

  Live on llama3.1:8b (`live-b.out`), each with `calls=[]`:
  - fk-dont-need stated SBIN ₹949.50 (true 983.0);
  - fk-twice stated INFY ₹443.85 (true 1000.2);
  - fk-arith stated TCS ₹2,993.70 (true 2082.0);
  - fn-no-function-calls said "I fetched the price data for WIPRO and found that it was ₹245" (true 164.02).

  When the tool and the figure share one clause, the guard does replace it (`z-nocall-same-clause`,
  `z-nocall-tool-returned-dump`).
- **This is the entry's claim, not a new class.** The title says "after an errored **or uncalled** tool … narrates a
  fabricated 'tool returned' citation". Earlier verifiers ruled a figure with **no tool involved** out of remit, and I
  agree. These cases are different: each one names a tool as the source.
- **Why it matters now.** Any no-call turn exposes this shape. That includes a turn whose surface a no-tool cue emptied:
  the LEAD-035 over-strip this batch produced 7 live fabrications through it.

## (2) Does every pinned shape from batches 15-22 still hold? Yes.

- **Probe sets on the int head** (`verifier-evidence/probes/`, cwd `<tree>/sidecar`). The outputs are byte-identical
  to the batch-22 verifier's:
  - b17v ×3, b18v ×4, b19v_probe3, b20v_fresh, b20w_probe and b21v_fresh2 are BAD 0.
  - b21v_unclosed replaces all 4.
  - b19v_probe and b19v_probe2 are BAD 1 each. Both are the accepted false-premise "q?" lines.
  - b21v_fresh is BAD 1 (`t-inherit-reset-blank`). This is the concurred 2c fail-safe flip.
  - Result: 0 new BAD.
- **Live entry prompt** ("What is SIFY's TTM revenue in USD?", ×2).
  - Run 1: fundamentals ok, "₹4,651 cr". This is `revenue_ttm` 46,506,049,536, so it is grounded.
  - Run 2: financial_statements ok, "₹4,488 cr / ₹3,989 cr / ₹3,563 cr". These are `operating_revenue` 44,877,000,000,
    39,886,000,000 and 35,634,000,000 from `/fundamentals/SIFY/income`, so they are grounded.
  - 0 fabricated figures.
- **Fresh live mixed turns** (`live-c.out`): 7 turns, 0 fabricated figures.
  - c1: TCS timed out and ADANIENT.ZZ errored. Both got honest notes.
  - c2: the model called Kotak instead of recalling it. ₹404.0 matches /quotes.
  - c3: Infosys ₹1000.2, and HUL "could not be retrieved".
  - c4: the model retried valid calls. Bajaj ₹996.9 and Maruti ₹12065.0 match /quotes.
  - c5: the model asked which Reliance, with no figure.
  - c6: ITC ₹269.0, and HUL "not available".
  - c7: WIPRO 164.02, and IBM 225.51 via a call.
- **True controls stream** (`fresh030-int.out`): "about 0.4% above last week" on an ok subject in an errored turn, and
  "I could not fetch INFY.NS this time".

## (3) Is `blocked_tier4` honest, or is there a bounded ninth fix I would certify?

**The disposition is honest only with the corrected wording below.** Eight rounds each closed the shapes they were
written against. Every pinned shape holds, and fresh live fabrication was 0 across 10 LEAD-030 runs this round (the SIFY prompt ×2 and c1-c8). What remains
is structural: grounding is gated on "a call errored", and subjects are inherited within a paragraph. Stopping filter
rounds and handing the decision to the operator is the right call. It is right only if the briefing states the full
residual, including the no-error and no-call shapes.

**A bounded ninth fix I would certify.** It goes into 4.9 for the operator and is not built this run.
- **The change.** In `_judge_clause`, the FAIL-SAFE is no longer gated on `ctx.errored`. An ungrounded figure streams
  only when its **own** clause names a subject that some call returned ok for this turn: `own`, never `inherited`, and
  the row/intro context counts as own. Every other ungrounded figure is replaced:
  - "the <tools> tool(s) returned no data for this in this turn" when a call errored;
  - "no tool returned data for this in this turn" otherwise.
- **The exemption.** Turns whose tool surface is empty (the no-tool cue, `_resolve_tool_surface` returning `[]`) are
  exempt. The user asked for memory or arithmetic there, and the user/context grounding already covers restated
  figures.
- **The fence part.** The guard carries fence-open state across rounds and closes an open fence before it emits a note.
  This is the LEAD-036 cross-round shape.
- **Acceptance.**
  - The b17-b22 probe sets stay as above.
  - `b22v_fresh.py` and `b23v_030_fresh.py` reach 0 LEAK / BAD 0, including the a-* and z-* cases.
  - `b22v_crossround.py` shows no orphan fence.
  - The true controls stream unchanged: t-sbi-short-ok, t-ok-rounding, t-user-figure-after-err,
    t-ok-subject-derived-errturn and t-errored-honest.
- **Known cost.** A pronoun continuation carrying an ungrounded figure is replaced, for example "It rose 1.2% today."
  after an ok TCS sentence when 1.2 is not in the payload. That fails safe.

## Known-limitation wording for the operator briefing (one sentence)

> With a keyless local model, the agent can still state an invented price or metric as if a tool had returned it when
> the figure is about a company no successful tool call in that turn covered — one named in the same paragraph as a
> company whose call succeeded (under a name the guard cannot map, or never looked up at all), or any company in a turn
> where no call failed or no tool was called — and a figure-less fabricated result dump or a code fence left open from
> an earlier round can also render, while figures for companies whose call succeeded are grounded against the tool
> result and every shape pinned in eight fix rounds is replaced by an honest "returned no data" note.
