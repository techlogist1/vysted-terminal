# R15-LEAD-059 fix verification (rc1 round 5, fix-r2)

Fresh verifier, 18:27 IST 2026-09-27. Code under test: `769b1f31` (worktree-agent-rc1-r5-fix-int).
Own sidecar on 127.0.0.1:52341, scratch VYSTED_DATA_DIR, header `X-Vysted-Region: IN`.
Raw responses: `verify/` beside this file.

**Verdict: certified.** No case (a)-(e) refutes the fix. Two adjacent defects are listed at the end.

The fix: `listing_lanes(bare)` gives an NSE listing only its verified dual listing
(`symbol_resolver.dual_listed_bse_code`, a name-similarity check at 0.75 or above) as its BSE lane.
The announcements and shareholding lanes now use it; results, corporate-actions and deals already did.
`_company_name_key` also strips BSE's `-$` marker.

## Offline audit of the bundled masters (every ticker, not a sample)

- 2657 tickers are in both the NSE and BSE masters. After the fix, 2651 keep their BSE lane and **6 lose it**:
  FOCUS (0.40), KALYANI (0.61), RAJPUTANA (0.55), MAL (0.31), SEL (0.62), ZEAL (0.38).
  All 6 are different companies (for example, Kalyani Commercials and Kalyani Cast-Tech, or Mangalam Alloys and Meyer Apparel).
  Before the fix, the announcements code gated the BSE lane on `is_bse_symbol`, so all 6 merged the other company's BSE feed.
- The lowest-scoring kept equity pairs (0.81-0.93: BLACKROSE, SANDESH, 21STCENMGM, BOMDYEING, GSTL, ...) are all the same company.
- Changing `-$` in the name key flips exactly 6 pairs from refused to accepted: KDDL, IZMO, KSE, LINC, TRF, TTL.
  All 6 are the same company. None goes the other way.
- The writer's names were RELIANCE, TCS, KDDL, FOCUS, ICONIKSPEV and ZEAL. The held-out names below avoid them, except FOCUS, which the claim names.

## Cases

| # | Case | Expectation | Command | Result | Pass |
|---|---|---|---|---|---|
| a | FOCUS announcements | 0 rows from BSE 543312 or any company other than Focus Lighting | `curl -H 'X-Vysted-Region: IN' :52341/disclosures/announcements?symbol=FOCUS` | 44 rows, all `exchange=NSE`. 44/44 headlines name "Focus Lighting and Fixtures". 43/44 attachments are `nsearchives.../FOCUS_*`. sources=[NSE]. note="BSE FOCUS is a different company; only the NSE feed is served". `/resolve?q=FOCUS` gives NSE Focus Lighting (bse_code null) and BSE Focus Business Solution (543312, INE0DXR01010). Pre-fix evidence cd001-ann.json had 34 NSE + 16 BSE rows. | PASS |
| b1 | KALYANI (held out) | NSE Kalyani Commercials only, no Kalyani Cast-Tech (544023) rows | `.../announcements?symbol=KALYANI` | 47 rows, all NSE. 0 "Cast-Tech" headlines. Different-company note present. | PASS |
| b2 | MAL (held out) | NSE Mangalam Alloys only, no Meyer Apparel (531613) rows | `.../announcements?symbol=MAL` | 47 rows, all NSE. 0 "Meyer" headlines. | PASS |
| b3 | SEL, RAJPUTANA (held out) | NSE company only | `.../announcements?symbol=SEL` / `RAJPUTANA` | 48 and 45 rows, all NSE. 0 rows from the BSE company. | PASS |
| c1 | INFY 500209 (held-out dual listing) | Both lanes merge, no NSE row lost | `...?symbol=INFY&limit=200` vs `&exchange=NSE` | merged: 189 rows (176 NSE + 13 BSE), sources=[NSE,BSE], note=null. NSE-only: 176 rows. **0 NSE rows missing** from the merge. The other 69 BSE rows are cross-feed pairs of NSE rows. | PASS |
| c2 | HDFCBANK, IZMO (`-$` held out) | Merge, and any loss is only the limit trim | same, limit=200 | HDFCBANK: 200 rows (179 NSE + 21 BSE). The 14 NSE rows not in the merge are all older than the merge's oldest row, so the 200-row trim removed them. IZMO: 200 rows (193 NSE + 7 BSE), 2 missing, both older than the trim. | PASS |
| d | BSE-only names SPICEJET 500285, ASMTEC 526433 | BSE rows are served | `...?symbol=SPICEJET` / `ASMTEC` | SPICEJET: 8 rows. ASMTEC: 28 rows. All BSE, sources=[BSE], covered, no note. Also: `symbol=543312` returns 19 BSE rows. | PASS |
| e1 | Sibling lanes, FOCUS | NSE only, other-company note, no BSE rows | `/disclosures/{results,shareholding,corporate-actions,deals}?symbol=FOCUS` | results 35 NSE, shareholding 21 NSE, corporate-actions 4 NSE, deals 11 NSE (NSE bulk/block/sast). Every lane has the note. 0 BSE rows. | PASS |
| e2 | Sibling lanes, KALYANI | Same as e1 | same, symbol=KALYANI | results 41 NSE, shareholding 20 NSE, corporate-actions 9 NSE, deals 0 (NSE lanes ok). Note on all four. | PASS |
| e3 | Sibling lanes, INFY | The dual listing still merges | same, symbol=INFY | results 70 (60 NSE, 6 NSE+BSE, 4 BSE), sources [NSE,BSE]. corporate-actions 20 (15 NSE, 5 NSE+BSE). deals 219 (24 NSE, 195 BSE). shareholding 21. No note. | PASS |
| f | Tests + lint | green | `PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_corporate_disclosures.py tests/test_symbol_resolver.py tests/test_disclosures_router.py tests/test_b7_exchange_disclosures.py tests/test_disclosure_tools.py tests/test_research_disclosures.py`, plus the writer's 4 tests via `-k`, plus ruff check and format --check on the 4 changed files | 184 passed. Writer's tests: 4 passed. ruff: all checks passed, 4 files already formatted. | PASS |

## Adjacent (not refutations)

1. **high: `FOCUS.BO` serves the other company's feed.** `/disclosures/announcements?symbol=FOCUS.BO` returns 44 rows, all Focus Lighting NSE rows,
   plus the note "BSE FOCUS is a different company". The `.BO` suffix pins the BSE identity (resolver: `FOCUS.BO` is Focus Business Solution, 543312).
   The cause is that `get_announcements` strips the suffix before calling `listing_lanes`. The other four lanes do the same, because they share `bare`.
   `symbol=543312` works. Before the fix, `.BO` returned the mixed feed; now it returns only the other company's rows.
   Evidence: `verify/a2-FOCUS-BO-ann.json`.
2. **low: `symbol=FOCUS&exchange=BSE` says the listing does not exist.** The note reads "FOCUS is not listed on BSE", but BSE does list a FOCUS (543312, a different company).
   The wording should say the BSE ticker belongs to another company. Evidence: `verify/a2-FOCUS_exchange_BSE-ann.json`.
