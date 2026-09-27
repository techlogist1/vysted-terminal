# batch-7/W5-agent-writes-portfolio (shard rc1-battery-9)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: source, `127.0.0.1:52355`,
data dir `rc1-round-5-recheck-data-rc1-battery-9`.

All 9 entries are frontend host-action / chat / portfolio-panel React+Zustand behavior
(`src/lib/host-actions.ts`, `src/modules/chat/ChatSidebar.tsx`,
`src/modules/portfolio/PortfolioPanel.tsx`). `host-actions.test.ts:1127` confirms writes
route only through the store, never a sidecar ledger call — so there is genuinely no
sidecar/curl leg for 8 of the 9. Battery role may not run vitest or drive a GUI. For each,
verified the certifying test file is real and git-committed at this sha (not a scratch
file) and read the pinned test body to confirm it still asserts the register's exact
repro shape. One entry (AGENT-044) has a curl-able backend half (the `/resolve` route the
frontend wraps), which was run live.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-041 | `git ls-files` + read `src/lib/host-actions.test.ts:1782,1808` | undo of an applied `portfolio_delete_position` and of an applied `write_note mode=replace` both restore the prior state exactly | ci_pinned: `host-actions.test.ts` — "an applied holding delete can be undone: the holding is back with its id (R15-AGENT-041)"; "an applied note replace can be undone: the prior text is restored (R15-AGENT-041)" |
| R15-AGENT-032 | `git ls-files` + read `src/modules/chat/ChatSidebar.test.tsx:769` | under AUTO a failing auto-apply writes `"Couldn't apply: Open Flux"`, never an `"Applied:"` line, and the change stays `pending` | ci_pinned: `ChatSidebar.test.tsx` — "under AUTO a failing auto-apply writes no 'Applied:' line, it says why (R15-AGENT-032)" |
| R15-UI-017 | `git ls-files` + read `src/modules/chat/ChatSidebar.test.tsx:609` | a send with no key: `messages` stays `[]` (no orphaned user turn), input keeps the typed prompt, "No API key for anthropic" shown | ci_pinned: `ChatSidebar.test.tsx` — "a send with no key leaves no orphaned user turn and keeps the prompt (R15-UI-017)" |
| R15-AGENT-043 | `git ls-files` + read `src/lib/host-actions.test.ts:339` | the same 3-criteria fixture as the register: `"Wrote 2 of 3 screener criteria; dropped roe: value must be a number — review and Run"`, `ack.dropped == ["roe: value must be a number"]` | ci_pinned: `host-actions.test.ts` — "write_screener_filters says which malformed criterion it dropped, in label and ack (R15-AGENT-043)" |
| R15-AGENT-044 | live `GET /resolve?q=...` for the register's exact three names | `"MAZAGON DOCK"` → resolved `MAZDOCK` (Mazagon Dock Shipbuilders Ltd); `"MAZAGONDOCK"` → `ok:false`, "No instrument matched 'MAZAGONDOCK'.", `resolved:null`; `"Cochin Shipyard"` → resolved `COCHINSHIP` | holds (live backend repro matches batch-7's cited values exactly); frontend wrapper additionally pinned by `host-actions.test.ts:201` "add_to_watchlist resolves a company name or fails with candidates, never a blank row (R15-AGENT-044)" |
| R15-UI-034 | `git ls-files` + read `PortfolioPanel.test.tsx:394-474` | edit RELIANCE, switch portfolio, Save → "are required"/no-op guard fires; a holding removed mid-edit on Save → "That holding is no longer in this portfolio — nothing was saved", quantity input keeps typed value, holdings unchanged | ci_pinned: `PortfolioPanel.test.tsx` — "an edit ends when the portfolio switches; Save then writes nothing silently (R15-UI-034)"; "Save on a holding removed mid-edit says nothing was saved (R15-UI-034)" |
| R15-UI-035 | `git ls-files` + read `PortfolioPanel.test.tsx:430-454` | delete on a portfolio switched to after mount removes the correct holding, leaves the other portfolio's holdings untouched | ci_pinned: `PortfolioPanel.test.tsx` — "Delete works in a portfolio switched to after mount (R15-UI-035)" |
| R15-UI-036 | `git ls-files` + read `PortfolioPanel.test.tsx:213-240` | totals `title` reads "Oldest quote in these totals: 2026-05-15T14:00:00Z"; a fake-timer 5s advance triggers exactly one more `fetchQuotes` call | ci_pinned: `PortfolioPanel.test.tsx` — "refreshes quotes on the Watchlist interval and dates the totals by the oldest quote (R15-UI-036)" |
| R15-UI-037 | `git ls-files` + read `PortfolioPanel.test.tsx:93-102` | label reads "Avg cost / share", input placeholder "per share", no "Cost basis" text anywhere, column header "Avg cost" | ci_pinned: `PortfolioPanel.test.tsx` — "the cost input and column say per share (R15-UI-037)" |

Raw: `battery/raw/set-29/R15-AGENT-041.txt`, `R15-AGENT-032.txt`, `R15-UI-017.txt`,
`R15-AGENT-043.txt`, `R15-AGENT-044-mazagon-dock.json`, `R15-AGENT-044-mazagondock.json`,
`R15-AGENT-044-cochin-shipyard.json`, `R15-UI-034.txt`, `R15-UI-035.txt`, `R15-UI-036.txt`,
`R15-UI-037.txt`.

COVERAGE: 9/9 ids raw; no raw: none.
