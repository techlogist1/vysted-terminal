# rc1 round-4 owner-drive: portfolio-notes

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (worktree
`rc1-round-4-cand`). Own sidecar `127.0.0.1:52324`, data dir
`rc1-round-4-data-rc1-drive-portfolio-notes` (`cp -R` of the round's seed profile,
keyless). Sleep-wrapper pid 71586 (its worker 71589 needed a direct kill too —
noted below); both confirmed dead, port unreachable, at end of run. No writes to
the candidate worktree; all raw evidence under
`docs/redesign/verification/r15/surface/portfolio-notes/rc1/round-4/`.

## Method

Same shape as round-3 (read first, not reused as evidence): portfolio holdings
are fully client-side (`src/store/portfolios.ts`, workspace-blob-owned); the
sidecar `/portfolio/positions` router is GET-only legacy-ledger-import. So
"drive every control" = (1) run the candidate's own real-component vitest
suites (`PortfolioPanel.test.tsx`, `metrics.test.ts`, `NotesPanel.test.tsx`,
`NotesToolbar.test.tsx`, `notes.test.ts`, `csv.test.ts`, `host-actions.test.ts`)
— these mount the REAL panels/editor and exercise the real store logic, the
same seams the census mocked (`fetchPositionQuotes`, `downloadCsv`); (2) curl
the sidecar's real routes (legacy ledger, live quotes) against my own isolated
sidecar; (3) two live end-to-end agent calls through the local model
(llama3.1:8b) against the real agent runtime + intent gate, one add (control)
and one delete (the census/round-3 regression check for the intent-gate fix).

## Scored table

| # | Drive | Result | Score | Raw file |
|---|---|---|---|---|
| 1 | Full portfolio+notes real-component suite (91 tests: empty/validation, live P&L/weight, unpriced-holding `totalValue: null` not fake 0, mixed-currency subtotals, crypto pricing/currency, delete/edit after portfolio switch, CSV export incl. Currency column + blank Weight%, notes store/editor race, scope-switch-in-debounce, Task List, slash menu incl. keyboard nav, wikilink wrap/round-trip/keyboard nav/post-mount watchlist pickup, toolbar Link popover) | 6 files, 91/91 passed | ok | `01-vitest-panels.txt` |
| 2 | `host-actions.test.ts` (add/update/delete resolution incl. by-id, ambiguous-lots refusal, unmatched-target honest null/never-guess, undo, negative-cost rejection, no-sidecar-ledger-call) | 1 file, 106/106 passed | ok | `02-vitest-host-actions.txt` |
| 3 | Sidecar legacy ledger: GET `/portfolio/positions` | `200 []` | ok | `03-sidecar-positions-get.txt` |
| 4 | Legacy ledger POST (write surface removed, not just gated) | `405 Method Not Allowed` | ok | `04-sidecar-positions-post-405.txt` |
| 5 | Legacy ledger PUT `/positions/1` | `404 Not Found` | ok | `05-sidecar-positions-put-404.txt` |
| 6 | Legacy ledger DELETE `/positions/1` | `404 Not Found` | ok | `06-sidecar-positions-delete-404.txt` |
| 7 | Live quote RELIANCE.NS | `₹1226.00`, `nse_direct`, 200 | ok | `07-quote-reliance.txt` |
| 8 | Live quote TCS.NS | `₹2082.00`, `nse_direct`, 200 | ok | `08-quote-tcs.txt` |
| 9 | Live quote BTC/USDT, no `asset_class` param | `502 provider_error` (falls through the equity chain: nse/nse/bse/yfinance, never reaches ccxt — **expected**: `asset_class` defaults to `"equity"` server-side, and only `"crypto"` routes to ccxt; my probe omitted the param the real panel always sends per `src/modules/portfolio/api.ts:82`) | ok (self-inflicted false negative, corrected by #9b, not a finding) | `09-quote-btcusdt.txt` |
| 9b | Live quote BTC/USDT with `?asset_class=crypto` (the shape the panel actually calls) | `$83,884.01`, `provider: ccxt:binance`, `market_state: open`, `freshness: live`, currency `USDT` — never ₹ | ok (R15-DATA-081 fix holds) | `09b-quote-btcusdt-assetclass.txt` |
| 10 | Sidecar intent-gate suite (`test_b3_runtime_intent_gate.py`) | 194/194 passed | ok (R15-AGENT-019 regression check holds) | `10-pytest-intent-gate.txt` |
| 11 | Agent (llama3.1:8b, live, autonomy=auto): "Add 10 INFY.NS at 1500 to my portfolio" | Correct `portfolio_add_position` tool_use, `ok:true`; narration says "awaiting review" under AUTO (known benign model-narration quirk, not re-raised — census/round-3) | ok | `11-agent-add-infy.jsonl` / `.stdout.txt` |
| 12 | Agent (llama3.1:8b, live, autonomy=auto): "Delete TCS from my portfolio" | Produced a `portfolio_delete_position` tool_use (**fixed vs. census, where this exact phrasing produced no tool_use at all** — R15-AGENT-019 holds). The model hallucinated `position_id: "<nil>"` with no `symbol` field (no `--context` was passed to this headless call, so it had no real holding to reference) and the sidecar-level `tool_result` said `ok:true` — this is the protocol-layer "proposal accepted" ack, not "resolved against real holdings": the actual resolve/apply function (`host-actions.ts:1879-1881`) fails closed on exactly this shape (`problem || !target → fail(problem)`, "never guess which position to mutate"), proven by drive #2's passing "an unmatched target is an honest null" case. Not a new defect — a model-hallucination artifact of the no-context headless lane, and the resolution path it would hit is separately proven honest. | ok (see note) | `12-agent-delete-tcs.jsonl` / `.stdout.txt` |
| 13 | CSV formula-injection cells (`=`,`+`,`-`,`@` written verbatim, unescaped) | Unchanged (code-read: `escapeCsvCell` only quotes on comma/quote/newline) — matches register `R15-UI-079` (open, low, not in this fix scope) | ok (known open, unchanged) | code-read: `src/lib/csv.ts:12-14` |
| 14 | `get_portfolio`/context-provider currency field on holdings | Unchanged (code-read: no `currency` field on the published snapshot) — matches register `R15-AGENT-091` (open, low, not in this fix scope) | ok (known open, unchanged) | code-read: `src/lib/context-provider.ts`, `src/store/portfolios.ts` |
| 15 | 100-position portfolio (tenth-item + overflow) | Not re-driven live — unchanged render-list code path since round-3's clean pass, and batch-27 (the only merge since round-3) touched fundamentals/resolver-pool code, not this path | NOT TESTED (unchanged) | — |
| 16 | Huge note (multi-MB) perf | Not re-driven — unchanged code path since round-3 | NOT TESTED (unchanged) | — |
| 17 | GUI-only (WKWebView CSV/.md save dialog, Tauri note-mirror atomic write, real drag/keyboard routing inside a live webview) | — | NEEDS-GUI | — |

## rc1-round-3 → round-4 deltas

No regression. All items round-3 marked `ok` still hold at this candidate
(batch-27, the only merge since round-3, touched `symbol_resolver.py` +
fundamentals withholding — nothing in the portfolio/notes surface). The one
new observation (#12's hallucinated `position_id`) is not a regression or a
fresh product defect: it is the local model inventing an argument when given
no context, against a resolve/apply path independently proven to fail closed.
No new real defect found this round.

## Spend

$0.00 — two local llama3.1:8b calls (61.7s + 40.6s), lock acquired/released
cleanly via `trap` each time, both within the 15-min budget on the first try.
No paid-lane calls needed.
