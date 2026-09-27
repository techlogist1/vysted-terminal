# rc1-vshard-8:3 (tie R15-AGENT-090) — the ratio guard replaces a TRUE, sourced ratio when the sentence carries a date

Auditor: refutation audit round 4, group agent-inproc. HEAD 1a8ff356 (docs-only after 33586c21; code tree =
01015033; the guard is byte-identical to the candidate). Own sidecar :52410 (pgid 77341, scratch data dir), llama3.1:8b under
/tmp/vysted-r15-ollama.lock.

## Verdict: new_defect_confirmed (medium)

## 1. Shard claim
docs/redesign/verification/r15/rc1/round-4/verifier/shard-8.md:58-63: on the literal SIFY prompt llama3.1:8b wrote the TRUE
sourced ratio with the tool's provenance date; sidecar log 'ratio guard replaced an untraced claim: 2026-06-26, one SIFY ADR
represents six equity shares.'; the user saw "According to the SEC 20-F cover page filed on The ADR-to-ordinary-share ratio is
not available from this session's sources." Offline: any date adds its day/month as claimed counts.

## 2. Code read at HEAD
_MARKED (sidecar/services/agent_runtime.py:1929-1952) blanks a 4-digit year (:1934 `\b(?:19|20)\d{2}\b`) but has no date
rule, so the day and month of 2026-06-26, 06/26/2026, 26-06-2026, "June 26, 2026" or "26 June 2026" survive as share-count
candidates (_COUNT :1955). _ratio_claim_traced (:2014-2015) needs every claimed count in one tool result's depositary
segment, and the sourced set is {"6"}, so a true sentence that names its filing date is never traced.

## 3. Real tool result at HEAD + the live sentence (`cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/sify_fund.py`, network read of Yahoo/SEC)
```
ok: True | ads_ratio: {"ordinary_shares_per_ads": 6, "statement": "American Depositary Shares, each represented by Six Equity Shares", "provenance": {"source": "SEC 20-F cover page", "filed": "2026-06-26", "url": "https://www.sec.gov/Archives/edgar/data/1094324/000155485526001437/sify-20260331.htm"}}
sourced counts: {'6'}
live sentence -> "The ADR-to-ordinary-share ratio is not available from this session's sources. "
undated        -> 'One SIFY ADS represents six equity shares. '
share counts of live sentence: {'06', '26', '6', '1'}
```

## 4. Through the real invoke_agent (scripted provider; `cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/ratio_rt.py date`), result = fundamentals WITH ads_ratio 6
```
== rc1-vshard-8:3: TRUE sourced ratio (ads_ratio 6 in the tool result), with and without a date
WHOLE  According to the SEC 20-F cover page filed on 2026-06-26, one SIFY ADR represents six equity shares.
   deltas=['According to the SEC 20-F cover page filed on 2026-06-26, one SIFY ADR represents six equity shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  According to the SEC 20-F cover page filed on 2026-06-26, one SIFY ADR represents six equity shares.
   deltas=27 llama-style tokens
   OUT="According to the SEC 20-F cover page filed on The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=True
WHOLE  According to the SEC 20-F cover page, one SIFY ADR represents six equity shares.
   deltas=['According to the SEC 20-F cover page, one SIFY ADR represents six equity shares.']
   OUT='According to the SEC 20-F cover page, one SIFY ADR represents six equity shares.'
   replaced=False  figure-left-outside-replacement=True
LLAMA  According to the SEC 20-F cover page, one SIFY ADR represents six equity shares.
   deltas=19 llama-style tokens
   OUT='According to the SEC 20-F cover page, one SIFY ADR represents six equity shares.'
   replaced=False  figure-left-outside-replacement=True
WHOLE  As of June 26, 2026, each SIFY ADS represents 6 equity shares.
   deltas=['As of June 26, 2026, each SIFY ADS represents 6 equity shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  As of June 26, 2026, each SIFY ADS represents 6 equity shares.
   deltas=18 llama-style tokens
   OUT='As of June 26, 2026, each SIFY ADS represents 6 equity shares.'
   replaced=False  figure-left-outside-replacement=True
WHOLE  Each SIFY ADS represents 6 equity shares.
   deltas=['Each SIFY ADS represents 6 equity shares.']
   OUT='Each SIFY ADS represents 6 equity shares.'
   replaced=False  figure-left-outside-replacement=True
LLAMA  Each SIFY ADS represents 6 equity shares.
   deltas=9 llama-style tokens
   OUT='Each SIFY ADS represents 6 equity shares.'
   replaced=False  figure-left-outside-replacement=True
WHOLE  Per the 20-F filed 06/26/2026, each SIFY ADS represents six equity shares.
   deltas=['Per the 20-F filed 06/26/2026, each SIFY ADS represents six equity shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  Per the 20-F filed 06/26/2026, each SIFY ADS represents six equity shares.
   deltas=22 llama-style tokens
   OUT="Per the 20-F filed The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=True
WHOLE  Per the 20-F filed 26-06-2026, each SIFY ADS represents six equity shares.
   deltas=['Per the 20-F filed 26-06-2026, each SIFY ADS represents six equity shares.']
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  Per the 20-F filed 26-06-2026, each SIFY ADS represents six equity shares.
   deltas=22 llama-style tokens
   OUT="Per the 20-F filed The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=True
WHOLE  On 26 June 2026 Sify's 20-F stated that each ADS represents 6 equity shares.
   deltas=["On 26 June 2026 Sify's 20-F stated that each ADS represents 6 equity shares."]
   OUT="The ADR-to-ordinary-share ratio is not available from this session's sources."
   replaced=True  figure-left-outside-replacement=False
LLAMA  On 26 June 2026 Sify's 20-F stated that each ADS represents 6 equity shares.
   deltas=21 llama-style tokens
   OUT="On 26 June 2026 Sify's 20-F stated that each ADS represents 6 equity shares."
   replaced=False  figure-left-outside-replacement=True
```
Every dated true sentence is replaced when it arrives whole; the ISO and numeric forms are also replaced under llama chunking
and reproduce the shard's exact garble ("... filed on The ADR-to-ordinary-share ratio ..."). The undated control is kept.

