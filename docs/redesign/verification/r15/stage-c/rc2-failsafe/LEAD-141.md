# R15-LEAD-141: 3-letter NSE word tickers (attempt 1, DECISIONS 5.14 fail-safe)

Base `b7d37fd9`. Branch `r15-fs-lead141`. Model: Opus 5.5 (`claude-opus-5-5`), judgement tier, medium.

## Root cause

LEAD-136 (a91d3373) made a word-like ticker count only when anchored. Its two checks both miss 3-letter words:

- `_reads_as_word` looks the token up in `english_words.txt.gz`, and that list held web2 entries of 4+ letters only.
- `_lowercase_word_use` fires only on an all-lower-case occurrence.

So ACE in "Ace shuttler PV Sindhu storms into final" was not prose. It became a short-only symbol signal, and with an India host (or any India marker) `_strong_entity_score` returned 0.60, which is kept. The same applies to DEN ("Den of thieves"), CUB ("Cub reporter"), PAR ("Par for the course") and KEN ("Ken Griffin"). Those are 5 of the 17 symbols in the class.

## Change

1. **Word list: 3+ letters.** `english_words.txt.gz` is rebuilt from the same source the same way: every alphabetic web2 entry, lower-cased, sorted, gzip level 9, mtime 0. The only difference is the length floor, now 3 instead of 4. The 4+ part is byte-identical in content: before the change I checked that the rebuild of the 4+ entries equals the shipped set. The list goes from 232,989 to 234,289 words (+1,300 three-letter entries) and from 731,652 to 734,081 bytes. Same path and loader, so the PyInstaller `--add-data services/resolver_masters` entry already ships it.
2. **Scope guard in `_reads_as_word` (Tier-3 decision).** A 3-letter entry counts only when the token **is the target's ticker** (new `ticker=` keyword, passed `symbol` at both call sites in `_entity_signals`).
   - 3-letter brand tokens that are not the ticker keep their base path. Examples: Zee for ZEEL, Yes for YESBANK, Gas for IGL/MGL/ATGL, Jet, Zen. That is 106 NSE names.
   - Why: the claim is the ticker class. Brand recall is LEAD-142, filed separately, and must not get worse.
   - Pinned: "Zee bags cricket rights" stays 0.60 for ZEEL.
3. **Anchor rule unchanged.** Once a 3-letter ticker reads as a word, the existing `_word_used_as_name` decides. A Title-Case or sentence-initial use counts only when one of these holds:
   - an `anchored_ticker` form ($ACE, NSE: ACE, ACE.NS)
   - the ticker written ALL-CAPS in a mixed-case title
   - NSE/BSE in the title
   - a corroborating neighbour: a name token ("City Union Bank", "Den Networks", "Par Drugs") or a security noun ("Ace Q2 results", "Ken Enterprises IPO")
   - a snippet naming the company that way

   Marquee family names stay exempt (none are 3 letters except `l&t`, which is non-alphabetic).

| file | change |
|---|---|
| `sidecar/services/research/relevance.py` | +12/-6 |
| `sidecar/services/resolver_masters/english_words.txt.gz` | binary, rebuilt (3+ letters) |
| `sidecar/tests/test_research_relevance.py` | +98 |

## Tests (new)

- `test_every_nse_word_symbol_needs_an_anchor_in_title_case` (sibling of the LEAD-136 enumeration):
  - It enumerates NSE master ∩ word list. The set now includes the 3-letter words: **251 symbols**, up from 234, and 17 of them are 3-letter: ABB, ACE, AWL, AYE, BEL, CUB, DEN, HAL, KEN, MAL, OIL, PAR, SAB, SIL, SIS, TIL, UDS.
  - It asserts that ACE, DEN, CUB, PAR and KEN fall out of the enumeration.
  - For EVERY symbol it asserts that "<Word> of the day: what it means for your weekend" is dropped (marquee names exempt) and "<SYMBOL> shares hit upper circuit on NSE" is kept.
- `test_three_letter_word_ticker_needs_an_anchor[ACE|DEN|CUB|PAR|KEN]`:
  - The verifier's headlines are dropped at ≤ the weak ceiling.
  - Company forms are kept: ACE shares, Action Construction Equipment Q2, NSE: ACE, Ace Q2 results, Den Networks Q1, DEN surges, City Union Bank Q2, CUB shares on NSE, Par Drugs And Chemicals shares, PAR Drugs Q1, Ken Enterprises IPO, KEN shares on NSE.
- `test_three_letter_words_leave_brand_list_headlines_unchanged`:
  - This pins the LEAD-142 headlines to their exact `b7d37fd9` scores. "Titan, Trent lead Nifty gains as consumer stocks rally" = 0.25/0.25 (TITAN/TRENT), "Stocks to buy: Titan, Lenskart, Dabur ..." = 0.25/0.0, "Trent rallies 5% as Zudio store count crosses 800" = 0.0/0.25. ZEEL "Zee bags cricket rights" = 0.6.
  - It is a no-regression guard, so it passes on base by design.

