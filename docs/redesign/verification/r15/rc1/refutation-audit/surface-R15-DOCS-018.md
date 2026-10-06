# Refutation audit: R15-DOCS-018 (group surface) at HEAD 6741387b

Verdict: **partial**

## Certification
batch-10 VERDICTS.md:38: CURRENT_STATE.md:92-95 says provider_registry 'resolves by standard model key + preference order (not the asset-class chain)'. The fix commit is f10fb8ce.

## Gate verifier refutation (rc1-verifier:13)
docs017-018.txt: §3.3 has 0 hits for nse_direct, NSE, BSE and jugaad, and still says 'yfinance_provider.py - no-key default for equities'. The fix_shape asked for the IN chain and ranks.

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
sp500.json symbols: 503
{'fundamentals': 'yfinance', 'ohlcv': 'ccxt (nse_direct, nse, bse, yfinance fallback)', 'quote': 'ccxt (nse_direct, yfinance fallback; nse, bse failing)'}
```
provider_registry.py at HEAD: nse_direct rank 15, region IN (:166-170); nse rank 20, IN (:183-187); bse rank 25, IN (:202-206); yfinance rank 50 (:218-219). The /health output from the scratch sidecar on :52375 (last line above) reports the IN chain.

## Reasoning
The entry's literal false sentence ("routes every data request by asset class", equity -> yfinance) is gone. §3.3:320-330 now describes model-key plus preference-order resolution with asset_class as a hint, so that half is **fixed**.
The entry's title conclusion ("so the baseline doc understates India data coverage") and its fix_shape ("listing the IN chain and ranks") were never addressed. CURRENT_STATE.md has 0 hits anywhere for nse_direct or jugaad, and §3.3 has 0 for NSE or BSE. The only equity provider bullet is 'yfinance_provider.py — no-key default for equities', which is wrong for IN-region requests: nse_direct, nse and bse rank ahead of yfinance there.
The verifier is right about the missing IN chain. That is a stated part of this entry, not taste. Batch 10 certified only the asset-class sentence, so the verdict is 'partial'.

## Root cause
docs/CURRENT_STATE.md §3.3 (lines ~318-335): the provider bullets list yfinance as the equity default and omit the IN-scoped chain nse_direct (15) > nse/jugaad (20) > bse (25) > yfinance (50) from sidecar/services/provider_registry.py:161-219.

## Acceptance test
sidecar/tests/test_provider_registry_region.py (or a new test_current_state_doc.py): for every ProviderDeclaration in provider_registry whose region set contains 'IN', assert that its id appears in docs/CURRENT_STATE.md §3.3. Also assert that the yfinance bullet does not claim to be the unconditional equity default: the section must contain the phrase 'region' or 'IN' in the yfinance bullet.
