# R15-LEAD-136: dictionary-word NSE names (attempt 2, changed strategy)

Base `ae6ffff0`. Branch `r15-r3-lead136`. Model: Opus 5.5 (`claude-opus-5-5`), judgement tier, medium.

## Root cause

Attempt 1 (30306bf2) asked whether a ticker or name token was in a bundled word list. It built that list from the lower-case entries of web2 only. web2 lists "Titan", "Cupid", "Trent", "Apollo", "Lincoln", "Nile" and "Mazda" only in capitalised form, so the bundler dropped them as proper nouns. Those tickers kept the pre-fix behaviour: "Tech titan Elon Musk unveils new rocket" scored 1.00 keep=True for Titan Company.

A second gap: the rule never looked at how the headline writes the word. In "Tech titan ..." the word is lower case, which on its own shows that it is not the company name.

## Change (both required parts)

1. **Case-folded word membership.** `english_words.txt.gz` was rebuilt from every alphabetic web2 entry of 4+ letters, lower-cased. That is 232,989 words, up from 209,484 (731,652 bytes). `_reads_as_word` lower-cases the token before the lookup. So proper-noun-only entries now count: a ticker that matches any dictionary entry is ambiguous. Marquee family names (reliance, tata, ...) stay exempt, and the check is still India-scoped.
2. **Occurrence-form rule (`_lowercase_word_use`), independent of any list.** If the title writes a symbol or brand token only in lower case, it is word usage and gives no title signal. The exception is when a corroborating neighbour sits next to it (see `_named_by_neighbour`). The rule applies to every target. The test proves it holds with the word list emptied.
3. **Corroboration (`_named_by_neighbour`), shared by both rules.** A neighbour corroborates when it is one of:
   - a following name token
   - a following suffix or security/finance noun: Ltd, Limited, Company, Co./Co Ltd, shares, stock, IPO, Qn, FYxx, results, earnings, revenue, profit, quarterly, dividend
   - a preceding name token
   - a preceding NSE/BSE marker
   - a marquee group's possessive before the name ("Tata's Trent")
4. **Trent's brand tokens (decision, Tier 3).** Brands such as Zudio and Westside are not hand-listed. A brand-only headline counts in two cases:
   - the title also carries a corroborating neighbour, as in "Trent Q2 profit jumps as Zudio expands" or "Trent's quarterly profit"
   - the title writes the name capitalised and the snippet names the company with a corroborating token. Example: "Trent rallies as Zudio expands" over "Shares of Trent Ltd rose ...".

   The snippet never rescues a lower-case title use. Known limit (marked `ponytail:`): a bare word-brand followed by a verb with no corroboration still drops, e.g. "Titan bets on premium watches". A brand table is the upgrade path.
5. `news_provider.py` is unchanged. The research brief's news leg already goes through `relevance.gate_news`, which calls `row_relevant` on every item for an IN target. The news panel's alias tagging is a separate surface and outside this claim.

Files:

| file | change |
|---|---|
| `sidecar/services/research/relevance.py` | +86/-32 |
| `sidecar/services/resolver_masters/english_words.txt.gz` | binary, rebuilt |
| `sidecar/tests/test_research_relevance.py` | +139 |

## Tests (new)

- `test_every_nse_word_symbol_needs_an_anchor` enumerates the class:
  - It loads the bundled NSE master (`resolver_masters/nse_instruments.json`, the snapshot `symbol_resolver` loads) and intersects it case-insensitively with the word list. **Intersection: 234 symbols** (196 on the base list).
  - For EVERY symbol it asserts two things. "the <word> of the matter" and "Why the <word> debate is back" are dropped. "<SYMBOL> shares hit upper circuit on NSE" is kept.
  - TITAN, CUPID, TRENT, APOLLO, CAMPUS, SAFARI and ETERNAL are asserted to be in the enumerated set. They come out of the intersection; none is hand-listed.
  - Gotcha the enumeration caught: RELIANCE (a marquee name, exempt from the list) leaked on "the reliance of the matter". The occurrence-form rule now covers it.
