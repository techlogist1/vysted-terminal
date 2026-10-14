# R15-LEAD-136 — dictionary-word NSE names need an anchor (list-independent)

Base `d0744711`; branch `r15-r2-lead136`. Model: Opus 5.5 (claude-opus-5-5), judgement tier.

## Root cause

`relevance._entity_signals` treated a symbol/brand token as prose only when it
was in the hand-curated `COMMON_WORD_TICKERS` (round 1, R15-FINAL-004). Any NSE
name that is an English word but not in that list (CAMPUS, SAFARI, ETERNAL, and
~190 others in the NSE master) still scored 1.0 on any headline with the word,
because (a) the brand-token check and (b) the "all distinctive tokens present"
rule both fire on a one-word match ("ETERNAL LIMITED" → `["eternal"]`).

## Change (strategy: a property, not a list)

- `_reads_as_word(token, india=)`: a `COMMON_WORD_TICKERS` entry, or, for an
  Indian target, any token in a bundled English dictionary
  (`services/resolver_masters/english_words.txt.gz`: Webster's 2nd, public
  domain, BSD `/usr/share/dict/web2`, lower-case entries ≥4 letters, 209,484
  words, 659 KB). Marquee family names from the existing
  `marquee_aliases.json` (reliance, tata, …) are exempt: the resolver already
  treats a bare family name as the brand.
- `_word_used_as_name(token, title, name_toks)`: a word-like token counts only
  when anchored: `anchored_ticker` (cashtag, `NSE: X`, `X.NS`), the ticker written
  ALL-CAPS in a mixed-case title, NSE/BSE in the title, or the word directly
  followed by another name token of the company ("Safari Industries", "Campus
  Activewear") or by a corporate suffix / security noun (Ltd, Limited, shares,
  stock, scrip, IPO, Q1-Q4, FYxx).
- Host/path hits of a word symbol (`safaribookings.com/safari-tours`) are prose;
  a `symbol=SAFARI` quote url still counts.
- A one-token name that is a word is no longer "all distinctive tokens present".
- India-scoped: the non-IN path keeps its own gates (Apple, a dictionary word,
  stays a brand for AAPL; non-IN news trusts the per-symbol feed). Tier 3, from
  the entry's NSE scope.
- Packaging: `services/resolver_masters/` already ships via `--add-data` in
  `scripts/sidecar-specs.mjs` (`MAIN_ADD_DATA`), so no recipe change was needed.
  It loads through `importlib.resources` like the other masters.
- Known ceiling (marked `ponytail:` in code): a bare word-brand plus a verb
  ("Persistent wins deal", "Route bags order") now reads as prose and is
  dropped. Name-plus-suffix/security-noun headlines are kept.

Files: `sidecar/services/research/relevance.py` (+105/-8),
`sidecar/tests/test_research_relevance.py` (+111),
`sidecar/services/resolver_masters/english_words.txt.gz` (new, binary).

## Tests

`test_dictionary_word_indian_name_needs_an_anchor` runs on CAMPUS, SAFARI and
ETERNAL, plus three fresh real NSE words in no curated list: PERSISTENT (Persistent
Systems), TRIDENT (Trident Ltd) and SYMPHONY (Symphony Ltd). Each case asserts
`is_nse_symbol` and absence from `COMMON_WORD_TICKERS`. The resolver binds all six
at score 1.0 (`symbol_resolver.resolve(sym, "IN")`).
`test_word_symbol_in_host_or_path_is_prose_but_quote_url_is_the_ticker` covers the
host/path rule. Two regression guards were added:
`test_non_word_and_marquee_indian_names_unchanged` (RELIANCE plain headline,
INFY, Route Mobile) and `test_dictionary_gate_is_india_scoped` (AAPL).

Fail-before (base `relevance.py` swapped in, new tests run):
```
FAILED tests/test_research_relevance.py::test_dictionary_word_indian_name_needs_an_anchor[CAMPUS-Campus Activewear Limited-dropped0-kept0]
FAILED tests/test_research_relevance.py::test_dictionary_word_indian_name_needs_an_anchor[SAFARI-Safari Industries (India) Limited-dropped1-kept1]
FAILED tests/test_research_relevance.py::test_dictionary_word_indian_name_needs_an_anchor[ETERNAL-ETERNAL LIMITED-dropped2-kept2]
FAILED tests/test_research_relevance.py::test_dictionary_word_indian_name_needs_an_anchor[PERSISTENT-Persistent Systems Limited-dropped3-kept3]
FAILED tests/test_research_relevance.py::test_dictionary_word_indian_name_needs_an_anchor[TRIDENT-Trident Limited-dropped4-kept4]
FAILED tests/test_research_relevance.py::test_dictionary_word_indian_name_needs_an_anchor[SYMPHONY-Symphony Limited-dropped5-kept5]
FAILED tests/test_research_relevance.py::test_word_symbol_in_host_or_path_is_prose_but_quote_url_is_the_ticker
7 failed, 2 passed, 40 deselected, 1 warning in 0.22s
```
The 2 that pass on base are the two regression guards
(`test_non_word_and_marquee_indian_names_unchanged`,
`test_dictionary_gate_is_india_scoped`). They are meant to pass on both sides.
All 7 behaviour tests fail on base.
Pass-after:
```
9 passed, 40 deselected, 1 warning in 0.06s
```

