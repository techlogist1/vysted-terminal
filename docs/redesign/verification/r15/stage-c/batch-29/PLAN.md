# R15 Stage C — batch-29 plan

Base: `004-r4-experience-rebuild` @ `522c32461fd72d33973daabd06dca553872ca0fc`. D81 (trading out) is on the base.
Nothing here touches a trading surface, and nothing re-adds one.

**Selection.** The register has 7 OPEN entries at critical/high/medium, which matches the adjudicated queue
(1 critical, 1 high, 5 medium). None is on the exclusion list. All 7 are taken, all 7 are planned as fixes. Nothing
is proposed as not-a-defect and nothing is deferred. Lows are not in this batch's severities, so LOWS_TRIAGE.json
does not apply.

| id | sev | prior cert failures | area |
|---|---|---|---|
| R15-RESEARCH-001 | critical | 2 (the next one trips the three-failure rule) | research-search, data-smallcaps |
| R15-DATA-030 | high | 1, plus 1 integrator revert (c780c516) | ui-panels, data-smallcaps |
| R15-DATA-063 | medium | 2 | ui-panels |
| R15-LEAD-004 | medium | 2 | data-smallcaps |
| R15-LIFECYCLE-020 | medium | 2 | data-smallcaps, ui-panels |
| R15-LEAD-048 | medium | 0 (new, from batch-28 issues) | ui-panels, agent-chat |
| R15-LEAD-049 | medium | 0 (new, from batch-28 issues) | data-smallcaps |

Every mechanism below was re-opened at the base and, where marked, probed in-process on 27 Sep. The batch-28
not-certified reasons (`stage-c/batch-28/VERDICTS.json` `not_certified`) are the corrected mechanism for five of the
seven. They override each entry's original claim.

**Class kept together.** DATA-030 + RESEARCH-001: a short or common-word ticker (IT, ON, ALL, LT, ITC) or a
first-word name collision (ITC Hotels, LT Foods, Reliance Power, On Holding) is read as entity identity. News
tagging (`news_provider`) and the research relevance gate (`relevance`) are both affected. Both go to one writer (W1).

## Writers at a glance

| W | model | entries | why this model |
|---|---|---|---|
| W1 | opus | RESEARCH-001, DATA-030 | This set needs root-causing before the fix shape is known. The ON repro leaks 7 items through at least two separate mechanisms. The batch-28 alias fix was reverted because it broke single-word company names. RESEARCH-001 is one failure away from the three-failure stop. |
| W2 | sonnet | DATA-063, LEAD-004 | Each fix is specified, with a deterministic acceptance test. |
| W3 | sonnet | LIFECYCLE-020, LEAD-049 | Each fix is specified, with a deterministic acceptance test. |
| W4 | sonnet | LEAD-048 | A frontend fix with a written vitest. |

**Common rules for every writer.**
- Branch: `worktree-agent-batch-29-W<n>`. First run `git reset --hard 522c32461fd72d33973daabd06dca553872ca0fc`,
  then check `git log -1` (the worktree base hazard).
- Push every deliverable.
- Edit only the files you own.
- Run only the focused test files, and never run a full suite in the foreground. Anything over about 120 s runs
  detached and is polled.
- Before each Python commit, run `ruff format <files> && ruff format --check sidecar && ruff check sidecar`. Before
  each TS commit, run prettier `--check` on the touched files, plus `pnpm typecheck` detached.
- Do not edit `CHANGELOG.md`, `docs/redesign/DECISIONS.md`, `CLAUDE.md`, `tauri.conf.json`, `.github/`,
  `types/plugin.ts` or the register. Report every Tier-3 decision in your return. The integrator records them.
- Where a test pinned the old, wrong behaviour, fix that test and give the reason in the commit body. Never skip or
  weaken a test.
- Anything outside your entries goes in issues[], never into the diff.

---

## W1 — opus (entity identity in news tagging and the research relevance gate)

**Owned files:**
- Code: `sidecar/services/news_provider.py`, `sidecar/services/research/relevance.py`, and, only if a wire field
  must change, `sidecar/models/news.py` + `types/data.ts` (NewsItem only, changed in the same commit).
