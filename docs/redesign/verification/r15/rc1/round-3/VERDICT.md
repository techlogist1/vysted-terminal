# rc1 gate round 3: verifier verdict

**FAIL.** Candidate `5ff9be041180c1c316ad48ceb120a23549a7575a`, the fix-int head that fast-forwards `01d6920a`. The sheet is `docs/redesign/verification/R15_GATE_RC1.md` and the findings are in `findings/rc1-verifier.json`. All paths below are relative to this directory. The verifier sidecar ran on :52312 from the candidate worktree (`verifier/spot-screener/HEAD.txt`: "worktree HEAD 5ff9be041180c1c316ad48ceb120a23549a7575a").

## 1. Register criterion: PASS

- Register at the candidate: `open` entries at critical/high/medium = []. Status counts: fixed 392, open 205 (all low), blocked_tier4 29, needs_gui 11, removed_with_feature 14, not_a_defect 5.
- Fixed-uncertified: R15-CODE-DATA-023. The probe does not reproduce it. `verifier/sample/CODE-DATA-023-probe.txt` shows the docstring now reads "nse-all — every NSE master row (EQ + ETF + SM/NSE Emerge)". The only count left is at line 95 ("~5,156"), which is R15-LEAD-029 (open, low).

## 2. Gate 8, no trading path: PASS

- `verifier/gate8/openapi-paths.txt`: 101 paths. `grep -iE 'order|broker|kill|audit|safety'` returns 0.
- `verifier/gate8/tools-own.txt`: "CAPABILITY_CATALOG 56 … TOOL_SCHEMAS 56 … KNOWN_TOOL_IDS 56 … MCP 40". The MCP list has no portfolio, host-action or order tool.
- `verifier/gate8/rg-classified-counts.tsv`: all 850 sweep hits are classified and 0 are UNCLASSIFIED. Classes include: financial-metric margin, OpenRouter "broker" (LLM routing), hardware-fit "marginal", company names with "Brokers", removal/negation statements, tests asserting absence, and historical docs. "Connect broker" appears only in `EmptyState.test.tsx`.
- `verifier/gate8/first-launch-terms.txt`: "Vysted has no brokerage connection. It cannot place, route or simulate orders."
- `verifier/gate8/agent-02-order-attempt.log`: "I can't assist with actions that require a brokerage connection." No tool_use event.
- `verifier/gate8/frontend-gate-probe.run.log`: `ASK place_order accept -> failed | status pending | detail unknown action "place_order" | acks []` and `AUTO submit_order -> failed | acks []`. Result: "Tests 3 passed (3)".
- `verifier/gate8/SAFETY_SURFACE_ROWS.tsv`: 36 paths, 2 identical, 34 differing, each with a row. Examples: `sidecar/models/audit_log.py absent +0/-58 … deleted by 3d037351 … (D81)`, `src-tauri/src/kill_switch.rs absent … deleted by 5d45a0ae`. The full diff is `safety-surface.diff`.
- `verifier/gate8/data-dir-tables.txt`: no audit_orders table in any db. portfolio.db has `positions,sqlite_sequence`.
- `verifier/gate8/pytest-no-trading-surface.txt`: "8 passed".

## 3. Gate 8, tracked portfolio: PASS

- Holdings after the add (`pf-01-after-add.json`): `[["MSFT", 10, 400]]`.
- P&L (`pf-02-pnl.txt`): "pnl=marketValue-costValue=1161.6998…; pnlPercent=29.0425% (price 516.1699829101562 USD @ 2026-09-25T20:00:01Z)".
- Gated write (`agent-01-gated-add.log`): "Staged for your review, not applied yet: portfolio_add_position AAPL". Holdings afterwards (`pf-03-after-gated-add.json`) are unchanged: `[["MSFT", 10, 400]]`.
- Holdings after the delete (`pf-04-after-delete.json`): `[[]]`. CSV build and accept: `frontend-gate-probe.run.log`, 3 passed. The on-disk CSV write through Tauri is R15-UI-009 (needs_gui).

## 4. ci-local: PASS