In-process recert, same cases as `final-pass/reproof/recert/f004-relevance.txt` plus round-1 controls (host economictimes.indiatimes.com):
```
== FOCUS Focus Lighting and Fixtures Limited
  expect DROP Focus on flying, not selfies                               score=0.25 keep=False OK
  expect DROP European shares focus on inflation data                    score=0.25 keep=False OK
  expect DROP Investors focus on Fed minutes as Nifty slips              score=0.25 keep=False OK
  expect KEEP Focus Lighting and Fixtures shares hit upper circuit       score=1.00 keep=True OK
  expect KEEP Focus Lighting Q1 results: profit up 40%                   score=1.00 keep=True OK
  expect KEEP NSE: FOCUS jumps 8%                                        score=1.00 keep=True OK
== CAMPUS Campus Activewear Limited
  expect DROP Campus placements surge as IT hiring revives               score=0.25 keep=False OK
  expect DROP Back to campus: retailers bet on festive demand            score=0.25 keep=False OK
  expect KEEP Campus Activewear Q2 profit rises 18%                      score=1.00 keep=True OK
  expect KEEP Campus Activewear shares jump after brokerage upgrade      score=1.00 keep=True OK
== SAFARI Safari Industries (India) Limited
  expect DROP Safari tourism booms in Kenya as visitors return           score=0.25 keep=False OK
  expect DROP Apple Safari update fixes security flaw                    score=0.25 keep=False OK
  expect KEEP Safari Industries Q1 results beat estimates                score=1.00 keep=True OK
  expect KEEP Safari Industries stock hits 52-week high                  score=1.00 keep=True OK
== ETERNAL ETERNAL LIMITED
  expect DROP The eternal debate: growth vs value investing              score=0.25 keep=False OK
  expect KEEP Eternal shares rise as Blinkit orders grow                 score=1.00 keep=True OK
  expect KEEP Eternal Ltd Q2 profit falls on quick-commerce costs        score=1.00 keep=True OK
== CLEAN Clean Science and Technology Limited
  expect DROP Clean energy stocks rally on policy push                   score=0.25 keep=False OK
  expect DROP Clean chit for broker in SEBI probe                        score=0.25 keep=False OK
  expect KEEP Clean Science and Technology Q2 profit rises 12%           score=1.00 keep=True OK
  expect KEEP Clean Science shares slip after block deal                 score=1.00 keep=True OK
== TRUST Trust Fintech Limited
  expect DROP Trust deficit weighs on markets                            score=0.25 keep=False OK
  expect DROP Investors lose trust in small caps                         score=0.25 keep=False OK
  expect KEEP Trust Fintech IPO subscribed 100 times                     score=1.00 keep=True OK
== OIL Oil India Limited
  expect DROP Oil prices climb as OPEC trims output                      score=0.25 keep=False OK
  expect DROP Crude oil slips below $70                                  score=0.25 keep=False OK
  expect KEEP Oil India Q2 profit jumps 30%                              score=1.00 keep=True OK
  expect KEEP Oil India shares rally on gas discovery                    score=1.00 keep=True OK
== IDEA Vodafone Idea Limited
  expect DROP Big idea: how to pick midcaps                              score=0.25 keep=False OK
  expect KEEP Vodafone Idea shares surge after AGR relief                score=1.00 keep=True OK
== RELIANCE Reliance Industries Limited
  expect KEEP Reliance Industries Q2 results beat estimates              score=1.00 keep=True OK
  expect KEEP Reliance to buy stake in X                                 score=1.00 keep=True OK
== ROUTE ROUTE MOBILE LIMITED
  expect KEEP Route Mobile wins telecom deal                             score=1.00 keep=True OK
== INFY Infosys Limited
  expect KEEP Infosys wins European deal                                 score=1.00 keep=True OK
mismatches 0
```

## Live (own sidecar from source, port 52960, keyless data copy seeded from final-seed-data, dev-keystore `{"secrets": {}, "migrated": true}`, region IN)

Research `depth=quick` (FAST) via the sidecar's MCP `research` tool, header `X-Vysted-Region: IN`:

- `Campus Activewear` → symbol CAMPUS, ok=True. News: `data: []`, note "No on-entity news found for CAMPUS — 1 item(s) returned by the news feed were off-entity/off-topic and dropped." Brief sources 0. 0 mentions of "placement", "tourism" or "Apple". Web: timeout. Price and fundamentals timed out keyless.
- `Safari Industries` → symbol SAFARI, ok=True. News: `data: []` (the feed returned nothing for the symbol leg). Brief sources 0. 0 unrelated common-word headlines.
- Raw `/news?symbol=X&limit=40` scored with the new gate: CAMPUS 40 items, 0 kept; SAFARI 40, 0 kept; ETERNAL 40, 0 kept. Today's live feed has no headline that uses "campus", "safari" or "eternal" as a common word, so the class itself is proven by the in-process cases above, not by live data. No unrelated headline reached either brief.

## Checks

- `pytest tests/test_research_relevance.py tests/test_research_fast.py -q` → `85 passed`
- full `pytest tests -q` (detached) → `3981 passed, 1 skipped, 4 warnings in 220.42s (0:03:40)`, EXIT=0
- `ruff format <changed>` → `2 files left unchanged`; `ruff format --check .` → `455 files already formatted`; `ruff check .` → `All checks passed!`
- No TS change.
