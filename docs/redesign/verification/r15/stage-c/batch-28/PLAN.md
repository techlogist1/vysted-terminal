# R15 Stage C — batch-28 plan

Base: `004-r4-experience-rebuild` @ `bf203553bd250293c1ae186ee696828794ec23a2`. D81 (trading out) is on the base.
Nothing here touches a trading surface, and nothing re-adds one.

**Selection.** The register has 32 OPEN entries at critical/high/medium (4 critical, 8 high, 20 medium). None is in the
exclusion list (`R15-RESEARCH-043`, `R15-DATA-059`, `R15-DATA-002`, `R15-AGENT-019`, `R15-AGENT-090`,
`R15-RESEARCH-007`, `R15-DATA-061`; the last four are `blocked_tier4` now). All 32 fit under the 40 cap, so all are
taken. 31 are planned as fixes and 1 (`R15-LEAD-046`) is proposed as not-a-defect for the verifier's fresh concurrence.
Nothing is deferred. Lows are not in this batch's severities, so LOWS_TRIAGE.json does not apply.

**Sources.** 26 entries were reopened, or filed, by the rc1 round-4 refutation audit
(`r15/rc1/refutation-audit/round-4/REFUTATION_AUDIT.{md,json}` plus the per-entry evidence files named there). Its
root cause, fix shape and acceptance test are the corrected mechanism, and they override each entry's original claim.
I re-opened every named site at the base and confirmed each mechanism below; where the audit is wrong, this plan says
so. `R15-DATA-008` comes from the round-4 datapack follow-up (`datapack-R15-DATA-008.md`). `R15-LEAD-045/046` come
from batch-27's "Issues noticed". I root-caused both with live probes on 27 Sep; the numbers are below.

**Classes kept together.** These are never split across writers:
- DATA-030 + RESEARCH-001: news alias tagging feeds the research news gate (W2).
- DATA-008 + LEAD-004: `correctness_gate` overlay and TTM labelling (W4).
- LEAD-022 + UI-090: "positively US" for a dotted symbol, one rule (W4).
- LEAD-044 + LIFECYCLE-020 + LEAD-045: the screener/warm Yahoo batch path (W5).
- CODE-FRONTEND-017 + UI-015: both in `src/store/sec.ts` (W6).
- RESEARCH-022: keyless challenge pages, fixed for mojeek and brave (W3).

## Writers at a glance

| W | model | entries | why this model |
|---|---|---|---|
| W1 | opus | AGENT-001, AGENT-092, AGENT-094, AGENT-095, LEAD-014 | Risk-adjacent. It covers the agent runtime state machine (the delegate-run halt and brief delivery), the ratio guard, and the tool-arg gate every adapter shares. |
| W2 | sonnet | RESEARCH-001, DATA-030, RESEARCH-027, DATA-063, DATA-113 | Each fix is specified, with a deterministic acceptance test. W2 owns `types/data.ts` and `types/earnings.ts`. |
| W3 | sonnet | DATA-003, DATA-024, DATA-038, RESEARCH-022 | Each fix is specified, with a deterministic acceptance test. |
| W4 | sonnet | DATA-008, LEAD-004, LEAD-022, UI-090, DATA-055 | Each fix is specified, with a deterministic acceptance test. |
| W5 | opus | LEAD-044, LIFECYCLE-020, LEAD-045, DATA-114, DATA-053 | LEAD-045 needed root-causing: the transport change has to keep the cookie and crumb paired, and it changes the batch test seam. LEAD-044 threads region through the shared screener fan-out and the persisted warm store (cross-session state). |
| W6 | sonnet | AGENT-053, AGENT-055, AGENT-096, CODE-FRONTEND-017, UI-015, UI-021, CODE-PLATFORM-017 | These are frontend fixes, each with a written vitest. |

**Common rules for every writer.**
- Branch: `worktree-agent-batch-28-W<n>`. First run `git reset --hard bf203553bd250293c1ae186ee696828794ec23a2`, then
  check `git log -1` (the worktree base hazard).
- Push every deliverable.
- Edit only the files you own.
- Run only the focused tests, and never run a full suite in the foreground. Anything over about 120 s runs detached
  and is polled.
- Before each Python commit, run `ruff format <files> && ruff format --check sidecar && ruff check sidecar`. Before
  each TS commit, run `pnpm prettier --check` on the files you touched, plus `pnpm typecheck`, detached. Before a
  Rust commit, run `cargo fmt --check` plus clippy, detached.
- Do not edit `CHANGELOG.md`, `docs/redesign/DECISIONS.md`, `CLAUDE.md`, `tauri.conf.json`, `.github/` or
  `types/plugin.ts`. Report every Tier-3 decision in your return. The integrator records the decisions.
- Where a test pinned the old, wrong behaviour, fix that test and say why in the commit body. Never skip or weaken a
  test.
- Anything you notice that is outside your entries goes in issues[], never into the diff.

---

## W1 — opus (agent runtime)

**Owned files:** `sidecar/services/agent_runtime.py`, `sidecar/services/agent_tools/research.py`,
`sidecar/services/run_manager.py`, `sidecar/services/llm/openai.py`.
Tests: `sidecar/tests/test_agent_runtime.py`, `sidecar/tests/test_b3_runtime_tool_args.py`,
`sidecar/tests/test_run_manager.py`, `sidecar/tests/test_llm_openai.py`.

### R15-AGENT-001 (critical): fraction fields reach the model as raw floats
- **Mechanism (confirmed).** `research.py:492-547`: `fundamentals_content` rewrites only
  `_STATEMENT_MONEY_FIELDS` plus `market_cap` to `display_value` strings. `model_view` (`:403-459`) rewrites only
  money. As a result `dividend_yield` 0.0082 reaches the model as a bare float, next to derived legs whose unit is
  "fraction", and the model reads it as 0.0082%. `semantics.display_value(v, "fraction", None)` already renders
  `"0.82%"`.
- **Fix.** Add one module constant `_FRACTION_FIELDS`, taken from the `models/fundamentals.py` docstring:
  - dividend_yield
  - revenue_growth, earnings_growth, revenue_growth_computed, earnings_growth_computed
  - roe, roa, roce
  - gross_margin, operating_margin, profit_margin
  - held_percent_insiders, held_percent_institutions
  - fifty_two_week_change

  In `fundamentals_content`'s holder loop (this covers compare rows), rewrite each numeric one with
  `display_value(v, "fraction", None)`. In `model_view`, apply the same rewrite to `structured.fundamentals.data`.
  The panel and auto-publish keep the raw payload.
