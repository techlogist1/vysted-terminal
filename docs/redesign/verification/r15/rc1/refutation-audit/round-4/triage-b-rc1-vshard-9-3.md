# triage-b — rc1-vshard-9:3 (tie R15-AGENT-053)

Audited 07:33 IST at HEAD bed3b166. The code tree equals 01015033. The fix round touched no frontend file. node_modules is slightly stale: the installed lock lacks only the direct `@tiptap/extension-list` specifier, which is unrelated to the files under test.

## Claim (shard 9)
The tie's acceptance, "open Backtest and News → snapshot carries their run id/headlines", fails on the headlines. News publishes only `{watchedSymbols, focusedArticleId}`. `genericPanelSummary` collapses arrays to a count, and the preamble never renders otherPanels.

## Code at HEAD
- `src/modules/news/NewsFeedPanel.tsx:206-219` publishes `payload: { watchedSymbols: newsSymbols, focusedArticleId }`. No headline, title or summary is published. The comment at :197-199 promises that "the chat sidebar can mention the focused headline in the agent's preamble".
- `focusedArticleId` is `item.id` (:123-124, :344). The sidecar mints that id as a sha1 of url+title (`sidecar/services/news_provider.py:138`). It is opaque, and no tool resolves it back to a headline.
- `src/modules/chat/context-provider.ts:265-289` `genericPanelSummary`: arrays become `N items` (:272-273), and the result is capped at 200 chars (:256). `captureTerminalState` (:370-383) puts that line in `otherPanels`.
- `sidecar/services/agent_runtime.py:404-481` `_render_terminal_preamble` does not render `otherPanels`. **By design**: the docstring reads "Detail ... is pulled on demand via the get_terminal_state tool — this stays terse". `_terminal_state` (:1676-1677) returns the whole `__terminal__` state, otherPanels included. The shard's third sub-claim is therefore not a defect on its own. The content gap is.

## Repro at HEAD
1. Frontend (vitest, scratch config `triage-b-raw/vt/vitest.config.mts` with root = repo and cacheDir = scratch). The test publishes exactly NewsFeedPanel's payload shape and reads `captureTerminalState()`.
   Command: `node_modules/.bin/vitest run --config docs/redesign/verification/r15/rc1/refutation-audit/round-4/triage-b-raw/vt/vitest.config.mts --reporter=verbose --silent=false`
```
5:NEWS otherPanels entry: {"source":"news","summary":"watchedSymbols=2 items, focusedArticleId=3f1c2a9d0b7e4c55a8e1d2f3b4c5d6e7f8091a2b"}
6:FULL snapshot keys: focusedPanel,focusedSymbol,charts,watchlist,portfolio,brief,otherPanels,openPanels,region,capturedAt
10: Test Files  1 passed (1)
11:      Tests  1 passed (1)
```
   The agent's whole view of an open News panel is "watchedSymbols=2 items, focusedArticleId=<sha1>". It gets no headline and not even the symbol names.
2. Sidecar (in-process `_build_context_preamble` with that otherPanels entry):
```
PREAMBLE:
## What the user is looking at
Focused panel: news.
Open panels: news.
```
   The `get_terminal_state` tool returns the same summary line. Nothing anywhere carries a headline.

## Duplicate search
I scanned the register for otherPanels, genericPanelSummary, panel-context, context-provider and headline+snapshot. The only hits are AGENT-053 itself and focus-id / portfolio entries (AGENT-042/051/052, CODE-FRONTEND-015, AGENT-091), which are different defects.

## Classification: partial on R15-AGENT-053
The entry's stated mechanism is fixed: payloads are no longer dropped, the generic summary exists, the backtest run id is carried, and the chips are buttons, as the shard confirmed. Its stated acceptance, "snapshot carries their run id/**headlines**", and its repro, "open ... News ... then ask the copilot about what is on screen", do not hold for News. That is a stated part of the tie's own class (`context-bus-coverage`).

## Severity: medium (unchanged)
A stated feature is degraded: the agent can't say what is on the news screen. The workaround is that the user names the headline or the agent fetches news itself.

## Certification failures
The baseline for R15-AGENT-053 is 1, from the latest note clause "certification failures so far: 1" (rc1 round-2 partial). This partial adds 1, for a total of 2.
