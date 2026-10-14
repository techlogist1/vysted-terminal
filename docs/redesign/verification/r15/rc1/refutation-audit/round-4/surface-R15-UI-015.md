# Refutation audit round 4, group surface: R15-UI-015 (rc1-verifier:9)

Auditor: Opus, 06:45-07:10 IST. HEAD 33586c21 on 004-r4-experience-rebuild; code tree equals 01015033
(`git diff --name-only 01015033 HEAD | grep -v '^docs/'` printed nothing). Own sidecar :52415 from
`sidecar/.venv` (`python -m uvicorn app:app`, `VYSTED_DATA_DIR` = scratch data dir). Scratch vitest
config: root = repo, `test.dir` = scratchpad `refaudit4-surface/vt` (node_modules symlinked), so no repo
file was written.

## Entry (register)

- Repro: keyless FRED DGS10 502 retried 12x by `useRetryOnSidecarReady`; same for 502s in
  News/Earnings/SEC/Screener. Secondary clause: `store/sec.ts:241-243 additionally discards the search
  error message`.
- fix_shape: retry only connection-level failures or 503; News uses the hook; **keep the reason in
  sec.searchCompanies**; hook test 502 -> one attempt, TypeError -> retries.
- History: batch-8 not_certified (not claimed, partial landing: earnings/screener still flattened);
  batch-9 certified (earnings/screener 1 fetch each on a 502). Neither batch touched `searchCompanies`
  (`git show e9f28770 -- src/store/sec.ts` adds `filingsCause` only).

## Entry's own repro at HEAD: primary clause (retry) is fixed

```
$ curl -s 'http://127.0.0.1:52415/macro/DGS10?provider=fred'
{"detail":"FRED needs a free API key for macro data. ...","code":"provider_error",...}  HTTP 502
```

Hook predicate (`src/lib/use-sidecar-retry.ts:44-46`):
`return !(err instanceof SidecarError) || err.status === 0 || err.status === 503;`

Panel wrappers re-throw the original error: MacroPanel.tsx:65 `throw status.cause`;
NewsFeedPanel.tsx:250 `throw error`; EarningsCalendarPanel.tsx:144 `throw state.upcomingCause ?? ...`;
SecFilingsPanel.tsx:79 `throw useSecStore.getState().filingsCause`; ScreenerPanel.tsx:126
`throw state.universeCauses[universe] ?? ...`.

Scratch vitest `ui015.scratch.test.tsx` (hook mounted with fake timers, 60 s each):

```
"hookAttempts60s": { "sidecar502": 1, "sidecar501": 1, "sidecar503": 13, "typeError": 13 }
```

Repo tests: `vitest run src/lib/use-sidecar-retry.test.ts src/modules/earnings/EarningsCalendarPanel.test.tsx
src/modules/screener/ScreenerPanel.test.tsx src/modules/news/NewsFeedPanel.test.tsx src/store/sec.test.ts
src/lib/host-actions.test.ts src/store/screener.test.ts` -> `Test Files 7 passed (7) / Tests 200 passed (200)`.

## Verifier's refutation re-run: secondary clause still holds

`src/store/sec.ts:244-259` at HEAD:

```ts
    } catch {
      set({ searchResults: EMPTY_SEARCH, searchStatus: "error" });
    }
```

Live, the engine gives a real reason for the search failure on this stack (MCP unbound):

```
$ curl -s 'http://127.0.0.1:52415/sec/filings/search?q=Apple&limit=10'
{"detail":"sec-edgar-mcp is not available — the subprocess did not bind a port this launch (...) Relaunch the app to retry the bind; ..."}  HTTP 501
```

Scratch vitest, same SidecarError(501, that detail) fed to `searchCompanies("Apple")`, then to `loadFilings("AAPL")`:

```
"searchState": { "searchResults": [], "searchStatus": "error" },
"reasonAnywhere": false,
"filings": { "filingsStatus": "error", "filingsError": "sec-edgar-mcp is not available — ...", "causeIsSidecarError": true }
```

So the search path discards the reason (and the SidecarError) while the filings path keeps both.

## Impact of the residual (why low)

- `SecFilingsPanel.tsx` reads only `searchResults` (lines 49, 201, 208, 214); `grep -n searchStatus
  src/modules/sec/*.tsx` prints nothing. A failed search and "no match" look identical: the dropdown
  simply does not open.
- Workaround: type the ticker or CIK and press Enter; the filings load then shows the same reason
  (`filingsError` kept, above).
- No retry storm, no wrong data: the autocomplete is a convenience. Low, not the entry's medium.

## Verdict: partial (low)

The entry's primary repro no longer reproduces, but a part its own repro and fix_shape name
("keep the reason in sec.searchCompanies") is unmet at HEAD. Not a verifier error: the verifier tested
the entry's own clause. Not taste: the fix_shape states it.

- root_cause: `src/store/sec.ts:257-258`: bare `catch {}` sets `searchStatus: "error"` and drops the
  SidecarError and its message; the panel never reads a search error.
- fix_shape: catch `err`, keep `searchError: err instanceof Error ? err.message : "company search failed"`
  (clear it on load/idle/clearSearch), and have SecFilingsPanel show it as one muted line under the symbol
  field when `searchStatus === "error"` (for example "Company search unavailable: <reason>") instead of
  showing nothing.
- acceptance_test: `src/store/sec.test.ts`: `sidecarGet` rejects `new SidecarError(501, "sec-edgar-mcp is
  not available")` -> after `searchCompanies("apple")`, `searchStatus === "error"` and
  `searchError` contains "sec-edgar-mcp is not available". SecFilingsPanel test: typing "Apple" with that
  rejection renders the reason text. Live re-proof: with the MCP unbound, `curl
  :<port>/sec/filings/search?q=Apple` -> 501 and the panel shows the reason under the field.

## Certification-failure count

Given baseline for UI-015 = 0 (the note has no "certification failures so far" clause; the given
baseline does not count the batch-8 not_certified row, which was "Not claimed": the integrator recorded
a partial landing). + 1 for this partial = **1**. If the batch-8 "Not claimed" row is counted
mechanically, the count is 2.
