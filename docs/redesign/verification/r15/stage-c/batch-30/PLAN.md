# R15 Stage C: batch-30 plan

- Planner: Opus, 27 Sep 2026. Base: `004-r4-experience-rebuild@19a70e80`.
- Selection: every OPEN critical/high/medium entry outside the eight stopped ids — R15-DATA-030 (high), R15-LEAD-050
  (medium), R15-LEAD-051 (medium). Plus R15-LEAD-052 (low), taken because it shares LEAD-050's root cause in the
  same function (never split a class). Lows triage not applied (`low` is not among this batch's severities; LEAD-052
  is newer than LOWS_TRIAGE.json and not in it).
- Two writers, disjoint files. No proposed_not_defect, nothing deferred.

## The shared class (why DATA-030, LEAD-050 and LEAD-052 are one writer)

All three are the same root cause: **the code has no notion of a common-word ticker**. A ticker that is also an
English word or a news acronym (IT, ON, ALL, AI) is treated either like every other ticker (news tagging: case-folded
`\bIT\b` tags "it's") or by a length proxy (relevance gate: "3+ chars upper-case passes, 2 chars never passes"),
which is wrong in both directions (GE drops; ALL-CAPS "ALL EYES ON THE FED" passes). The fix is ONE committed
stoplist + ONE anchored-mention helper, consumed by both `news_provider._tag_symbols` and
`relevance._strong_entity_score`. It lives in `sidecar/services/research/relevance.py` (the pure lexicon module that
already holds INDIA_CONTEXT_MARKERS etc.); `news_provider.py` imports it. Import check done: `services.research`'s
`__init__` pulls only `models`, and `relevance` imports only `finance`/`target` — no cycle with `news_provider`.

## Writer A (opus) — R15-DATA-030, R15-LEAD-050, R15-LEAD-052

Opus because DATA-030 is on its THIRD and LAST attempt (certification failures 2; a fourth failure stops it to the
operator), and both earlier attempts regressed on-entity tagging: the fix shape needs judgement (the curated list, the
collision rule), not transcription.

Files: `sidecar/services/news_provider.py`, `sidecar/services/research/relevance.py`, `sidecar/tests/test_news.py`,
`sidecar/tests/test_research_relevance.py`.

### R15-DATA-030 (high) — news tagging over- and under-match

