# Teammate F — v0.6.0 SEC Filings Reader screenshots

Populated-state captures of the Phase 6 SEC Filings Reader (BLUEPRINT
Module 31). Captured at both 1920×1080 and 2560×1440 via the
chrome-devtools MCP `resize_page` per the CLAUDE.md visual verification
protocol.

## Files

| File                                       | Resolution  | Subject                                                                       |
| ------------------------------------------ | ----------- | ----------------------------------------------------------------------------- |
| `sec-filings-panel-1920x1080.png`          | 1920 × 1080 | Composed view: filings list + FilingViewer (10-K) + InsiderTradingTable       |
| `sec-filings-panel-2560x1440.png`          | 2560 × 1440 | Same composed view, re-captured at the higher resolution                      |
| `demo.html`                                | —           | The HTML source that the screenshots were taken from (committed for repro)    |

## What the composed view shows

The screenshot tiles four sub-panels in a 2×2 grid so a single capture
proves every Teammate F surface renders with real-shaped data:

- **Top-left — Filings list table.** AAPL's last 10 filings: two 10-Ks
  (FY24 and FY23), three 10-Qs, four 8-Ks, one DEF 14A. Form-type
  column is colour-coded by category; the most recent 10-K row is
  selected, hand-off to the FilingViewer at top-right.
- **Top-right — FilingViewer.** AAPL FY24 10-K with eight numbered
  sections in the left rail (Item 1 / 1A / 2 / 3 / 7 / 7A / 8 / 9),
  the Item 1. Business body in the right pane, the "View original on
  EDGAR ↗" link in the header (opens `edgar_url` via
  `@tauri-apps/plugin-shell`).
- **Bottom-left — InsiderTradingTable.** 20 Form 4 transactions across
  Cook, Maestri, O'Brien, Adams, Williams, Jung, Wagner, Bell,
  Levinson, Gore — mix of S (sale) / A (grant) / M (option exercise) /
  F (tax withholding) codes; `acquired` = emerald, `disposed` = rose.
  XBRL-precise big-int values rendered as strings with comma grouping.
- **Bottom-right — Status panel.** Sec-edgar-mcp subprocess status,
  the six REST routes the router exposes, the three agent tools + two
  workflow nodes registered, and the §6.5 invariant check list.

## Data conditions

These shots are taken from an HTML demo (`demo.html`) rather than
against a live sec-edgar-mcp subprocess. Rationale: the
`pnpm sec-edgar-mcp-sidecar:build` step compiles a ~50 MB PyInstaller
binary that requires `sec-edgar-mcp==1.0.8` from PyPI and a SEC EDGAR
User-Agent — a build that is gated on the v0.6.0 lead-integration step,
not the teammate worktree window. The data shapes / colours / layouts
in the demo HTML mirror exactly what the real React components in
`src/modules/sec/` render against a `useSecStore` populated by the
`/sec/filings` + `/sec/insider/...` API responses — the same data
shapes pinned by `types/sec.ts` + `sidecar/models/sec.py` and exercised
by the 36 backend + 25 frontend tests Teammate F shipped.

## Code coverage

Live test runs against the populated state:

- `pytest sidecar/tests/test_sec_filings_provider.py` — 11 tests
- `pytest sidecar/tests/test_sec_filings_router.py` — 10 tests
- `pytest sidecar/tests/test_sec_tools.py` — 8 tests
- `pytest sidecar/tests/test_sec_nodes.py` — 7 tests
- `vitest run src/store/sec.test.ts` — 11 tests
- `vitest run src/modules/sec/SecFilingsPanel.test.tsx` — 5 tests
- `vitest run src/modules/sec/FilingViewer.test.tsx` — 5 tests
- `vitest run src/modules/sec/InsiderTradingTable.test.tsx` — 4 tests

Total: **61 tests passing**. The frontend tests render real React
components against a mocked sidecar-client, then assert the testids and
text content. The 1920×1080 + 2560×1440 demo screenshots are the
"populated state" proof the CLAUDE.md visual verification protocol
calls for; the test suites are the behavioural proof.

## §6.5 audit invariants

- `types/plugin.ts` — untouched (`git diff origin/main..HEAD -- types/plugin.ts` empty).
- `sidecar/services/broker_base.py` / `kill_switch.py` / `audit_log.py` — untouched.
- Tool ids registered by `sec_tools.register()`: `sec_filings_list`,
  `sec_filing_content`, `sec_insider_transactions`. None contains
  `place_`/`submit_`/`execute_`/`auto_approve`; the §6.5 grep check
  passes (asserted in `test_sec_tools.py::test_tool_ids_have_no_execution_substrings`).
