# Refutation audit: R15-LEAD-010 (group research)

- **Verdict:** partial
- **HEAD:** `6741387b` at start, then `91dac548` (docs-only). None of these files changed: `sec_filings_provider.py`, `routers/sec_filings.py`, `agent_tools/sec_tools.py`, `src/store/sec.ts`.

**Certification history.** Batch-5 (`VERDICTS.md:232`) found this entry a REGRESSION: the 1,000-row unhinted window. Fix `7ae5117` (forward the form hint, `_FILING_WINDOWS=(40,100)`) landed before the merge but was never re-verified by a stage-c verifier. The rc1 verifier's statement "certified in no stage-c VERDICTS" is correct.

**Refuted by:** `rc1-verifier:11` (`lead010-cold.txt`). Four claims:

- The MSFT 10-Q `/sections` returns 404 with and without `form_type`.
- The no-hint main route returns 404 for `0001564590-22-035087`.
- With the hint, the main route returns 200.
- `get_filing_sections` and the `/sections` router drop `form_type`.

## Rig

- Own sidecar from `sidecar/.venv` on `127.0.0.1:52365`, with the scratch data dir `$SCRATCH/refaudit-research/data`. The cache was cold.
- `VYSTED_SEC_EDGAR_MCP_PORT=52154`: the already-running shared sec-edgar-mcp, used read-only.
- stdin was held open (`sleep 86400 |`) because `main.py` exits on stdin EOF.

## Entry's own repro, then the verifier's refutation

Command: `$SCRATCH/refaudit-research/lead010.sh`.

```
2026-09-25T04:33:24Z
91dac548
## ENTRY REPRO (panel path: list 10-K, open with the listed row's form hint, as src/store/sec.ts:193-199 does)
10-K list: ['0000320193-25-000079', '0000320193-24-000123', '0000320193-23-000106', '0000320193-22-000108', '0000320193-21-000105', '0000320193-20-000096']
GET /sec/filings/0000320193-25-000079?identifier=AAPL&form_type=10-K
-> 200 1.259802s
{"filing":{"accession":"0000320193-25-000079","cik":"0000320193","company_name":"Apple Inc.","symbol":null,"form_type":"10-K","filed_date":"2025-10-31","period_of_report":"2025-09-27","edgar_url":"https://www.sec.gov/Arc
GET /sec/filings/0000320193-24-000123?identifier=AAPL&form_type=10-K
-> 200 1.394265s
{"filing":{"accession":"0000320193-24-000123","cik":"0000320193","company_name":"Apple Inc.","symbol":null,"form_type":"10-K","filed_date":"2024-11-01","period_of_report":"2024-09-28","edgar_url":"https://www.sec.gov/Arc
## entry accessions WITHOUT the hint (unhinted path, cold for 24-000123 via a fresh cache key? no: cache is per accession -> use a different accession)
GET /sec/filings/0000320193-22-000108?identifier=AAPL
-> 404 0.473037s
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
GET /sec/filings/0000320193-22-000108/sections?identifier=AAPL
-> 404 0.407554s
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
## VERIFIER REFUTATION (MSFT 10-Q, cold)
10-Q list: [('0001193125-26-191507', '2026-04-29'), ('0001193125-26-027207', '2026-01-28'), ('0001193125-25-256321', '2025-10-29'), ('0000950170-25-061046', '2025-04-30'), ('0000950170-25-010491', '2025-01-29'), ('0000950170-24-118967', '2024-10-30'), ('0000950170-24-048288', '2024-04-25'), ('0000950170-24-008814', '2024-01-30'), ('0000950170-23-054855', '2023-10-24'), ('0000950170-23-014423', '2023-04-25'), ('0001564590-23-000733', '2023-01-24'), ('0001564590-22-035087', '2022-10-25'), ('0001564590-22-015675', '2022-04-26'), ('0001564590-22-002324', '2022-01-25'), ('0001564590-21-051992', '2021-10-26'), ('0001564590-21-020891', '2021-04-27'), ('0001564590-21-002316', '2021-01-26'), ('0001564590-20-047996', '2020-10-27'), ('0001564590-20-019706', '2020-04-29'), ('0001564590-20-002450', '2020-01-29'), ('0001564590-19-037549', '2019-10-23'), ('0001564590-19-012709', '2019-04-24'), ('0001564590-19-001392', '2019-01-30'), ('0001564590-18-024893', '2018-10-24'), ('0001564590-18-009307', '2018-04-26'), ('0001564590-18-001129', '2018-01-31'), ('0001564590-17-020171', '2017-10-26'), ('0001564590-17-007547', '2017-04-27'), ('0001564590-17-000654', '2017-01-26'), ('0001193125-16-742796', '2016-10-20'), ('0001193125-16-550254', '2016-04-21'), ('0001193125-16-441821', '2016-01-28'), ('0001193125-15-350718', '2015-10-22'), ('0001193125-15-144151', '2015-04-23'), ('0001193125-15-020351', '2015-01-26'), ('0001193125-14-380252', '2014-10-23'), ('0001193125-14-157088', '2014-04-24'), ('0001193125-14-018634', '2014-01-23'), ('0001193125-13-409855', '2013-10-24'), ('0001193125-13-160748', '2013-04-18')]
GET /sec/filings/0000950170-23-014423/sections?identifier=MSFT
-> 404 0.929785s
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
GET /sec/filings/0001564590-22-035087?identifier=MSFT
-> 404 0.758424s
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
GET /sec/filings/0000950170-24-048288/sections?identifier=MSFT&form_type=10-Q
-> 404 0.591533s
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
GET /sec/filings/0000950170-24-048288?identifier=MSFT&form_type=10-Q
-> 200 3.425871s
{"filing":{"accession":"0000950170-24-048288","cik":"0000789019","company_name":"MICROSOFT CORP","symbol":null,"form_type":"10-Q","filed_date":"2024-04-25","period_of_report":"2024-03-31","edgar_url":"https://www.sec.gov
GET /sec/filings/0000950170-24-048288/sections?identifier=MSFT
-> 200 0.002082s
{"sections":[]}
GET /sec/filings/0001564590-22-035087?identifier=MSFT&form_type=10-Q
-> 200 2.801434s
{"filing":{"accession":"0001564590-22-035087","cik":"0000789019","company_name":"MICROSOFT CORP","symbol":null,"form_type":"10-Q","filed_date":"2022-10-25","period_of_report":"2022-09-30","edgar_url":"https://www.sec.gov
DONE
```

