# Final-pass owner-drive: portfolio-notes

Head under test: `d38b5d1a2487bd52fe8a7e741a3a5266e3206611` (scratch worktree `final-cand`, read-only).
Own sidecar: `127.0.0.1:52844`, booted from `final-cand/sidecar` source on a copy of `final-seed-data`
(`final-data-final-drive-portfolio-notes`), MCPs on the shared :52801/:52802. Reads that needed no write went to the shared :52800.
Method: the census/rc1 route. The real `PortfolioPanel`, `NotesPanel` and `NotesToolbar` are mounted in a scratch jsdom vitest harness
(config root = final-cand, jsdom url `http://localhost:5173`, never committed; copies under
`surface/portfolio-notes/final/harness/`). They drive the real stores and host actions against my own sidecar. Direct HTTP probes cover the routes, and
`scripts/r15/vy.py` (a scratch copy that only admits port 52844, as the composer and screener lanes did) covers live agent turns on
llama3.1:8b under the Ollama lock. Evidence: `docs/redesign/verification/r15/surface/portfolio-notes/final/`.

What changed on this surface since rc1 round 2 (`4c6dfe8c`): 12 files. The fixes landing in this group were R15-UI-079 (CSV formula guard),
R15-UI-078 (one validateHolding), R15-AGENT-091 (holding currency), R15-CROSS-PLATFORM-006 (note filenames),
R15-CODE-PLATFORM-050/051/052, R15-DOCS-010 (toolbar active fill) and R15-CODE-FRONTEND-024. Outside the group, R15-LIFECYCLE-027
(`f1182138`) gave every `sidecarRequest` a default 30 s budget, and that budget turns out to bite this group (P8).

## Scored table

