# batch-24 W1 live bar tally (R15-LEAD-035)

Source sidecar `127.0.0.1:52350`, llama3.1:8b via ollama, keyless, agent mode, autonomy
ask. Full transcript: `live-full.out` (client stdout across all 23 runs); per-run JSONL
events in `live/<tag>.jsonl`.

## 7 OVER prompts x3 (must call `price_data`, state the `/quotes` price)

| tag | r1 | r2 | r3 |
|---|---|---|---|
| o-never-said | price_data, correct | price_data, correct | price_data, correct (1 timeout retry) |
| o-other-than | price_data, correct | price_data, correct | price_data, correct |
| o-but-do-fetch | price_data, correct (1 invalid-args retry) | price_data, correct | price_data, correct |
| o-except | price_data, correct | price_data, correct | price_data, correct |
| o-dont-need | price_data, correct | price_data, correct | price_data, correct |
| o-twice | price_data, correct | price_data, correct | **fundamentals, not price_data** (market cap stated, not the quote) |
| o-web | price_data, correct | price_data, correct (1 invalid-args retry) | price_data, correct (1 invalid-args retry) |

20/21 correct. `o-twice.r3` ("Don't call tools twice — what is HDFCBANK.NS at?") is the
one exception: the gate correctly kept the full tool surface (not stripped — `price_data`
was available), but the model chose `fundamentals` instead and answered with market cap,
not the `/quotes` price. This is model tool-choice, not a gate/regex miss — the documented
LEAD-030/037 residual (PLAN.md "Report every run honestly ... note it, do not re-run to
hide it").

## Literal repro x2 (must make no call, stage nothing)

- `repro.r1`: `calls=[]`, `results=[]`, `/portfolio/positions` unchanged (`[]`). Correct
  math stated (₹15,500).
- `repro.r2`: same — `calls=[]`, `results=[]`, positions unchanged, correct math.

## Control ("Add 10 TCS at 3,200 to my portfolio")

`live/control-add.jsonl`: `portfolio_add_position` called, staged behind review
("Staged for your review, not applied yet: portfolio_add_position TCS. Accept it below to
apply."), `/portfolio/positions` unchanged (`[]`) — not auto-applied, per §6.5.

## Pre-run quotes (from live-full.out header)

RELIANCE.NS ₹1226.0, TCS.NS ₹2082.0, ITC.NS ₹269.0, HDFCBANK.NS ₹735.6, WIPRO.NS ₹164.02.
`/portfolio/positions` empty before the run.