- **Test.** Add `test_fundamentals_model_payload_renders_fractions_as_percent` to `test_agent_runtime.py`. Feed a
  COCHINSHIP-shaped result through `_model_facing_content("fundamentals", ...)` and assert:
  - `dividend_yield == "0.82%"`
  - `revenue_growth == "2.40%"`
  - `earnings_growth == "-19.37%"`
  - no fraction field is a float

  Class cases the fix was not written against: a `compare_symbols` row (`roe`, `profit_margin`), and
  `model_view` over a research payload's `structured.fundamentals.data` (`held_percent_insiders`).

### R15-AGENT-092 (high): a halted round's brief is still delivered
- **Mechanism (confirmed).** `run_manager.py:299-306`: `if name == "publish_brief": brief = dict(event.input)` runs
  ahead of the `undispatched` buffer. The brief is therefore stored when the tool_use is yielded, which happens
  before the halt check. `delegate-runs.ts` enqueues `output.brief` on `error` too, and AUTO applies it.
- **Fix.** `publish_brief` goes into `undispatched` like every other host action. In `_on_tool_result`
  (`nonlocal brief`), when the popped action is `publish_brief`, set `brief = action["input"]` and do not append it
  to `host_actions`. No frontend change.
- **Test.** Add `test_a_halted_rounds_brief_is_not_delivered`. Round 1 dispatches publish_brief
  `{title:'dispatched brief'}`. Round 2 publishes `'halted brief'` over `RunBudget(max_tokens=1000)`. Assert
  `row.status == 'error'` and `row.brief['title'] == 'dispatched brief'`. In the variant where round 1 is
  `write_note`, `row.brief is None`.

### R15-AGENT-094 (high): `_coerce` crashes on a union schema type
- **Mechanism (confirmed).** `agent_runtime.py:923`: `expected in _JSON_STRING_TYPES` hashes a list-valued `type`.
  The only such type is arrange_layout's `panels.items` `['string','object']`, so the result is TypeError and the
  whole turn dies.
- **Fix.** Add one guard at the top of `_coerce`: `if not isinstance(expected, str): return value`. The validator
  decides. No catalog change.
- **Test.** Add `test_union_typed_items_do_not_crash` to `test_b3_runtime_tool_args.py`. Run `_normalise_tool_args`
  on arrange_layout `{pattern:'custom', panels:['chart','news']}` and on the object-row form: the input is unchanged
  and there is no sentinel. Also walk every catalog capability schema that has a list-valued `type` and assert
  `_coerce` never raises on a sample value (the class guard).

### R15-AGENT-095 (medium): the ratio guard reads a date's day and month as share counts
- **Mechanism (confirmed).** `agent_runtime.py:1929-1954`: `_MARKED` blanks only a 4-digit year. `2026-06-26`
  therefore leaves `06` and `26` as count candidates, `_ratio_claim_traced` finds them unsourced, and a true, dated
  ratio sentence is replaced.
- **Fix.** Put one date alternative at the front of `_MARKED`, covering:
  - ISO `(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}`
  - numeric `\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)?\d{2}`
  - `<Month> \d{1,2}` and `\d{1,2} <Month>`, with full and 3-letter month names

  Because `_MARKED` is applied on both sides, source segments get the same treatment. Do not change the claim class.
- **Test.** Add `test_a_dated_sourced_ratio_is_kept`, parametrised over the audit's four sentences (ISO, "June 26,
  2026", 06/26/2026, "26 June 2026"). Each is kept against `_SIFY_FUNDAMENTALS_WITH_DEPOSITARY` and replaced against
  `_SIFY_FUNDAMENTALS`. `'As of 2026-06-26 each SIFY ADS represents 5 equity shares. '` stays replaced. Add one extra
  case the fix was not written against: "on 2026/06/26" with "Sep 3" wording.

### R15-LEAD-014 (medium): tool-arg repair accepts a type-name placeholder echo
- **Mechanism (confirmed).** `openai.py:569-573` rejects only a reply equal to the schema, or one keyed by
  JSON-Schema keywords. `{"symbol": "string"}` passes validation and is dispatched. `_repair_tool_args` is the only
  repair site (grep confirmed).
- **Fix.** After the existing echo check, return `None` when any value is a string equal to its own property's
  declared `type`, drawn from `{'string','number','integer','boolean','array','object','null'}`.
- **Test.** Add a parametrised test to `test_llm_openai.py`, beside
  `test_repair_rejects_a_schema_echo_on_a_tool_with_no_required_keys`:
  - `fundamentals` with `'{"symbol": "string"}'`
  - `resolve_symbol` with `'{"query": "string"}'`
  - `write_note` with `'{"scope": "string", "text": "string"}'`

  Each yields the INVALID_ARGS_SENTINEL. Controls: `news` `'{}'` and `fundamentals` `'{"symbol": "AAPL"}'` are
  still returned.

---

## W2 — sonnet (news, research legs, indicator/earnings contracts)

**Owned files:** `sidecar/services/news_provider.py`, `sidecar/models/news.py`,
`sidecar/services/research/relevance.py`, `sidecar/services/research/deep.py`, `sidecar/services/research/fast.py`,
`sidecar/models/indicators.py`, `sidecar/services/indicators.py`, `sidecar/services/earnings_provider.py`,
`sidecar/models/earnings.py`, `types/data.ts`, `types/earnings.ts`, `src/modules/earnings/*` (EpsEstimateGrid,
EarningsSurpriseChart, EarningsCalendarPanel and their tests), `src/store/earnings.ts` (null-currency handling only).
Tests: `sidecar/tests/test_news.py`, `sidecar/tests/test_research_deep.py`, `sidecar/tests/test_research_fast.py`,
`sidecar/tests/test_indicators.py`, `sidecar/tests/test_earnings_provider.py`.

### R15-DATA-030 (high): news symbol tagging matches tickers case-insensitively
- **Mechanism (confirmed).** `news_provider.py:575-608`: `_aliases` keeps every 2+ character ticker. `_tag_symbols`
  matches every alias with `re.IGNORECASE`, so:
  - IT matches "it's"
  - RELIANCE matches "Reliance Power"
  - LT matches "LT Foods"
  - ITC matches "ITC Hotels"
- **Fix.**
  1. Return the aliases as two kinds, tickers and a name. Match tickers case-sensitively, as uppercase tokens. Match
     only the company name case-insensitively.
  2. Drop a bare-ticker text alias when the ticker is the first word of a different company's name in the resolver
     masters (NSE/BSE/US), for example LT → "LT Foods" and ITC → "ITC Hotels". Those symbols are then tagged by
     name or by per-symbol-feed provenance.
  3. Keep the `build_aliases` signature, or update its callers inside `news_provider.py` only. Grep first:
     `agent_tools/news_tool.py` and `routers/news.py` call it and must stay unchanged.
