# R15-LEAD-059 — writer notes (rc1 round-5 fix-r2)

Branch `worktree-agent-rc1-r5-fix-focus`, base `b047f519` (descends from `e5877962`). Written 18:14 IST.

## Root cause

The announcements lane decided which BSE feed to merge by the **ticker string**, not the company:

- `sidecar/services/corporate_disclosures.py:554` (base) — the BSE lane was applicable when
  `symbol_resolver.is_bse_symbol(bare)`, i.e. whenever *any* BSE scrip carries the ticker `FOCUS`.
- `sidecar/services/corporate_disclosures.py:199` (base) — `_fetch_bse_announcements` then keyed the
  feed on `symbol_resolver.bse_scrip_code(bare)` — the BSE master row under the same ticker, which for
  FOCUS is **543312, Focus Business Solution Ltd** (ISIN INE0DXR01010). NSE FOCUS is **Focus Lighting
  and Fixtures**. The two feeds were merged under one symbol.
- `sidecar/services/corporate_disclosures.py:1133` (base) — the shareholding lane had the same flaw: its
  BSE fallback lane (`is_bse = is_bse_symbol(bare)`) would serve 543312's patterns as FOCUS's when the
  NSE lane failed.

The resolver already had the right pairing: `symbol_resolver.dual_listed_bse_code`
(`symbol_resolver.py:768`) returns the BSE scrip only when the same-ticker BSE row IS the NSE company
(`_bse_row_is_same_company`: instrument type + legal-name agreement), and the resolver shows NSE FOCUS
with `bse_code: null`. Results, corporate actions and deals already used it; announcements and the
shareholding fallback did not. It was not a name search or a prefix match; it was a plain same-ticker lookup.

A second, smaller root cause surfaced once announcements used the resolver pairing: `_company_name_key`
(`symbol_resolver.py:1470`) did not strip BSE's trailing `-$` marker ("KDDL Ltd-$"), so short names that
ARE one company (KDDL, IZMO, KSE, LINC, TRF, TTL) failed the name check and got no dual-listing code.
Longer names passed the 0.75 ratio despite the marker. Without that fix the change would have dropped
those names' true BSE leg from announcements.

## Fix

- `corporate_disclosures.listing_lanes(bare)` returns `(NSE lane applies, BSE scrip code)` for one
  company: an NSE listing gets `dual_listed_bse_code(bare)`, never the same-ticker scrip, and a BSE-only
  name keeps its own scrip. All five lanes (announcements, results calendar, corporate actions, deals,
  shareholding) take their lanes from this helper, so no two lanes gate differently.
- When a same-ticker BSE scrip exists but belongs to another company, the NSE-only answer carries
  `note: "BSE FOCUS is a different company; only the NSE feed is served"` (the existing `note` field;
  `coverage` stays `covered`). No shape change: the `note` comment in `models/announcements.py` is widened.
- `symbol_resolver._company_name_key` strips a trailing `-$` before comparing names (one line).

Known ceiling, not changed: `strip_exchange_suffix` drops `.BO`, so `FOCUS.BO` resolves to the NSE
company (NSE-only feed, no mixing). Serving the BSE company for an explicit `.BO` would contradict the
pinned `test_class_case_deals_and_actions_gate_the_same_way_amal_bo_still_served` (an explicit `.BO` is
served from the NSE lanes), so it is left for an operator decision.

## Tests (`sidecar/tests/test_corporate_disclosures.py`)

- `test_lanes_are_anchored_on_one_company_not_the_ticker` checks the bundled masters with no mocks:
  RELIANCE→(True,500325), TCS→(True,532540), KDDL→(True,532054), FOCUS→(True,None), ICONIKSPEV→(False,511260).
- `test_announcements_never_merge_another_companys_bse_feed`: for FOCUS the BSE seam is never called,
  sources are `["NSE"]`, every row is NSE and the note says why.
- `test_true_dual_listing_still_merges_without_a_note`: RELIANCE merges both feeds, keys BSE on 500325
  and has no note.
- `test_shareholding_never_falls_back_to_another_companys_bse_patterns`: when FOCUS's NSE lane fails,
  the call raises and 543312's patterns are never fetched.

At base, the first three new FOCUS/anchor tests fail. With only the resolver line reverted, the anchor
test fails on KDDL. After the fix:
- focused modules: `pytest tests/test_corporate_disclosures.py tests/test_symbol_resolver.py
  tests/test_disclosure_tools.py tests/test_disclosures_router.py tests/test_b7_exchange_disclosures.py
  tests/test_research_disclosures.py tests/test_b5_india_deals.py` gives **191 passed**.
- full sidecar suite: `pytest tests` gives **3784 passed, 1 skipped** (EXIT=0).
- `ruff format --check .` and `ruff check .` in `sidecar/`: clean.

## Live re-check (own sidecar, port 52340, scratch VYSTED_DATA_DIR)

`curl -s -H 'X-Vysted-Region: IN' 'http://127.0.0.1:52340/disclosures/announcements?symbol=<S>'`

| symbol | build | count | sources | rows by exchange | note |
|---|---|---|---|---|---|
| FOCUS | pre-fix (b047f519) | 50 | NSE, BSE | NSE 34, **BSE 16 (scrip 543312)** | none |
| FOCUS | fixed | 44 | NSE | NSE 44, BSE 0 | "BSE FOCUS is a different company; only the NSE feed is served" |
| RELIANCE | fixed | 50 | NSE, BSE | NSE 45, BSE 5 | none |
| TCS | fixed | 50 | NSE, BSE | NSE 42, BSE 8 | none |
| ZEAL (held-out collision) | fixed | 50 | NSE | NSE 50 | "BSE ZEAL is a different company; …" |
| KDDL (held-out `-$` dual) | fixed | 50 | NSE, BSE | NSE 36, BSE 14 | none |

On the fixed build, the other FOCUS lanes (`/disclosures/shareholding`, `/results`, `/corporate-actions`,
`/deals`) are all `coverage: covered`, carry the same note, and read from NSE only. `GET /resolve?q=FOCUS`
is unchanged: NSE Focus Lighting has `bse_code: null` and BSE Focus Business Solution has `543312`.
Evidence: `pre-focus-ann.json`, `pre-focus-resolve.json`, and `post-*.json` in this folder.

## Held-out names used

ZEAL (NSE Zeal Global Services vs BSE 539963 Zeal Aqua) and KDDL (BSE "KDDL Ltd-$", 532054). The
resolver's other same-ticker, different-company collisions (KALYANI, RAJPUTANA, MAL, SEL) take the same
path.
