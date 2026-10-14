# set-70 — batch-18/W2-nse-emerge-sm-identity-in-the-correctness-gate (rc1-battery-12)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Live quotes via sidecar :52352 + in-process
python call into sidecar/services/correctness_gate.symbols_match (candidate's own .venv), using
fresh NSE Emerge symbols the original writer/verifier did not use.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-034 | curl /quotes/{SHERA,RICHA}; curl /fundamentals/SHERA; in-process `symbols_match(bare, "<BARE>-SM.NS")` for SHERA/RICHA/ONYX/USHAFIN + a negative pair + the pre-existing SMR.NS non-SM case | quotes 200 (SHERA 177.9, RICHA 78.0 — matches batch-18's certified values); fundamentals 404 not_found (data-availability, not a gate mismatch — matches batch-18's Yahoo-rate-limit note); symbols_match True for all 4 -SM pairs, False for a mismatched pair, True (unaffected) for SMR/SMR.NS | holds |

COVERAGE: 1/1 ids raw; no raw: none.