Unfiltered window reach (MSFT):

```
unfiltered limit 40 rows 40 ('2026-09-01', '4')
unfiltered limit 100 rows 100 ('2026-03-24', '11-K')
```

Agent tool path, in-process `services.agent_tools.sec_tools._sec_filing_content` against the same MCP (`tool010.py`):

```
{'accession': '0001564590-21-051992', 'identifier': 'MSFT'} -> ok False provider error: filing metadata unavailable for '0001564590-21-051992'
{'accession': '0001564590-21-051992', 'identifier': 'MSFT', 'form_type': '10-Q'} -> ok True sections=0
{'accession': '0000320193-21-000105', 'identifier': 'AAPL'} -> ok False provider error: filing metadata unavailable for '0000320193-21-000105'
{'accession': '0000320193-21-000105', 'identifier': 'AAPL', 'form_type': '10-K'} -> ok True sections=2
```

Live llama3.1:8b tool-choice probe (`ollama010.py`, under the lock). The input was the `sec_filings_list(form_type=10-K)` result plus the request "open Apple's Oct-2021 10-K". The model made no valid `sec_filing_content` call in 3 samples, so hint-passing behaviour is undetermined at llama:

```
tools sent: ['sec_filings_list', 'sec_filing_content']
sample 0 "Based on the SEC filings, Item 1 of Apple's 10-K filed in October 2021 is not directly available from the output. However, I can suggest a tool to access and extract specific information from the fili"
sample 1 "I can see that Apple's 10-K filing for October 2021 has an accession number of 0000320193-21-000105. I will now open this filing and provide information about Item 1.\n\nOpening the filing...\n\nThe text "
sample 2 "Based on the output, I will call another tool to get the 10-K filed in October 2021.\n\n{\"name\": \"get_section_from_10k\", \"parameters\": {\"cik\":\"0000320193\",\"accession\":\"0000320193-21-000105\"}}"
```

## Reasoning

**The entry's own repro holds at HEAD** on the path the entry names, the filing viewer panel. AAPL 10-Ks `-25-000079` and `-24-000123`, listed via `form_type=10-K`, open with 200 in about 1.3 s cold. The panel sends the listed row's form (`src/store/sec.ts:193-199`) and the route forwards it (`routers/sec_filings.py:107-121`). This is the first live confirmation of `7ae5117`.