- Tests: `sidecar/tests/test_news.py`, `sidecar/tests/test_research_relevance.py`,
  `sidecar/tests/test_research_deep.py`, `sidecar/tests/test_research_fast.py`.

### R15-DATA-030 (high): news tagging matches tickers case-insensitively and on first-word name collisions

**Mechanism (confirmed at base).**
- `news_provider._aliases` (:575-587) returns the requested ticker, its suffix-stripped base (2+ characters) and the
  company name.
- `_tag_symbols` (:595-610) matches every alias with `re.IGNORECASE` and `\b..\b`. So:
  - IT matches "it's".
  - ON matches "on" and "On Holding".
  - The RELIANCE bare alias matches "Reliance Power".
  - The LT bare alias matches "LT Foods".
  - The ITC bare alias, and the `itc` name alias from "ITC Limited", both match "ITC Hotels".
- The batch-28 fix dropped an alias wholesale when any other master name started with it. The integrator reverted
  that fix in c780c516.
- Probed today: a correct own-symbol exclusion would still drop AAPL's `apple`. APLE "Apple Hospitality REIT" and
  AAPI "Apple iSports" are genuinely different companies whose names start with "apple". **Alias-level dropping
  is the wrong granularity.**

**Fix (root cause: collisions are per occurrence, not per alias).**
1. Match ticker aliases (the requested form and the bare base) case-sensitively, as uppercase tokens. Match only the
   company-name alias case-insensitively.
2. Treat a collision as a property of one OCCURRENCE. An alias hit does not count when the text right after it
   continues into a DIFFERENT listed company's name that starts with the same word(s). Examples: "ITC **Hotels**",
   "LT **Foods**", "RELIANCE **POWER**", "Apple **Hospitality**".
   - Build one cached index from the NSE, BSE and US masters: first name word → the next name words of each
     company, with corporate suffixes stripped via the resolver's `_strip_corporate_suffix`.
   - Exclude the target's own rows (same symbol, or same ISIN where the master has one).
   - A company whose stripped name is a single word adds no continuation.
   - Never drop an alias wholesale.
3. Keep the `build_aliases` / `enrich` signatures. `routers/news.py` and `agent_tools/news_tool.py` call them and
   stay unchanged (grep first).

**Test.** Add a parametrised `_tag_symbols` test to `test_news.py` (item `symbols=[]`, `build_aliases([sym])`). Pin
the region with `VYSTED_REGION`/the region contextvar wherever the name alias depends on it, because under IN a bare
`IT` names the KOTAKIT ETF.
- Must be `[]`:
  - IT + "Tax-free bond yields are in a sweet spot. Get in before it's too late."
  - ON + "Choosing these AI-exposed college majors could dent your job prospects"
  - ON + "On Holding announces $500m buyback"
  - RELIANCE.NS + "Reliance Power wins Bhutan project"
  - RELIANCE.NS + "RELIANCE POWER SHARES SURGE"
  - LT.NS + "LT Foods Q2 profit jumps 30%"
  - ITC.NS + "ITC Hotels shares list at premium"
- Must tag. These are the batch-28 revert regressions, pinned:
  - RELIANCE.NS + "Reliance Industries Q2 profit rises 10%"
  - IT (US) + "Gartner beats estimates"
  - AAPL + "Apple beats on services"
  - MSFT + "Microsoft raises dividend"
  - NVDA + "Nvidia unveils a new chip"
  - INFY.NS + "Infosys wins $1bn deal"
  - ITC.NS + "ITC Q2 profit rises 8%"
- Class cases the fix was not written against:
  - AAPL + "Apple Hospitality REIT raises dividend" → `[]`
  - ALL + "All eyes on the Fed" → `[]`

### R15-RESEARCH-001 (critical): DEEP/ULTRA still cites other companies' news for a common-word US ticker

**Mechanism (confirmed at base, probed).**
- `relevance.gate_news` (:623-657) trusts `via_symbol_feed` items. Every other item for a non-IN target goes through
  `row_relevant`.