- **Mechanism (confirmed at 19a70e80).** `news_provider._aliases` (l.575) = ticker as requested + bare
  exchange-stripped base (len>=2) + `_company_name` (full master name minus corporate suffix, e.g. "reliance
  industries", "meta platforms", "c3.ai"). `_tag_symbols` (l.595) matches every alias case-insensitively with
  `\b..\b` over title+summary. Both `/news` (`routers/news.py:100,111`) and the agent `news` tool
  (`agent_tools/news_tool.py:55-56`) go through `build_aliases` + `enrich`, so this is the single fix site.
  - Over-match A (common-word class): IT tags "it's", ON tags "On Holding", AI tags "AI-exposed college majors"
    (live: 7 off-entity region items on `/news?symbols=AI`), ALL tags "all".
  - Over-match B (prefix collision): the bare ticker/name is the first word of ANOTHER listed company's name:
    RELIANCE vs "Reliance Power"/"Reliance Communications"/"Reliance Global Group"; LT vs "LT Foods"; ITC vs "ITC
    Hotels"; META vs "Meta Critical Minerals"/"Meta Infotech"; AAPL's name alias "apple" vs "Apple Hospitality REIT".
    (All present in the masters: probed `_us_master`/`_nse_master`/`_bse_master`, 10365/3508/5045 rows.)
  - Why the two prior attempts failed: batch-28 dropped the alias entirely when it collided (killed "apple" for AAPL);
    batch-29 made ticker aliases case-sensitive and relied on the full multi-word name (killed "Meta unveils…",
    "Reliance shares…", "Maruti sales…", "Uber beats…"). Both removed an alias for every headline to stop a few.
- **Fix (changed strategy, per the ledger).** Keep the name alias and the case-insensitive ticker alias exactly as
  they are for every ordinary ticker. Two occurrence-level rules only:
  1. **Stoplist.** `COMMON_WORD_TICKERS: frozenset[str]` in `relevance.py`: an explicit, committed, curated list of
     tickers (US + NSE + BSE masters) that are common English words or news acronyms — IT, ON, ALL, AI, and the
     rest the writer finds by intersecting the masters' 2-5 char tickers with `/usr/share/dict/words` plus a hand
     list of news acronyms (EV, ESG, IPO, CEO, ...), then pruning by hand: EXCLUDE tickers whose company is routinely
     written by that word (META, UBER, RELIANCE, SAIL...) — the guard test's six on-entity headlines are the check.
     Scratch generation script is not committed; only the list is. For a stoplist ticker, the ticker alias (bare
     and suffixed) counts ONLY as an anchored mention: `anchored_ticker(ticker, text) -> bool`, case-sensitive
     `$TICKER`, `EXCH: TICKER` / `(EXCH:TICKER)` for NYSE/NASDAQ/Nasdaq/AMEX/NYSE American/NYSEARCA/NSE/BSE, or
     `TICKER.NS`/`TICKER.BO`. Its name alias ("gartner", "c3.ai", "allstate", "on semiconductor") and per-symbol-feed
     provenance still tag it.
  2. **Prefix collision.** An alias occurrence does not count when the text at that position (case-folded) begins
     with a DIFFERENT listed company's stripped name that is strictly longer than the alias and word-bounded
     ("reliance power" at "Reliance Power wins…"). The target's own stripped name, and names equal to the alias
     ("reliance" for RELIANCE, INC.), never disqualify. Other occurrences in the same text still tag. Build the
     colliding-name set per symbol in `build_aliases` from the three masters via
     `symbol_resolver._strip_corporate_suffix(name.lower())` (per call, no module cache — masters are lru-cached
     and tests reset them; a stale derived cache would be a new bug). `build_aliases`' return shape may change; its
     only callers are `routers/news.py` and `agent_tools/news_tool.py`, which pass it straight to `enrich` — do not
     edit those two files.
- **Tests (sidecar/tests/test_news.py, one parametrised test per behaviour, through the existing `_news_for`
  route helper).**
  - Off-entity -> `[]`: IT + "Tax-free bond yields are in a sweet spot. Get in before it's too late."; AI +
    "Choosing these AI-exposed college majors could dent your job prospects"; ON + "On Holding raises
    guidance"; RELIANCE.NS + "Reliance Power wins Bhutan project"; LT.NS + "LT Foods Q2 profit jumps 30%"; ITC.NS +
    "ITC Hotels shares list at premium"; AAPL + "Apple Hospitality REIT raises dividend" (class case on a NAME
    alias, not written against).
  - On-entity -> tagged: IT + "Gartner beats estimates"; AI + "C3.ai shares jump"; AI + "Shares of (NYSE: AI)
    rally"; RELIANCE.NS + "Reliance Industries Q2 profit rises 10%"; AAPL + "Apple beats on services" (the
    batch-28 regression, unpinned until now per the entry note).
  - `test_data_030_revert_guard_short_name_headline_tags_its_symbol` stays byte-identical and green.
- **Held back for the verifier (do NOT put in the tests):** ALL + "Nasdaq closes at all-time high" -> []; META +
  "Meta Critical Minerals secures permit" -> []; MARUTI.NS + "Maruti Infrastructure bags order" -> []; ON +
  "onsemi (NASDAQ: ON) beats" -> ['ON']; live `/news?symbols=AI|IT|ON` (US) off-entity alias-tagged region items = 0
  and `/news?symbols=META,RELIANCE.NS,UBER` still non-empty.

### R15-LEAD-050 (medium) + R15-LEAD-052 (low) — relevance gate short-ticker rule

- **Mechanism (confirmed).** `relevance._strong_entity_score` (non-IN, short-only branch): `return 0.6 if
  len(ticker) >= 3 and written else 0.0`, where `written` = the ticker as an upper-case token in the title. Length
  is a proxy for "common word": GE (short signal from brand token "ge" of "GE Aerospace") can never pass (LEAD-050,
  a regression of RESEARCH-001), while ALL passes on an ALL-CAPS title (LEAD-052, the ponytail ceiling left there).
  Note `_entity_signals` gives a 2-letter SYMBOL no signal at all (`len(symbol) >= 3`, pre-existing, unchanged); a
  2-letter target reaches the short branch only via a brand token — that is the base behaviour LEAD-050 restores.
- **Fix.** Replace the length proxy with the shared stoplist: non-IN short-only -> if `ticker in
  COMMON_WORD_TICKERS`: 0.6 iff `anchored_ticker(ticker, title)`; else 0.6 iff the ticker is written upper-case as a
  token (any length). Remove the ponytail comment; update the docstring. IN path untouched.