Fail-before: base `relevance.py` and base `english_words.txt.gz` checked out from `b7d37fd9`, new tests run, fix restored:
```
NSE symbols in the word list: 234 (0 three-letter: [])
FAILED tests/test_research_relevance.py::test_every_nse_word_symbol_needs_an_anchor_in_title_case
FAILED tests/test_research_relevance.py::test_three_letter_word_ticker_needs_an_anchor[ACE-Action Construction Equipment Limited-dropped0-kept0]
FAILED tests/test_research_relevance.py::test_three_letter_word_ticker_needs_an_anchor[DEN-Den Networks Limited-dropped1-kept1]
FAILED tests/test_research_relevance.py::test_three_letter_word_ticker_needs_an_anchor[CUB-City Union Bank Limited-dropped2-kept2]
FAILED tests/test_research_relevance.py::test_three_letter_word_ticker_needs_an_anchor[PAR-Par Drugs And Chemicals Limited-dropped3-kept3]
FAILED tests/test_research_relevance.py::test_three_letter_word_ticker_needs_an_anchor[KEN-Ken Enterprises Limited-dropped4-kept4]
6 failed, 1 passed, 56 deselected, 1 warning in 0.25s
```
Pass-after:
```
NSE symbols in the word list: 251 (17 three-letter: ['ABB', 'ACE', 'AWL', 'AYE', 'BEL', 'CUB', 'DEN', 'HAL', 'KEN', 'MAL', 'OIL', 'PAR', 'SAB', 'SIL', 'SIS', 'TIL', 'UDS'])
7 passed, 56 deselected, 1 warning in 0.34s
```
The LEAD-136 / FINAL-004 tests are unchanged and green. `test_every_nse_word_symbol_needs_an_anchor` now enumerates 251 and passes.

## Real headlines (class check)

Top 12 Google News RSS (IN edition) items per query, fetched 3 Oct 2026 and scored by `row_relevant` on an economictimes host. "base" = the same code with the word list cut back to the shipped 4+ set, which is what `b7d37fd9` does for these targets.

| query / target | base keeps | fix keeps |
|---|---|---|
| "Ace shuttler" / ACE | **4/12** | 0/12 |
| "Action Construction Equipment" / ACE | 12/12 | 11/12 |
| "Den of" / DEN | **10/12** (Den of Geek reviews) | 0/12 |
| "Den Networks" / DEN | 12/12 | 12/12 |
| "Cub reporter" / CUB | **5/12** | 0/12 |
| "City Union Bank" / CUB | 12/12 | 12/12 |
| "Par for the course" / PAR | **4/12** | 0/12 |
| "Ken Griffin" / KEN | **9/12** | 0/12 |

The one company headline now dropped is "Ace targets 15 pc export revenue share for cranes by 2030 - Construction Week India". It is a bare Title-Case brand plus a verb with no corroboration. That is the anchor requirement as specified, and the same shape as the LEAD-136 `ponytail:` limit / LEAD-142 (a brand/alias table is the upgrade).

## Live

Setup:
- Own sidecar from source (`main.py --port 52950`), stdin held open by a fifo.
- Data dir `scratchpad/fs-141-data`, seeded from `final-seed-data`. `dev-keystore.json` is exactly `{"secrets": {}, "migrated": true}`.
- Header `X-Vysted-Region: IN`. The log shows 0 "missing bundled" lines.
- The research calls ran inside `mkdir /tmp/vysted-r15-ollama.lock` and released it with `rmdir`.
- The sidecar was stopped by pid afterwards and the port confirmed free.

MCP `research`, `depth=quick`:
- **"Action Construction Equipment"** (8.8 s): resolves to ACE / Action Construction Equipment Limited / NSE, confidence 1.0. News `ok`, rss, `data []`, note "No on-entity news found for ACE — 1 item(s) returned by the news feed were off-entity/off-topic and dropped." No unrelated word-use headline in the brief.
- **"City Union Bank"** (8.5 s): resolves to CUB / City Union Bank Limited / NSE, confidence 1.0. News `ok`, 1 item: "Wizz Financial collaborates with City Union Bank to Unveil 'Wizz Voyager' ..." (Yahoo CUB.NS feed). That is the bank's own story; there is no "Cub ..." word headline.
- Raw `/news?symbol=ACE|CUB|DEN|PAR|KEN&limit=40` (IN region feed): 40 items each, 0 kept by `gate_news` for each symbol, and no title in today's feed uses any of the five words. The Google News table above is the real-world class check.

## Checks

All run in the worktree with `sidecar/.venv` (Python 3.13):

```
$ .venv/bin/python -m pytest tests/test_research_relevance.py tests/test_news.py tests/test_news_tool.py tests/test_research_fast.py -q
151 passed, 1 warning in 18.98s

$ .venv/bin/python -m pytest tests -q          # detached, polled
4010 passed, 1 skipped, 4 warnings in 214.87s (0:03:34)
EXIT=0

$ .venv/bin/ruff format services/research/relevance.py tests/test_research_relevance.py
2 files left unchanged                       EXIT=0
$ .venv/bin/ruff format --check .
455 files already formatted                  EXIT=0
$ .venv/bin/ruff check .
All checks passed!                           EXIT=0
```

No TypeScript was touched.
