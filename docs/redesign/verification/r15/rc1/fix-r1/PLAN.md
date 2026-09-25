# RC1 fix round 1 — triage plan

Triage lead: rc1-fix-r1-triage (Opus). Base `4097dac4` (sidecar/src are byte-identical at
`29b9ae9b`). Reproductions ran on my own sidecar `:52331` (rc1-cand source, seed-data copy
`rc1-data-rc1-fix-r1-triage`) and in-process with the rc1-cand venv. Scratch output:
`scratchpad/triage/`. Working log: `../logs/rc1-fix-r1-triage.md`.

12 findings: **7 real** in 4 file-disjoint writer sets, **5 rejected**, **0 deferred**.

## Writer sets

### W1 research-coverage (opus): rc1-drive-research-briefs:1, rc1-battery-4:1

Files: `sidecar/services/research/deep.py`, `sidecar/services/research/iter.py`,
`sidecar/services/research/fast.py`, `sidecar/services/agent_tools/deep_research.py`,
`sidecar/tests/test_research_deep.py`, `sidecar/tests/test_research_fast.py`.

- **research-briefs:1 (confirmed from the evidence).** `deep.web_only_floor_note` (deep.py:301)
  and the heavy-panel copy (iter.py:1169-1174) decide "web sources alone" from the up-front
  snapshot only (`structured_feeds_available`). A researcher `price`/`fundamentals` leg that
  later succeeds (`_record_structured`, deep.py:438, sets `findings.coverage[dim]` and appends
  `vysted://<dim>/<SYM>`) is ignored. BDL deep brief: snapshot legs both timed out, the brief
  cites `vysted://price/BDL` as [6], and it still carries the note. Fix: the note applies only
  when no structured price or fundamentals source was gathered anywhere in the run. For deep,
  that means the snapshot OR `findings.coverage`/`structured_sources`. For iter, it means the
  snapshots OR `merged_sources` holding a `vysted://price|fundamentals/` url.
  Tests: (a) deep, where the snapshot failed but the findings hold `vysted://price/BDL`, so
  there is no note. (b) The iter synth path, where the snapshots failed but a merged
  `vysted://fundamentals/` source exists, so there is no note. (c) Both paths still add the
  note when only web sources exist.
- **battery-4:1 (reproduced, mechanism corrected).** The in-process runs were cold and on the
  rc1-cand venv. `price_data` alone took 10.8 s (9 paced NSE waits: cookie warm-up, 3
  history windows for the default 6mo range, and the quote). `fundamentals` alone took 11.3 s.
  Run under gather they took 20.4 s. `snapshot_structured` then dropped BOTH legs at 6 s
  (BHEL, COALINDIA, NTPC, POWERGRID). So each leg alone already overruns the box when cold.
  Throttle queueing only makes it worse. Cutting the price range to 5d did not help (A/B, NTPC).
  The root cause is that `_WITNESS_LEG_TIMEOUT_S` = 6 s is the FAST/NORMAL FR-070 budget, but
  the same box governs the snapshot on the DEEP (180 s wall), iter/heavy and Tier-B paths.
  There it throws away the metric cards for nothing. Fix: `snapshot_structured` takes the
  leg time box from its caller. FAST keeps 6 s. The deep, iter, heavy and deep_research callers
  pass a longer box (≤ 25 s, and well inside their wall). Do not touch the nse_direct pacer:
  it is an intentional anti-bot measure (R15-DATA-066).
  Test: a fake `tool_call` whose price leg resolves after longer than the FAST box. The
  snapshot is ok under the longer box and dropped under the default box. Monkeypatch the
  boxes small, so the test never sleeps seconds.
- Why opus: this is research-runtime timing against the wall budgets, and the note is an
  honesty surface. The fix must not let the FAST path exceed FR-070.

### W2 agent-model-boundary (opus): rc1-scenarios:5, rc1-drive-onboarding-stranger:1

