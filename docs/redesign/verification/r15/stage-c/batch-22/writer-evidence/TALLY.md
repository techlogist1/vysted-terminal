# batch-22 W1 evidence — R15-LEAD-030 (short-name aliases, rule 2c), R15-LEAD-036 (unclosed fence)

Commits on `worktree-agent-batch-22-W1` (base `93ba12da`): `4bc0bd3e` LEAD-030, `51464b15` LEAD-036.

## Pinned tests (before / after)

`pinned-base-93ba12da.out`: base services with this batch's tests copied in.
`test_agent_runtime`: 14 failed, 254 passed. The 14 are the 6 unclosed/mid-table cases, the 4 short-name cases
(SBI, Airtel, L&T, "L & T" with the user's spacing) and 4 of the 5 rule-2c cases. The fifth, Nifty in an
all-errored turn, already went through rule 1 on base. `test_figure_grounding` fails at collection on base
because `payload_names` does not exist there.
`pinned-fix-51464b15.out`: 268 passed + 47 passed.

Focused, fix sha: `pytest tests/test_agent_runtime.py tests/test_figure_grounding.py` 315 passed (base 290).
`test_agent_runtime test_figure_grounding test_b5_runtime_history test_tool_call_rescue test_llm_ollama
test_b3_runtime_intent_gate`: 377 passed. Full sidecar pytest: 3445 passed, 1 skipped.
`ruff format --check sidecar && ruff check sidecar`: clean.

Two pinned expectations changed because their premise is now false by design (logged in 4bc0bd3e):
- `test_figure_grounding`: ("TCS", user text "", "consultancy" absent). Every distinctive name word is an
  alias now, not only the ones the user wrote. The `user_text` parameter was subsumed and removed.
- `test_a_true_statement_beside_an_error_streams`: the "IT stocks rose 1.4%" row after a blank line. That is a
  subjectless, ungrounded figure in a turn with an errored call, and rule 2c replaces it. The blank-line
  reset itself is re-pinned in `test_an_ungrounded_figure_on_no_ok_subject_fails_safe`.

## Offline probes (cwd `<tree>/sidecar`; `probes-base-93ba12da/` vs `probes-fix/`)

| probe | base | fix |
|---|---|---|
| b17v_probe / 2 / 3 | BAD 0 | BAD 0 |
| b18v_probe / _b / _c / _d | BAD 0 | BAD 0 |
| b19v_probe 3 | BAD 0 | BAD 0 |
| b19v_probe (no arg), b19v_probe 2 | BAD 1 each | BAD 1 each. Both are the accepted false-premise "q?" lines (t-err-user-figures-list, t-err-user-position-summary), unchanged since batch-20. |
| b20v_fresh, b20w_probe | BAD 0 | BAD 0 |
| b21v_fresh | BAD 1: w-mixed-sbi-abbrev "SBI last traded at ₹812.40" streamed | BAD 1: t-inherit-reset-blank (see below); w-mixed-sbi-abbrev now PASS |
| b21v_fresh2 | BAD 3: n-BHARTIARTL.NS "Airtel ... ₹1,874.20", n-LT.NS "L&T ... ₹3,512.00", f036-unclosed-tilde dump streamed | BAD 0 |
| b21v_unclosed | 3 of 4 dumps streamed verbatim (u-tilde-unclosed, u-backtick-unclosed, u-backtick-unclosed-prose) | all 4 replaced with the note |

t-inherit-reset-blank ("Infosys could not be refreshed.\n\nThe index rose 0.8% today.", TCS ok, Infosys errored) is the
flip PLAN rule 2c asks for. After the blank line the figure's clause names no subject and inherits none, so it
attaches to no ok subject in a turn that has an errored call, and it is replaced. The b21 probe's TRUE label
assumed the blank-line reset exempts the figure. Under 2c, an unattached figure beside an error is not
trusted.

## Live bar (:52350, sidecar from this tree at `51464b15`, llama3.1:8b via ollama, autonomy ask)

`b22w_live.py` writes `live.out` (run 1) and `live2.out` (run 2, the `l2-*` tags), plus a per-tag
`live/<tag>.jsonl`/`.txt`. `guard-log.txt` holds the sidecar's own "guard replaced" lines, which is the
model's pre-guard text for every replaced sentence clause. A replaced fence or JSON unit is not logged
(pre-existing). Reference values were read from the same sidecar: `/quotes/SBIN.NS` 983.0,
`/quotes/BHARTIARTL.NS` 1785.4, `/quotes/TCS.NS` 2082.0, `/quotes/LT.NS` 3876.2, `/quotes/RELIANCE.NS`
1226.0, `/quotes/NVDA` 224.36 to 224.52 (live), `/fundamentals/TCS.NS` pe_ratio 15.115435, market_cap
7532857786368.

| tag | calls / results | verdict |
|---|---|---|
| o-sify-ttm | financial_statements ok | no figure stated; honest "not available" |
| l-mixed-sbi-airtel | price_data SBIN.ZZ errored, BHARTIARTL.NS errored (provider timeout) | REPLACED: "The latest price of Airtel is ₹640.45 per share." (guard-log; real 1785.4). The SBI sentence carries no figure and streams. |
| l-mixed-lt | price_data TCS.NS ok, LT.ZZ errored | TCS "₹2082.0" streams (= /quotes); L&T acknowledged with no figure |
| l-allerr-codeblock | price_data x5, all invalid args | REPLACED: "So, the latest closes of SBI, Airtel and L&T are ₹732.35, ₹647.60" and "₹284.70 respectively." with one note. A round-1 "```" that the model opened before a tool call, with an empty body, streams (cosmetic). |
| l-raw-json | fundamentals invalid args, then fundamentals TCS ok | round 1: a unit replaced by the fundamentals note (a fence or JSON unit, unlogged). Round 2: "The pe_ratio of TCS is 15.115435 and its market_cap is ₹753,286 cr." streams (= /fundamentals). It sits after a "```" still open at stream end, so it is judged as the unclosed fence's body (LEAD-036) and kept, because it is grounded on an ok subject. |
| l-nifty-2c | price_data XYZ.ZZ errored | no figure; the model said it would call market_overview (did not) |
| c-ok-rounding (true) | price_data NVDA ok | "$224.57" streams (the series' last print; /quotes read 224.36 to 224.52 across the minute) |
| c-short-ok (true, short name on an ok subject) | price_data SBIN.NS ok | "The current price of SBI is ₹983.0." streams (= /quotes) |
| c-short-ok-mixed (true, short name beside an error) | price_data BHARTIARTL.NS ok, INFY.ZZ errored | "Airtel's latest price is ₹1785.4." streams (= /quotes) |
| c-user-after-err | price_data x2, invalid args | the model did not restate the user's figures (no figure, nothing replaced). Re-run as l2-user-after-err. |
| l2-nifty-2c-mixed | price_data TCS.NS ok, XYZ.ZZ errored | TCS "₹2082.00" streams (= /quotes); the model declined the Nifty figure (2c is not exercised live, but is pinned in `test_an_ungrounded_figure_on_no_ok_subject_fails_safe`) |
| l2-short-hul | price_data TCS.NS ok x2, HINDUNILVR.ZZ and HUL errored | TCS "₹2082.0" streams; HUL acknowledged with no figure |
| l2-user-after-err (true) | portfolio_add_position staged x2 (ask), price_data XYZ.ZZ errored | "You sold 8 RELIANCE.NS shares at ₹1,300 each, so your proceeds were ₹10,400." streams; these are the user's own figures (8 x 1300 = 10400) |
| l2-short-ril | price_data TCS.NS ok, RELIANCE.ZZ errored | TCS "₹2082.0" streams; RIL acknowledged with no figure |

Fabricated figures streamed: 0 of 4 logged (₹640.45, ₹732.35, ₹647.60 and ₹284.70, all in guard-log). A fifth
replaced unit, l-raw-json round 1, was a fence or JSON unit and is not logged, so its text is unknown.
True controls unchanged: 9 of 9 (TCS x4, SBI, Airtel, NVDA, TCS fundamentals, the user's sale figures).
Two of the replaced figures were written under a short name ("Airtel", and "SBI, Airtel and L&T"). Both were in
all-errored turns, where rule 1 would have caught them on base as well. The model produced no short-name
fabrication in a mixed turn: it stayed honest in l-mixed-lt, l2-short-hul and l2-short-ril. That class is
pinned offline instead (b21v_fresh w-mixed-sbi-abbrev and b21v_fresh2 n-* fail on base and pass on the fix,
plus `test_an_errored_subject_named_by_a_short_name_is_replaced`).

## Known residuals (not fixed here)

- Paragraph inheritance: a name form no alias covers ("Big Blue"), written after an ok-subject sentence in the
  same paragraph, inherits the ok subject and streams. 2c as PLAN specifies it keeps this behaviour. The test
  pins the uncovered name at the start of the paragraph instead.
- Grounding is per subject, not per (tool, subject). This is the known residual since batch-20.
- A resolve_symbol query becomes an alias whole, word by word. A query like "Airtel price" makes "price" an
  alias of BHARTIARTL, which only over-replaces (fails safe).
- A payload `name` key that is not a company name (for example a series or field name) also becomes an alias,
  which likewise only over-replaces.
- Two-letter initialisms are not aliases, and neither are names made of generic words only ("ICICI" is common
  across the masters). Figures written that way fall to rule 2c, or stream if they inherit an ok subject.
- A replaced fence or JSON unit is not logged. Only sentence clauses reach the "guard replaced" log line.
