# triage-c: rc1-vshard-3:4 (tied to R15-CODE-FRONTEND-017)

Auditor: triage-c, rc1 gate round 4, written 07:24 IST. HEAD is 7c450c8e and its code tree is identical to 01015033. src/store/sec.ts is unchanged since 01015033 (`git diff 01015033 HEAD -- src` is empty).

**Verdict: partial on R15-CODE-FRONTEND-017. Severity: medium (kept).**

## Shard claim

rc1-vshard-3:4 says the SEC filing-detail and insider slices still have no per-slice generation, so a late response for the previous symbol or accession overwrites the current one. Only `loadFilings` is guarded, by `filingsGeneration`.

## Tied entry

R15-CODE-FRONTEND-017 (fixed in batch 7, commit e81c9e7; class `fetch-no-request-generation`). Its title: "A slower stale response overwrites the newer one: the SEC panel reverts to the previous symbol ...".

Its fix_shape: "Per-slice generation counter (or AbortController) checked before commit, shared as one small helper for sec/earnings/analyst-ratings/quant/macro; stop loadFilings writing activeIdentifier; key status/error by cache key."

Batch 7 certified only the census proof P1 (the filings list) and the earnings 7-day/30-day case.

## Duplicate search

I grepped the register for loadFilingDetail, loadInsider, activeAccession, insiderStatus, request generation, fetch-no-request-generation, stale response and late response. The only hit is R15-CODE-FRONTEND-017 itself.

## Code at HEAD (src/store/sec.ts)

- :128 `let filingsGeneration = 0;` is the only generation counter in the store.
- :188-214 `loadFilingDetail` has no generation check. On success it commits `filingDetailStatus: "ready"` **and `activeAccession: accession`** (:201-209), so it writes the active id from the response. That is the same pattern the fix removed from `loadFilings`. On failure it commits the scalar `filingDetailStatus: "error", filingDetailError` (:212).
- :220-242 `loadInsider` has no generation check either and commits the scalar `insiderStatus`/`insiderError` (:233-240).

The consumers are:
- src/modules/sec/FilingViewer.tsx:30-32 renders the viewer for `activeAccession`. SecFilingsPanel.tsx:324-331 keys it on that value.
- FilingViewer.tsx:81-118 shows `filingDetailError` as an error banner even when the open filing's detail is present.
- InsiderTradingTable.tsx:100-101 and :154-172 show `insiderError` above whatever rows are cached for the current identifier.

## Re-run at HEAD

I ran a scratch vitest over a `git archive HEAD` copy of src at `$S/fe` (node_modules symlinked; test saved as `$S/TRIAGEC_FE017.test.tsx.txt`). `sidecarGet` is mocked with deferred promises, and the insider case renders the real InsiderTradingTable.

```
cd $S/fe && ./node_modules/.bin/vitest run src/store/TRIAGEC_FE017.test.tsx   -> 4 failed (4), EXIT=1
D1 {"activeBeforeLate":"B-2","activeAfterLate":"A-1","status":"ready"}
D2 {"activeAfterBackThenLate":"A-1"}
D3 {"active":"B-2","status":"error","error":"EDGAR timeout","b2Cached":true}
I1 {"errorBeforeLate":null,"errorShownOnMsftAfterLate":"Could not load insider data — EDGAR timeoutRetry","msftRowStillShown":true,"status":"error"}
```

- **D1:** filing A-1 is opened (slow), then B-2 is opened and becomes ready. When A-1 lands, `activeAccession` flips back to A-1 and the viewer jumps to the old filing.
- **D2:** A-1 is opened, the user presses Back (`setActiveAccession(null)`), and the late A-1 response reopens the viewer.
- **D3:** a late A-1 failure puts "EDGAR timeout" on B-2's viewer.
- **I1:** a late AAPL insider 504 puts "Could not load insider data — EDGAR timeout" above MSFT's rows.

EDGAR detail loads that take tens of seconds are normal. shard-7 measured a 23 s unhinted 10-Q lookup, so these orderings do not need contrived timing.

## Classification

The entry's stated repro (the filings list P1, plus earnings) holds. What does not hold is a stated part of the same class, as the fix_shape names it: a per-slice generation checked before commit, no active id written from a response, and status/error keyed by cache key. Two SEC slices still miss all three. D1/D2 is literally the title's symptom ("the SEC panel reverts to the previous ...") on the detail slice.

So this is **partial** on the tie, not a new defect and not a duplicate. The shard's severity of medium stands. The viewer silently switches the document the user is reading, or shows another request's error. That is a stated feature degraded in a common flow, and re-opening the filing is the workaround.

## Root cause

- src/store/sec.ts:188-214: `loadFilingDetail` commits without a generation check and writes `activeAccession: accession` from the response (:208).
- src/store/sec.ts:212: its error goes to an unkeyed scalar.
- src/store/sec.ts:220-242: `loadInsider` commits `insiderStatus`/`insiderError` without a generation check (:233-240).

## Fix shape

Give `loadFilingDetail` and `loadInsider` their own generation counters, the same pattern as `filingsGeneration` at sec.ts:128/158/174/182. Better still, extract the one small helper the fix_shape asks for and reuse it for all three.

Stop `loadFilingDetail` writing `activeAccession`. The caller (`setActiveAccession` in SecFilingsPanel) already owns it, mirroring the fix that stopped `loadFilings` writing `activeIdentifier`. A response or error whose generation is no longer the newest must be dropped before `set`. Caching the payload in `filingDetailByAccession`/`insiderByIdentifier` is harmless, but the status and error must not be committed. Optionally key the error by accession or cache key so FilingViewer and InsiderTradingTable only show their own.

## Acceptance test

In `src/store/sec.test.ts`, add these cases with deferred `sidecarGet` mocks:
1. `loadFilingDetail('A-1')` is left pending. Call `setActiveAccession('B-2')` and let `loadFilingDetail('B-2')` resolve, then resolve A-1. Expect `activeAccession` to be `'B-2'` and `filingDetailStatus` to be `'ready'`.
2. The same, but after `setActiveAccession(null)`. Expect `activeAccession` to stay `null`.
3. A late A-1 rejection after B-2 is ready. Expect `filingDetailError` to be `null`.
4. `loadInsider('AAPL')` is left pending while `loadInsider('MSFT')` resolves, then AAPL rejects. Expect `insiderStatus` to be `'ready'` and `insiderError` to be `null`.

Live re-proof: the scratch command above must report 4 passed.

## Certification-failure count

- R15-CODE-FRONTEND-017's note has no 'certification failures so far' clause.
- The batch VERDICTS certify it in batch-7, and it appears in no not_certified list.
- No REFUTATION_AUDIT file has a regression_confirmed or partial verdict for it.

That gives a baseline of 0. This partial adds 1, so the count is **1**.
