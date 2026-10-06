# triage-a: rc1-vshard-0:4 (also covers rc1-vshard-7:4): every 10-Q has zero sections

Auditor: Opus, group `triage-a`. Written 07:33 IST.

- HEAD: bed3b166. `git diff --name-only 01015033 HEAD | grep -v '^docs/' | grep -v '^CHANGELOG.md$'` printed nothing, so the code tree equals the post-fix-round merge 01015033. Unfiltered, the only non-`docs/` path is `CHANGELOG.md`, which is documentation, not code.
- Sidecar: my own on :52420 (`sleep 86400 | sidecar/.venv/bin/python3 main.py --host 127.0.0.1 --port 52420 --data-dir <scratch>/data`, with `VYSTED_SEC_EDGAR_MCP_PORT=52421` and `VYSTED_OPENBB_MCP_PORT=0`).
- sec-edgar-mcp: my own, spawned from the shipped binary on :52421 (`sleep 86400 | src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin --port 52421`).
- Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-a/`.

## Verdict

**partial on R15-DATA-038**, not on the shard's tie R15-DATA-007 (and not on R15-LEAD-010, the tie of the duplicate finding rc1-vshard-7:4).

- Severity: **high**, raised from the shard's medium.
- Certification failures: 1 (baseline 0, plus 1 for this verdict).

## What reproduces at HEAD

```
curl -s -H "X-Vysted-Region: US" "http://127.0.0.1:52420/sec/filings/0000320193-23-000077?identifier=AAPL&form_type=10-Q"
-> form 10-Q date 2023-08-04 sections 0 total_chars 0          (item1-aapl-10q-detail.json)

curl ... "/sec/filings/0000320193-26-000018?identifier=AAPL&form_type=8-K"
-> form 8-K sections 0 total_chars 0                            (item1-aapl-8k-detail.json)

