# R15-LEAD-116 writer record (03:34 IST, Sonnet 5.5, base 9368c626)

## Root cause
All five lanes did `bare = strip_exchange_suffix(symbol)` before `listing_lanes(bare)`, so an explicit `.BO` pin collapsed onto the NSE company whenever the ticker names two companies (FOCUS: NSE Focus Lighting vs BSE 543312 Focus Business Solution).

## Fix
- `symbol_resolver.pinned_other_company_bse_code(symbol)`: for an explicit `.BO` where the ticker is in both masters and `_bse_row_is_same_company` is False, return the BSE scrip code; else None. Judged on names, independent of `dual_listed_bse_code` (AMAL.BO with that masked still returns None).
- `corporate_disclosures._lane_symbol` replaces the five `strip_exchange_suffix` lines; the lanes then key on the scrip code, exactly as `symbol=543312` does (`listing_lanes` gives BSE-only). `listing_lanes` itself is untouched.
- LEAD-117 NOT taken: the venue_not_covered note is in get_announcements only and the fix needs a new branch plus wording, more than one line.

## Tests (sidecar/tests/test_corporate_disclosures.py)
- test_explicit_bo_pin_on_a_different_company_takes_the_bse_company_in_every_lane (5 params): NSE provider calls raise, FOCUS.BO result == 543312 result. All 6 new cases failed at base.
- test_bo_pin_keeps_same_company_and_bare_behaviour: FOCUS.BO -> 543312, bare FOCUS None, AMAL.BO None with dual_listed masked, listing_lanes(FOCUS) == (True, None), INFY.NS/HDFCBANK keep both lanes.
- pytest test_corporate_disclosures.py test_disclosure_tools.py test_symbol_resolver*.py: 146 passed. ruff format --check sidecar and ruff check sidecar clean.

## Live (own sidecar, port 52391, X-Vysted-Region: IN, scratch data dir)
Real masters: FOCUS.BO is_bse=True dual=None pinned=543312; AMAL.BO dual=506597 pinned=None; INFY.NS dual=500209; HDFCBANK dual=500180.
Raw JSON and summary.txt in this folder. FOCUS.BO JSON == symbol=543312 JSON in all five lanes:
announcements 23, results 10, shareholding 13, corporate-actions 5, deals 39 (BSE only).
Bare FOCUS: NSE only with the "different company" note (44/35/21/4/11). AMAL.BO merges NSE+BSE as before (21/10/104/5/18). INFY.NS 50/70/21/20/219 and HDFCBANK 50/75/22/20/120 still merge both exchanges.
Sidecar stopped (pid 4026).