Files: `sidecar/services/agent_runtime.py` (only `_model_facing_content` / `_RESEARCH_TOOLS`),
`sidecar/services/agent_tools/research.py`, `sidecar/services/llm/tool_call_rescue.py`, and
their tests (`sidecar/tests/test_research_semantics.py` or `test_agent_runtime.py`, and
`sidecar/tests/test_llm_openai.py` or a new `test_tool_call_rescue.py`).

- **scenarios:5 (revenue half, reproduced).** `/fundamentals/SIFY` correctly carries
  `currency: USD` and `financial_currency: INR`, and P/S is withheld. But
  `_model_facing_content` (agent_runtime.py:957) only applies the R15-AGENT-001 money
  projection (`research.model_view`) to the `research` tool. The direct `fundamentals` tool
  hands the model a raw `revenue_ttm: 46506049536.0` next to `currency: "USD"`, and two models
  then stated "$46.51 billion USD". This is the same defect class as AGENT-001, on a sibling
  tool. Fix: apply the money projection (statement sizes in `financial_currency ?? currency`
  via `semantics.display_value`, and trading-currency money such as `market_cap` in
  `currency`) to every tool result that carries a Fundamentals dump, meaning `fundamentals`
  and `compare_symbols`.
  Tests: a SIFY-shaped `fundamentals` result reads `₹4,651 cr` for revenue, not the raw float.
  The same holds for a `compare_symbols` result (a case the fix was not written against).
- **scenarios:5 ADR-ratio half: not fixable in product.** None of the tools carries an ADR
  ratio, and copilot.json rule 2 already forbids inventing figures. Both small models broke
  that rule. This half is recorded as a model-capability issue and is not fixed by W2.
- **onboarding-stranger:1 (confirmed from the evidence).** `rescue_leaked_tool_call` only
  parses JSON `{"name", "arguments"|"parameters"}` blocks. llama3.1:8b leaked the call as
  call syntax (`price_data(symbol="ZOMATO.NS")`) with a hand-typed result, so nothing ran.
  This is the R15-AGENT-018 class in a new form. Fix: also rescue a
  `<offered_name>(k=<literal>, ...)` call, parsed with `ast` and literal values only. Only
  names offered this round are rescued, and anything that does not parse stays text.
  Tests: the Zomato text rescues to `price_data {"symbol": "ZOMATO.NS"}`. A second form
  (a fenced multi-kwarg `fundamentals(symbol="TCS.NS")`) also rescues. Prose that mentions
  `research(X)` with a bare name, or a name not offered, does not fire.
  Not in scope, logged as an issue: the fabricated result that already streamed stays visible.
- Why opus: this is the agent-runtime tool boundary. A false-fire rescue would run tools the
  user never asked for.

### W3 fundamentals-derived (sonnet): rc1-datapack:1

Files: `sidecar/services/yfinance_provider.py`, `sidecar/tests/test_yfinance_provider.py`.

- **Reproduced.** `/fundamentals/SIFY` on :52331 returns `pe_ratio -103.15` with
  `field_meta {status: ok, provider: derived, basis_note: "price / EPS"}`. The guard at
  yfinance_provider.py:695 is `if fund.pe_ratio is None and fund.ratio_price is not None and
  fund.eps:`, which lets a negative EPS through. Fix: derive only when `eps > 0`. Otherwise
  leave `pe_ratio` None, with field_meta stating that it is not meaningful for a loss-making
  company (negative EPS). Use the existing unavailable / not-applicable vocabulary.
  Tests: a SIFY-shaped fixture (eps -0.13) gets no P/E and a stated reason. A second fixture
  (VERTEX-shaped, eps -0.25) gets the same. A positive-EPS fixture still derives price / EPS.

### W4 portfolio-and-docs (sonnet): rc1-drive-portfolio-notes:1, rc1-gate8:1

Files: `src/modules/portfolio/PortfolioPanel.tsx`, `src/modules/portfolio/PortfolioPanel.test.tsx`,
`docs/PHASE_10_HANDOFF.md`, `docs/README.md`.

