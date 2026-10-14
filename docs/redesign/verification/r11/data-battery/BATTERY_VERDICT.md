# R11 twelve-stock validation battery — verdict

**Names (all fresh — never in any prior battery):** MARUTI, DRREDDY, HAVELLS (large) · VOLTAS, MPHASIS, CROMPTON (mid) · PRAJIND, CERA, SHAILY (small) · WENDT (micro) · TANFACIND, ACGL (BSE-only). Reference packs built by 12 independent web-research agents (screener.in / exchange filings / moneycontrol / trendlyne / company IR, ≥2 sources per headline figure, trap annotations for bonus/split/demerger/base effects).

**Result: entity identity 12/12 · figures 95 ok / 19 watch / 6 MISMATCH (of 120) · growth_basis="mrq_yoy" on every response (D55 flowing end-to-end).**

## Mismatch disposition (every one root-caused; adversarially verified where the app was accused)

| Figure | App | Ref | Verdict |
|---|---|---|---|
| WENDT eps/pe/earnings_growth | 72.72 / 105.4 / -60.5% | 90.4 / 84.9 / -40.2% | **APP CORRECT** on its stated consolidated basis — verifier summed consolidated quarterly EPS to 72.75 and matched -60.51% consolidated Q4 PAT YoY exactly; the reference numbers were standalone AND partly a stale screener.in ratio-cache (its own panel showed P/E 84.9 beside numbers implying 67). |
| CROMPTON roe | -6.3% | ~10.5% | **APP CORRECT** — FY26 reported PAT is negative (₹716 Cr Butterfly impairment); verifier computed reported-basis ROE -6.34%. The 10.5% is a stale/normalized aggregator panel (shown beside a negative EPS on the same page). |
| WENDT dividend_per_share | 20 | 30 (FY) / 40 (TTM-paid) | **Yahoo dividendRate quirk** (surfaces the last event, not a trailing sum). **Caught live by D56**: the deep brief's Conflict Note reads "provider's standard dividend rate lists ₹20.00 … omits special dividends; the ₹40.00 trailing paid figure represents the complete distributed amount" — the app now states the truth beside the quirk. |
| PRAJIND dividend_per_share | 6.0 | 3.6 (declared FY26, unpaid) | **Basis artifact** — app matches the trailing-PAID basis (FY25 ₹6 paid); the FY26 ₹3.60 final is AGM-pending. Same class reconciled for SHAILY (2 paid vs 3 declared-unpaid) and MARUTI (135 paid vs 140 declared-unpaid). |
| PRAJIND revenue_growth | -1.8% | +2% (MRQ) | **Provider quarter-lag** — Yahoo's MRQ figure tracks an older quarter (its -1.8 ≈ the annual -1.9); the field's basis label is honest; the underlying lag is upstream. Data-note. |

**Zero app fabrications found.** The two watch-heavy names (WENDT, CROMPTON) are cases where the app's number was MORE current than the aggregator's own ratio panel.

Artifacts: `reference-pack.json` (12 packs + traps + sources), `diff-results-round1/2.json`, `diff_battery.py` (harness), adversarial verification in the run report.