- `test_proper_noun_dictionary_word_needs_an_anchor[TITAN|CUPID|TRENT|APOLLO]` checks the verifier's headlines plus River Trent, Apollo 11 and "Tech titan co-founder". Company forms are kept: Titan Company, Titan Co Ltd, Titan Co., Trent Q2, Trent's quarterly profit, Tata's Trent, Apollo Micro Systems, and the ALL-CAPS ticker.
- `test_lowercase_occurrence_is_word_use_without_any_list` patches `_english_words` to an empty set. TITAN lower-case uses still drop, "Titan shares" is kept, "ixigo shares jump" is kept for IXIGO, and AAPL "an apple a day" drops while "Apple unveils" is kept.
- `test_snippet_naming_the_company_corroborates_a_capitalised_title_word` covers the Trent/Zudio decision above.

Fail-before: base `relevance.py` and base `english_words.txt.gz` restored via stash, then the new tests run:
```
NSE symbols in the word list: 196
FAILED tests/test_research_relevance.py::test_every_nse_word_symbol_needs_an_anchor
FAILED tests/test_research_relevance.py::test_proper_noun_dictionary_word_needs_an_anchor[TITAN-Titan Company Limited-dropped0-kept0]
FAILED tests/test_research_relevance.py::test_proper_noun_dictionary_word_needs_an_anchor[CUPID-Cupid Limited-dropped1-kept1]
FAILED tests/test_research_relevance.py::test_proper_noun_dictionary_word_needs_an_anchor[TRENT-Trent Limited-dropped2-kept2]
FAILED tests/test_research_relevance.py::test_proper_noun_dictionary_word_needs_an_anchor[APOLLO-Apollo Micro Systems Limited-dropped3-kept3]
FAILED tests/test_research_relevance.py::test_lowercase_occurrence_is_word_use_without_any_list
FAILED tests/test_research_relevance.py::test_snippet_naming_the_company_corroborates_a_capitalised_title_word
7 failed, 49 deselected, 1 warning in 0.24s
```
Pass-after:
```
NSE symbols in the word list: 234
7 passed, 49 deselected, 1 warning in 0.33s
```

## In-process recert (economictimes host)

Base gives 6 mismatches: every TITAN, CUPID, TRENT and APOLLO prose headline scores 1.00 keep=True. After the change:
```
FOCUS   drop "Focus on flying, not selfies", "Investors focus on Fed minutes as Nifty slips"; keep "Focus Lighting and Fixtures shares hit upper circuit", "NSE: FOCUS jumps 8%"
CAMPUS  drop "Campus placements surge as IT hiring revives"; keep "Campus Activewear Q2 profit rises 18%"
SAFARI  drop "Apple Safari update fixes security flaw"; keep "Safari Industries Q1 results beat estimates"
ETERNAL drop "The eternal debate: growth vs value investing"; keep "Eternal shares rise as Blinkit orders grow"
RAIN    drop "Rain lashes Mumbai, trains delayed", "Monsoon rain deficit hits kharif sowing"; keep "Rain Industries Q2 loss narrows", "RAIN shares surge 8%"
TITAN   drop "Tech titan Elon Musk unveils new rocket" 0.25, "Media titan Murdoch steps down" 0.25, "Titan submersible inquiry report released" 0.25; keep "Titan Company shares rise" 1.00, "Titan Q2 profit jumps 20%" 1.00
CUPID   drop "Cupid's arrow: Valentine's Day spending hits record" 0.25; keep "Cupid Ltd shares hit upper circuit"
TRENT   drop "River Trent floods as storm lashes England" 0.25; keep "Trent Q2 profit jumps as Zudio expands", "Trent shares fall 4% after results"
APOLLO  drop "Apollo 11 anniversary: NASA looks back"; keep "Apollo Micro Systems bags defence order"
RELIANCE keep "Reliance Industries Q2 results beat estimates", "Reliance to buy stake in X"
ROUTE   drop "Best route to the airport"; keep "Route Mobile wins telecom deal"
INFY    keep "Infosys wins European deal"
mismatches 0
```

## Live

Setup:
- Own sidecar from source on port 52950.
- Data dir `scratchpad/r3-136-data`, seeded from `final-seed-data`. `dev-keystore.json` is exactly `{"secrets": {}, "migrated": true}`.
- Header `X-Vysted-Region: IN`. The log never shows "missing bundled".
- Each research run happened inside `mkdir /tmp/vysted-r15-ollama.lock` and released it with `rmdir`.

