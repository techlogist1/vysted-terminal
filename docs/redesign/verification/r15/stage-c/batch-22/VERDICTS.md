# R15 Stage C — batch-22 verifier verdicts

**Verdict: block.**

- **Target:** `worktree-agent-batch-22-int@e4d72417`.
- **Stack:** a source sidecar from that tree on 127.0.0.1:52310, with data from a copy of `vysted-iso/data`. MCP ran on
  :52153/:52154. The model was llama3.1:8b via ollama with autonomy ask.
- **Base comparisons:** a detached worktree at `93ba12da`.
- **Evidence:** `verifier-evidence/`.
- **Outside-world truth:** screener.in reads SBIN ₹983 and ITC ₹269 (25 Sep close). The app's `/quotes` agrees:
  SBIN 983.0, ITC 269.0, TCS 2082.0, INFY 1000.2 and HDFCBANK 735.6.

**Chain.** Green on the integrator's logs (`b22int-logs`):
- ci-local `CI_EXIT=0` (3456 passed, 1 skipped);
- focused tests: 388 passed;
- smoke: `SMOKE_EXIT=0`.

**Why block.** The W2 merge (`e4d72417`, `planner.py`) makes the product worse. Explicit data requests such as
"Don't forget to use the tools to get the latest TCS.NS price." now lose the whole tool surface. Live, the model then
streams fabricated prices narrated as fetched, and the figure guard is inert because no call errored.

Nothing certifies this batch. The W1-only merge `da25a6a9` showed no regression against base in any probe I ran:
BAD 4 vs BAD 8 on my fresh set, and every older probe at BAD 0 or accepted. It is a candidate to take alone if the
lead wants the W1 gains now. That is a lead decision, not a certification.

## R15-LEAD-030 — not certified (8th time); improved, no regression

**What holds.**
- **Offline probes, cwd `<tree>/sidecar`** (`probes/`):
  - b17v ×3, b18v ×4, b19v_probe 3, b20v_fresh, b20w_probe and b21v_fresh2 are BAD 0.
  - b19v_probe (no arg) and b19v_probe 2 are BAD 1 each. Both are the accepted false-premise "q?" lines.
  - b21v_fresh is BAD 1: `t-inherit-reset-blank` ("The index rose 0.8% today.", a subjectless ungrounded figure in an
    INFY-errored turn).
  - I **concur** with this 2c flip. No tool carries 0.8%, and the figure attaches to no ok subject. Under PLAN rule 2c
    that is fail-safe by design.
  - b21v_unclosed replaces all 4.