- **Test.** Add a parametrised `_tag_symbols` test to `test_news.py` over the audit's 5 negatives (IT, ON,
  RELIANCE.NS, LT.NS, ITC.NS) and 2 controls. Add one case the fix was not written against: `ALL` +
  "All eyes on the Fed" → `[]`.

### R15-RESEARCH-001 (critical): DEEP/ULTRA cite another company's news for a non-IN target
- **Mechanism (confirmed).** `relevance.py:637` passes items through unless `is_india_target`. For a US target, an
  alias-tagged region-feed item reaches the DEEP extraction (`deep.py:920-928`). The per-symbol feed marks
  provenance only transiently: `news_provider.py:312` sets `symbols=[symbol]`, and `enrich` then overwrites it.
- **Fix.**
  1. Add `via_symbol_feed: bool = False` to `NewsItem` (`models/news.py`), and mirror it as
     `via_symbol_feed: boolean` in `types/data.ts` NewsItem in the same commit.
  2. In `enrich`, set it True when `_tag_symbols` matched by `symbol in item.symbols` (provenance).
  3. In `gate_news`, for an equity-like target that is not IN, apply `row_relevant` only to items without
     `via_symbol_feed`. The IN path is unchanged. The signature stays the same, so FAST's call (`fast.py:495`) gets
     the same gate.
- **Test.** Add a test to `test_research_deep.py`: `_run_researcher` with
  `ResearchTarget('IT','Gartner, Inc.','NYSE','equity',1.0,'US')`. The own-feed item is kept. The region item
  ("Tax-free bond yields…", tagged `['IT']`) is absent from the structured pair and from the extraction prompt.
  Also run `test_research_fast.py` in full, focused. If a FAST news test pinned the old pass-through for a US
  target, fix it and say why.

### R15-RESEARCH-027 (medium): the NORMAL web round is not time-boxed
- **Mechanism (confirmed).** `fast.py:675-697`: `_web()` awaits `_web_round` unboxed. Every structured leg is
  boxed at 6 s, while keyless can take 18-25 s.
- **Fix.**
  - Add `_WEB_ROUND_TIMEOUT_S = 8.0`.
  - In `_web()`, `asyncio.wait_for(_web_round(...), _WEB_ROUND_TIMEOUT_S)`. On TimeoutError, return
    `{available: False, citations: [], results: [], reason: 'timeout', note: 'Web search did not answer within 8s —
    structured data only'}`.
  - Emit the search step `skipped`, with `latency_ms`.

  `_web_round`, which DEEP uses, is unchanged.
- **Test.** Add `('web_search', 'web', None)` to `test_a_stalled_leading_leg_is_time_boxed_and_the_rest_publish`,
  or add a sibling test. With a 20 s `_SlowLegToolCall('web_search')`, assert:
  - elapsed < 10 s
  - `web.available is False`, with a note naming the timeout
  - fundamentals ok
  - the search step `latency_ms >=` the box

### R15-DATA-063 (medium): indicators carry no freshness
- **Mechanism (confirmed).** `models/indicators.py:67-74` has no `freshness`, and `services/indicators.py:1390`
  drops `series.freshness`.
- **Fix.**
  - Add `freshness: str | None = None` to `IndicatorResponse`, and mirror it in `types/data.ts` IndicatorResponse in
    the same commit.
  - Set `freshness=series.freshness` in `compute()`.
  - The router's EmptySeriesError downgrade leaves it None.
- **Test.** In `test_indicators.py`, a stubbed `get_history` series with freshness `'eod'` gives
  `GET /indicators/X?indicators=rsi` freshness `'eod'`. The empty-series case gives 200 with freshness None.

### R15-DATA-113 (medium): EPS is labelled in the ADR's trading currency
- **Mechanism (confirmed).** `earnings_provider.py:219/:253` sets `payload.currency = info['currency']`. Every EPS
  field is labelled with it (`:345`, `:488`, `:528`, `:576`), while Yahoo serves CNY/DKK per-share EPS for
  PDD/NVO/JD. Only revenue has the scale check (`_revenue_currency`, `:118`). The audit named `types/data.ts`; the
  earnings mirror actually lives in `types/earnings.ts`.
- **Fix.**
  1. Add `trailing_eps` (`info['trailingEps']`) to the payload at `:219/:253`.
  2. Add `_eps_currency(payload, sample_eps)`, mirroring `_revenue_currency`. It returns the trading currency when
     `financialCurrency` equals it, or when `sample×4 / trailing_eps` lies in the existing 0.3-3x band. It returns
     `financialCurrency` when the value is outside the band. It returns None otherwise (non-positive or missing
     trailing EPS on a foreign reporter).
  3. Use `_eps_currency` for the EPS currency at every EPS label site.
  4. Type the field `str | None` in `models/earnings.py` and in `types/earnings.ts`, in the same commit.
  5. Every frontend consumer of that `currency` (grep `src/modules/earnings`, `src/store/earnings.ts`) prints a
     bare number for null, as `revenue()` already does.
- **Test.** Parametrise over the audit's list in `test_earnings_provider.py`:
  - PDD → CNY
  - NVO → DKK
  - JD → CNY
  - TSM → USD
  - WIT → USD
  - AAPL → USD
  - INFY.NS → INR
  - BIDU → None

  Check the estimate and the history/surprise rows. `revenue_currency` stays unchanged. In
  `EpsEstimateGrid.test.tsx`, 'CNY' renders the CNY affix and null renders a bare number.

---

## W3 — sonnet (India disclosures, SEC filings, keyless search)

**Owned files:** `sidecar/services/corporate_disclosures.py`, `sidecar/routers/disclosures.py`,
`sidecar/services/agent_tools/catalog.py` (the deals description text only), `sidecar/services/sec_filings_provider.py`,
`sidecar/services/search/base.py`, `sidecar/services/search/mojeek.py`, `sidecar/services/search/brave.py`.
Tests: `sidecar/tests/test_disclosure_tools.py`, `sidecar/tests/test_disclosures_router.py`,
`sidecar/tests/test_b5_india_deals.py`, `sidecar/tests/test_sec_filings_provider.py`, `sidecar/tests/test_sec_tools.py`,
`sidecar/tests/test_mojeek_backend.py`, `sidecar/tests/test_keyless_backend.py`, `sidecar/tests/test_brave_backend.py`.

