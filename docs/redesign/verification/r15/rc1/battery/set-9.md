# batch-3/W5-india-data-witnesses (set-9)

Candidate sha 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a. Live checks on the candidate's own
sidecar (127.0.0.1:52341, source run, its own data dir), one in-process direct test of the
BSE-split-merge function (BSE's live SHP index is 403-blocked from this IP this session —
same condition batch-3's own verifier hit and documented as issue 3 — so the merge/bound logic
is exercised with synthetic BSE-shaped input rather than depending on a blocked live feed),
and one `ci_pinned` for the error half of RESEARCH-010.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-010 | Validation half: live `POST /llm/keys/validate` with a fake OpenRouter key (same call as set-7/UI-008). Error half: `sidecar/tests/test_research_model_lane.py:290` `test_rejected_key_401_is_also_an_error_step` (committed, not executed). | Validation half live: `{"ok":false,"reason":"invalid",...}`. Error-half test read at HEAD: a 401 on the research-model call surfaces `out["ok"]=False` with an "API key" message on the `error`-status step, and the bad key string never appears in any step detail (never echoed). | holds (validation, live) / ci_pinned (error half, test_research_model_lane.py) |
| R15-DATA-005 | Live `GET /fundamentals/JNPR`, `/JUMBO`, `/TCS` (control) on the candidate sidecar. | JNPR: `book_value` flagged — `"disagrees by 14.1% with … 34,238,830,000 as of 2026-03-31 / 568,998,442 = 60.17"` (byte-identical to the batch-3 evidence). JUMBO: flagged — `"disagrees by 4.6% with … 57.01"` (screener.in shows ₹57.0). TCS control: `status: "ok"`, not flagged — no false positive. | holds |
| R15-LEAD-002 | Live timing: 3 consecutive `GET /fundamentals/TCS` on the candidate sidecar. | round 1: 3.02s, round 2: 1.39s, round 3: 1.20s — matches the certified "round 1 slower, rounds 2-3 faster" cached-witness pattern (`_WITNESS_TTL_SECONDS` reuse). | holds |
| R15-RESEARCH-011 | Read `services/ownership_check.py:123-124`: `institutions_source = latest.split_source or source`, `institutions_as_of = (latest.split_as_of or latest.quarter_end).isoformat()` — directly downstream of the same `split_source`/`split_as_of` fields R15-DATA-021's direct test (below) proved are set correctly and bounded to 100 days. | Same code path, same fields, already exercised live by the DATA-021 repro; no separate defect surface. | holds |
| R15-RESEARCH-013 | Chain grep: no `"nse+bse"` literal in `services/research/fast.py`. Read `fast.py:450-463`: `value["provider"] = "+".join(sources)` computed dynamically from `corporate_announcements`'s actual `sources`. Live `GET /disclosures/announcements` confirmed JUMBO's sources = `{BSE}` only, RELIANCE's = `{NSE, BSE}`. | The stamp is provably dynamic (no hardcoded literal) and fed by exchange sets that are genuinely single- vs dual-listed live, matching the certified JUMBO=bse / RELIANCE=nse+bse split. | holds |
| R15-DATA-019 | Live `GET /disclosures/announcements?symbol=JUMBO`. | `count: 17` (vs the certified 18; day-to-day drift as the announcement window rolls, expected), newest row `2026-07-31T17:43:26` "Scrutiniser" — matches the batch-3-quoted newest-row timestamp exactly. Attachment URLs are real `bseindia.com/xml-data/corpfiling/AttachHis/*.pdf` links. | holds |
| R15-DATA-021 | In-process: `services.corporate_disclosures._merge_bse_split()` with `_bse_shareholding` monkeypatched to one BSE quarter (2024-12-31, carrying a split) and 7 synthetic NSE quarters (2021-09 .. 2024-09), mirroring the original SIL shape without depending on the currently-403'd live BSE feed. | 2021-09 through 2024-06 (184-1188 days from the BSE quarter) carry `institutions_percent=None` (no split); 2024-09 (92 days, inside the 100-day `_SPLIT_MERGE_MAX_DAYS` bound) carries the split, labelled `split_source="BSE"`. Exact match to the certified bound behaviour. | holds |
| R15-DATA-022 | Live `GET /disclosures/shareholding?symbol=SMR` on the candidate sidecar (BSE SHP still 403 this session — a direct probe of `api.bseindia.com/.../SHPQNewFormat` confirmed 403, `www.bseindia.com` pages still 200). | HTTP `502`, `code: "provider_error"`; the sidecar log records the exact internal reason: `"disclosures: every shareholding source failed for 'SMR' (BSE: bse shareholding: index HTTP 403)"` — an honest failure, never a silent `count 0`. | holds |

## Notes
- BSE's `api.bseindia.com` SHP-index/scrip-header lane is still 403 (Akamai) from this IP this
  session — the SAME environment condition batch-3's own verifier hit and logged as issue 3.
  `www.bseindia.com` attachment/XBRL downloads still work (confirmed via DATA-019's live
  attachment URLs). This is not a candidate regression.
- No regressions found in this set. No new defects found.