Research FAST (MCP `research`, `depth=quick`), on the final code:
- **Titan Company**: resolves to TITAN / Titan Company Limited / NSE, bound at score 1.00. News `ok`, rss, 1 item: "Titan Company deepens focus on mechanical horology as category grows almost 5-fold" (Pulse by Zerodha), which is the company's own story. Filings: 20 NSE+BSE announcements, all Titan's. No unrelated common-word headline. Web search timed out at 8 s; price timed out keyless.
- **Trent**: resolves to TRENT / Trent Limited / NSE, bound at score 1.00. News `ok`, `data []`: the feed returned no item for the symbol leg. Filings: 20 announcements, all Trent's. No unrelated headline. Web search timed out at 8 s.
- Raw `/news?symbol=TITAN|TRENT&limit=40` returns the same 40 region items for both symbols, scored with the new gate:
  - TITAN keeps 1, the Titan Company story above.
  - TRENT keeps 0. The note is "No on-entity news found for TRENT — 40 item(s) returned by the news feed were off-entity/off-topic and dropped".
  - Today's feed has no common-word titan or trent headline. The real-world class check below fills that gap.

Real headlines: the top 12 items of each Google News RSS (IN edition) query, fetched 3 Oct 2026 and scored by `row_relevant`.

| query / target | base keeps | fix keeps |
|---|---|---|
| "Titan Company" / TITAN | 12/12 | 9/12 |
| "tech titan" / TITAN | **10/12** | 2/12 |
| "Trent shares" / TRENT | 12/12 | 9/12 |
| "Trent Zudio" / TRENT | 12/12 | 7/12 |
| "River Trent" / TRENT | **7/12** | 0/12 |

- **Dropped by the fix (base kept them):**
  - "How SAP became Europe's low-key tech titan"
  - "Apple's 50-year journey from garage to tech titan"
  - "Exam reforms: Tech titan Nandan Nilekani ..."
  - "Dow Jones Tech Titan Amazon Eyes Buy Point"
  - every River Trent story
  - "REG - Severn Trent PLC - Issuance of shares"
  - "Titan Intech gets GeM OEM recognition" (a different company)
- **Kept, the companies' own headlines:**
  - "Titan Co Ltd Q1 FY27 revenue grows 41%"
  - "Titan Co. slips Thursday"
  - "Titan Shares: Motilal Oswal Maintains 'Buy'"
  - "Trent shares crash 13% ..."
  - "Trent's Q1 Profit Jumps 26% ..."
  - "Tata's Trent Sees 22% Profit Rise ..."
  - "Indian fashion retailer Trent's quarterly profit jumps ..."
  - "Market wrap: ... Titan Company top gainers"
- **Residuals, recorded and not fixed:**
  - One false keep: "Ambani's Tech Titan IPO Story Isn't Yet Credible". The headline is Title Case, so the case form carries no signal, and "IPO" follows the word.
  - Recall misses of the bare brand plus verb shape, which is the `ponytail:` ceiling: "Titan bets on premium watches", "Trent: Zudio hits milestone", "Zudio Crosses 1,000 Stores As Trent Scales ...", "Indian retailer Trent posts higher quarterly profit".

## Checks

- New tests: 7 fail on `ae6ffff0` code and 7 pass after (tails above).
- Touched area: `pytest tests/test_research_relevance.py tests/test_research_fast.py tests/test_news.py tests/test_tests_encoding.py -q` gives `140 passed, 1 warning in 18.86s`.
- Full suite, `cd sidecar && .venv/bin/python -m pytest tests -q` (detached): `3996 passed, 1 skipped, 4 warnings in 215.27s (0:03:35)`, EXIT=0.
  - An earlier full run flagged `test_tests_encoding` because the new test used a positional `read_text("utf-8")`. I fixed it to `encoding=` before the green run.
  - After the green run I changed one docstring paragraph, then reran ruff and the touched-area tests.
- `ruff format <changed>`: `2 files left unchanged`. `ruff format --check .`: `455 files already formatted`. `ruff check .`: `All checks passed!`
- No TS change.