`fix-r1/ci-local.log`:
- Header: "ci-local run 1 at 5ff9be041180c1c316ad48ceb120a23549a7575a".
- Sidecar build: "[ensure-sidecar] building vysted-sidecar-aarch64-apple-darwin".
- Tests: "Tests 1849 passed (1849)" and "3649 passed, 1 skipped".
- Exit: "=== ci-local run 1 EXIT=0" and "=== ci-local run 2 EXIT=0".

## 5. smoke: PASS

`fix-r1/smoke.log`: "=== smoke at 5ff9be041180c1c316ad48ceb120a23549a7575a start" and "=== smoke EXIT=0".

## 6. Agent scenarios: FAIL (harness_environment)

- `scenarios/`: 7 `*-llama3.1-8b.jsonl` runs, each a single trial ending `{"kind":"done"}`, with no grading rows.
- Each of the 7 `*-openrouter.jsonl` runs is `{"kind":"skipped","reason":"no_key",…}`.

## 7. Owner-drives: FAIL (harness_environment)

- `surface/onboarding-stranger/rc1/round-3/` contains only `RC1-R3-ONBOARDING-STRANGER.md` and no raw output.
- Spot checks:
  - Screener. `verifier/spot-screener/08b-zero-result.json`: `"evaluated_count":49,"skipped_count":1,"result_count":0`. This matches the drive's `08-zero-result.json` (49/1/0).
  - Screener validation. 06 bogus universe returns 422, 07 limit 1001 returns 422, and 02 bad formula returns "unexpected character '%'" at position 22.
  - Failure-inducer. `verifier/spot-failure/data061-replay.txt`: `/quotes/ZZZZNOTREAL` → 404 `not_found`, identical to the drive's `data061-malformed-symbol.json`.
  - Onboarding. `verifier/spot-onboarding/onboarding-replay.txt`: resolve for "zomato" returns ETERNAL with `renamed_from ZOMATO`.

## 8. Fixed-name battery: FAIL (harness_environment)

`battery/INDEX.json` records `"sets": 75, "fixed_total": 392`. `battery/raw` contains only set-0 (12 files), set-1 (8) and set-2 (7), so 27 ids have raw output.

## 9. Data packs: PASS

- `battery/collected/` holds 24 files, each with `"complete": true`. Example: `P2_DAL.json` with `"manifest_name": "Dynamic Archistructures Ltd", "bse_code": "539681"`.
- `logs/rc1-datapack-collect.log` shows every call at 200. `grep -ciE 'error|traceback|refused'` returns 0.

## 10. Fix loop closed: PASS

- rc1-drive-composer-chat:1 is closed. `verifier/sample/composer-chat-1-recheck.txt` shows code `auth` and "No … API key is set — add it in Settings." for openai, groq, openrouter, deepseek and xai.
- rc1-drive-research-briefs:1: I concur with the Tier-4 deferral. It is the RESEARCH-043 class (DECISIONS_FOR_OPERATOR 4.14), recorded as rc1-verifier:9.

## 11. GUI round: DEFERRED (operator_attended)

The computer-use grant does not cover the built app. Needs a GUI: R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040.

## 12. Adversarial sample: FAIL (product_defect)

- **R15-DATA-005: own repro does not reproduce.** `verifier/sample/DATA-005-rerun.txt` shows VERTEX/JNPR/JUMBO/ONC book_value and price_to_book flagged, not ok.
- **R15-LEAD-026: own repro does not reproduce.** `verifier/sample/LEAD-026-rerun.txt`: `/history/ZZZZNOTREAL` → `"reason": "unknown_symbol"`.
- **Adjacent finding, new defect, HIGH (blocker).** `verifier/sample/DATA-005-adjacent-pb-vs-ps.txt`:
  - TSM: `price_to_book 92.1669 status ok` and `price_to_sales None status withheld reason Yahoo's price/sales … mixes bases: the listing trades in USD but reports its statements in TWD`.
  - Truth (`DATA-005-adjacent-truth.txt`): `2330.TW … 'priceToBook': 9.977827` and `HDFCBANK.NS … 'priceToBook': 1.8678916`.
  - Root cause, read at the candidate: `yfinance_provider.py:420` `_MIXED_BASIS_RATIOS = {"price_to_sales", "ev_to_ebitda"}`.
- Low adjacent findings: rc1-verifier:2 through :7 (see the sheet).
- gate8_refuted: false. Refuted entries: none.