| # | Interaction | Census | RC1 | Final (d38b5d1a) | Evidence line | Register id |
|---|---|---|---|---|---|---|
| P1 | Empty portfolio | ok | ok | ok | "This portfolio is empty … Add your first holding"; Export disabled; 0 requests (10-…replay.json P1-empty) | - |
| P2 | Form validation | partial | partial | **partial** | blank cost -> "Avg cost per share is required", 1e20 -> "Quantity is too large", "1,000" -> "must be a plain number" (all fixed); **"   " cost saves [TCS.NS,5,0]; "0x10" qty saves 16** (P2-validation) | R15-UI-078 -> drive-portfolio-notes:4 |
| P3 | INR P&L math vs independent quotes | partial | ok | **partial** | Warm: P7 after Retry: RELIANCE 10 @ 1200, price 1167.70 -> MV ₹11,677.00, P&L -₹323.00 (-2.69%), which matches 10x1167.7. Cold 2-holding first open: both quotes passed 30 s -> "Couldn't refresh live quotes" (P3-inr) | drive-portfolio-notes:1 |
| P4 | Delete/edit in a portfolio created after mount | broken | ok | ok | single click arms only ([TCS,INFY] kept), confirm deletes INFY; edit qty 7 saved; switch mid-edit resets the form, nothing written to the wrong portfolio (R15-UI-034 holds); delete in the first portfolio works (P4-delete-edit) | R15-UI-035, R15-UI-034 |
| P4c | Header: rename / blank rename / create / delete / delete last | (not driven) | (not driven) | ok | "  Core  " -> "Core"; blank rename ignored; create "Spec" active; delete needs confirm; deleting the last leaves a fresh "Portfolio" (P4c-header) | R15-UI-018 |
| P5 | Unresolved-only holding | partial | partial | **partial** | "Market value: — (no live quotes)", no ₹0 (UI-005 holds); **a 404 symbol raises "Couldn't refresh live quotes … Retry"** (P5-unresolved-crypto) | drive-portfolio-notes:3 |
| P5b | Crypto BTC/USDT and BTCUSDT | ok | ok | ok | BTC/USDT 0.5 @ 60,000 USDT -> price 84,616.03 USDT, P&L +12,308.02 USDT (+41.03%); BTCUSDT shown in $ | R15-DATA-081 |
| P6 | Mixed-currency + CSV export | partial | partial | ok | per-currency totals, "mixed currencies — totals per currency", Weight blank; CSV has Currency column; notes `=HYPERLINK…`, `@SUM`, `+cmd…`, `-2+3` exported as `'=…`, `'@…`, `'+…`, `'-…`; numeric -323 left unprefixed; "Saved <path>" status shown (P6-mixed-csv) | R15-DATA-042, R15-UI-079 (fixed, holds) |
| P7 | Quote transport failure (induced) + Retry | broken | ok | ok | banner + Retry render; Retry after recovery fills the row (P7-quotes-down) | R15-UI-004 |
| P8 | 100-holding portfolio | ok (100x200, slow) | ok (round 2 guard) | **broken** | rows render (tenth HINDUNILVR.NS, last row present, "Big · 100"), but **77/100 quote GETs abort at 30.0 s**; cold set: **0/100 resolve across 5+ fan-outs in 210 s**; the same sidecar's RELIANCE quote then times out at 25-40 s while :52800 answers in 1 ms (12-, 13-, 14-) | drive-portfolio-notes:1 (regression of rc1-drive-portfolio-notes:1, which was never register-tracked) |
| P9 | Agent host actions (store path) | broken | ok | ok | symbol-only update on a 2-lot symbol refuses and names both position_ids; update by id applied "Updated TCS.NS: ×21 @ ₹3,900", note kept; negative/blank/missing cost, boolean qty, 1e20 qty all refused (null); add/delete by symbol ok; unknown id refused (P9-agent) | R15-AGENT-042, R15-DATA-088 |
| P9b | get_portfolio currency, panel open | n/a | n/a | ok | AAPL currency "USD", INR names "INR" (P9-agent.openPanelSnapshot) | R15-AGENT-091 |
| P9c | get_portfolio currency, panel closed | n/a | n/a | **broken** | store fallback: AAPL {costBasis:190, currency:"INR"}; live llama turn answers "AAPL - 2 shares, cost basis ₹190" (A1-…stdout.txt) | R15-AGENT-091 -> drive-portfolio-notes:2 |
| sidecar | /portfolio/positions routes | partial | GET-only | ok | shared and own GET 200 `[]`; POST 405; PUT/DELETE 404; no order or broker path in openapi (11-portfolio-routes-http.jsonl) | R15-CODE-PLATFORM-021 |
| legacy | Read-once legacy import | n/a | n/a | ok | fetchLegacyPositions() on the seed ledger -> [] (P9-agent.legacyImport) | R15-LIFECYCLE-009 |
| N1 | Note lifecycle (type, clear, fast scope switch) | broken | ok | ok | clear persists ""; "fast-edit" lands in RELIANCE after a switch inside the debounce (N1-lifecycle) | R15-UI-001 |
| N2 | Agent write_note: append into open scope, keystroke, scope/mode | broken | ok | ok | append survives the next keystroke; global/general -> General; mode-less appends; replace writes TCS; whitespace text refused (N2-agent-write) | R15-UI-001, R15-CODE-FRONTEND-003/014 |
| N3 | Huge note (1.97M chars) + workspace round trip | ok | ok | ok | load 1.9 s, keystroke 192 ms, POST /workspace 200, GET 200, DELETE 204 (N3-huge) | - |
| N4 | Injection-shaped note: render | ok | ok | ok | 0 img, 0 script, 0 onerror, javascript: href stripped, no globals set (N4-injection) | - |
| N4b | Injection-shaped note: agent read (AUTO) | n/a | n/a | ok | llama read_notes(global) then a one-line summary; no write tool call emitted (A3-…stdout.txt). Under AUTO only panel/chart/watchlist auto-apply anyway (types/proposed-change.ts:38-42) | R15-AGENT-021 |
| N5 | Slash menu (10 items) + filter | partial | ok | ok | all 10 apply incl. Task List and Table; "/tab" filters to Table (N5-menus) | R15-UI-024 |
| N5b | Wikilink menu + live-added symbol | broken | ok | ok | `[[RELIANCE.NS]]` node, md "see [[RELIANCE.NS]]"; TCS.NS added after mount appears (N5-menus) | R15-UI-024 |
| N6 | Export .md outside Tauri + filename sanitiser | partial | ok | ok | Blob fallback fires "CON_.md", status "Downloaded .md"; safeFilename: CON->CON_, A:B?->A_B_, BTC/USDT->BTC_USDT, NUL.NS->NUL.NS_ (N6-export) | R15-CROSS-PLATFORM-006 |
| T1 | Toolbar H1-3/bold/italic/code/lists/task/quote/code block | ok | ok | ok | each applies; aria-pressed "true" + bg-charcoal-800 fill (T1-toolbar) | R15-DOCS-010 |
| T1b | Toolbar link popover | broken | ok | ok | popover applies https link (rel noopener nofollow); `javascript:alert(1)` refused, no link (T1-toolbar) | R15-UI-025 |
| T1c | Toolbar Insert [[wikilink]] on selection | broken | ok | ok | `[[ALPHA]]` wikilink node, rest of text kept | R15-UI-024 |
| GUI | Native save dialog / real file write of CSV and .md export; PNG/PDF note export; pixel layout of the holdings drop ladder | - | - | NEEDS-GUI | the Tauri `saveTextArtifact` path and real rendering need the app window (the harness mocks the write; the browser fallback is what jsdom reaches) | R15-UI-009 (fixed), R15-UI-083 (listed needs_gui) |