- For ON Semiconductor, `row_relevant` is True for off-entity rows through two mechanisms:
  - **(a) Short token read as prose.** `_entity_signals` lowercases the title, so the ≤3-character symbol or brand
    token `on` is found in any English sentence. `_strong_entity_score` then returns **0.6 for a non-IN short-only
    signal with no corroboration** (:510-511), above MATCH_FLOOR 0.34. Probed: "Lockheed wins contract on
    hypersonic program" → 0.6 and "On Holding announces buyback" → 0.6. For ALL (Allstate), "All eyes on the Fed"
    → 0.6 through the 3-character symbol.
  - **(b) Sector word read as a brand.** `brand_tokens("ON Semiconductor Corporation")` = `['on','semiconductor']`,
    because `semiconductor` is not in `_GENERIC_NAME_TOKENS`. Any "…semiconductor…" title (the Nvidia item) then
    scores a DISTINCTIVE 1.0.
- These rows reach DEEP because `news_provider` tagged them to ON case-insensitively in the first place (DATA-030).

**Fix.**
1. For a non-IN target, a short-only signal needs corroboration, as it already does for IN. It counts only when the
   row also names the company: a non-generic brand token of 4+ characters, or all distinctive name tokens together.
   Otherwise it falls to the weak ceiling. An uppercase-acronym ticker (AI, IT, ON, US-style) must not pass on the
   ticker alone.
2. Sector and descriptor words belong in `_GENERIC_NAME_TOKENS`. This is the existing data-driven mechanism: add
   `semiconductor(s)` and any other descriptor the investigation shows. Do not add a special case.
3. Before choosing the final rule, root-cause each of the 7 ON items (AP bond market, Lockheed, On Holding, Nvidia,
   Innate Pharma). Run DEEP `_run_researcher` in-process for ON (US, NASDAQ) against the live news tool, or a
   captured payload, and log each item's signal path. Fix every mechanism found, not only the two above.
4. `entity_match` is also the web-evidence gate for FAST, DEEP and disclosures. Run `test_research_relevance.py`,
   `test_research_fast.py` and `test_research_deep.py` focused. Where an existing test pinned the uncorroborated
   non-IN 0.6, fix it and say why. The IN path must be unchanged.

**Test.**
- `test_research_relevance.py`, ON target (US) must be False: "Lockheed wins contract on hypersonic program",
  "On Holding announces buyback" and "Nvidia semiconductor sales soar".
- `test_research_relevance.py`, must be True: "ON Semiconductor beats estimates" and "onsemi raises guidance" (if the
  name tokens allow it; otherwise document why).
- `test_research_relevance.py`, ALL target: "All eyes on the Fed" must be False.
- `test_research_deep.py`: `_run_researcher` with `ResearchTarget('ON','ON Semiconductor Corporation','NASDAQ',
  'equity',1.0,'US')` and a stub news result holding one own-feed item (`via_symbol_feed` true) and the 5
  off-entity region items tagged `['ON']`. Assert the region items are absent from the structured pair and from the
  captured extraction prompt, and the own-feed item is kept.
- Class case the fix was not written against: `ResearchTarget('AI','C3.ai, Inc.','NYSE','equity',1.0,'US')` with
  "AI stocks rally as chipmakers surge" is dropped.
- Keep the existing IT/Gartner test green.

**Live re-proof (report it).** With `VYSTED_REGION=US`, DEEP `_run_researcher` on ON prints `region_feed_items=0`.
The same run on IT and ALL still prints 0.

---

## W2 — sonnet (indicator freshness, TTM cadence)

**Owned files:** `sidecar/routers/indicators.py`, `sidecar/services/exchange_financials.py`.
Tests: `sidecar/tests/test_indicators.py`, `sidecar/tests/test_b7_exchange_financials.py`.

### R15-DATA-063 (medium): /indicators freshness is always null

