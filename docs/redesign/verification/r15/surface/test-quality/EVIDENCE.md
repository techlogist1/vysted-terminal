# test-quality probe — evidence (R15 wave 2)

Worker model: claude-fable-5-1. Read-only audit; no sidecar; targeted test runs only.

## 0. Suite census (measured)

- Python: 174 `test_*.py` files, 2341 `test_` functions under `sidecar/tests/`.
- TypeScript: 135 `*.test.ts(x)` files, ~1495 `it(`/`test(` cases.
- Rust: 13 `#[test]` in `src-tauri/src`.
- Skips/xfail: exactly ONE in the whole repo —
  `sidecar/tests/test_native_search_live.py:41` `skipif(not OPENROUTER_LIVE_KEY)` (live citation
  check; correct to gate). No `xfail`, no `it.skip/todo/only`, no `#[ignore]`.
- AST scan (`scratchpad/astscan.py`): 1 test with zero assertions, 21 with only weak assertions
  (`is not None` / `isinstance` / `> 0`).

## 1. Log (appended as the audit proceeds)

