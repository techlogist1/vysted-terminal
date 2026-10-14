# batch-30/WA-R15-DATA-030 (rc1-battery-18, candidate 9bc600ec)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-050 | `pytest tests/test_research_relevance.py -v -k "written_ticker or short_us_ticker"` (committed pinned test, incl. literal repro); in-process `row_relevant` on fresh cases (CF Industries, MP Materials — not written against the fix) | 10/10 pass: "GE beats estimates on jet engine demand" for GE stays True, "BP beats estimates on refining margins" for BP True, "ALL EYES ON THE FED..." for ALL stays False, the IT/ON/AI-class controls all hold; fresh cases CF ("CF beats on nitrogen prices") and MP ("MP beats estimates on rare earth output") both True | holds |

COVERAGE: 1/1 ids raw; no raw: none.
