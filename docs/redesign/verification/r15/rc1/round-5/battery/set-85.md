# batch-30/WB-R15-LEAD-051 (shard rc1-battery-19)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar booted from candidate source
on :52359, data dir `rc1-round-5-data-rc1-battery-19` (copy of the round-5 keyless seed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-051 | In-process python (candidate's `sidecar/.venv/bin/python3`) constructing `services.exchange_financials.FiledPeriods` with the exact fixture shapes from `stage-c/batch-30/VERDICTS.md`'s certification table: (1) IPO with only Jan-Mar26 + Apr-Jun26 filed (the entry's literal repro), (2) a single filed quarter Jul-Sep26 (fresh case), (3) a former-SME migrant with a held-back half plus two trailing quarters, (4) a pure half-yearly control with no quarter ever filed. | `.cadence()` returns: (1) `quarterly-gap` (was `half-yearly` at base — the regression this entry fixed), (2) `quarterly-gap`, (3) `quarterly` (trailing chain complete), (4) `half-yearly` (control unchanged). All 4 match the batch-30 certified base→head table exactly. Source: `exchange_financials.py:114-128` `cadence()` now reads `any(p.months == 3 for p in self.periods)` — any filed quarter of any age makes the filer quarterly — instead of the R15-LEAD-004 half-yearly-period-exists rule the entry was filed against. | holds |

Raw: `battery/raw/set-85/R15-LEAD-051.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