### R15-DATA-003 (critical): US-session AMAL gets Amal Ltd's Indian disclosures
- **Mechanism (confirmed).** Five service entries gate the India-only lanes by bare-ticker membership in the
  NSE/BSE master and never look at the session:
  - `get_announcements` (`:535-536`)
  - `get_results_calendar` (`:696`)
  - `get_corporate_actions` (`:878`)
  - `get_deals` (`:1035`)
  - `get_shareholding` (`:1095-1097`)

  The router caches (`routers/disclosures.py:70/89/108/130`) and `get_announcements_cached` (`:606`) key on the
  bare symbol only. Callers are the router, `agent_tools/disclosure_tools.py`, `ownership_check`,
  `dividend_actions`, `research/disclosures` and `workflow_scheduler`, and all of them route through these five
  functions.
- **Fix.**
  1. Add one helper in `corporate_disclosures`, `india_listing(symbol) -> bool`. It returns
     `(symbol_resolver.region_hint(symbol) or config.get_region()) == "IN"`, computed on the symbol before the
     suffix is stripped. The effect: a `.NS`/`.BO` suffix, or India-only master membership, counts as Indian, and a
     ticker in both masters (AMAL) defers to the session. This is the same precedence as
     `provider_registry._effective_region`.
  2. Do not call `symbol_resolver.resolve`: it can reach the network (US ISIN lookup).
  3. Call the helper first in all five entries. When it is False, return the existing `_not_applicable(bare)`.
  4. Make every cache key region-safe. Either append `config.get_region()` to the router keys and the announcements
     key, or run the helper before each cache read.
- **Test.**
  - `test_disclosure_tools.py`: under `set_request_region('US')`, with the NSE/BSE accessors monkeypatched to raise,
    `_shareholding_pattern` and `_corporate_announcements` for `AMAL` return ok, `not_applicable`, count 0. Under IN,
    Amal Ltd is still served.
  - `test_disclosures_router.py`: an IN request warms the cache, and a following US request for `AMAL` shareholding
    returns `not_applicable`.
  - One class case the fix was not written against: `get_deals('AMAL')` and `get_corporate_actions('AMAL')` under US
    → `not_applicable`; `AMAL.BO` under US → still served.

### R15-DATA-024 (high): a dual-listed name's BSE bulk/block deals are missing
- **Mechanism (confirmed).** `corporate_disclosures.py:1035-1036`: an NSE listing is served from the NSE lanes only.
  The BSE deal lane is reached only for BSE-only scrips, although `dual_listed_bse_code` is used for corporate
  actions (`:881-885`).
- **Fix.**
  - When `is_nse_symbol(bare)` and `dual_listed_bse_code(bare)` returns a code, append
    `(f"{EXCHANGE_BSE} {k}", _bse_deals(bare, code, k))` for each k in `kinds` that is in `_BSE_DEAL_TYPE`.
  - Do not dedup across venues. A failing BSE lane goes to `errors`.
  - Update the deals capability description in `catalog.py` to say that dual-listed names get NSE bulk/block/SAST
    plus BSE bulk/block. Run `test_capability_catalog.py` and `test_mcp_catalog_parity.py`.
- **Test.** In `test_b5_india_deals.py`, per the audit (KOPRAN, `dual_listed_bse_code` '524280'),
  `get_deals('KOPRAN','bulk')` returns the NSE 500000 row and the BSE 700000 row, `{'NSE','BSE'}` exchanges, and
  'BSE bulk' in sources.

### R15-DATA-038 (high): SEC filing viewer is empty for a 10-Q or 8-K
- **Mechanism (confirmed).** `sec_filings_provider.py:355-395`: `_sections_from_payload` keeps text values only.
  sec-edgar-mcp 1.0.8 returns `{has_financials: true}` for a 10-Q and `{}` for other forms, so the result has zero
  sections. `get_filing` (`:653-661`) caches that for 24h, and the docstring's premise ("the upstream sections only
  10-K/10-Q") is false.
- **Fix.**
  - In `get_filing`, when the sections list is empty, call the upstream `get_filing_content`. Check its argument
    names in the installed sec-edgar-mcp package before wiring it. Wrap `payload['content']` in the existing single
    "Filing Content" section, using the bare-text branch.
  - If that also has no text, raise an uncached `ProviderError`, with a stated reason.
  - Correct the docstring.
- **Test.**
  - `test_sec_filings_provider.py`: a recorder where the 10-Q `get_filing_sections` returns `{has_financials:true}`
    and `get_filing_content` returns text. Assert non-empty sections and `total_chars > 0`.
  - A second case where content is empty too: ProviderError, and no `sec:filing:<acc>` cache key.
  - `test_sec_tools.py`: `_sec_filing_content` on the same 10-Q is ok, with non-empty text.

### R15-RESEARCH-022 (medium): a 200 CAPTCHA page reads as a healthy empty answer
- **Mechanism (confirmed).** `mojeek.py:114-128` treats only 403/429 as a block, so a 200 challenge page parses to
  zero rows. `keyless.py:196-206` then calls `breaker.record_success()` and `any_engine_answered=True`, and the
  interstitial markers are checked only on parsed rows. `brave.py:122-131` has the identical shape, so the same
  class exists in two engines.
- **Fix.** Add one helper in `search/base.py`, `raise_if_challenge_page(text, engine_label)`. When the page text
  contains a challenge marker, it raises `SearchError(f"{engine_label}: blocked (challenge page)",
  reason=SEARCH_REASON_RATE_LIMITED)`. The markers are:
  - "captcha"
  - "complete this challenge"
  - "verify you are a human"
  - "are you a robot"
  - "unusual traffic"
  - "access denied"

  Mojeek and Brave call it when `_parse` returns no rows on a 200. `keyless.py` itself is unchanged.
- **Test.**
  - `test_mojeek_backend.py`: a 200 captcha body raises SearchError with reason `rate_limited`.
  - `test_keyless_backend.py`: the keyless loop over that stub raises `rate_limited`, naming "Mojeek: blocked
    (challenge page)", and the mojeek breaker's failures increment.
  - Class case the fix was not written against: `test_brave_backend.py`, a 200 "unusual traffic" body →
    `rate_limited`.
  - Control: a 200 page with no results and no marker still returns an empty response.

---

## W4 — sonnet (fundamentals seam, symbol form, quote freshness, overview label)

**Owned files:** `sidecar/services/correctness_gate.py`, `sidecar/services/exchange_financials.py`,
`sidecar/services/yfinance_provider.py`, `sidecar/services/locale.py`, `sidecar/routers/quotes.py`,
`src/modules/equity-overview/EquityOverviewPanel.tsx`.
Tests: `sidecar/tests/test_correctness_gate.py`, `sidecar/tests/test_b7_exchange_financials.py`,
`sidecar/tests/test_yfinance_provider.py`, `sidecar/tests/test_quotes.py`,
`src/modules/equity-overview/EquityOverviewPanel.test.tsx`.