- **Tests (sidecar/tests/test_research_relevance.py, one parametrised test).** GE/"GE Aerospace" + "GE beats
  estimates on jet engine demand" -> kept; BP/"BP p.l.c." + "BP beats estimates on refining margins" -> kept (second
  2-letter ticker, not written against); ALL/"Allstate Corp" + "ALL EYES ON THE FED AS RATE DECISION LOOMS" ->
  dropped; ON + "Shares of (NASDAQ: ON) jump" -> kept. The existing RESEARCH-001 parametrised test stays unchanged
  and green (its docstring's "2-letter never passes alone" sentence may be corrected, cases may not).
- **Held back for the verifier:** SM/"SM Energy Company" + "SM beats on Permian output" -> kept; AI/"C3.ai, Inc." +
  "AI stocks slide on rate fears" -> dropped; IT/"Gartner Inc" + "IT spending to rise 8%" -> dropped; live DEEP
  `_run_researcher` region_feed_items = 0 for IT/ON/ALL/AI (batch-29 table) with GE news_items > 0.

Focused runs for writer A: `pytest tests/test_news.py tests/test_news_tool.py tests/test_research_relevance.py
tests/test_research_fast.py tests/test_research_deep.py tests/test_market_overview.py` (detached, polled), plus
`ruff format` + `ruff check` on the four files.

## Writer B (sonnet) — R15-LEAD-051

Sonnet: clear spec, one function, checkable output.

Files: `sidecar/services/exchange_financials.py`, `sidecar/tests/test_b7_exchange_financials.py`.

- **Mechanism (confirmed).** `FiledPeriods.cadence()` (l.137-163) returns "half-yearly" unless EVERY Indian fiscal
  half overlapping the trailing 364 days holds a filed 3-month period. A recent IPO with only Jan-Mar 2026 and
  Apr-Jun 2026 filed has the Apr-Sep 2025 half in its window with nothing filed (it predates the listing), so it is
  labelled half-yearly, and `correctness_gate._ttm_basis` then says "(a half-yearly filer)".
- **Fix (the entry's fix_shape).** A filer with ANY filed period of quarter length (`p.months == 3`) on record is
  never half-yearly: "half-yearly" only when no 3-month period exists at all; otherwise "quarterly" if
  `trailing()` is not None, else "quarterly-gap". This makes the per-half `every_half_has_a_quarter` walk redundant
  — remove it (and `_fiscal_halves`/`_fiscal_half` only if nothing else uses them). Update the docstring.
- **Acceptance.** Note: the entry says the IPO "must resolve to 'quarterly'"; under the three-valued label its chain
  is incomplete (6 of 12 months), so the correct not-half-yearly label is `"quarterly-gap"` — pin that, and that
  `_ttm_basis(None, cadence)` contains no "half-yearly". Class case not written against: a single filed quarter
  (Apr-Jun 2026 only) -> not "half-yearly". The existing LEAD-004 tests in the file (NDTV shape, Fresh A, Fresh B,
  pure half-yearly, yahoo gap) stay unchanged and green.
- **Held back for the verifier:** a former-SME migrant (Oct-Mar 6-month + Apr-Jun + Jul-Sep quarters) -> not
  half-yearly; a pure half-yearly filer with September-ending newest period -> still half-yearly; live
  `/fundamentals` NDTV / JONJUA / TCS.NS reasons as in batch-29.

Focused runs for writer B: `pytest tests/test_b7_exchange_financials.py tests/test_correctness_gate.py
tests/test_fundamentals_basis.py tests/test_fundamentals.py tests/test_growth_check.py`, plus ruff.

## Coordination and run order (integrator)

- No shared file. No `types/data.ts` mirror change (no wire-shape change: `NewsItem` and the fundamentals reason
  strings are untouched). No frontend change.
- Writer A adds the stoplist/helper to `relevance.py` and imports it in `news_provider.py`; nobody else touches
  either file.
- Merge order: B then A (independent; B is the smaller diff). Then the full chain (`pnpm ci-local`, smoke) once.
- Out-of-scope observations for the verifier's issues list (not in any diff): the name alias "on semiconductor"
  still tags prose like "bets on semiconductor tariffs" for ON, and the relevance gate scores the same prose as
  distinctive via all name tokens (pre-existing, name aliases are deliberately untouched this attempt);
  R15-CODE-RESEARCH-012 and R15-LEAD-020 (lows) share files with this batch but not a root cause, left for a lows
  batch.