## 5. Live at HEAD, llama3.1:8b (fresh phrasings)
- date-2: "Check SIFY's fundamentals, then answer in ONE sentence that starts with the 20-F filing date written as YYYY-MM-DD:
  how many equity shares does one SIFY ADS represent?" -> fundamentals ok (ads_ratio present, section 3) -> sidecar log
  `2026-09-27 07:12:24,027 INFO services.agent_runtime: ratio guard replaced an untraced claim: '2026-06-26: One SIFY ADS represents six equity shares.'`; the answer the user got ends
  "The ADR-to-ordinary-share ratio is not available from this session's sources." for a ratio the tool carried.
- date-1 ("What does SIFY's latest 20-F cover page say ...") went to sec_filing_content (MCP unbound in this stack) and stated no ratio: not informative.
- date-3: "Using the fundamentals tool on SIFY, give the ADS ratio and the date of the filing it comes from, all in a single
  sentence (date as MM/DD/YYYY)." -> fundamentals ok -> "The ADS ratio for SIFY is 6, and the filing it comes from is a SEC 20-F cover page filed on June 26, 2026." was KEPT: the model wrote the month-name form, and the
  whitespace release (rc1-verifier:2) cut the sentence before '26', so the day never sat in the judged unit. Live over-replacement
  therefore depends on chunking for month-name dates; ISO/numeric dates trigger it whole or chunked (section 4).

## 6. Adversarial checks
- Not the verifier's rc1-verifier:2 defect: with the whitespace-release fix applied in memory (scratch plugin
  /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/plug/segfix_plugin.py), every dated true sentence is still replaced whole (/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/ratio_rt_fixed.out); the date rule is an
  independent root cause.
- A date marker fixes it without opening a hole (in memory, /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/plug/datefix_plugin.py, `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/date_fixed.py`):
```
WITH kept | BARE replaced | According to the SEC 20-F cover page filed on 2026-06-26, one SIFY ADR represents six equity shares.
WITH kept | BARE replaced | As of June 26, 2026, each SIFY ADS represents 6 equity shares.
WITH kept | BARE replaced | Per the 20-F filed 06/26/2026, each SIFY ADS represents six equity shares.
WITH kept | BARE replaced | Per the 20-F filed 26-06-2026, each SIFY ADS represents six equity shares.
WITH kept | BARE replaced | On 26 June 2026 Sify's 20-F stated that each ADS represents 6 equity shares.
WITH REPLACED | BARE replaced | As of 2026-06-26 each SIFY ADS represents 5 equity shares.
```
  and tests/test_agent_runtime.py + test_b5_runtime_notices.py + test_b3_runtime_tool_args.py pass with both scratch fixes (282 passed).

## 7. Classification
Reproduces at HEAD offline and live. It is not AGENT-090's class (hallucinated-field-no-plausibility-check: an untraced ratio
reaching the user): here the ratio IS in the tool result and the guard hides it, replacing it with a false "not available from
this session's sources". It is a precision defect the AGENT-090 guard introduced (its docstring: "Extend _MARKED, not the claim
class, when a true sentence is caught"). No register entry covers it (register grep: over-replac / ratio guard / dates: only
AGENT-090 and LEAD-031, which is the JSON-fragment splice). Severity medium (kept): the grounded ADR ratio, a stated feature
since batch 16, is withheld and replaced by a false unavailability statement whenever the model cites the provenance date in
the same sentence, which it does naturally because the tool hands it provenance.filed; no wrong figure is shown; re-asking
works around it.

Root cause: sidecar/services/agent_runtime.py:1929-1934 (_MARKED blanks the year of a date but not its month/day, so they read
as share counts and _ratio_claim_traced at :2014-2015 finds them unsourced).
Fix shape: add one date alternative at the front of _MARKED: ISO `(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}`, numeric
`\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)?\d{2}`, and month-name forms (`<Mon>[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?`,
`\d{1,2}(?:st|nd|rd|th)? <Mon>`), so a date is marked as not-a-count on both the claim and the source side, per the
guard's own "extend _MARKED" rule. No claim-class change.
Acceptance: sidecar/tests/test_agent_runtime.py new parametrized test_a_dated_sourced_ratio_is_kept: for "According to the SEC
20-F cover page filed on 2026-06-26, one SIFY ADR represents six equity shares. ", "As of June 26, 2026, each SIFY ADS
represents 6 equity shares. ", "Per the 20-F filed 06/26/2026, each SIFY ADS represents six equity shares. ", "On 26 June 2026
Sify's 20-F stated that each ADS represents 6 equity shares. ": `_guard_ratio_claims(s, [json.dumps(_SIFY_FUNDAMENTALS_WITH_DEPOSITARY)]) == s`
and against _SIFY_FUNDAMENTALS == RATIO_UNAVAILABLE + " "; and "As of 2026-06-26 each SIFY ADS represents 5 equity shares. "
stays replaced against the depositary result. Live: the date-2 prompt above on llama3.1:8b logs no "ratio guard replaced"
line for a sentence carrying 'six'/'6' and the answer states six.

Certification-failure count: verdict does not land on a register entry -> 0 (n/a).
