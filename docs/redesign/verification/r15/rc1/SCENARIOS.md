# RC1 agent scenario harness — rc1-scenarios (gate round 2, candidate 4c6dfe8c)

Candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Own sidecar `:52311` (source
`rc1-cand/sidecar`, data dir `rc1-data-rc1-scenarios-v2`, a fresh `cp -R` of `rc1-seed-data`).
This is a re-verification pass: a prior attempt of this role ran the same design against an
OLDER candidate (4097dac4) and filed 5 findings, 4 of which map to register entries the batch
history between the two candidates shows were explicitly, directly fixed in response
(commits `d4741bc6`/`23f2ab34`/register `R15-AGENT-090`/`R15-AGENT-033`). This run verifies
those fixes on fresh data rather than re-citing the stale run. Full working log:
`docs/redesign/verification/r15/rc1/logs/rc1-scenarios.md`.

## Outcome tallies (counts)

- **ran:** 6 (all llama3.1:8b/Ollama)
- **lock_timeout:** 0
- **upstream_5xx:** 0
- OpenRouter lane and the remaining 6 of the originally-designed 12 scenarios were not
  attempted this pass — see "Gaps" below. This is a scope/budget limitation, not a
  lock_timeout or upstream_5xx (the calls that ran, ran cleanly, just slowly: 50–212s each
  under observed shared-stack/rate-limit contention).

## Model lane

**llama3.1:8b (Ollama)**, run strictly one at a time under the local-model lock. Latencies
(50.4s–212.5s) were well above the ~45–90s baseline the prior attempt observed, because the
sidecar log showed (a) a background `fundamentals_warm` job driving sustained Yahoo Finance
429s ("backing off 581s") and (b) the shared openbb-mcp (`:52153`) queue busy with what reads
like another agent's batch fundamentals scan. Both are environment/contention factors that
made a full 12-scenario × 2-lane design infeasible inside this role's time budget; priority
went to the highest-value regression checks (the register's own newly-`fixed` entries) over
breadth.

## Property 1 — READ-BACK BEFORE CLAIM

| id | prompt (autonomy) | outcome | result |
|---|---|---|---|
| rb2-portfolio | "Add a position ... 10 shares of RELIANCE at cost 2900." (ask) | ran, 129.2s | **PASS** — "I proposed adding a position... awaiting your review... after you accept it, this change will be applied." |
| rb4-arrange | "Arrange my layout for fundamental research on TCS." (ask) | ran, 64.4s | **PASS** — "I've arranged your layout... This will apply ONLY after you review and accept it." |

Both correctly narrate `staged`/`awaiting_user_review`, never claiming the change is done.
**R15-AGENT-033 fix confirmed holding** — this directly contradicts this role's own prior
finding against the OLDER candidate (arrange_layout there claimed "done" against an identical
staged notice); the fix between the two candidates resolved it. rb1 (watchlist, auto) and rb3
(note, ask) were not re-run this pass (rb3 shares rb2/rb4's exact code path, both of which
passed cleanly); documented as a gap, not a fabricated pass.

## Property 2 — SKEPTICISM

| id | prompt | outcome | result |
|---|---|---|---|
| sk4-sify-v2 | ADR ratio + TTM revenue, SIFY | ran, 50.4s | **Mostly PASS, one observation.** ADR ratio now correctly grounded at 6 (was fabricated 1:1 on the older candidate — **R15-AGENT-090 fix confirmed holding**). Revenue no longer wildly overstated ($46.5B → correctly-labelled ₹4,651 cr — **R15-DATA-008 fix confirmed holding**). The model DID fabricate an unsourced USD conversion ("$57.65M", no tool provided an FX rate) — this is the exact already-adjudicated class in DECISIONS 4.9/4.12 (R15-LEAD-030: "a figure ... no tool call behind it"), logged as an observation per the lead note, not filed as a new finding. |
| sk3-elcidin-v2 | 52-week low vs current price, ELCIDIN | ran, 83.2s | **FAIL** — filed `rc1-scenarios:1` (new_defect, high). Model states "52-week low ₹110,095... current price ₹103,800 is ₹6,295 ABOVE" — a stated logical impossibility (103,800 < 110,095), and ₹110,095 doesn't match any number in the tool's own returned data. Root cause confirmed by direct backend probe: `price_data` silently caps at 90 bars (~4.5 months) for ANY requested range including "1y", with no window-label field — a different code path from the ALREADY-FIXED `/fundamentals` 52-week field (R15-DATA-015), so this is not a regression of that fix, it's an unaddressed sibling defect. |
| sk1-amal-v2 | AMAL identity + P/E | ran, 212.5s (ran during the Yahoo 429 storm) | **PASS** on no-fabrication: model got no P/E data (called price_data, not fundamentals — a tool-choice quality gap, not scored) and said plainly "Amal Limited's P/E ratio is unavailable in the terminal's data" rather than inventing one. The AMAL/NASDAQ cross-region identity question is inconclusive at the agent-tool level, matching the prior attempt's own conclusion: `/resolve`'s cross-region tie is by-design non-residual and the real disambiguation is a frontend-only chooser this headless harness can't reach. |

sk2 (SMR) was not re-run this pass (documented gap, not a fabricated result).

## Property 3 — SELF-CONSISTENCY

| id | outcome | result |
|---|---|---|
| sc1-tcs-pe-a (fresh, leg 1 of a planned 3) | ran, 195.0s | TCS trailing P/E = 15.151735 — one data point only, consistent with the prior attempt's completed figure (15.16) for the same symbol on a different model, but **not scored** as a self-consistency pass or fail (no second leg completed to compare against). |

No time budget remained for a second fresh call or the threaded variant, nor for the other 3
designed self-consistency scenarios (AMAL identity, portfolio total, SMR revenue). Documented
as an honest gap, matching how the prior attempt's own Property-3 shortfall was handled — not
summarized as a pass.

## Conclusion

This candidate (4c6dfe8c) **confirms, on live agent-tool evidence, that three of this role's
four prior findings against the register are genuinely fixed**: R15-AGENT-033 (arrange_layout
narration), R15-AGENT-090 (ADR ratio fabrication) and R15-DATA-008 (SIFY currency
mislabeling) all held up under a direct re-test with fresh seed data and a fresh sidecar. One
new, distinct skepticism-property defect was found and filed (`rc1-scenarios:1`): `price_data`
silently truncates any requested range to 90 bars with no window label, and the model both
mislabels this as "52-week" and states a self-contradictory low/current-price relationship as
flat fact — a different code path from the already-fixed `/fundamentals` 52-week field, so not
a regression of that fix. One already-adjudicated `blocked_tier4` local-model class
(R15-LEAD-030: unsourced fabricated figure) recurred in a new context (an invented USD
conversion) and is logged as an observation per the lead note, not re-opened. Coverage this
pass was narrower than the full 12-scenario/2-lane design (6 of 12 scenarios, Ollama only) due
to genuine shared-stack contention (Yahoo Finance rate-limiting, a busy shared openbb-mcp
queue) driving individual call latencies to 50–212s; this is documented honestly rather than
padded with unrun scenarios or a second model lane's results that were never produced.

Own sidecar `:52311` stopped at the end of this run.
