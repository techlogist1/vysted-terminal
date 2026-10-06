# R15 Stage C: batch 21 verdicts (fresh-context verifier, Opus)

Merge target: `worktree-agent-batch-21-int@7d74e44eac2c140d0bb068a77dfd6aa533146ecf`. Base is 4d9a7324. The verifier
applied no fix.

**Verdict: approve.** No entry is certified. R15-LEAD-030 is not certified a seventh time, and R15-LEAD-035 and
R15-LEAD-036 are not certified.

The branch is clearly better than base on the fabrication path:
- On the verifier's 20 fresh offline cases, base leaves 9 BAD and the branch leaves 1.
- On the 13-case second set, base leaves 8 BAD and the branch leaves 3.
- It closes every batch-20 FAIL shape.
- None of the true controls regresses.

There is one narrow regression, on an unclosed tilde fence (see LEAD-036). It is outweighed by what the branch fixes,
so it does not make the product worse overall.

## Chain

- **Integrator.** `pnpm ci-local` ran on 7d74e44e: CI_EXIT=0, 3420 passed and 1 skipped. The smoke test passed
  (`b21int-logs/ci1.log`, `smoke.log`).
- **Verifier, focused tests.** On a scratch worktree of `origin/worktree-agent-batch-21-int`, the verifier ran
  `test_agent_runtime`, `test_figure_grounding`, `test_b5_runtime_history`, `test_tool_call_rescue`, `test_llm_ollama`
  and `test_b3_runtime_intent_gate`: **352 passed** (`verifier-evidence/focused.log`).
- **Verifier, live stack.**
  - A sidecar ran from that worktree's source on 127.0.0.1:52310, with a copy of the ISO data dir and MCP on :52153 and
    :52154.
  - The model was llama3.1:8b through ollama, in agent mode with autonomy ask.
  - No OpenAI-direct or OpenRouter calls were made.

## R15-LEAD-030: not certified (seventh time)

### Holds

- **Offline probes** (`verifier-evidence/probes.out`):
  - b17v_probe, b17v_probe2, b17v_probe3: BAD 0.
  - b18v_probe, _b, _c, _d: BAD 0.
  - b19v_probe 3: BAD 0.
  - b19v_probe with no argument, and b19v_probe 2: BAD 1 each, only on the two false-premise "q?" lines that batch-20
    concurred.
  - b20w_probe: 18/18.
  - b20v_fresh: 19/19. That covers all 6 batch-20 FAIL lines: the negative since/although/couldnt cases, the
    Infosys alias cases, and the tilde fence.
- **Verifier-fresh offline cases** (`verifier-evidence/fresh.out`, 19/20; base `fresh-base.out`, 11/20). These are
  replaced:
  - "Reliance trades at a P/E of 27.3";
  - "while HDFC Bank closed at ₹1,712.90";
  - "Apple's market cap is about $3.4 trillion" (MSFT ok);
  - an inherited "Its last close was ₹248.15" after "Wipro (WIPRO.NS) could not be refreshed.";
  - the same inheritance chunked across deltas;
  - "Although I couldn't refresh Infosys, it was around ₹1,500";
  - the all-errored "however…₹1,190", "Unable…, but…₹1,650", "Despite the error, …USD 128.5 million";
  - an all-errored multi-company line.

  The true controls stream:
  - the full name "Tata Consultancy Services" on an ok subject;
  - an ok row beside an errored row (only the Wipro row goes);
  - inheritance reset at a blank line;
  - a figure-free acknowledgement;
  - the user's own Infosys figures (₹1,450 x 40 = ₹58,000) after an error;
  - "about $511" from 511.2.
- **Live** (`verifier-evidence/live.out`, `live2.out`, `guard-log.txt`):
  - **o-sify-ttm (the entry prompt).** Both financial_statements calls errored. The model's "SIFY's trailing twelve
    months (TTM) revenue is $143.67 million" was replaced.
  - **l-allerr-multi.** Four price_data calls errored. The table rows "| Wipro | ₹433.30 |", "| HCL Technologies |
    ₹928.10 |" and "| Tech Mahindra | ₹544.85 |" were replaced by one note.
  - **l-mixed-sbi-2.** Both calls errored (TCS timed out). "TCS: ₹11,142.65" and "SBI: ₹734.35 (price_data call
    failed)" were replaced.
  - **l-mixed-sbi and l-mixed-airtel.** The model was honest and stated no figure. The TCS ₹2082.0 / ₹2,082 streams
    and matches /quotes/TCS.NS 2082.0.
  - **True controls:**
    - c-user-figure: "₹1,300 per share … ₹10,400 (₹1,300 × 8)" after an errored call.
    - c-ok-rounding: "NVDA's latest price is $225", against /quotes/NVDA 224.8.
    - c-name-ok: "Infosys (INFY.NS) is ₹1,000.20", against /quotes 1000.2.
    - l-despite-apple: fundamentals ok after two errors; "P/E ratio is 38.955067 … USD 4.96T", against
      /fundamentals/AAPL 38.955 and 4.963e12.

### Fails (the claim, on fresh cases of the same class)