### R15-DATA-008 (critical): INFY.NS filed INR sizes served under financial_currency USD
- **Mechanism (confirmed).** `correctness_gate.py:673-739`: `overlay_filed_periods` serves INR exchange-filed
  `revenue_ttm`/`net_income_ttm` but leaves `financial_currency` at Yahoo's `USD`. `models/fundamentals.py:66-69`
  says the three statement sizes (revenue_ttm, net_income_ttm, free_cash_flow) are in `financial_currency`, so every
  consumer labels INR sizes as USD, about 91x. The 30% divergence check also compares USD with INR. SIFY itself is
  correct.
- **Fix (no FX, D-B2-3).** When the overlay serves any filed size:
  1. Set `financial_currency` to None when `f.currency == "INR"`, else to "INR".
  2. Withhold every statement size still on the old basis that the overlay did not replace (free_cash_flow on
     INFY.NS), when the old basis (`f.financial_currency or f.currency`) is not INR. Use
     `FieldMeta(status="withheld", reason=...)`. The reason names both currencies, in the style of
     `_withhold_mixed_basis_ratios`.
  3. Run the divergence check only when the old basis is INR. Otherwise, state the basis difference in the reason,
     never "disagrees".
- **Test.** Add a case to `test_correctness_gate.py`: `Fundamentals(symbol='INFY.NS', currency='INR',
  financial_currency='USD', revenue_ttm=<USD>, free_cash_flow=<USD>)` plus 4 INR filed quarters. Assert:
  - `out.financial_currency in (None, 'INR')`
  - free_cash_flow is withheld, with both codes in the reason
  - no "disagrees"

  Also assert that `fundamentals_content(json)` shows revenue_ttm as `₹… cr`. This is read-only use of W1's module,
  so do not edit it. Control: a Fundamentals already on an INR basis still gets the divergence reason when off by
  more than 30%.

### R15-LEAD-004 (medium): a quarterly filer is labelled half-yearly
- **Mechanism (confirmed).** `exchange_financials.py:114-121`: `cadence()` returns 'half-yearly' whenever
  `trailing()` finds any hole. `correctness_gate._ttm_basis` (`:581-585`) then prints "(a half-yearly filer) —
  annual, not trailing-4Q". NDTV filed Apr-Jun inside an Apr-Sep 6-month context.
- **Fix.** Make `cadence()` return 'half-yearly' only when no 3-month period is filed inside the fiscal half that
  contains the hole. When a 3-month period is filed there, return `'quarterly-gap'`. In `_ttm_basis`,
  `'quarterly-gap'` gets the wording "TTM basis: the exchange filings leave a quarter of the trailing year unfiled
  or unparsed; kept, flagged", with no "half-yearly" and no "annual, not trailing-4Q".
- **Test.** Add `test_a_quarterly_filer_with_a_six_month_q2_is_not_half_yearly` to `test_b7_exchange_financials.py`.
  Use 3-month periods ending 2026-06-30, 2026-03-31, 2025-12-31 and 2025-06-30, plus 2025-04-01..2025-09-30. Assert:
  - `cadence() == 'quarterly-gap'`
  - the reconcile reason has no "half-yearly"

  `test_jonjua_keeps_the_half_yearly_label` stays green.

### R15-LEAD-022 (high): a foreign exchange suffix not on the list is dashed
- **Mechanism (confirmed).** `yfinance_provider.py:320-322`: any dotted symbol whose suffix is not in the 37-entry
  `_YAHOO_EXCHANGE_SUFFIXES` becomes `s.replace('.', '-')`, which breaks 2222.SR, SAP.F, GGAL.BA and others.
- **Fix.**
  - After the India cases, dash a dotted symbol only when `symbol_resolver.is_us_symbol(s.replace('.', '-'))`, as
    for BRK-B and BF-B. Otherwise return `s` unchanged.
  - Delete `_YAHOO_EXCHANGE_SUFFIXES`.
  - Grep the callers of `_normalize_symbol` (`:198-207`, the same unconditional dash). If it is live on a
    quote/history path, route it through the same rule. If it is dead, report it in issues[].
  - First check that the US master holds the dashed forms (`BRK-B`). If it holds `BRK.B`, test either form.
- **Test.** Add '2222.SR', 'SAP.F', 'GGAL.BA', 'BMW.BE', 'EQB.NE', 'CEZ.PR' and 'QNBK.QA' to
  `test_yahoo_symbol_passes_foreign_exchange_suffixes_through`. Add BF.B → BF-B to the US-quirk test.

### R15-UI-090 (high): a foreign quote is labelled live against the NYSE session
- **Mechanism (confirmed).** `locale.py:173-187`: `instrument_region` falls through to US for anything that is not
  Indian. `routers/quotes.py:43-44` then stamps a same-day ASX/TSE/LSE/HKEX tick 'live' whenever NYSE is open.
- **Fix (fail closed; the exchange-timezone table is skipped).**
  - `instrument_region` keeps IN as it is.
  - It returns US only when the listing is positively US: a plain ticker with no dot, a dotted symbol whose dashed
    form is a US-master ticker (the LEAD-022 rule, `is_us_symbol`), or a US caret index. Grep the repo's caret
    indices; the list is at least ^GSPC ^DJI ^IXIC ^NDX ^RUT ^VIX ^SPX.
  - Anything else returns a new `"FOREIGN"` marker, and `_label_freshness` then calls
    `freshness_for(REGION_US, date, intraday=False)`: eod or stale, never live.
  - Put a `ponytail:` comment on it: a foreign listing is never 'live', even mid-session. The upgrade path is a
    per-exchange tz/session table.
- **Test.** Add a parametrised test to `test_quotes.py` using `_freeze_locale_clock`. BHP.AX, 7203.T, ^N225 and
  0700.HK at 15:00Z (ts 06:00Z/08:00Z, regions US and IN), and HSBA.L at 17:00Z (ts 15:30Z), are all `!= 'live'`.
  AAPL and BRK.B at 15:00Z stay `'live'`, and ^NSEI at 05:00Z stays `'live'`.

### R15-DATA-055 (medium): a young US listing's range is labelled '52w'
- **Mechanism (confirmed).** `EquityOverviewPanel.tsx:227`: `listedUnderAYear` reads only `listing_date`, which the
  sidecar sets only for `.NS`. `first_trade_date` is on the wire and ignored.
- **Fix.** `const listed = fundamentals?.listing_date ?? fundamentals?.first_trade_date`.
- **Test.** In `EquityOverviewPanel.test.tsx`:
  - listing_date null with first_trade_date 90 days ago → 'since listing' and no "1Y change" row
  - first_trade_date '2002-07-01' → '52w' plus the 1Y row

---

