# rc1 round-3 owner-drive: portfolio-notes

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52324`,
data dir `rc1-round-3-data-rc1-drive-portfolio-notes` (copy of the round's seed profile).
Sleep pid holding stdin: 86801 (killed at end of run). No writes to the candidate worktree.

## Method

Portfolio holdings moved fully client-side since the census (`src/store/portfolios.ts`,
workspace-blob-owned; the sidecar `/portfolio/positions` router is now GET-only,
`routers/portfolio.py`). CRUD/P&L/CSV/risk logic therefore lives in the panel component, not
a sidecar route — so the equivalent of "drive every control at the API level" is: (1) run the
candidate's own real-component vitest suites (the census used exactly this method — a jsdom
harness mounting the real `PortfolioPanel`/`NotesPanel`; the candidate now ships that same kind
of test inside `src/`, so re-running it IS re-driving the real component against real store
logic, not a tautology — the mocks are confined to `fetchPositionQuotes`/`fetchDailyCloses`/
`downloadCsv`, exactly the seams the census mocked); (2) confirm the sidecar's actual surface
(quotes, legacy ledger) live with curl against my own isolated sidecar; (3) one live end-to-end
agent call through the local model against the real agent runtime + intent gate + host-action
apply, the same shape as census's A2.

## Scored table

| Drive | Result | Score | Evidence |
|---|---|---|---|
| Portfolio empty/validation | EmptyState + CTA; blank/0/-3/'abc' qty-cost rejected | ok | vitest-panels.log |
| P&L / weight from live quote | Computed correctly against mocked known prices; formula unit-covered | ok | vitest-panels.log |
| Unpriced holding | Publishes `totalValue: null` + note, never a fake ₹0 (R15-UI-005 fix holds — census's `SURF-PORTFOLIO-NOTES-1` regression check) | ok | vitest-panels.log |
| Crypto BTC/USDT pricing | Priced as crypto, shown in USDT not ₹ (R15-DATA-081 fix holds — census `SURF-PORTFOLIO-NOTES-2`) | ok | vitest-panels.log |
| Mixed-currency portfolio | Per-currency subtotals, null published total | ok | vitest-panels.log |
| Delete/edit in a portfolio not active at mount | Both work now (R15-UI-034/R15-UI-035 fix holds — census `SURF-PORTFOLIO-NOTES-3`) | ok | vitest-panels.log |
| Quote refresh cadence + staleness cue | Refreshes on interval, skips overlapping fan-out, dates by oldest quote, EOD staleness cue shown | ok | vitest-panels.log |
| CSV export | Live-quote P&L in cells; mixed-currency gets a Currency column + blank Weight% (R15-DATA-042 fix holds) | ok | vitest-panels.log |
| CSV formula-injection cells (`=`,`+`,`-`,`@`) | Still written verbatim, unescaped — matches register's `R15-UI-079` (open, low, not in this fix scope) | ok (known open, unchanged) | src/lib/csv.ts:12-14 (code read) |
| Risk analytics (Sharpe/Sortino/Calmar/VaR/beta/correlation) | Loading state, insufficient-history honest message, correct render with history | ok | vitest-panels.log |
| Open-panel snapshot ids for agent disambiguation | Publishes each holding's id (R15-AGENT-042 fix holds — census `SURF-PORTFOLIO-NOTES-4`) | ok | vitest-panels.log, host-actions log |
| Sidecar legacy ledger route shape | GET 200 `[]`; POST 405; PUT/DELETE 404 — write surface is gone, not just gated (R15-CODE-PLATFORM-021/022 fix holds) | ok | sidecar-portfolio-routes.txt |
| Live /quotes real data | RELIANCE.NS ₹1226.00, TCS.NS ₹2082.00, both EOD/nse_direct, 200 | ok | sidecar-portfolio-routes.txt |
| Agent `portfolio_add_position` (local llama3.1:8b, live) | Correct tool_use (INFY.NS qty10 cost1500 purchased_at today), ok:true ack, narration honestly says "pending confirmation" (autonomy=auto; AUTO auto-apply per R15-AGENT-080 is the store-level behaviour, narration is a separate known-benign model-text quirk per census, not re-raised) | ok | agent-add-infy.log, agent-context.json |
| Host-action apply: add/update/delete-by-id, negative cost rejected, describe/apply parity, undo | All pass live against the real `host-actions.ts` (R15-CODE-FRONTEND-011/012, R15-DATA-088, R15-AGENT-041/042 fixes hold) | ok | vitest-host-actions.log |
| Intent gate: portfolio/note write phrasings no longer misclassified as read | 194/194 pass (R15-AGENT-019 fix holds — census `30-intent-gate-portfolio-notes.txt` regression) | ok | pytest-intent-gate.log |
| Notes: agent `write_note` append vs. editor keystroke race | Store authoritative, editor keystroke doesn't clobber the agent's append (R15-UI-001 fix holds — census `20-notes-panel-replay.json` N2 regression) | ok | vitest-panels.log |
| Notes: scope switch inside the debounce window | Each scope keeps its own text (previous drift bug fixed) | ok | vitest-panels.log |
| Notes: slash-menu row height | No longer a fixed clipping h-8 (R15-UI-050 fix holds) | ok | vitest-panels.log |
| Notes: Task List extension | Toggles, no longer throws (R15-UI-024 fix holds — census N5) | ok | vitest-panels.log |
| Notes: wikilink picker sees post-mount watchlist additions | Fixed (was frozen-at-mount, census `SURF-PORTFOLIO-NOTES-8`) | ok | vitest-panels.log |
| Notes toolbar: Link button | Inline popover + applies mark, never `window.prompt` (R15-UI-025's popover half fixed; the desktop `window.prompt`-absence itself is a WKWebView fact, NEEDS-GUI to see the popover render) | ok / NEEDS-GUI (render) | vitest-panels.log |
| Notes toolbar: Insert [[wikilink]] | WRAPS the selection instead of deleting it (was: deletes it, census toolbar row) | ok | vitest-panels.log |
| Notes: injection-shaped content (`<img onerror>`, `<script>`, `javascript:` href) | Not driven fresh this round — census already proved this sanitized (`N4`) and nothing downstream reads notes into the agent context; no code change touched sanitization this round (git log on notes/Tiptap config empty since census) | NOT TESTED (unchanged, low risk, ~$0 to redo) | code-read only |
| 100-position portfolio (tenth-item + overflow) | Not re-driven live this round (no code change to the render-list path since census's `P8` passed at 100/100); relying on unchanged-since-census + the general holdings-array render logic covered by the passing suite | NOT TESTED (unchanged) | — |
| Huge note (multi-MB) perf | Not re-driven; unchanged code path since census `N3` | NOT TESTED (unchanged) | — |
| GUI-only (drag reorder, WKWebView CSV/.md save dialog, Tauri note-mirror write, slash/wikilink keyboard nav inside a real webview) | — | NEEDS-GUI | — |

## Census -> rc1 deltas

All 8 census raw findings (`SURF-PORTFOLIO-NOTES-1..8`) reproduce as FIXED at this candidate,
each cross-checked against a live-mounted real-component test or (routes) a live curl. No
census-ok item regressed. No new real defect found. The known-open low-severity items
(`R15-UI-079` CSV formula injection, `R15-UI-025`'s WKWebView `window.prompt` absence as
NEEDS-GUI) are unchanged, consistent with the register's own status for them.

## Not driven (budget / unchanged-since-census)

Prompt-injection note content, 100-position render, and huge-note perf were not re-driven live
this round — the code paths involved are unchanged since the census proved them, and re-driving
would not have added new information for the ~10-15 min it would cost. All three are `NOT
TESTED` in `COVERAGE.json`'s sibling drives, not silently skipped.

## Spend

$0.00 — one local llama3.1:8b call (58.5s, in=2907/out=41 tokens), lock held then released
cleanly via trap. No paid-lane calls needed.