- **portfolio-notes:1 (confirmed by code read).** PortfolioPanel.tsx:255-259 bumps
  `quotesNonce` every 5 s whether or not the previous fetch is still in flight. The
  `cancelled` flag in the fetch effect (:224-248) only gates the state write, so every tick
  starts another full per-symbol fan-out on top of the one still running. Fix: mirror
  WatchlistPanel's `inFlightRef` guard (WatchlistPanel.tsx:182-251), so a tick is skipped
  while the previous fan-out has not settled.
  Test (vitest, fake timers): quotes never resolve, advance 3 intervals, and `sidecarApi.quote`
  is called once per holding, not 4 times. Once they resolve, the next tick refetches.
- **gate8:1 (confirmed).** docs/README.md:32 indexes PHASE_10_HANDOFF.md as the "Latest phase
  handoff". Its §3 (:116-141) tells users to connect Kite, lists `/brokers/*` routes and names
  `broker_portfolio`, and the file has no D81 notice. Fix: add a D81 removal banner at the top
  of the handoff and at §3, worded like docs/BROKER_INTEGRATIONS.md. Mark the README row as
  historical. Do not move the file, because CURRENT_STATE.md and archive/README.md link it.
  Run `pnpm exec prettier --write` on both files.
  Check: `grep -n D81 docs/PHASE_10_HANDOFF.md` hits both at the top and in §3.
  `pnpm format:check` passes.

## Rejected (evidence)

- **rc1-scenarios:1: not a regression.** On :52331, `/fundamentals/SIFY` returns
  `currency USD`, `financial_currency INR` and `price_to_sales` withheld (it "mixes bases").
  That is the register's fix_shape option 2, and the UI and brief format these values in
  `financial_currency ?? currency` (EquityOverviewPanel.tsx:833, brief-blocks.tsx:336). The
  agent-path misstatement is real, and W2 closes it under rc1-scenarios:5.
- **rc1-scenarios:2: not a regression.** Both 52-week bounds are served `status: flagged`,
  with the reason "…disagrees with the NSE + BSE exchange range 87,003.00-144,500.00 since
  2025-09-10". That is exactly the certified batch-5 outcome (stage-c/batch-5/VERDICTS.md:123-125,
  "the flag is the honest outcome"). The window and venue are stated in the reason.
- **rc1-scenarios:3: not a regression.** The runtime emits the certified end-of-turn notice
  ("Staged for your review, not applied yet: arrange_layout TCS") at the end of the stream.
  The tool result for arrange_layout is byte-identical to the portfolio_add_position and
  write_note results that the same model hedged correctly (agent_runtime.py:1570-1582). The
  gap is llama3.1:8b narration variance, which the certified fix explicitly covers with the
  deterministic notice.
- **rc1-scenarios:4: the number is not served data.** `price_data` returns no 52-week field.
  It returns 90 bars with `bars_available` and `window_start`, and the served bars' minimum
  low is 102,210 (/history ELCIDIN.NS 1y on :52331). The model's "52-week low ₹106,505"
  matches no served value. It is a llama3.1:8b computation or hallucination against the
  existing grounding rule, not the R15-DATA-015 mechanism.
- **rc1-drive-portfolio-notes:2: not a defect.** The record itself concludes that this is
  harness drift against the new ConfirmButton arm/confirm gate, and that R15-UI-035 still holds.

## Issues outside the entries (not in any diff)

- The scenarios:5 ADR-ratio fabrication. No product data source has the ratio, and the
  grounding rule already exists. This is a model-capability limit.
- The fabricated tool result that a leaked-call model already streamed stays in the
  transcript even after a rescue (W2 note).
- `nse_provider.get_archive_text` (:747-749) and `_SessionHolder.ensure` (:261) call
  `_throttle.wait()` while holding the module `_lock`. The R15-DATA-066 rule is "pace before
  the lock", so a queued archive fetch blocks every other nse_direct caller for its whole wait.
- The SAIL/ONGC traces show `nse_direct` quote-equity stalling for about 11 s before the
  history fallback, and the NSE cookie warm-up failing with a connection reset. Yahoo's
  getcrumb returned 429 at probe time. These are environment conditions during triage.