- **Fresh offline set** (`b22v_fresh.py` → `fresh-batch-22-verify.out`). Replaced on an errored subject: M&M
  (initialism with `&`), RIL, Infy, HDFC Life beside an ok HDFC Bank, an unclosed `~~~~text` all-errored, an unclosed
  ```` ```python ```` mixed, and a mid-table end. True controls stream unchanged:
  - "SBI closed at ₹983.00." (short name, ok);
  - the same with a derived "about 1%" in a mixed turn;
  - "roughly ₹3,236" (rounding);
  - a user figure restated after an error.
- **Live.**
  - o-sify-ttm: fundamentals ok. The model gave "₹4,651 cr", which is the payload `revenue_ttm` 46,506,049,536, so
    it is grounded.
  - l-allerr-bullets: fabricated Axis ₹83.55, Kotak ₹1,844.60 and ICICI ₹934.70 were all replaced (guard-log).
  - l-mixed-mm and l2-tata-paragraph: honest, no figure for the errored subject.
  - True controls: c-ok-rounding ITC ₹269.0 streamed in a mixed timeout+ok turn, c-user-figure ₹1,650 restated, and
    c-short-ok "SBI" clause streamed.

**What fails. The claim, on fresh cases (`fresh-batch-22-verify.out`).**

```
FAIL [FAB] v-tatamotors-errored: "TCS.NS closed at ₹3,235.50. Tata Motors last traded at ₹702.10.\n"
FAIL [FAB] v-tatamotors-uncalled: "TCS.NS closed at ₹3,235.50. Tata Motors last traded at ₹702.10.\n"
FAIL [FAB] v-bigblue-sameparagraph: "MSFT closed at $511.20. Big Blue last traded at $250.10.\n"
FAIL [FAB] v-infosys-sameparagraph-uncalled: "TCS.NS closed at ₹3,235.50, and its peer Infosys last traded at ₹1,540.00.\n"
BAD 4        (base 93ba12da: BAD 8 — the same 4 plus RIL, unclosed python fence, mid-table, Big Blue own paragraph)
```

- **Cause.** Rule 2c treats a clause that *inherits* an ok subject from its paragraph as attached. An unrecognised
  name, or an uncalled one, after an ok sentence in the same paragraph therefore bypasses the fail-safe. Big Blue in
  its own paragraph is replaced.
- **Tata Motors.** Its alias set is `{TATAMOTORS}` only, because the master no longer lists it after the demerger
  (`TMPV`).
- **Live l2-json-dump.** After fundamentals errored ("missing or non-string symbol"), a fenced fabricated
  `{"ok": true, "result": {"symbols": [{"isin": "INE009A01027", "name": "Infosys Ltd.", ...}]}}` dump streamed. It has
  no currency figure, but it is the synthetic tool-result citation the fix_shape names.

## R15-LEAD-035 — not certified; REGRESSION (W2)

`b22v_035.py` measures the tool surface sent to the provider in agent mode (`l035-surface.out`, base in
`l035-surface-base.out`).

**Good.**
- All 3 batch-21 phrasings and t-user-sale → 0 tools.
- Fresh phrasings → 0 tools: "Avoid calling any functions", "Zero tool calls please", "without tool use", "Do NOT use
  external data", "Please don’t invoke any tool".
- "No tools except price_data" keeps its tools. On base it lost them, so this is fixed.

**Live.**
- n-answer-without, n-do-not-call-a-tool, n-curly-dont, n-avoid-functions ("add them to my holdings") and
  n-zero-tool-calls ("add 7 INFY"): `calls=[]`, nothing staged.
- n-control-add staged `portfolio_add_position` ("review and accept this change in the review queue"), and
  `/portfolio/positions` stayed `[]`.
- n-named-exclusion called price_data and gave ₹2082.00.

**Regression.** These keep 42-55 tools on base and 0 on this branch:

```
BAD expect_no_tools=False n_tools=0 | Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS
BAD expect_no_tools=False n_tools=0 | Only use data from price_data for the above symbols: TCS.NS
BAD expect_no_tools=False n_tools=0 | Why did you not use the tools? Get the TCS.NS price now.
BAD expect_no_tools=False n_tools=0 | Why did you not use the tools
BAD expect_no_tools=False n_tools=0 | Don't forget to use the tools to get the latest TCS.NS price.
BAD expect_no_tools=False n_tools=0 | Do not answer without using the tools: what is TCS.NS trading at?
```

**Live consequence** (`live.out`).
- fp-dont-forget → `calls=[]`. The model output "Current price of TCS.NS: ₹3,313.40" (truth 2082.0), a Nifty of
  20,115.45, a Sensex of 68,475.15 and a "Market cap: ₹5,67,416 cr", all claimed as fetched.
- fp-just-from-market → `calls=[]`, "INFY.NS (₹1,243.35 ...)" (truth 1000.2).
- `notool_fab.out` confirms the guard lets a fabricated price through in such a no-call turn.

**Miss.** "Skip the tools for this one — ... add 3 more at ₹1,650" keeps all 55 tools, portfolio writes included.

**Cause.**
- NEG accepts 0-3 arbitrary filler words before VERB, so "don't forget to use the tools" and "not use the tools"
  in a question match. NEG also matches inside "Do not answer without using the tools", where the instruction is
  double-negative.
- `_NO_TOOL_FROM_GIVEN` uses `.*` twice, so any clause with "just/only … from … this message/the above" matches.
- I concur with the reviewer's block item. The fix needs the lead to decide the shape of rule 6, since PLAN's own
  "Answer only from the numbers in this message" does not fit it literally, and to decide whether NEG+filler is
  kept at all.

## R15-LEAD-036 — not certified; improved, no regression

**Holds** for every same-round fence. b21v_unclosed replaces all 4, and closed/unclosed backtick and tilde fences in
b19v/b20w/b21v render prose. Fresh cases also render prose with no marker:
- an unclosed `~~~~text` (all-errored);
- an unclosed ```` ```python ```` (mixed, errored subject);
- a mid-table end.

**Fails** on a fresh live case of the class. In l-allerr-bullets, round 1 streamed `\n\n```\n` and then made a native
price_data call, which errored. Round 2's fabricated bullets were replaced, but the note rendered inside that
still-open ``` block: "```\nTo get the latest closes ... The price_data tool returned no data for this in this
turn." `b22v_crossround.py` reproduces it offline for both ``` and ~~~ (`crossround.out`), with the same output on
base.

A fence opened in an earlier round and still open when the replaced unit streams needs closing, or needs holding at
the tool-call boundary.

## Issues (outside these entries; not in the diff)

- `/fundamentals/SIFY` reports `currency: "USD"`, but `revenue_ttm` 46,506,049,536 is INR, next to a USD market cap of
  968,088,640. The unit label is wrong at the data boundary.
- Grounding is by value. Live c-short-ok stated "SBI ... is ₹1082.0" as the current price, while the real price is
  983.0. 1082.0 is an older bar value inside the same price_data payload, so the guard counts it as grounded.
- n-avoid-functions: the model claims "I'll add these shares to your portfolio: you now hold 40 ITC shares" with no
  tool called. This is narration only; nothing was staged.

**Cleanup.** Sidecar sleep pid 3408 was killed. The scratch worktrees `batch-22-verify` and `b22v-base` were removed.