## W5 — opus (screener, Yahoo batch transport, warm loops, BSE/NSE quotes, F&O file walk)

**Owned files:** `sidecar/services/screener.py`, `sidecar/services/yahoo_batch_provider.py`,
`sidecar/services/fundamentals_warm.py`, `sidecar/services/provider_registry.py` (only if a signature needs it),
`sidecar/services/option_chain.py`, `sidecar/services/bse_provider.py`, `sidecar/services/nse_provider.py`.
Tests: `sidecar/tests/test_screener.py`, `sidecar/tests/test_b5_screener.py`, `sidecar/tests/test_yahoo_batch_provider.py`,
`sidecar/tests/test_fundamentals_warm.py`, `sidecar/tests/test_option_chain.py`, `sidecar/tests/test_bse_provider.py`,
`sidecar/tests/test_nse_provider.py`.

### R15-LEAD-045 (medium): the sidecar's own crumb and v7 calls 429 on every chunk
- **Mechanism (root-caused live by the planner, 27 Sep).** The register names `yfinance_provider.py`, but the code
  is in `yahoo_batch_provider.py:102-190` (`_Session`, httpx).
  - Probe through the sidecar's own `_Session`: fc.yahoo.com returns 404 (one cookie set), finance.yahoo.com returns
    200, then `getcrumb` returns 429 and `v7/finance/quote` returns 429.
  - The same three calls through `curl_cffi.requests.Session(impersonate="chrome")`: fc 404 (cookie set),
    `getcrumb` 200 (`aa.Qp…`), and v7 200 with rows.

  The throttle is a TLS-fingerprint block of plain httpx, not a data-layer outage. yfinance succeeds because it
  uses curl_cffi. `services/search/transport.py` already uses curl_cffi for fingerprint-blocked hosts, and
  `requirements.txt` already pins it, so no new dependency.
- **Fix.**
  1. Move `_Session`'s client (cookie bootstrap, crumb mint and the v7 request) to a `curl_cffi` `AsyncSession`
     with `impersonate="chrome"`, so one jar pairs cookie and crumb.
  2. Import curl_cffi at call time: a broken wheel must degrade the batch path, never break import. This is the
     PyInstaller rule; `transport.py` shows the pattern.
  3. Keep the 401/403/"Invalid Crumb" invalidate path.
  4. Replace the httpx `transport` test seam (`reset_for_tests(transport)`) with an injectable session factory,
     and update the existing `test_yahoo_batch_provider.py` fakes to it. Say why in the commit.
  5. Second half of the entry: when a chunk ends in a 429 after retry, make the fallback visible. Check what
     screener and warm serve from the store, then make sure the row or run carries the existing
     stale/rate-limited label (`throttled_seen` / `partial`) rather than a fresh-looking payload. Add a new typed
     reason only if none exists.
- **Test.**
  - `test_yahoo_batch_provider.py`: a fake session answers the crumb with 200 and v7 with rows. Assert
    `fetch_quotes_batch` returns them, and that the crumb was minted once for two chunks.
  - A second case: the fake crumb returns 429 and v7 returns 429. Assert the failures are typed `rate_limited` and
    the screener result is labelled throttled or partial, not fresh.

### R15-LEAD-044 (high): an IN session poisons sp500 rows with Indian namesakes
- **Mechanism (confirmed).** Three per-symbol fetches pass no region: `screener.py:555`
  (`get_fundamentals(symbol)`), `:574` (`get_quote(symbol, asset_class)`) and `:1078` (`get_fundamentals(key)`).
  `provider_registry._effective_region` defers a ticker that is in both masters to the session. So under IN, HAL
  resolves to Hindustan Aeronautics and is stored under the bare sp500 key (`_store_pair`, `upsert_info`), where it
  is served to every later session. `provider_registry.get_fundamentals(symbol, region=None)` and
  `get_quote(symbol, asset_class, region)` already accept `region`, so the registry is untouched.
- **Fix.**
  - Give the universe an intrinsic region: sp500 → 'US'; nifty50 and the India universes → 'IN'; custom → None.
  - Thread it through `_fetch_pair` and `_enrich_survivors` into both registry calls.
  - Also check `yahoo_batch_provider.py:519` (`validate_fundamentals(..., config.get_region())`) and pass the same
    region where the batch knows it.
  - No refuse-guard in `_store_pair`: once the root cause is fixed, no wrong-entity row can arrive. If a row
    poisoned before the fix is served from the store ahead of a refetch, report it in issues[] (a store migration
    is out of scope).
- **Test.** Add a test to `test_screener.py`. Under `set_request_region('IN')`, monkeypatch
  `get_fundamentals(symbol, region=None)` to return Halliburton/USD for region 'US' and HAL/INR otherwise, and force
  the v7 miss for HAL. An sp500 screen restricted to HAL records region 'US', and the row is Halliburton/USD. Assert
  the same for the `_enrich_survivors` path. Class case the fix was not written against: nifty50 under a US session
  records region 'IN'.

### R15-LIFECYCLE-020 (medium): background warm 429s open the user-facing Yahoo circuit
- **Mechanism (confirmed).** `yahoo_batch_provider.py:322` records every chunk 429 at weight 1.0, whoever called.
  Three `_warm_once` cycles (`screener.py:1338`) or `fundamentals_warm.py:178` open the circuit that user screens
  read.
- **Fix.**
  - Add a keyword `throttle_weight: float = 1.0` to `fetch_quotes_batch`, threaded to
    `record_rate_limited(YAHOO, weight=throttle_weight)` (the parameter exists).
  - `_warm_once` and fundamentals_warm pass `_WARM_THROTTLE_WEIGHT = 0.25`.
- **Test.** Add `test_warm_429s_alone_do_not_open_the_user_circuit` to `test_b5_screener.py`. Three 429 warm cycles
  leave `is_open(YAHOO)` False, and a user fetch still makes an HTTP call. Control: three user-path 429s open it.
  Class case: the same assertion through fundamentals_warm's batch call.

### R15-DATA-114 (medium): a failed walk-back day ends the F&O walk
- **Mechanism (confirmed).** `option_chain.py:181-182`: `if status == "failed": return None` ends the walk on a
  failed walk-back day, and the `_probe_key` check/record runs only for `day == today`.
- **Fix.**
  - Replace the early return with `upstream_down = True; continue`, so the walk turns cache-only.
  - Apply the `_probe_key` check and record to every probed trading day.
- **Test.** Add a test to `test_option_chain.py`. Tue 2026-09-22 is missing, Mon is failed, and Fri 2026-09-18 is
  cached. Three calls each return 2026-09-18, and the stub records only `['2026-09-22', '2026-09-21']`. The two
  existing today-probe tests stay green.

