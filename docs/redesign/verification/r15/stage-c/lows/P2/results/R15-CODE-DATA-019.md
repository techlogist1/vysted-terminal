# R15-CODE-DATA-019 second-attempt result

- Entry: R15-CODE-DATA-019 (matched_criteria dead wire field), partition P2, prior set W4
- Outcome: fixed_untested
- Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
- Branch: worktree-agent-lows-CN-r15-code-data-019-4c6dfe8
- Cherry-picked: none (W4 branch carried no commit for this entry; its files do not overlap these)
- Fix commit: a1539309
- Written: 06:51 IST

## Files
- sidecar/services/screener.py: apply_criteria no longer tracks passed indices; flat path uses all() (same short-circuit AND)
- sidecar/models/screener.py: ScreenerResultRow.matched_criteria removed
- types/screener.ts: matched_criteria removed from the row mirror
- src/modules/screener/ScreenerPanel.test.tsx, src/modules/screener/ScreenerResultsTable.test.tsx, src/store/screener.test.ts: key removed from typed fixtures (tsc excess-property)
- sidecar/tests/test_screener.py: dropped the [0, 1, 2] assertion that pinned the phantom field; added acceptance test

## Tests written (not run)
- sidecar/tests/test_screener.py::test_result_row_has_no_matched_criteria (flat + group paths, model_fields)

## Untested pending integration
- pytest sidecar/tests/test_screener.py, vitest on the three TS test files, tsc. Only py_compile, ruff format/check and prettier were run on touched files (clean).

## Risks
- ScreenerResultRow is extra="forbid"; no code path re-validates a stored row payload (grep: no ScreenerResult(Row).model_validate), so old payloads carrying the key are not re-ingested anywhere.
- src/lib/host-actions.ts flattenLeaves left untouched per the refuter note.