**Mechanism (confirmed).**
- `services/indicators.compute` (:1396) copies `series.freshness`.
- Only `routers/history.py::_label_series_freshness` (:101-122) ever sets that field. `routers/indicators.py`
  (:77-84) takes the series straight from `provider_registry.get_history`, which never labels it. So every live
  `/indicators` response carries `freshness: null`.
- The existing test `test_indicators_endpoint_carries_series_freshness` (test_indicators.py:508) stubs `get_history`
  to return a pre-labelled series, a shape the real provider never produces. That is why it passed.

**Fix.**
- In `routers/indicators.py`, label the series with the same function before computing:
  `series = _label_series_freshness(series, asset_class, timeframe)`, imported from `routers.history`. Reuse it; do
  not write a second copy.
- The EmptySeriesError downgrade stays `freshness=None`.
- No model or `types/data.ts` change: the field and its mirror already exist.

**Test.**
- Rewrite that test to stub `get_history` with an UNLABELLED series (freshness None, bars dated on a recent trading
  day). Assert `/indicators/X?indicators=rsi` freshness is non-null and equals `/history/X` freshness for the same
  stub (parity, so the test does not depend on the clock). Say why in the commit.
- Add one case the fix was not written against: `asset_class=crypto` gives `live`.
- Keep the downgraded-empty test green.

**Live re-proof.** `/indicators/TCS?indicators=rsi&timeframe=1d&range=1mo` freshness equals `/history/TCS`
freshness. Also check INFY.NS (ema) and AAPL (sma).

### R15-LEAD-004 (medium): cadence() calls a quarterly filer half-yearly

**Mechanism (confirmed).** `FiledPeriods.cadence()` (exchange_financials.py:114-134) has two faults:
- With `trail` present it returns `half-yearly` whenever any trail period is not 3 months. It never checks whether
  a quarter is filed inside that half. This is Fresh B: an Oct-Mar 6-month period with Oct-Dec filed standalone.
- With `trail` None it returns `half-yearly` unless a 6-month period encloses a quarter. A plain unfiled quarter with
  no 6-month context is therefore called half-yearly. This is Fresh A: Oct-Dec 2025 missing, Jan-Mar 2026 filed.

**Fix.** Decide by the INDIAN FISCAL HALF (Apr-Sep, Oct-Mar). Find each fiscal half that overlaps the trailing year
(the 12 months to the newest period end) and is not covered by filed 3-month periods, either because a 6-month
period stands in for it or because it has a hole.
- If any such half has NO 3-month period filed anywhere inside it, return `half-yearly`. A half-yearly filer never
  files a quarter.
- Otherwise, a complete trail returns `quarterly` and a trail with a hole returns `quarterly-gap`.
- `correctness_gate._ttm_basis` is unchanged: it already words `quarterly-gap`.

**Test.** Add to `test_b7_exchange_financials.py`:
- `test_an_unfiled_quarter_without_a_half_year_context_is_not_half_yearly`. 3-month periods end 2026-06-30,
  2026-03-31, 2025-09-30 and 2025-06-30 (Oct-Dec missing). Assert `quarterly-gap`, and assert `_ttm_basis` has no
  "half-yearly".
- `test_a_half_year_with_its_quarter_filed_inside_is_not_half_yearly`. Periods: Apr-Jun 2026, Oct 2025-Mar 2026
  (6 months), Oct-Dec 2025 and Jul-Sep 2025. Assert `!= 'half-yearly'`.
- Class case the fix was not written against: a pure half-yearly filer (only Apr-Sep 2025 and Oct 2025-Mar 2026
  6-month periods) is still `half-yearly`.
- `test_jonjua_keeps_the_half_yearly_label` and the NDTV test stay green. JONJUA files no quarter inside Apr-Sep
  2025.

---

## W3 — sonnet (background Yahoo circuit, Nifty 50 seed)

**Owned files:** `sidecar/services/screener.py` (warm weight only), `sidecar/services/fundamentals_warm.py`,
`sidecar/services/yahoo_batch_provider.py` (the docstring of `fetch_quotes_batch` only),
`sidecar/services/screener_universes/nifty50.json`.
Tests: `sidecar/tests/test_b5_screener.py`, `sidecar/tests/test_fundamentals_warm.py`,
`sidecar/tests/test_resolver_rename.py`.

