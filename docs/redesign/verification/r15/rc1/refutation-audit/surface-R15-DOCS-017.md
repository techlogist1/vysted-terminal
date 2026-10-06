# Refutation audit: R15-DOCS-017 (group surface) at HEAD 6741387b

Verdict: **partial**

## Certification
batch-10 VERDICTS.md:37: CURRENT_STATE.md:358-365 reads sp500 '506 symbols, static snapshot dated 2026-06-04 ... R15-LEAD-013 open' and describes criteria as 'nested AND/OR via CriterionGroup'. The fix commit is f10fb8ce, followed by f7f58adf ("CURRENT_STATE sp500 line matches the reverted pack").

## Gate verifier refutation (rc1-verifier:12)
docs017-018.txt: §3.3 still says 506 while sp500.json has 503, and 'nse-all', 'bse-all' and 'india-all' have 0 hits.

## Entry's own repro plus the verifier's grep, re-run at HEAD
```
HEAD §3.3 chars 4495
'AND-only' 0 []
'top 100' 0 []
'reserved' 1 ['reserved/unimplemented.']
'nested AND/OR' 1 ['`custom`. Criteria support **nested AND/OR** via `CriterionGroup`']
'routes every data request by asset class' 0 []
'by asset class' 0 []
'preference order' 1 ['installed providers in **preference order** until one succeeds — `asset_class`']
'506' 1 ['`sp500` (full S&P 500 — 506 symbols, a static snapshot dated 2026-06-04 that']
'503' 0 []
'R15-LEAD-013 open' 1 ['has drifted from current membership, R15-LEAD-013 open),']
'nse-all' 0 []
'bse-all' 0 []
'india-all' 0 []
'nifty50' 1 ['`nifty50` (50), `crypto-top50` (50, reseeded from the bundled snapshot on']
'nse_direct' 0 []
'jugaad' 0 []
'NSE' 0 []
'BSE' 0 []
'IN' 0 []
'no-key default for equities' 1 ['- **`yfinance_provider.py`** — no-key default for equities. Load-bearing']
whole-doc hits nse-all/bse-all/india-all/nse_direct: {'nse-all': 0, 'bse-all': 0, 'india-all': 0, 'nse_direct': 0, 'jugaad': 0}
```
History:
- `git show f407107:sidecar/services/screener_universes/sp500.json` has 506 symbols, so the doc line was correct when batch 10 certified it.
- `git log f407107..HEAD -- sp500.json` shows 34c2bbec "regenerate sp500 universe pack (R15-LEAD-013)", which landed in batch 11 (4097dac). It changed the pack to 503 symbols with snapshot_date 2026-09-24. The register now marks R15-LEAD-013 'fixed'. `git log f407107..HEAD -- docs/CURRENT_STATE.md` is empty, so batch 11 never touched the doc.
- sidecar/models/screener.py:28-39 ScreenerUniverseId includes 'nse-all', 'bse-all' and 'india-all' (R10, D40). The whole of CURRENT_STATE.md has 0 hits for any of them.

## Reasoning
The entry makes three claims:
1. "AND-only, OR reserved": **fixed**. §3.3 now says nested AND/OR via CriterionGroup.
2. "sp500 is only top 100": **fixed at certification**. At HEAD the sp500 clause (506, 2026-06-04, 'R15-LEAD-013 open') is wrong again. The cause is not a regression in the doc fix. Batch 11's R15-LEAD-013 regenerated the pack to 503 symbols dated 2026-09-24 and closed LEAD-013 without refreshing the doc line. The verifier's 506-vs-503 point therefore holds at HEAD, but it is new drift introduced by a later fix.
3. "nse-all/bse-all/india-all are undocumented": **never fixed**. The entry title and fix_shape both name them explicitly ("the real universe list and sizes (sp500 506, nse-all, bse-all, india-all)"). The batch-10 certification skipped this part.
Claims 1 and 2 held at certification and claim 3 was never done, so the correct verdict is 'partial'. The verifier's refutation is valid in substance. It was not judged on taste.

## Root cause
docs/CURRENT_STATE.md:358-365 (§3.3, screener bullet): the universe list omits nse-all (~2,675 NSE rows), bse-all (Active BSE scrips) and india-all (union, NSE preferred). The sp500 clause still quotes the pre-LEAD-013 pack (506 symbols, 2026-06-04, 'R15-LEAD-013 open'), but the pack now has 503 symbols with snapshot_date 2026-09-24.

## Acceptance test
sidecar/tests/test_sp500_universe.py (or a new sidecar/tests/test_current_state_doc.py): read docs/CURRENT_STATE.md §3.3. Assert that it contains f"{len(sp500.json['symbols'])} symbols" and sp500.json['snapshot_date'], that it contains no 'R15-LEAD-013 open', and that every id in typing.get_args(models.screener.ScreenerUniverseId) except 'custom' appears in backticks in the section (so nse-all, bse-all and india-all must appear).
