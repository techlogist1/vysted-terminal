# rc1-scenarios — agent scenario harness (gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `:52311`, source
`rc1-round-5-cand/sidecar`, data dir `rc1-round-5-data-rc1-scenarios` (fresh copy of the
keyless seed profile), sleep pid `20255` (kill target for teardown). `GET /health` ok.

## Provider resolution

- `vy._key('openrouter')` and `vy._key('openai')` both resolve (true/true).
- Probed openrouter's default `:free` slug (`inclusionai/ling-3.0-flash-vl:free`) —
  returned an `error` event, HTTP 404 from OpenRouter itself ("This model is unavailable
  for free"), 0 tokens. Does not satisfy "one probe call returns tokens."
- Probed `openai --model gpt-4o-mini` — ok, 3 output tokens.
- **Hosted lane = openai / gpt-4o-mini.**

## Scenarios and pass rules

Written to `SCENARIOS.md` before any trial ran: 4 read-back (RB1-4), 4 skepticism
(SK1-4), 4 self-consistency (SC1-4).

## Key results (full matrix in SCENARIOS.md)

- **RB1-RB4 hosted**: pass^3 on all four (openai correctly relays the runtime's staged/
  not-applied ground truth every time, for watchlist add, note write, portfolio add and
  brief+layout).
- **RB1, RB4 local (llama3.1:8b)**: FAIL — the model's own narration claims completion
  ("I've added TCS.NS to your watchlist", "it's at the top of the cockpit") while the
  runtime's injected tool-result / host_action notice says "Staged for your review, not
  applied yet." Graded as **model weakness, not a product defect**: the SAME runtime
  mechanism (the `_staged_actions_notice` / `_grounded_host_action_result` injection) is
  working correctly — hosted gpt-4o-mini, given the identical injected ground truth,
  narrates it correctly every time. RB2, RB3 local: pass (narrated staged correctly).
- **SK1 (AMAL) hosted+local — FAIL, all trials.** All three hosted trials and the local
  trial confidently state a price for "Amalgamated Financial Corp. (AMAL)" (the US bank
  the user named) **denominated in INR** with zero flag. Verified live: `GET /resolve?
  q=Amalgamated+Financial` correctly resolves to the US NASDAQ entity (confidence 1.0,
  `needs_disambiguation: false`), but `GET /quotes/AMAL?asset_class=equity` (region IN)
  returns the unrelated Indian instrument's quote (₹674.40, `provider: nse_direct`,
  `currency: INR`) — the exact repro named in the live register's `R15-DATA-002` entry
  (files `sidecar/routers/quotes.py`, `sidecar/routers/fundamentals.py`,
  `sidecar/services/resolution_policy.py`). **R15-DATA-002 is status `blocked_tier4`,
  one of the nine entries the round-5 lead note adjudicates to the operator (DECISIONS
  4.15).** Per the round's rule 6, this is filed as a **concurrence note on R15-DATA-002**
  — not a new_defect, not a regression, no fix round.
- **SK2 (SIFY ADR ratio) hosted+local — FAIL, all trials, self-contradictory.** Hosted
  trial 1 states the served EPS is share-basis (needs ×6 adjustment); hosted trials 2 and
  3 state the opposite (already ADR-basis, no adjustment) — three fresh identical prompts,
  two mutually exclusive fabricated answers, no tool result anywhere states a basis at
  all. The local trial fabricates the same claim with a fake citation ("According to the
  fundamentals provided by yfinance, the EPS ... is already on an ADR basis"). This
  matches the live register's `R15-AGENT-090` ("Agent fabricates SIFY's ADR ratio with a
  fake 'fundamentals data' citation ... the model states 1:1, later 1:2"), status
  `blocked_tier4`, DECISIONS 4.17. Filed as a **concurrence note on R15-AGENT-090** — not
  a new_defect, no fix round.
- **SK3 (BGNE) hosted+local — PASS, all trials.** `resolve_symbol`/`price_data` return an
  explicit not-found/empty-series error for BGNE (delisted/renamed on Nasdaq to ONC after
  this candidate's data snapshot); every trial states plainly it could not find data —
  no fabrication.
- **SK4 (DAL internal consistency) hosted — 1/3 pass per-trial** (trial 1 computes a
  5,990% margin and explicitly flags it as an inconsistency; trials 2-3 compute ~10.24%
  and call it "reasonable" with no flag on the far more obvious problem: "Delta Air
  Lines" reported in INR crore at a scale ($1-2M) three orders of magnitude off a real
  major airline). Root cause verified live: bare `GET /fundamentals/DAL` (region IN)
  resolves to "Dynamic Archistructures Limited" (DAL.BO), an unrelated Indian company —
  the same bare-ticker/session-region collision mechanism as SK1, i.e. the same
  `R15-DATA-002` class. Filed as a second **concurrence note on R15-DATA-002**, not a new
  finding.
- **SC1-SC4 (self-consistency) hosted — pass^3 on all four.** TCS.NS P/E (15.13), AMAL
  resolution (Amal Limited, NSE/BSE India — consistent because these prompts carry no
  disambiguating US-company framing, unlike SK1), RELIANCE.NS watchlist add (same symbol,
  same staged status), DAL revenue/net income (same INR-crore figures, internally
  consistent with each other even though they reproduce the DATA-002 collision) — all
  three trials per scenario agree.
- **SC1-SC4 local** — see SCENARIOS.md matrix; single-trial results, no cross-trial
  consistency claim implied (property reported as single-trial local run per rule).

## Findings

No `new_defect` or `regression` findings filed. Every failure observed traces to either
(a) llama3.1:8b narration overriding the runtime's correct injected ground truth (model
weakness — the hosted lane, given the identical injected notices, narrates correctly every
time, so this is not a runtime/product defect), or (b) a live reproduction of an entry
already adjudicated to the operator under this round's rule 6 (R15-DATA-002,
R15-AGENT-090) — recorded as concurrence notes, not new findings, per that rule.

## Teardown

Sidecar `:52311` stopped: killed sleep pid 20255, then the surviving worker pid 20258
directly (the pipe's write end wasn't enough to end the FastAPI process on its own).
`curl /health` confirmed down afterward.
