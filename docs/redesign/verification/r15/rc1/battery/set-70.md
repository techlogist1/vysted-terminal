# batch-18/W2-nse-emerge-sm-identity (rc1-battery-7)

Candidate `4c6dfe8c`. Own sidecar on `:52347`. 1 certified entry re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-034 | `GET /fundamentals/{SHERA,RICHA,ONYX,USHAFIN}` + `GET /quotes?symbols={...}` (4 fresh NSE Emerge/SME symbols, region IN) + `grep sidecar/services/correctness_gate.py` for the `-SM` infix strip | all four `/fundamentals/*` return **404** `"not_found"` (missing data upstream — matches cert's noted Yahoo rate-limit caveat), never a `CorrectnessError … symbol mismatch`; all four `/quotes/*` serve live NSE prices (177.9 / 78.0 / 36.0 / 54.0); `_SUFFIX_RE = re.compile(r"(?:-SM)?[.\-](NS\|BO\|BSE)$", ...)` present, comment cites R15-LEAD-034 | holds |

Raw output: `battery/raw/set-70/*`.