control: curl ... "/sec/filings/0000320193-25-000079?identifier=AAPL&form_type=10-K"
-> form 10-K sections [('business', 10000), ('risk_factors', 10000)] total_chars 20000
```

I then ran the raw upstream payload and the agent tool in-process (`raw_sections.py`, with `VYSTED_SEC_EDGAR_MCP_PORT=52421`):

```
RAW get_filing_sections 10-Q: {"success": true, "form_type": "10-Q", "sections": {"has_financials": true}, "available_sections": ["has_financials"]}
TOOL sec_filing_content ok= True sections= 0 total_chars= 0 keys= ['filing', 'ok']
```

The upstream source is sec-edgar-mcp 1.0.8, `tools/filings.py:173-216`, extracted from the shipped binary. It fills `business`, `risk_factors` and `mda` only when `hasattr(filing_obj, ...)`. A 10-Q object has none of those attributes, so it returns only `has_financials`. Any form other than 10-K or 10-Q returns `{}`. This is deterministic, not flaky upstream behaviour.

## Root cause at HEAD

- `sidecar/services/sec_filings_provider.py:368-372` keeps only the dict values that are text. For a 10-Q the only key is `has_financials: true`, so zero rows come out.
- The docstring at `:363-364` says: "An empty `sections` is a real empty (the upstream sections only 10-K/10-Q)". Its premise is false, because the upstream does not section a 10-Q.
- `:653-661`: `get_filing` wraps that zero-section result in a `FilingDetail` with `total_chars` 0 and caches it for 24 h (`_FILING_CONTENT_TTL = 86400`).

What the user sees:

- `src/modules/sec/FilingViewer.tsx:193` renders "No section selected." with no reason given.
- The agent's `sec_filing_content` (`sidecar/services/agent_tools/sec_tools.py:101-113`) returns `ok: true` with an empty filing and no note.

## Why this is partial on R15-DATA-038, not new and not duplicate

**R15-DATA-038** (fixed, high, class `silent-parse-drop`).

- Title: "SEC Filings panel's filing viewer ... always empty ... and the empty result is cached 24h".
- root_cause: "a zero-row parse of a success payload is cached as a real empty".
- fix_shape: "treat a success payload that parses to zero rows as a logged parse error, not a cacheable empty".
- The entry's own repro, the AAPL 10-K `…-25-000079`, now returns Business and Risk Factors, so the stated repro holds.
- The 10-Q success payload is a stated part of that same class, and it still parses to zero rows and is cached 24 h as a real empty. That clause of the fix_shape is not honoured.
- The fix commit 05ef16a0 exempted empty section dicts explicitly, on the false premise quoted above.
- The only batch-4 certification case was a 10-K (ORCL), so the gap was never exercised.

**R15-DATA-007** (the shard's tie; class `fabricated-metadata`) is not the defect.

- At HEAD the 10-Q metadata is real: form 10-Q, date 2023-08-04, company "Apple Inc.".
- The sectioner receives `form_type: 10-Q`.

**R15-LEAD-010** (`windowed-lookup-ignores-filter`) is not it either. The lookup succeeded.

**R15-CODE-DATA-013** (open, low) is not a duplicate, although its note folds in the batch-12 aside "`/sections` returns [] for 10-Q".

- The fold claims that deleting the dead `/sections` route resolves the 10-Q case. It does not.
- The empty result comes from `get_filing` itself, which serves the viewer's main route `GET /sec/filings/{acc}` and the agent's `sec_filing_content`. Both returned 0 sections above.
- So CODE-DATA-013 does not cover this defect, and its fold note is wrong.

## Severity

I raised it to high: a core flow is broken for a whole class of inputs.

- Opening any filing other than a 10-K shows a blank viewer with no stated reason. That includes every 10-Q (three per issuer per year) and every 8-K.
- The agent is told `ok: true` with empty content.
- The only workaround is the external EDGAR link.

## Certification failures

R15-DATA-038 baseline is 0:

- no "certification failures so far" clause in its register note;
- no appearance in any `stage-c/batch-*/VERDICTS.json` `not_certified` list;
- no partial or regression verdict for it in `REFUTATION_AUDIT.json` or `round-*/REFUTATION_AUDIT.json`.

Adding this partial gives **1**.

## Fix shape

In `get_filing`, when `_sections_from_payload` yields no text sections, call the upstream `get_filing_content` tool, which is already served by the same sec-edgar-mcp. It returns the filing text, capped at 50,000 characters.

- Wrap that text in the existing single "Filing Content" section, the bare-text branch at `:381-391`.
- If that also yields no text, raise `ProviderError` with a stated reason, e.g. "sec-edgar-mcp returned no text for this 10-Q". The error must not be cached. The panel then shows its error state with the reason, and `sec_filing_content` returns `ok: false`.
- Correct the docstring at `:363-364`.

## Acceptance test

In `sidecar/tests/test_sec_filings_provider.py`, set up the recorder like this:

- `get_filing_sections` for a 10-Q returns `{"success": true, "form_type": "10-Q", "sections": {"has_financials": true}}`.
- `get_filing_content` returns `{"success": true, "content": "PART I ... Item 2. MD&A ..."}`.

Assertions:

1. `(await get_filing(acc, cik_or_symbol='AAPL', form_type='10-Q')).sections` is non-empty and `total_chars > 0`.
2. A second case, where `get_filing_content` also returns empty text, raises `ProviderError` and leaves `data_cache` without the `sec:filing:<acc>` key.
3. In `sidecar/tests/test_sec_tools.py`, the same 10-Q gives `(await _sec_filing_content({...}))['ok'] is True` with a section whose text is non-empty.

Live re-proof:

```
curl -s -H "X-Vysted-Region: US" "http://127.0.0.1:<port>/sec/filings/0000320193-23-000077?identifier=AAPL&form_type=10-Q" | jq '.total_chars'
```

This must print a value greater than 0, and the same must hold for the 8-K `0000320193-26-000018`.
