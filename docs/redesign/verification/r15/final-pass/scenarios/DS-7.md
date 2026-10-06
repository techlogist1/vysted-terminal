# DS-7 — ownership / promoter-holding reconciliation on small caps (investor lens)

Probe: scratchpad ds7.py against my clean binary stack (:52810), shareholding + correctness-gate ownership reconcile for
DAL, AMAL, SAFE, ICON, CHTR, CSL, SMR, TTC, SUNRAJDI. Raw: raw/investor/ds7.json, raw/investor/ds7-sh.json.

## Observed
- DAL, AMAL, SAFE, ICON: provider insider % within 3pp of the BSE/NSE shareholding filing -> status ok. Correct.
- CHTR, CSL, SMR, TTC, SUNRAJDI: real divergence beyond 3pp -> flagged, witness cites the filing. Correct.
- Zero-mismatch flags (institutions holding): AMAL Yahoo 0.00 vs filing 0.03, and ICON / SUNRAJDI likewise, are flagged by the zero-mismatch rule but the
  witness text says "beyond 3pp", which is false for a 0.03pp gap (correctness_gate.py reconcile_ownership ~:478-525). Wrong reason text,
  right instinct -> investor:8 (low).
- Source-label check (RESEARCH-011 class): the SUNRAJDI deep brief Conflict Note correctly attributes "BSE shareholding filing ... 35.83%
  as of 2026-06-30". KPIT FAST had no ownership leg, so nothing to label.

VERDICT DS-7: finding investor:8
