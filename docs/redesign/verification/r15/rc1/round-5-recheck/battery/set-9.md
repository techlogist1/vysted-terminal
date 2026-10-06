# set-9 — batch-3/W5-india-data-witnesses (rc1-battery-20, round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52360`, data dir
`rc1-round-5-recheck-data-rc1-battery-20` (copied from the round-5-recheck keyless seed).
Re-ran each id's ORIGINAL repro (round-5 `battery/set-9.md` "Per-entry evidence"), not
judged from the diff.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-005 | `GET /fundamentals/{VERTEX,JNPR,JUMBO,ONC}` | all four still `field_meta.book_value` (or `.shares_outstanding`) `status: "flagged"` with a stated share-basis-disagreement reason; VERTEX 50% gap, JNPR 14.1%, JUMBO 4.6%, ONC 8%/7.7% — matches round-5 cert exactly | holds |
| R15-DATA-019 | `GET /disclosures/announcements?symbol={JUMBO,TTC,AMAL}&limit=25` | JUMBO count 18, TTC 16, AMAL 21; `windows.BSE.window_start` still `2026-03-31` for JUMBO/TTC — matches round-5 cert | holds |
| R15-DATA-021 | `GET /disclosures/shareholding?symbol=SIL` | quarters 2022-09-30..2026-06-30 carry `split_basis:"filed"` with `split_as_of == quarter_end`; quarters 2021-09-30..2022-06-30 carry `split_basis: null`, `fii_percent/dii_percent: null` — matches round-5 cert | holds |
| R15-DATA-022 | `GET /disclosures/shareholding?symbol=SMR` | count 1, `quarter_end: "2026-06-04"`; promoter/fii/dii/public 65.74/9.88/0.84/23.55 — matches round-5 cert | holds |
| R15-LEAD-002 | 3x `GET /fundamentals/TCS` (`X-Vysted-Region: IN`) back-to-back on the same sidecar | call 1: 17.08s (cold ownership witness fetch); calls 2-3: 2.27s / 1.51s (order-of-magnitude faster, same shape as round-5's 15.74s→1.13s/1.07s); source confirms `correctness_gate.py:860` `_WITNESS_TTL_SECONDS = fundamentals_store.TTL_V7_SECONDS` still routes the ownership fetch through `_cached_witness` | holds |
| R15-RESEARCH-011 | source read `ownership_check.py::_fetch_latest` + `research/semantics.py::_ownership_leg` + pinned test | `_fetch_latest` (ownership_check.py:123-124) still stamps `institutions_source=latest.split_source or source` / `institutions_as_of=(latest.split_as_of or latest.quarter_end)`; `semantics._ownership_leg` (semantics.py:595/597) still reads `institutions_source`/`institutions_as_of`; `test_ownership_check.py::test_merged_bse_split_keeps_its_own_provenance_in_the_brief` present | holds (ci_pinned: `sidecar/tests/test_ownership_check.py::test_merged_bse_split_keeps_its_own_provenance_in_the_brief`) |
| R15-RESEARCH-013 | source read `research/fast.py::_filings_leg` + pinned test | `fast.py:486` still `value["provider"] = "+".join(str(s).lower() for s in result.get("sources") or [])`; `test_research_fast.py::test_fast_filings_leg_provider_names_only_the_serving_exchanges` present | holds (ci_pinned: `sidecar/tests/test_research_fast.py::test_fast_filings_leg_provider_names_only_the_serving_exchanges`) |

Raw: `battery/raw/set-9/R15-{DATA-005-VERTEX,DATA-005-JNPR,DATA-005-JUMBO,DATA-005-ONC,DATA-019-JUMBO,DATA-019-TTC,DATA-019-AMAL,DATA-021-SIL,DATA-022-SMR,LEAD-002-timing,RESEARCH-011,RESEARCH-013}.txt`

COVERAGE: 7/7 ids raw; no raw: none.