### R15-DATA-053 (medium): BSE volume ignores its unit, and NSE quotes carry no session fields
- **Mechanism (confirmed).**
  - `bse_provider.py:630` sets `quote.volume = TTQ` raw and ignores `TTQin` ('(Lakh)'), so INFY 8.12 means 812,000.
  - `nse_provider.py:575-625`: `_quote_from_payload` and `_quote_from_history` never set open/high/low/prev_close.
    `Quote` has those fields (`models/market.py`).
- **Fix.**
  - BSE: scale TTQ by 1e5 when `TTQin` contains 'Lakh' and by 1e7 when it contains 'Cr'. Any other non-empty unit
    gives `volume None`.
  - NSE history: set open/high/low from `last` (`CH_OPENING_PRICE`, `CH_TRADE_HIGH_PRICE`, `CH_TRADE_LOW_PRICE`),
    and `prev_close=prev`.
  - NSE payload: `prev_close=previousClose`, and map the `priceInfo` intraday open/high/low when present.
- **Test.**
  - `test_bse_provider.py`: an INFY-shaped StockTrading fixture (TTQ '8.12', TTQin '(Lakh)') → 812000. Class case:
    '(Cr)' → ×1e7.
  - `test_nse_provider.py`: the history-fallback quote carries the row's open/high/low/prev_close, with
    low <= price <= high.

---

## W6 — sonnet (frontend: agent context, layouts, screener, SEC store, chart, code node)

**Owned files:** `src/modules/news/NewsFeedPanel.tsx`, `src/modules/chat/context-provider.ts`, `src/lib/layout-templates.ts`,
`src/store/command-palette.ts`, `src-tauri/src/lib.rs` (the layout menu ids only; not a Tier-1 file),
`src/store/screener.ts`, `src/store/sec.ts`, `src/modules/sec/SecFilingsPanel.tsx`, `src/modules/chart/ChartPanel.tsx`,
`src/modules/node-editor/code-node-inspector.tsx`, `src/modules/node-editor/code-node.ts` (only if the inspector stops
needing `evaluateCodeExpression`).
Tests: `src/modules/chat/context-provider.test.ts`, `src/modules/news/NewsFeedPanel.test.tsx`,
`src/lib/layout-templates.test.ts`, `src/store/command-palette.test.ts`, `src/store/screener.test.ts`,
`src/lib/host-actions.test.ts`, `src/store/sec.test.ts`, `src/modules/sec/SecFilingsPanel.test.tsx`,
`src/modules/chart/ChartPanel.test.tsx`, `src/modules/node-editor/code-node-inspector.test.tsx`,
`sidecar/tests/test_code_node.py`.

### R15-AGENT-053 (medium): the agent sees the News panel as an opaque id
- **Mechanism (confirmed).** `NewsFeedPanel.tsx:206-219` publishes `{watchedSymbols, focusedArticleId}` (a sha1),
  and `genericPanelSummary` (`context-provider.ts:272-273`) collapses arrays to "N items".
- **Fix.**
  - Publish `focusedHeadline` (the hovered item's title) and `topHeadline` (`items[0]?.title` when ready), and add
    both to the effect deps.
  - In `genericPanelSummary`, render an array of primitives inline (the first few values joined by ',') within the
    200-char cap.
- **Test.**
  - `context-provider.test.ts`: `{watchedSymbols:['AAPL','MSFT'], focusedHeadline:'Apple beats on services'}` → the
    summary contains the headline and 'AAPL'. Update the pinned 'watchedSymbols=2 items' expectation and give the
    reason.
  - `NewsFeedPanel.test.tsx`: mouseEnter on row 2 publishes that row's title as `focusedHeadline`.

### R15-AGENT-055 (medium): one layout id means two different layouts
- **Mechanism (confirmed).** `layout-templates.ts:672` `MENU_PAYLOAD_TO_MODE` is keyed by the agent template ids
  (single-focus, research-cockpit, compare). Those map to menu modes whose panel sets differ from `planLayout` of
  the same id. The keys are fed by `src-tauri/src/lib.rs:464-477` (`layout:<template>` ids) and by
  `command-palette.ts:163` `LAYOUT_MENU_LABELS`.
- **Fix.**
  - `lib.rs` emits the mode ids: `layout:fundamental`, `layout:technical`, `layout:macro`, `layout:compare-desk`,
    plus `layout:default`. The "Compare" label becomes "Compare Desk".
  - Key `MENU_PAYLOAD_TO_MODE` and `LAYOUT_MENU_LABELS` by those ids.
  - `MODE_PLANS` and `planLayout` keep their panel sets.
- **Test.** Add 'one plan per template id (R15-AGENT-055)' to `layout-templates.test.ts`. For every id in
  `LAYOUT_TEMPLATE_IDS`, `dispatchLayoutMenuCommand(id)` either returns false or places exactly `planLayout(id)`'s
  set. A source read of `lib.rs` asserts every `layout:<x>` id is a `MENU_PAYLOAD_TO_MODE` key or 'default'. Update
  the existing `MENU_PAYLOAD_TO_MODE` key-set test (`:553`) to the new ids, with the reason.

### R15-AGENT-096 (medium): the screener runs the flat list instead of the flat group
- **Mechanism (confirmed).** `screener.ts:343-351`: `applyFilters` keeps the caller's flat `criteria` beside a flat
  group, so `runScreener` sends the flat list, while the ack, label and server all treat the group as superseding
  it.
- **Fix.** Add one line in `applyFilters`: `criteria: group && !hasNestedGroup(group) ? (group.criteria as
  ScreenerCriterion[]) : criteria`. Nested groups are unchanged.
- **Test.**
  - `screener.test.ts`: `applyFilters({criteria:[mcap>1000], group:{and:[pe<20]}})` → `state.criteria` is
    `[pe<20]`.
  - `host-actions.test.ts`, with fetch stubbed: the audit's cases (1) AND, (2) OR, (3) the rc1-vshard-3:3 input and
    (4) save_screen, then loadScreen, then run. Each body equals the group's leaves.

### R15-CODE-FRONTEND-017 (medium) + R15-UI-015 (medium): sec.ts loaders
- **Mechanism (confirmed).**
  - FE-017: `sec.ts:188-214` `loadFilingDetail` commits with no generation check and writes `activeAccession`, and
    its error goes to an unkeyed scalar.
  - FE-017: `sec.ts:220-242` `loadInsider` has no generation check either. Only `loadFilings` is guarded.
    `earnings.ts` is already guarded (`upcomingGeneration`).
  - UI-015: `searchCompanies` (`:244-258`) uses a bare `catch` that drops the error, and `SecFilingsPanel` never
    reads a search error.
- **Fix.**
  - Give `loadFilingDetail` and `loadInsider` each a generation counter, following the `filingsGeneration` pattern:
    a superseded response or error is dropped before `set`. Caching the payload in the keyed map is fine.
  - `loadFilingDetail` stops writing `activeAccession`; the caller owns it.
  - `searchCompanies` gets the same guard (the same race class) and keeps
    `searchError = err instanceof Error ? err.message : 'company search failed'`. It is cleared on loading, on idle
    and in `clearSearch`.
  - `SecFilingsPanel` renders one muted line under the symbol field when `searchStatus === 'error'`: "Company search
    unavailable: <reason>".
- **Test.**
  - `sec.test.ts`: the audit's four deferred-mock cases (a late A-1 detail, A-1 after `setActiveAccession(null)`, a
    late A-1 rejection, a late AAPL insider rejection). Class case the fix was not written against: a late 'app'
    search result after the 'apple' search resolved does not overwrite it.
  - Also in `sec.test.ts`: a 501 SidecarError sets `searchError`.
  - `SecFilingsPanel.test.tsx`: the reason renders.

