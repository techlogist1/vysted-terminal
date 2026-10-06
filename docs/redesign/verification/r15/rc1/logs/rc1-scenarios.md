# rc1-scenarios working log — gate round 2 (candidate 4c6dfe8c)

A prior attempt of this role (mtimes 25 Sep, this file's git history) ran the same 12-scenario
design against an OLDER candidate (4097dac4) and filed 5 findings there. Between 4097dac4 and
the current candidate (4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2, 297 commits) two of those
findings were directly, explicitly fixed: `d4741bc6`/`23f2ab34` ("fix(rc1): ... (rc1-scenarios:5)")
project fundamentals/financial_statements/compare_symbols money fields to currency-labelled
display strings for the model, and the ADR-ratio tool result now carries a sourced `ads_ratio`
field (R15-AGENT-090, register status `fixed`). R15-AGENT-033 (arrange_layout narrating "done"
against a staged notice) is also register status `fixed`. This run's job was to verify those
fixes actually hold on the fresh candidate, not re-litigate a stale one — so seed data and
sidecar were rebuilt fresh (`rc1-data-rc1-scenarios-v2`, sidecar on :52311 from `rc1-cand`
sha 4c6dfe8c) rather than reusing the prior attempt's now-stale artifacts.

## Mechanism verification (direct backend probes, before any LLM call)

- `services.agent_tools.fundamentals._fundamentals({"symbol":"SIFY"})` then
  `services.agent_tools.research.fundamentals_content(...)`: raw revenue_ttm 46,506,049,536
  (a plain float, currency USD / financial_currency INR) projects to `"₹4,651 cr"` for the
  model, and the result now carries `ads_ratio: {ordinary_shares_per_ads: 6, statement:
  "American Depositary Shares, each represented by Six Equity Shares", provenance: {source:
  "SEC 20-F cover page", ...}}`. Both R15-DATA-008 and R15-AGENT-090's fix mechanisms are real
  and reach the model-facing tool content, not just the register's own commit message.
- `services.agent_tools.price_data._price_data({"symbol":"ELCIDIN.NS","range":"1y"})`: capped
  at 90 bars regardless of the requested range (`bars_returned:90, bars_available:111,
  window_start:2026-05-20` — ~4.5 months for a "1y" request), no 52-week/window-label field.
  This is a DIFFERENT code path from `/fundamentals`'s `fifty_two_week_low` (which R15-DATA-015
  did fix, with a `"flagged, kept"` annotation) — `price_data.py` has zero mentions of
  fifty_two_week/flagged/reason. Confirmed this before spending an LLM call on it.

## Own sidecar

`:52311`, source `rc1-cand/sidecar` (candidate 4c6dfe8c), data dir `rc1-data-rc1-scenarios-v2`
(fresh `cp -R` of `rc1-seed-data`), sleep-wrapper pid 58290. `/health` ok. Stopped at the end of
this run (see SCENARIOS.md).

## Scenarios run (llama3.1:8b / Ollama, one at a time under the lock)

5 completed end-to-end; a 6th (self-consistency second leg) was not attempted after the first
five calls' latencies made the property-3 pair/thread design infeasible inside this role's
budget (see SCENARIOS.md "gaps"). Latencies were 50–212s per call, well above the
prior-attempt's own ~45–90s baseline, and the sidecar log showed a `fundamentals_warm`
background job hammering Yahoo Finance into sustained 429s ("backing off 581s") plus a shared
openbb-mcp queue busy with what looks like another agent's batch fundamentals scan — both
environment/contention factors, not product defects, but they are why this run's scenario count
is smaller than the full 12-per-property design.

1. **rb4-arrange** (arrange_layout, ask) — 64.4s. Model: "I've arranged your layout... This
   will apply ONLY after you review and accept it." Correctly hedged. **PASS** — R15-AGENT-033
   fix holds, no regression (contradicts this role's own prior finding against the old candidate).
2. **sk4-sify-v2** (ADR ratio + TTM revenue) — 50.4s. Model: "...6 ordinary shares... SIFY's
   TTM revenue in USD is ₹4,651 cr, which is approximately $57.65M." The ADR ratio (6) is now
   correct and grounded (R15-AGENT-090 fix holds — a large improvement over the old candidate's
   fabricated 1:1). The revenue figure is no longer the wild 94x-overstated $46.5B (R15-DATA-008
   fix holds). BUT the model still garbled the ratio sentence ("not available... 6 ordinary
   shares") and fabricated an unsourced USD conversion ($57.65M — no tool gave an FX rate or a
   USD figure). That fabricated-figure pattern is the exact class DECISIONS 4.9/4.12 already
   adjudicated `blocked_tier4` under R15-LEAD-030 ("a figure ... no tool call behind it") — per
   the lead note, logged here as an observation, NOT filed as a new finding / fix round.
3. **sk3-elcidin-v2** (52-week low vs current price) — 83.2s. **FAIL** — filed `rc1-scenarios:1`
   (new_defect, high). See findings file for detail: a stated logical impossibility (current
   price below the model's own stated "low", captioned as "above" it) plus a low figure that
   doesn't match the tool's own returned data.
4. **rb2-portfolio** (portfolio_add_position, ask) — 129.2s. Model: "I proposed adding a
   position... awaiting your review... after you accept it, this change will be applied."
   **PASS**.
5. **sk1-amal-v2** (AMAL identity + P/E) — 212.5s (slowest; ran during the fundamentals_warm
   429 storm). Model called resolve_symbol then price_data (not fundamentals — a tool-choice
   quality gap, not scored as a finding), got no P/E data, and said "Amal Limited's P/E ratio is
   unavailable in the terminal's data" rather than fabricating one. **PASS** on the no-fabrication
   test; the AMAL/NASDAQ cross-region identity question itself is inconclusive at the agent-tool
   level (as in the prior attempt) — `/resolve`'s cross-region tie is by-design non-residual
   (`resolution_policy._residual_tie`, D58b/R11) and the real disambiguation is a frontend-only
   `EquityOverviewPanel` chooser this headless harness cannot reach; not filed, matches the
   prior attempt's own (correct) conclusion.
6. **sc1-tcs-pe-a** (self-consistency baseline, fresh) — 195.0s. "The trailing P/E ratio for
   TCS is 15.151735." One data point only (no time budget left for a second fresh call or a
   threaded variant) — consistent with the prior attempt's completed OpenRouter figure (15.16)
   for the same symbol, but NOT a scored self-consistency pass/fail on its own.

## Gaps (honest, not fabricated)

- Property 3 (self-consistency): only 1 of the designed 3-leg (fresh/fresh/thread) comparison
  completed for TCS P/E; AMAL identity, portfolio total and SMR revenue self-consistency were
  not attempted. Not scored as pass or fail.
- OpenRouter lane: not run this pass. Given 50–212s per Ollama call under observed contention,
  and this role's finite budget, priority went to confirming/refuting the register's `fixed`
  claims on Ollama (the model class every register regression here was actually caught on)
  rather than thinner coverage split across two model lanes. `or-*` scenario files from the
  PRIOR (stale, 4097dac4) attempt remain in the scenarios directory for reference only — they
  are NOT evidence for this candidate and are not cited in any finding here.
- rb1 (watchlist, auto autonomy) and rb3 (note, ask) were not re-run; rb3's code path is
  identical to rb2/rb4 (both of which passed cleanly this run), so it was deprioritised in
  favour of the skepticism/new-defect scenarios once time became the binding constraint.