### R15-LIFECYCLE-020 (medium): warm 429s still open the user circuit, only later

**Mechanism (confirmed).**
- `provider_health.record_rate_limited` adds `weight` to `consecutive_throttles`, which only `record_success` resets
  (provider_health.py:111-150).
- The warm loops pass `_warm_chunk_weight(n)`, a fractional share of `_WARM_THROTTLE_WEIGHT` = 0.25 per cycle
  (screener.py:169, :1386, :1398-1403; fundamentals_warm.py:179). Across many all-429 cycles the fractions sum to 3,
  and the user circuit opens. The verifier saw it open at warm cycle 10.

**Fix (the entry's "separate budget").** Background warm 429s do not advance the user circuit's streak at all. Their
own `_warm_consecutive_throttles` backoff still slows them, and they still honour an open circuit through
`_fetch_chunk`.
- Set `_WARM_THROTTLE_WEIGHT = 0.0` and pass it directly from both warm callers.
- Delete `_warm_chunk_weight`. It exists only to split a weight that is now zero.
- Update the comment on `_WARM_THROTTLE_WEIGHT` and the `fetch_quotes_batch` docstring.
- Grep every `record_rate_limited` reachable from `_warm_once` and `fundamentals_warm` (for example a per-symbol
  yfinance fallback at yfinance_provider.py:101). Any warm-reachable full-weight record is the same defect: report
  it and fix it inside your owned files, or put it in issues[] if it is outside them.

**Test.** Extend `test_warm_429s_alone_do_not_open_the_user_circuit`, or add a sibling test, with the verifier's
fresh case:
- 3 `fundamentals_warm` india sweeps plus 15 sp500 `_warm_once` cycles, all 429.
- Assert `is_open(YAHOO)` is False and `status()['consecutive_throttles'] == 0`.
- Assert a following user `fetch_quotes_batch(['RELIANCE.NS'])` spends an HTTP call.
- Class case the fix was not written against: 50 `fundamentals_warm` cycles alone. Keep the user-path control (3
  user 429s open it).

### R15-LEAD-049 (medium): nifty50 seed carries the retired TATAMOTORS

**Mechanism (confirmed).**
- `nifty50.json:33` lists `TATAMOTORS.NS`. It is the only one of the 50 constituents missing from the NSE master
  (probed).
- The listed security's continuation is **TMPV**: ISIN INE155A01022 and BSE 500570 are the old Tata Motors
  identifiers, and `former_names.json` ties "Tata Motors Limited" to TMPV.
- TMCV (ISIN INE1TAE01010) is the demerged commercial-vehicle company, a different instrument.

**Fix.** Change the constituent to `TMPV.NS`. Update `snapshot_date`/`source` only if the file's convention requires
it. Sibling audit: `TATAMOTORS` appears in no other universe or seed file. It also appears in `test_agent_runtime.py`
and `test_data_depth.py` fixtures, as literal strings that test unrelated behaviour, so leave those alone.

**Test (`test_resolver_rename.py`).**
- `test_every_nifty50_constituent_is_in_the_nse_master`: every bare symbol in `nifty50.json` is a key of
  `_nse_master()`. This class pin catches any future retired constituent.
- `test_retired_tatamotors_resolves_to_tmpv`: seed the rename lane with NSE's row `TATAMOTORS → TMPV`
  (`nse_symbol_change.set_active_map_for_tests`). Assert `resolve('TATAMOTORS','IN').best.symbol == 'TMPV'` with a
  rename annotation.
- Also assert that TMPV is among the candidates carrying `former_name` on a cold (empty-map) resolve, which is the
  entry's "still surfaces TMPV via the former-name index".

---

## W4 — sonnet (arrange_layout silent reset)

**Owned files:** `src/lib/host-actions.ts`. Test: `src/lib/host-actions.test.ts`.

### R15-LEAD-048 (medium): an unrecognised arrange_layout pattern silently resets

**Mechanism (confirmed).**
- Parse: `host-actions.ts:974-984` defaults `pattern` to `default`.
- Apply (:1579-1666) branches on auto, focus, custom, and `LAYOUT_TEMPLATE_IDS`. Anything else falls through to
  `ws.resetLayout()` and reports success.
- The preview (:1220-1266) likewise titles every unknown pattern as "Reset the panel arrangement".
- Layout-menu mode ids (`MENU_PAYLOAD_TO_MODE` in `layout-templates.ts`: fundamental, technical, macro,
  compare-desk) are therefore silently reset.

**Fix.**
- In apply and preview:
  - `default` (and a missing pattern) keeps the reset.
  - A `MENU_PAYLOAD_TO_MODE` key runs `applyLayoutMode(api, mode)`, the same layout the menu produces. Fail with "the
    layout has not mounted" when there is no api. Load `symbol` onto the chart as the template branch does. The
    preview says "Switch to the <mode> layout".
  - Any other pattern returns `fail(\`unrecognised layout "<pattern>"\`)`, and the preview names it as unknown with
    `CANT_APPLY`.
- No catalog or enum change (Tier-3: the host accepts the menu ids the model may echo from the Layout menu; the
  schema is unchanged).

**Test (`host-actions.test.ts`).**
- `arrange_layout {pattern:'fundamental'}` calls `applyLayoutMode` with `fundamental`, does not call `resetLayout`,
  and succeeds.
- `{pattern:'banana'}` fails with a message naming `banana`, and `resetLayout` is not called.
- `{pattern:'default'}` still resets.
- Class case the fix was not written against: `{pattern:'compare-desk'}` routes to the mode, while
  `{pattern:'compare'}` still takes the template path.
- Preview: an unknown pattern is not titled "Reset".

---

## Coordination and run order for the integrator

- **Files are disjoint across W1-W4.** No writer touches another writer's file.
- **Mirrors.** No mirror change is expected. `IndicatorResponse.freshness` and `NewsItem.via_symbol_feed` already
  exist in `types/data.ts`. W1 is the only writer allowed to touch `types/data.ts` (NewsItem), and only together with
  `models/news.py`.
- **Merge order.** Merge W2, W3 and W4 first (small and independent), then W1. After merging W1, run
  `test_news.py`, `test_research_relevance.py`, `test_research_fast.py`, `test_research_deep.py` and
  `test_agent_runtime.py -k news` detached. `entity_match` also gates web evidence.
- **Suite.** After all merges, run the full pytest and vitest detached, then `pnpm ci-local` detached.
- **Revert guard.** Batch-28's DATA-030 revert happened because no test covered single-word company names. W1's
  AAPL, MSFT, NVDA and INFY controls are that pin. The integrator must see them green before accepting W1.

## Issues noticed while planning (for the integrator to file; not in any writer's diff)

1. **Cold resolve binds the wrong Tata entity.** A cold-offline `resolve('TATAMOTORS','IN')` (empty NSE rename map)
   binds **TMCV** (0.69, name "Tata Motors Limited", ISIN INE1TAE01010) over TMPV (0.68), which is the retired
   ticker's ISIN continuation. This is a silent wrong-entity bind until the network rename lane hydrates.
   `marquee_aliases.json`'s comment says "TMCV replaces the delisted TATAMOTORS", which contradicts the ISIN
   continuation. It is outside LEAD-049's fix_shape.
2. **sp500.json has 2 symbols outside the US master.** `ECHO` and `VMRK` are absent from the US master, a stale or
   unknown universe entry of the same class as LEAD-049.
3. **Bare `IT` in the IN default region.** `news_provider._company_name('IT')` returns `kotakmamc-kotakit` (the
   IT.NS ETF). That is region binding (the blocked R15-DATA-002 territory), noted only for W1's test region pinning.
4. **A trailing period defeats the `inc` stopword.** `relevance.name_tokens("Gartner, Inc.")` keeps `inc.` as a
   distinctive token.