**The verifier's refutation reproduces exactly at HEAD:**

- MSFT `-23-014423` and `-24-048288` `/sections` return 404, with or without `form_type`, because the route has no `form_type` parameter.
- `-22-035087` without the hint returns 404. With `form_type=10-Q` it returns 200.

**Is it the entry's defect?** In part, yes. The entry's defect is "a filing visible in a form-filtered list is unreachable by accession, because the metadata lookup re-lists an unfiltered recent window". At HEAD that is still true for every caller that does not send the hint. The unfiltered 100-row window for MSFT reaches back only to 2026-03-24 (a heavy Form 4 / 11-K filer), which is exactly the entry's mechanism. The affected product caller is not just the dead route:

- **Agent tool.** `sec_filing_content` for AAPL's 2021 10-K `0000320193-21-000105`, which `sec_filings_list(form_type=10-K)` lists, returns `ok:false "filing metadata unavailable"` without `form_type`. With it, the call returns `ok:true`. `catalog.py:741-746` declares `form_type` optional and describes it as something that only "speeds up the lookup". A model is therefore told it may omit the parameter, while in fact omitting it makes every filing past row 100 unresolvable. That contradicts the ponytail ceiling note at `sec_filings_provider.py:576-579` ("the form hint is how deeper filings resolve"). Copilot and researcher reach filings through this tool (batch-5 `VERDICTS.md`).
- **`/sections` route.** `routers/sec_filings.py:124-131` and `sec_filings_provider.py:650-662` drop the hint entirely. The route has no frontend caller (only tests), and R15-CODE-DATA-013, which is open, already tracks it as a dead pass-through route. Fixing or deleting it under that entry is fine, but it is the same windowed-lookup defect.
- **Raw `GET /sec/filings/{acc}` without a hint.** This is a documented ceiling, and the panel only omits the hint when the row is not in `filingsByIdentifier`.

**Verdict: partial.** The panel repro is fixed, and the verifier's "regression" framing overstates it: nothing that worked before broke. But the same defect is still reachable through the agent tool and the sibling route.

## Adjacent observation

This is not the verifier's finding, so register it separately. Every 10-Q opens as a 200 with **0 sections** and `total_chars 0` (MSFT `-24-048288` and `-22-035087`, the tool path too). Raw sec-edgar-mcp `get_filing_sections` for a 10-Q returns `{"sections":{"has_financials":true}}` with no text (`sec10q.out`). `_sections_from_payload` treats this as "a real empty", and `FilingViewer.tsx:154-196` renders an empty nav plus "No section selected." with no honest "this form is not sectioned upstream" state. The result is a silent false-empty on the most common periodic filing.

## Root cause

- `sidecar/services/agent_tools/catalog.py:741-746`: the tool contract makes the form hint optional and describes it as a speed-up only.
- `sidecar/services/sec_filings_provider.py:579` and `:618-632`: the unhinted lookup only scans the unfiltered 40/100 window.
- `sidecar/services/sec_filings_provider.py:650-662` and `sidecar/routers/sec_filings.py:124-131`: `get_filing_sections` and its route do not accept or forward `form_type`.

## Acceptance test

**Provider fallback.** In `sidecar/tests/test_sec_filings_provider.py`, add a recorder in which the unfiltered `get_recent_filings` windows (limit 40 and 100, 100 rows returned) never contain `0000320193-21-000105`, while the `form_type=10-K` list does. Then:

- `await get_filing('0000320193-21-000105', cik_or_symbol='AAPL')` with no hint must return `filing.form_type == '10-K'`, not raise `ProviderError(kind='not_found')`.
- `get_filing_sections(acc, cik_or_symbol='AAPL', form_type='10-K')` must also resolve. The fallback could be, for example, a form-filtered retry over the sectionable forms, or accession resolution through the EDGAR index.

**Tool.** In `sidecar/tests/test_sec_tools.py`, assert `(await _sec_filing_content({'accession': acc, 'identifier': 'AAPL'}))['ok'] is True` for the same recorder.

**Router.** Add a test that `GET /sec/filings/{acc}/sections?identifier=AAPL&form_type=10-K` forwards `form_type`, unless R15-CODE-DATA-013 deletes the route.
