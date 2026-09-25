# batch-6/W5-host-actions-portfolio

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-FRONTEND-011 + R15-CODE-FRONTEND-007 | Source check: `host-actions.ts` `parseHostAction` | one `parseHostAction(name, input): HostIntent` parse at enqueue, bound `{portfolioId, holding}` for portfolio intents, apply fails honestly ("no longer in the portfolio") if the bound target moved by accept time | holds (source-confirmed) |
| R15-CODE-FRONTEND-009 + R15-CODE-FRONTEND-010 | Source check: `host-actions.ts` `save_screen`/`write_screener_filters` cases | `save_screen` writes the agent's recipe into the draft then calls the real `saveScreen(screenName)` (no duck-typed cast); `write_screener_filters` explicitly chains `runScreener()` on `run:true` (no ignored cast) | holds (source-confirmed) |
| R15-AGENT-043 | Source check: `host-actions.ts` `parseScreenerCriterion`/`keepLeaf` | a rejected leaf returns its drop reason (`ScreenerCriterion \| string`) instead of silently vanishing; `dropped: string[]` accumulates the reasons for the label/ack detail | holds (source-confirmed) |
| R15-AGENT-042 | Source check: `PortfolioPanel.tsx` holdings publish, `host-actions.ts` `resolveHolding` | `id: holdings[i]?.id` published per row (open-panel path now carries ids too); an ambiguous same-symbol match refuses and names the candidate lots instead of picking the first | holds (source-confirmed) |
| R15-AGENT-041 | Source check: `host-actions.ts` `ApplyResult.preImage`, `undoPreImage` | every data-write intent's apply captures a typed pre-image ("as it stands now, not as staged, so Undo restores exactly it"); `undoPreImage` restores it and refuses honestly if the target moved again before Undo | holds (source-confirmed; no live browser this shard for the review-panel Undo button) |
| R15-AGENT-032 | Source check: `store/proposed-changes.ts` `ChangeOutcome`, `ChatSidebar.tsx` `changeOutcomeLine` | `enqueue`/`accept` resolve to a typed `"applied" \| "staged" \| "failed"`; both transcript call sites (direct enqueue path + slash-command path) write the line off that resolved value — a `"failed"` outcome never gets an "Applied:" line | holds (source-confirmed) |
| R15-DATA-088 | Source check: `portfolios.ts` `normalizeHolding` | drops any row with a non-finite/`<=0` quantity or a non-finite/`<0` cost basis (0 cost still allowed); no coercion-to-0 remains | holds (source-confirmed) |
| R15-CODE-FRONTEND-012 + R15-DATA-089 + R15-CODE-PLATFORM-021 + R15-CODE-PLATFORM-022 | Live against candidate `:52344`: `GET/POST/PUT/DELETE /portfolio/positions[/1]` | `GET` 200 `[]`; `POST` 405 Method Not Allowed; `PUT`/`DELETE` 404 (no sub-route at all) — GET-only surface confirmed live. Source: `routers/portfolio.py` has exactly one route (`GET /positions`); `host-actions.ts` has zero references to `syncPositionToSidecar`/`sidecarPositionId`/`portfolioUrl`/`positionBody`; `portfolios.ts` has zero references to the old `addPosition`/`updatePosition`/`deletePosition`/`refresh` client | holds (live + source confirmed) |

No regressions found in this writer set.

Raw output: `docs/redesign/verification/r15/rc1/battery/raw/set-22/*`.
