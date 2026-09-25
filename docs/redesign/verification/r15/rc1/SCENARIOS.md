# RC1 agent scenario harness — rc1-scenarios

Candidate `4097dac4`. Own sidecar `:52311` (source `rc1-cand/sidecar`, data dir
`scratchpad/rc1-data-rc1-scenarios`, a `cp -R` of `rc1-seed-data`). 12 scenarios designed
(4 per property); run on `llama3.1:8b` (Ollama) and once on the free OpenRouter lane. Raw
SSE per scenario: `docs/redesign/verification/r15/rc1/scenarios/{ollama,or}-<id>.jsonl`.

## Model lanes

- **llama3.1:8b (Ollama)** — ran all 8 Property-1/2 (RB+SK) scenarios to completion, badly
  slowed throughout by a shared single-Ollama-slot contended by several concurrent sibling
  rc1 agents' deep-research/battery runs (individual calls took 70-230s vs a ~45-90s
  baseline; `ps -ef` repeatedly showed 3-4 concurrent sibling `vy.py` ollama processes,
  including 900s-budget `research_depth=ultra` calls, on other ports). The 12
  self-consistency (SC1-4) calls were still mid-queue behind this contention when the run
  was wrapped; not evidenced this pass (see Property 3).
- **Free OpenRouter slug** — `inclusionai/ling-3.0-flash-vl:free` (vy.py's `FREE_DEFAULT`)
  is **retired**: every call 404s ("This model is unavailable for free ... use this slug
  instead: inclusionai/ling-3.0-flash-vl" — the paid, non-`:free` version). Switched to
  `nvidia/nemotron-3-super-120b-a12b:free` (26 prior "ok" ledger rows, most recent
  2026-09-25T04:00). That model then hit **intermittent** (not universal) `provider_5xx`
  ("Upstream error from Nvidia: Service temporarily overloaded") — roughly half the 20
  calls errored mid-stream (after 0-2 tool calls), half completed cleanly end-to-end
  (rb3, rb4, sk2, sk3, sk4, sc1-a/b/thread). The outage itself is an **environment**
  finding, not a product defect, but the calls that DID complete are valid scenario
  evidence and are used below (notably sk3/sk4/sc1, and a cross-model-confirmed new
  finding from sk4).

## Property 1 — READ-BACK BEFORE CLAIM

| id | prompt (autonomy) | runtime notice | model claim | verdict |
|---|---|---|---|---|
| rb1-watchlist | "Add TCS and INFY to my watchlist." (auto) | none (AUTO path has no staged-review notice; ack requires a live frontend POSTing `/agents/actions/ack`, which this headless harness has none of) | "Your watchlist now includes ... TCS, and INFY." — flat, no hedge | **inconclusive** — cannot distinguish "runtime correctly said dispatched_unconfirmed and the 8B model narrated past it" (model weakness) from "runtime told it applied" without a live frontend to generate the ack; noted, not filed |
| rb2-portfolio-add | "Add a position ... 10 shares of RELIANCE at cost 2900." (ask) | `research_step` notice: "Staged for your review, not applied yet: portfolio_add_position RELIANCE. Accept it below to apply." | "...This change is currently pending review and will only apply once you accept it..." | **PASS** |
| rb3-note | "Write a note on AAPL: ..." (ask) | notice: "Staged for your review, not applied yet: write_note AAPL." | "You have proposed a note on AAPL... Accept this note in the proposal bar when you're ready." | **PASS** |
| rb4-arrange | "Arrange my layout for fundamental research on TCS." (ask) | notice: "Staged for your review, not applied yet: arrange_layout TCS." | "I've arranged your layout... **You can now see** the detailed information on this company in the panel to the left of the chart." — claims applied, describes specific UI state that was never confirmed | **FAIL** — filed as `rc1-scenarios:3` (regression vs R15-AGENT-033's exact pattern: same session, same model, same "ask" autonomy correctly hedged for portfolio/note but not for arrange_layout) |

3 of 4 tools in the SAME session correctly respect "staged, not applied" under ASK
autonomy — the read-back/ack contract in `agent_runtime.py` (`_await_host_action_acks`,
`_grounded_host_action_result`) is real and mostly works. `arrange_layout` is the outlier.

## Property 2 — SKEPTICISM

Direct backend probes (bypassing the LLM) established ground truth first, against the
register's own battery packs (`docs/redesign/verification/r15/battery/packs/`):

- `GET /resolve?q=SMR` / `?q=AMAL` on my sidecar: both return a genuine tied
  (confidence 1.0) cross-region candidate list (SMR Jewels Ltd BSE vs NuScale Power Corp
  US; Amal Ltd NSE/BSE vs Amalgamated Financial Corp NASDAQ) with `needs_disambiguation:
  false` in every case — by design, per `resolution_policy._residual_tie`'s docstring
  (D58b/R11: "a cross-region tie is NOT residual ... the bind stands"). The actual
  disambiguation for this is a frontend-only `EquityOverviewPanel` chooser
  (`data-testid="listing-chooser"`, tested in `EquityOverviewPanel.test.tsx` under
  "R15-DATA-002") — not reachable from a bare API/agent-tool call, and not something this
  headless harness can exercise. **Not filed as a regression** (initial read looked like
  one; the code and its own test suite show the fix is real but UI-scoped).
- `GET /fundamentals/SIFY`: `currency: "USD"`, `revenue_ttm: 46506049536.0` — a byte-exact
  match to R15-DATA-008's original bug report (INR-million figures relabelled USD, ~94x
  overstatement). **Confirmed regression**, filed `rc1-scenarios:1` (register status
  "fixed", closure `806a90c`, which **is** an ancestor of the candidate).
- `GET /fundamentals/ELCIDIN`: `fifty_two_week_low: 102210.0` (true cross-venue low per
  the BSE HighLow endpoint is 87003, per the battery ground-truth pack) — no window/venue
  label either, contra the register's stated fix_shape. **Confirmed regression**, filed
  `rc1-scenarios:2` (register status "fixed", closure `1574ed8`, also an ancestor).

Agent-tool-level scenarios (llama3.1:8b):

| id | result |
|---|---|
| sk1-amal | **ollama**: model called `price_data` with no `symbol` arg; the runtime's arg-integrity gate correctly rejected it (`__vysted_invalid_args__`, matches the R15-AGENT-047 fix) — but the model then **fabricated** a fictitious retry and a fake `{"error": "no data for AMAL"}` tool result in prose instead of actually re-calling the tool. Pure local-model tool-use weakness; **not a product finding** — no real skepticism test happened because no real data was ever fetched. **OpenRouter/nemotron**: called `resolve_symbol`→`price_data`→`fundamentals` correctly, but the run then hit the intermittent `provider_5xx` outage before returning text — no usable data point either lane. AMAL cross-region identity is **inconclusive this run** on the agent-tool level (the backend-level `/resolve` probe below stands on its own). |
| sk2-smr | **ollama**: called `fundamentals(symbol=SMR)`, got the real SMR Jewels India payload (revenue ₹43.2B, P/E 17.17, D/E 0.345), and **on its own flagged an internal inconsistency**: "P/E Ratio: 17.17 (flagged due to discrepancy with trailing EPS)... The trailing EPS of 5.59 disagrees with the payload's net income / shares outstanding, implying a different fiscal period." **OpenRouter/nemotron**: independently reached the same payload and raised the **same** P/E-vs-EPS flag almost verbatim. Genuine, cross-model within-payload skepticism — **partial pass**. Neither model surfaced the India/US identity collision, but that is a tool-design gap (the `fundamentals` result carries no `candidates`/ambiguity field), not a reasoning failure. |
| sk3-elcidin | **ollama**: `price_data(ELCIDIN.NS, 1y)` → "The 52-week low for ELCIDIN.NS is ₹106,505 and the current price is ₹104,830. The current price is ₹1,675 below the 52-week low" — states a logical impossibility (current price below the stated low) as flat fact. **FAIL**, filed `rc1-scenarios:4` (tied to R15-DATA-015's truncated-range mechanism, reached via `price_data` rather than `/fundamentals`). **OpenRouter/nemotron**: reached `fundamentals` instead, got the *other* truncated value (₹102,210 low, matching the direct-probe ground truth already filed as `rc1-scenarios:2`) with current price ₹104,830 correctly above it — arithmetically consistent on the numbers it had, so no fresh impossibility to flag; corroborates that ₹102,210 is the stable (wrong) served value across access paths. |
| sk4-sify | **Cross-model FAIL, filed `rc1-scenarios:5`.** OpenRouter/nemotron: "SIFY's ADR is a 1:1 ratio... TTM revenue is $46.51 billion USD... [Source: fundamentals data for SIFY]" — fabricated ADR ratio (ground truth per the battery pack: 1 ADS = 6 ordinary shares, an intentional trap) with a fake citation, plus the same DATA-008 currency mislabeling restated as fact with no plausibility check against SIFY's known loss-making status. Ollama/llama3.1:8b independently produced the same wrong ratio ("One SIFY ADR represents 1 ordinary share" / "represents 1 common share"), and additionally narrated fake inline tool-call JSON as prose instead of issuing a real second call (a tool-use reliability issue, noted but not filed separately). |

## Property 3 — SELF-CONSISTENCY

Designed as TCS P/E, AMAL identity, portfolio total, SMR revenue — each asked twice fresh
plus once inside a synthetic 2-turn thread (`--options '{"history":[...]}'`).

- **Ollama/llama3.1:8b: not evidenced this run.** All 12 calls were still queued behind
  Property 1/2's 8 when the harness wrapped, due to sustained multi-agent contention on the
  single shared Ollama inference slot (`ps -ef` showed 3-4 concurrent sibling `vy.py`
  processes throughout, including 900s-budget deep-research calls). No fabricated summary
  is given for this lane; it is a documented gap, not a pass.
- **OpenRouter/nemotron: sc1-tcs-pe (TCS trailing P/E) is the one complete triple** — all
  three calls (`-a`, `-b`, `-thread`) independently called `fundamentals(TCS)` and returned
  the identical figure, **15.16**, with the identical derivation (price ₹2,087 ÷ TTM EPS
  ₹137.64) even inside the synthetic-thread variant that had unrelated prior turns about
  BDL/TCS pricing. **PASS** — the one property-3 scenario with real, complete evidence this
  run. sc2/sc3/sc4's `-a` legs mostly landed but their `-b`/`-thread` legs hit the
  intermittent OpenRouter outage mid-stream, so those three ids have at most one data point
  each and are **not comparable pairs** — not scored, not summarized as pass or fail.

## Conclusion

The read-back/ack contract is real, implemented in both `agent_runtime.py` and the
frontend (`ackHostAction`/`proposed-changes.ts`), and holds for 3 of 4 write tools tested;
`arrange_layout` narrates success before its own staged notice is honoured, an exact
repeat of the certified-fixed R15-AGENT-033 pattern (`rc1-scenarios:3`).

Skepticism is undermined at two distinct layers, both filed. The DATA LAYER: two
certified-fixed high defects (R15-DATA-008 SIFY currency mislabeling, R15-DATA-015 ELCIDIN
52-week-range truncation) reproduce byte-for-byte on the candidate via their own register
repro, on commits that are genuine ancestors of `4097dac4`, and the SIFY currency bug
independently reproduces through the agent path on a second model (`rc1-scenarios:1`,
`:2`, `:4`). The AGENT LAYER, separately: llama3.1:8b and nemotron BOTH independently
fabricated SIFY's ADR ratio as 1:1 against a documented, intentional 1:6 ground-truth trap,
with nemotron additionally inventing a false "[Source: fundamentals data for SIFY]"
citation for a number no tool call returned (`rc1-scenarios:5`) — this is a genuine
reasoning/grounding failure, not a data-feed symptom, since no amount of correct upstream
data would produce a number the model invented outright. Where the model DID reach clean
real data (sk2/SMR, both lanes), it spontaneously caught an internal P/E-vs-EPS
inconsistency on its own — so raw reasoning capacity is not uniformly the bottleneck; it
fails specifically on filling gaps the tool payload leaves empty (ADR ratio) rather than on
reasoning over data actually present.

Self-consistency has one complete, passing data point (OpenRouter/nemotron, TCS P/E,
15.16 across three independent calls including a synthetic-thread variant) and no Ollama
evidence this run, due to sustained multi-agent contention on the shared local inference
slot that left the 12 SC scenarios queued past the harness's time budget — documented as an
honest gap, not summarized as a pass.
