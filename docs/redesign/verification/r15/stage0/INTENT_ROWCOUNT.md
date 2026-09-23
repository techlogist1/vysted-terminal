chunk | expected | assessed | raw | verdicts | status
--- | --- | --- | --- | --- | ---
blueprint-0 | 48 | 48 | 7 | 7 | complete
blueprint-48 | 48 | 48 | 7 | 7 | complete
blueprint-96 | 48 | 48 | 6 | 6 | complete
blueprint-144 | 48 | 48 | 10 | 10 | complete
blueprint-192 | 48 | 48 | 7 | 7 | complete
blueprint-240 | 48 | 48 | 1 | 1 | complete
blueprint-288 | 45 | 45 | 3 | 3 | complete
spec-0 | 45 | 45 | 2 | 2 | complete
spec-45 | 45 | 45 | 3 | 3 | complete
spec-90 | 45 | 45 | 12 | 12 | complete
spec-135 | 45 | 45 | 14 | 14 | complete
spec-180 | 41 | 41 | 14 | 14 | complete
pdd-readme-0 | 45 | 45 | 3 | 3 | complete
pdd-readme-45 | 45 | 45 | 10 | 10 | complete
pdd-readme-90 | 45 | 45 | 2 | 2 | complete
pdd-readme-135 | 45 | 45 | 2 | 2 | complete
pdd-readme-180 | 45 | 45 | 5 | 5 | complete
pdd-readme-225 | 45 | 45 | 1 | 1 | complete
pdd-readme-270 | 45 | 45 | 7 | 7 | complete
pdd-readme-315 | 39 | 39 | 3 | 3 | complete
deferred-0 | 42 | 42 | 15 | 15 | complete
deferred-42 | 42 | 42 | 9 | 9 | complete
deferred-84 | 40 | 40 | 9 | 9 | complete

Method: expected = count of promise entries in `census/intent/promises-<source>.json` at the
chunk's `[start,end)` offset (offsets/sizes derived from source doc lengths: blueprint 333 @48,
spec 221 @45, pdd-readme 354 @45, deferred 124 @42 — matches every `ledger-*.json` filename
present in `census/intent/`, 23 total). assessed = rows in
`census/intent/ledger-<chunk>.json` carrying a `status` or `verdict` field (placeholders
excluded). raw/verdicts = finding counts in `census/raw/intent-<chunk>.json` and
`census/refute/intent-<chunk>.json` respectively (both files required to exist).

Note: `intent-S2A.json` .. `intent-S2G.json` launch-args together name only 19 of the 23 chunk
ids (S2F/S2G are retry waves over a subset already in S2A-E, not new chunks; blueprint-48,
blueprint-192, pdd-readme-0, pdd-readme-45 never appear in any S2A-G launch-args file but their
ledgers exist and are fully assessed regardless — likely dispatched in an earlier round not
covered by S2A-G). All 23 chunks pass: expected == assessed, raw and refute files both present
with matching counts. No shortfall found this round.
