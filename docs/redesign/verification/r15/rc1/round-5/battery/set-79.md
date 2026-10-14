# set-79 — batch-28/W6-sonnet (rc1-battery-20)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Batch-28 certified these 7 entries via
scratch `B28V_*` vitest files that were deleted after certification (VERDICTS.md: "All were
deleted afterwards"). Since certification, permanent pinned tests citing the same register ids
now exist in the repo's own test tree (`src/**/*.test.ts(x)`, `sidecar/tests/`). Per the harness
rule, vitest/pytest suites are not executed here; each verdict is `ci_pinned` naming the
now-permanent test(s), confirmed by reading the test source at the candidate sha (raw files
under `battery/raw/set-79/`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-053 | Read `src/modules/chat/context-provider.test.ts`. | `describe("captureTerminalState — otherPanels generic summary (R15-AGENT-053)")`: `it("inlines a headline so the agent sees actual news content, not an opaque id (R15-AGENT-053)")` and the backtest/news generic-summary test pin panels beyond chart/watchlist/portfolio now publishing. | ci_pinned |
| R15-AGENT-055 | Read `src/lib/layout-templates.test.ts`. | `describe("one plan per template id (R15-AGENT-055)")`: menu-mode ids are disjoint from agent template ids; every native-menu payload maps to exactly one mode plan. | ci_pinned |
| R15-AGENT-096 | Read `src/lib/host-actions.test.ts`, `src/store/screener.test.ts`. | `describe("write_screener_filters / save_screen: a flat group's leaves are what actually runs (R15-AGENT-096)")` and the matching `screener.test.ts` case pin `runScreener` sending the group's leaves, not the stale flat list. | ci_pinned |
| R15-CODE-FRONTEND-017 | Read `src/store/sec.test.ts`. | `it("a slower response for the previous symbol never overwrites the newer one (R15-CODE-FRONTEND-017)")` and `it("I1: a late rejection for a previous issuer does not paint its error over the current one (R15-CODE-FRONTEND-017)")`. | ci_pinned |
| R15-CODE-PLATFORM-017 | Read `sidecar/tests/test_code_node.py` + `src/modules/node-editor/code-node-run.test.ts`. | Sidecar side: `test_round_half_away_from_zero_not_bankers_rounding` (round(2.5)==3), `test_unregistered_function_is_disallowed_syntax_not_a_value` (log(x,10) raises "disallowed syntax: Call"), ternary tests. Frontend side: `describe("validateWorkflow (R15-CODE-PLATFORM-017)")` pins the editor deferring to the sidecar (mathjs no longer used for preview). | ci_pinned |
| R15-UI-015 | Read `src/lib/use-sidecar-retry.test.ts`, `NewsFeedPanel.test.tsx`, `SecFilingsPanel.test.tsx`, `EarningsCalendarPanel.test.tsx`. | `describe("useRetryOnSidecarReady (R15-UI-015)")` plus panel-level tests each asserting a deterministic 502/error settles after ONE attempt (no 13x retry storm). | ci_pinned |
| R15-UI-021 | Read `src/modules/chart/ChartPanel.test.tsx`. | 5 tests tagged R15-UI-021: Backspace in a field outside the chart keeps the drawing selected; a locked drawing survives Delete; Delete-with-nothing-focused; a body-targeted Delete only removes the chart whose selection was not cleared by an outside pointerdown. | ci_pinned |

Note (not a regression, carried from batch-28's own "Issues noticed"): AGENT-053's
`focusedArticleId`-hovered path still truncates a long headline inside the 200-char summary cap
and drops `topHeadline` — this residual was already disclosed at certification and is unchanged
here (no new raw probe needed to confirm a known, already-disclosed residual).

COVERAGE: 7/7 ids raw; no raw: none.
