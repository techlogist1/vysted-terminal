# triage-d / rc1-vshard-5:2 (tie R15-DATA-061) -> partial on R15-DATA-061

Audited 07:21-07:27 IST. HEAD bed3b166 (code == 01015033, see triage-d-rc1-vshard-2-2.md header). Own sidecar :52435 (uvicorn from sidecar/.venv, scratch VYSTED_DATA_DIR, MCP ports 0).

## Is it closed by the fix round?
No. Fix commit fbc5b87e ("yfinance not_found for out-of-alphabet symbols and empty statement frames") touches only `sidecar/services/yfinance_provider.py`.
`git diff --stat 1006c6da 01015033 -- sidecar/services/macro sidecar/routers/macro.py sidecar/services/errors.py sidecar/app.py ...` lists only `sidecar/services/yfinance_provider.py | 28`. The macro providers, the macro router and the error mapper are byte-identical to the shard's candidate.

## Live at HEAD (:52435)
```
ZZNOTREAL?provider=ecb               -> {"detail":"The data provider returned an unexpected response.","code":"provider_error","action":"Retry, or try again later."} [HTTP 502]
   log: ECB upstream error for 'ZZNOTREAL': not enough values to unpack (expected 2, got 1)
ZZNOTREAL.X.Y?provider=ecb           -> same 502 provider_error "Retry"
   log: ECB upstream error for 'ZZNOTREAL.X.Y': REQUEST ERROR 404: No results found. There are no results matching the query.
GDP?provider=world-bank              -> same 502 provider_error "Retry"
   log: World Bank upstream error for 'GDP'/'IND': APIError: JSON decoding error (https://api.worldbank.org/v2/en/sources/2/series/GDP/...)
NOTAREALINDICATOR?provider=world-bank -> same 502 provider_error "Retry" (same APIError)
ZZNOTREAL?provider=imf               -> same 502 provider_error "Retry"
   log: IMF series_id 'ZZNOTREAL' must be ``<dataflow>/<key>``
GDP?provider=worldbank | world_bank | bogus -> 502 provider_error "Retry" (non-Literal provider falls to the legacy openbb path)
GDP?provider=fred (keyless)          -> 502, detail "FRED needs a free API key ...", action "Retry, or try again later."
controls: NY.GDP.MKTP.CD?provider=world-bank -> 200 (observations from 1960); EXR.M.USD.EUR.SP00.A?provider=ecb -> 200
```
The World Bank and ECB upstreams are up (the controls return 200), so each 502 above is an unknown or malformed id or a bad provider, told to "Retry". Supplementary GET on the shared :52152 sidecar: the macro code there is identical to HEAD, since only yfinance_provider/symbol_resolver/agent_runtime differ. `/macro/GDP?provider=worldbank` and `/macro/ZZNOTREAL?provider=ecb` give the same 502 "Retry" there. With openbb-mcp bound, the shard showed the legacy path answering openbb 422 literal_error, which again maps to 502 "Retry".

## Code
- `sidecar/services/macro/ecb_provider.py:175-178`: a bare `except Exception` raises `ProviderError(...)` with no kind. ECB's "REQUEST ERROR 404: No results found" and ecbdata's key-parse ValueError both become kind None, so the app mapper (`services/errors.py:102`) returns 502 provider_error "Retry, or try again later.".
- `sidecar/services/macro/world_bank_provider.py:162-167`: same. wbgapi APIError for an unknown indicator becomes kind None.
- `sidecar/services/macro/imf_provider.py:121`: a malformed id raises with no kind. The upstream-404 leg at :212-213 IS mapped to not_found, which the batch-8 note asked for. ECB and World Bank never got the same treatment.
- `sidecar/routers/macro.py:69,89-101`: `provider: str | None`. Anything outside `_V0_6_0_PROVIDERS` ('world-bank' is valid, 'worldbank'/'world_bank' are not) goes to the legacy openbb `get_macro_series` path, and every failure there is a 502 "Retry". The search and catalog routes on the same router already type provider as `MacroProvider` (lines 47, 56) and 422 a bad value.

## Class
R15-DATA-061 is error-misclassification. Its fix_shape: "One mapper ... {rate_limited:429, not_found:404, network:503, None:502} ... classify ... as not_found". Its evidence and notes name `/macro/GDP` (entry repro INT-spec-135-137), "IMF upstream 404s are classified provider_error/502, not not_found" (batch-8), and "/macro/GDP?provider=worldbank ... unvalidated provider value upstream" (batch-9). The entry's own repros hold at HEAD: /macro/GDP no longer leaks raw text; /quotes/ZZZZNOTREAL is 404 per the fix-r1 RECHECK. The same class still fails on the macro routes, so this is the tied entry's class and the verdict is partial.
Severity: medium, unchanged. Honest-failure feature degraded: an unknown or malformed macro id, or a mistyped provider, reads as a transient upstream fault and tells the user to retry something that will never succeed. The frontend does not auto-retry a 502 (`src/lib/use-sidecar-retry.ts:44-45`), so there is no retry storm.
Certification failures: the register note has no clause. The baseline is 2: batch-8 and batch-9 VERDICTS.json not_certified. There are 0 refutation-audit partial or regression verdicts. With this partial the count is 3, matching the shard's "3rd failure".

End-of-audit (07:33 IST): own sidecar pid 90459 on :52435 stopped by pid (health now 000); no child processes; the repo working tree is unchanged apart from these output files.