### R15-UI-021 (medium): Delete removes the selected drawing in every chart
- **Mechanism (confirmed).** `ChartPanel.tsx:810-837`: each instance's window keydown listener exempts
  `document.body`, and `selectedDrawingId` is never cleared when the user leaves that chart. One body-targeted
  Delete therefore deletes the selection in every chart.
- **Fix.** In the same effect, register a document `pointerdown` listener that calls `setSelectedDrawingId(null)`
  when `rootRef.current` does not contain the event target, and remove it on cleanup.
- **Test.** In `ChartPanel.test.tsx`, render chart-A and chart-B:
  - Select A, then B, firing pointerDown before each click. Delete on body leaves A with 1 drawing and B with 0.
  - Select A, pointerDown outside both, Backspace on body: A still has 1.

  The existing "Delete with nothing focused still deletes" test stays green.

### R15-CODE-PLATFORM-017 (medium): the code-node preview uses mathjs, not the server evaluator
- **Mechanism (confirmed).** `code-node-inspector.tsx:44-57` computes Preview with mathjs `evaluateCodeExpression`,
  while runs use the Python evaluator (`sidecar/services/workflow_nodes/code_node.py`). The two disagree on
  `log(x,10)`, `round(1.005,2)` and nested ternaries.
- **Fix.**
  - Compute the Preview with a debounced (~300 ms) POST to the existing `/workflow/run`, sending a one-node
    `transform.code` spec with the sample inputs. Use the sidecar client the node editor already uses; see
    `code-node-run.ts`.
  - Render the node output value or the node error.
  - Drop `evaluateCodeExpression` from the inspector. mathjs `compileCodeExpression` stays only as the inline "does
    not parse" hint.
  - If `evaluateCodeExpression` then has no caller, delete it and its tests. Report whether that happened.
- **Test.** In `code-node-inspector.test.tsx`, with the run transport mocked to return the server result:
  - `log(x, 10)` with x=100 shows "disallowed syntax: Call" and never "= 2"
  - `round(x, 2)` with x=1.005 shows "= 1"
  - the nested ternary shows the server error

  Pin the same three expressions in `sidecar/tests/test_code_node.py`.

---

## Proposed not-a-defect (needs the verifier's fresh concurrence)

### R15-LEAD-046 (medium, data-smallcaps): HDB forward_pe vs the home listing
Live probe, 27 Sep, sidecar venv `yfinance.Ticker(s).info`:

| symbol | trailingEps | forwardEps | analysts | trailingPE | forwardPE | nextFiscalYearEnd |
|---|---|---|---|---|---|---|
| HDB | 1.43 USD/ADS | 1.3915 | 4 | 16.09 | 16.54 | 1806451200 |
| HDFCBANK.NS | 45.75 INR | 63.07 | 41 | 16.08 | 11.66 | 1806451200 |
| IBN | 1.61 | 1.8608 | 4 | 17.34 | 15.00 | same |
| ICICIBANK.NS | 77.0 | 94.0 | 42 | 17.23 | 14.11 | same |

**Implied FX.** At the FX implied by trailing EPS, 45.75 × 3 shares per ADS / 1.43 ≈ 95.9 INR/USD, the home
consensus is 63.07 × 3 / 95.9 ≈ 1.97 USD per ADS. The ADR's 4-analyst consensus is 1.39.

**Vysted computes both figures correctly.**
- trailing reconciles exactly
- `forward_pe = price / forwardEps` on the ADR's own consensus
- the horizon is already labelled (`forward_pe_fiscal_year`, the same FY end for both)
- IBN's ADR consensus agrees with its home listing within 6%

**Why no product fix is proposed.** The gap is between two independent analyst consensus sets (4 opinions vs 41).
It is not a stale value, a currency basis error or a bug in Vysted's code. Withholding or reconciling it would need
a new home-listing fetch per ADR plus a consensus-quality policy. That is a feature, not a fix, and it is outside
this release's defect scope.

**Verifier.** Concur, or send it back with a counter-probe.

## Notes for the integrator (run order)

1. Merge W1, W3, W4, W2, W5, W6 in that order. The file sets are disjoint by construction. The only cross-set
   reads are:
   - W4's DATA-008 test calls W1's `fundamentals_content`, read-only. Merge W1 first; W4's assertion holds on
     either base, because it tests the Fundamentals fields.
   - W4's UI-090 and LEAD-022 share the "positively US" rule, inside W4.
   - W2 owns both `types/data.ts` mirrors (NewsItem `via_symbol_feed`, IndicatorResponse `freshness`) and
     `types/earnings.ts`.
2. After each merge, run that writer's focused tests. Then run `pnpm ci-local` detached, poll it, and run
   `node scripts/smoke-test-sidecars.mjs`. W6 touches `src-tauri/src/lib.rs`, so the cargo fmt and clippy legs
   matter. W5's LEAD-045 changes the batch transport to curl_cffi (already pinned and already collected for the NSE
   lanes); confirm the smoke test's main sidecar still serves `/screener/run`.
3. Record the Tier-3 decisions in CHANGELOG/DECISIONS. Each writer reports its own; the planner's are:
   - UI-090 fails closed without a tz table
   - LEAD-044 has no store refuse-guard
   - RESEARCH-022 fixes the class for mojeek and brave through `search/base.py`
   - AGENT-055 adds new menu ids in `lib.rs`
4. Live re-proofs for the verifier are the acceptance lines in `REFUTATION_AUDIT.json`, per id. LEAD-045's is: on a
   booted sidecar, `curl -X POST /screener/run` for sp500 returns rows with no `rate_limited` skip ledger when
   yfinance itself can fetch.