## Census -> final deltas

**Earlier ok, now not ok:**
- **P8 / P3 (drive-portfolio-notes:1, high, regression).** Census got 100/100 quotes (slow), and rc1 round 2 fixed the overlapping fan-out
  backlog with `quoteFetchInFlightRef`. R15-LIFECYCLE-027 (`f1182138`, after rc1) put a default 30 s budget on every `sidecarRequest`,
  including `GET /quotes/{symbol}`. Any portfolio with more than about 25 cold Indian holdings (nse_direct serializes at about 1 req/s) now
  aborts most requests at 30 s. The guard releases at the abort while the sidecar keeps working. The next 5 s tick re-requests all 100
  symbols, so the server backlog grows by about 100 requests every 40 s. Live: 0/100 resolved in 210 s, and the same sidecar's RELIANCE quote
  stayed unanswered until about 4 min after the panel unmounted (14-recovery-watch.log, first 200 at 16:47:17), which starves the watchlist and chart on that sidecar too. Even a 2-holding portfolio opened
  just after boot showed the failure banner.
- **P9c (drive-portfolio-notes:2, high, regression of R15-AGENT-091).** The fix gives the store-fallback path the region's currency, not
  the holding's. With the panel closed (the normal chat state), a USD AAPL lot is served as `currency: "INR"`, and the copilot states
  "cost basis ₹190", which is the entry's own repro outcome. The pinning test only checks an INR name in region IN.

**Still partial, now a register-fixed entry that reproduces:**
- **P2 (drive-portfolio-notes:4, low, regression of R15-UI-078).** The blank, 1e20 and "1,000" cases are fixed. A whitespace-only cost
  still saves 0, and "0x10" saves 16.

**Fresh defect:**
- **P5 (drive-portfolio-notes:3, medium, new).** A 404 symbol, such as a typo or a delisted small cap, raises the transport-failure banner
  with a Retry that can never succeed, even next to fully priced rows. It is the converse of R15-UI-004. rc1 behaved the same, so this is not a regression.

**Fixed since rc1, confirmed live:** R15-UI-079 (formula prefix, numerics untouched), R15-UI-078 (blank/1e20/1,000 cases),
R15-CROSS-PLATFORM-006, R15-DOCS-010, R15-AGENT-091 on the panel-open path. Everything rc1 scored ok still holds, apart from P3/P8 above.

**Agent lane notes:** A1x/A1y in the evidence dir are two harness mistakes, kept as evidence: a flat snapshot, then camelCase keys. The sidecar takes
`context_snapshot.{focused_source, by_source.__terminal__}`, and with the wrong keys get_portfolio honestly said it had no portfolio. A1 used
the correct wire shape. A2 (AUTO, "Delete my TCS position", two TCS lots): llama emitted portfolio_delete_position with a placeholder position_id, the sidecar reported it awaiting review (staged, never auto-applied), and an unknown id is refused at apply (P9 delete_unknown_id -> null). The gate held. No R4 instance was filed: in A1 the model repeated a
tool result faithfully, and the wrong currency sits in the product's own data.

Not filed (would not change a decision): CSV numeric cells carry unrounded floats (`-2.6916666666666664`, `333.69000244140625`).
safeFilename does not suffix `COM0`/`LPT0`, which no ticker uses.