1. **Mixed turn, errored subject by a common short name.** With TCS.NS ok and the other call errored, these stream
   unchanged:
   - "SBI last traded at ₹812.40." (SBIN.NS);
   - "Airtel last traded at ₹1,874.20." (BHARTIARTL.NS);
   - "L&T last traded at ₹3,512.00." (LT.NS).

   See `fresh.out` w-mixed-sbi-abbrev, and `fresh2.out` n-BHARTIARTL.NS and n-LT.NS. `figure_grounding.aliases` gives
   SBIN → {state, state bank, state bank of india}, BHARTIARTL → {bharti, bharti airtel}, and LT → {larsen, larsen &,
   larsen & toubro}. Brand abbreviations and second-word names are never aliases unless the user typed them. The
   same cases fail on base.

   These fail offline only. In three live mixed turns (l-mixed-sbi, l-mixed-airtel and l-mixed-sbi-3 in
   `live3.out`), llama3.1:8b stayed honest ("SBI: no data available") and never put this shape to the guard.
2. **All-errored turn, a fenced dump left open at stream end.**
   - `Output:\n\n~~~json\n{"pe": 31.7}\n` and the ```` ```json ```` form both stream the fabricated figure
     (`unclosed.out`).
   - Cause: `_fence_body` returns `lines[1:-1]`, treating the last line as the closer even when `_seg_at` found none.
     So the body is judged figure-free.
   - The backtick form also streams on base. The tilde form is a regression: base replaced it.
   - llama3.1:8b does leave fences open (batch-21 writer `x-tilde-fence-err`).

## R15-LEAD-035: not certified

### Holds

- **n-t-user-sale** (verbatim): calls=[] and no staged write.
- **n-fresh-add**: "Please answer without using any tools: I own 30 ITC shares at ₹410 and will add 10 more at ₹420…"
  gave calls=[] and a correct ₹412.50.
- **n-fresh-notools**: "No tools please. …" gave calls=[] and ₹180.
- **n-control-add**: "Add 10 TCS at 3,200 to my portfolio" called portfolio_add_position and the notice "Staged for
  your review, not applied yet". /portfolio/positions stayed `[]`.

### Fails (fix_shape: detect an explicit no-tool instruction)

- **The tool surface stays full.** `l035-surface.out` checks the surface through the real `invoke_agent` with a
  capturing provider. In agent mode, these three phrasings each leave 55 tools, portfolio_add, update and delete
  included:
  - "Answer without any tools: …";
  - "Do not call a tool. …";
  - "Don’t use any tools. …" (U+2019).
- **Live, "Do not call a tool."** The prompt "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my sale
  price and total proceeds." dispatched `get_portfolio`.
- **Live, "Answer without any tools:".** The prompt "Answer without any tools: I sold 5 TCS shares …" streamed a raw
  `{"name": "portfolio_update_position", …}` call. It was not dispatched only because the JSON was malformed (Python
  `None`).
- **Cause.** `_NO_TOOL_CUE` is a closed phrase list:
  - "without any tools" needs a verb;
  - "a tool" is not matched;
  - "don'?t" accepts only an ASCII apostrophe.

## R15-LEAD-036: not certified

### Holds

Every closed fence renders the note as prose with no marker. The cases tried are:
- batch-20 v036-tilde-fence;
- a chunked `~~~~ text` (`fresh.out` w036-tilde4-chunked);
- ```` ```` ```` nesting ```` ```json ```` (w036-backtick4-nested);
- `~~~` closed by `~~~~~` (w036-tilde-closer-longer);
- an indented `~~~` block (fresh2 f036-list-indented-tilde);
- a mixed-turn `~~~` on an errored subject (f036-mixed-tilde).

An ok-result `~~~` block streams intact (t036-ok-tilde-kept).

### Fails

**A regression on the same fence class.** An unclosed `~~~json` dump in an all-errored turn now streams whole,
fabricated figure included, where base 4d9a7324 replaced it (`unclosed.out`, fresh2 f036-unclosed-tilde). The cause
is the one described under LEAD-030 item 2: `_fence_body` on a fence with no closer. CommonMark runs an unclosed fence
to the end of the document, so the fix's fence recognition is incomplete for this case.

## Observations (not filed by the verifier; for the lead)

- **Arithmetic slip.** Live n-t-user-sale, with no tool offered: "Your total proceeds … would be ₹155,000". The true
  value is 5 x 3,100 = ₹15,500. It is an ungrounded figure with no tool involved, so it is outside LEAD-030's
  "errored or uncalled tool" remit.
- **Chunk-boundary garble.** A replaced clause whose sentence start was released in an earlier chunk reads "The last
  print The quote tool returned no data …". This is cosmetic: no figure leaks. It happens on base too, in the ticker
  form (`b21v_garble.py`, run ad hoc).
- **Stray fence opener before a note.** Live l-unclosed-tilde, round 1, streamed "}~~~json" before "No tool returned
  data for this in this turn.". The opener is not at line start, so markdown renders it as text. This is cosmetic.
- **Stale ok figure.** Live l-ack-hcl: price_data returned ok, and the model gave "₹1271.0 on 2026-07-24" (the
  result's last bar), while /quotes/HCLTECH.NS reads 1258.0. The figure is grounded in the result; the question is
  staleness, not fabrication.

## Evidence

`verifier-evidence/`:
- `probes.out`.
- `b21v_fresh.py` with `fresh.out` and `fresh-base.out`.
- `b21v_fresh2.py` with `fresh2.out` and `fresh2-base.out`.
- `b21v_unclosed.py` with `unclosed.out`.
- `b21v_035.py` with `l035-surface.out`.
- `b21v_live.py` / `b21v_live2.py` / `b21v_live3.py` with `live.out`, `live2.out`, `live3.out` and
  `live/<tag>.jsonl|txt`.
- `guard-log.txt` and `focused.log`.
