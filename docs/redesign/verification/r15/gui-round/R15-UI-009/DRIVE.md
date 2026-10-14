# R15-UI-009 — GUI drive at ace7dd7 (rc2 candidate, session 3)

- entry: R15-UI-009 (high) — Watchlist/Portfolio/Screener Export CSV silent no-op in WKWebView
- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (gui worktree scratchpad/gui-ace7dd7, HEAD verified)
- app: scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (packaged, tauri:// origin)
- isolated home: scratchpad/gui-round-home-R15-UI-009 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true})
- real ~/Library/Application Support/com.vysted.terminal mtime before: 1790978102

## Code read at ace7dd7 (before driving)
- src/lib/csv.ts `downloadCsv` -> `saveTextArtifact("csv", ...)` (src/lib/export-artifact.ts): Tauri -> `invoke("get_app_data_dir")` then `invoke("write_text_atomic", {path: <dataDir>/exports/csv/<file>})`, returns `{path}`; Blob fallback only outside Tauri.
- WatchlistPanel.tsx:335-338 and PortfolioPanel.tsx:736-739: show `Saved <path>` / `Export failed: ...` in an exportStatus strip.
- ScreenerResultsTable.tsx:283-285: `downloadScreenerCsv` = `void downloadCsv(...)` — result discarded, NO on-screen status for success or failure (no exportStatus in the screener). Expect the screener file on disk but no saved-path text on screen.

## Presence / steps
- 2026-10-03T01:40:10Z idle=145.2 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[0] (pre-launch-1) -> idle < 900, waiting.
- 2026-10-03T01:52:59Z idle=914.4 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Finder" vysted=[] entry=R15-UI-009 ace7dd7 pre-launch-1b
- Boot 1 (seeding): pid 44656 launched 2026-10-03T01:52:59Z; children 44673 vysted-sidecar --port 49934 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal (--cache-dir same), 44671 openbb-mcp --port 49935. Log at <isolated home>/Library/Application Support/com.vysted.terminal/logs/vysted.log (isolated). GET /workspace/__autosave__ -> raw/ace7dd7-seed-before.json (6 symbols, 0 holdings, empty note); POST /workspace raw/ace7dd7-seed-post.json (same payload as R15-CODE-AGENT-001's ace7dd7 seed: 7 symbols incl. MSFT, holdings AAPL 10 @ 180 + NVDA 5 @ 120, seeded note) -> {"status":"saved"}. Killed 44656 + children; none left; blob on disk = 7 symbols, 2 holdings, note. raw/app-stdout-boot1.log, raw/vysted-boot1.log.
- 2026-10-03T01:55:27Z idle=1062.5 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Finder" vysted=[] entry=R15-UI-009 ace7dd7 pre-launch-2
- 2026-10-03T01:56:49Z idle=1144.8 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Finder" vysted=[pid = 45730 pid = 45743 ] entry=R15-UI-009 ace7dd7 pre-capture-01
- passive capture: first `rig.py capture` refused exit 4 "frontmost app is 'Finder', not Vysted" (RIG_ABORTS.log 2026-10-03T01:56:50.912485Z) — precondition, my app launched unactivated, no human input (idle 1144.8); same as R15-LIFECYCLE-008's precedent. Brought MY pid 45730 front via System Events (unix id 45730).
- 2026-10-03T01:57:08Z idle=1163.4 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Vysted Terminal" vysted=[pid = 45730 pid = 45743 ] entry=R15-UI-009 ace7dd7 pre-capture-01b
- Launch 2 (drive): pid 45730 at 2026-10-03T01:55:27Z; children vysted-sidecar --port 51239 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal, openbb-mcp 51240, sec-edgar-mcp 51241. Window bounds [116,43,1280,832] -> launched size 1280x832 points (captures 2560x1664).
- ace7dd7-01-boot-passive.png (opened): dark theme; "Welcome to Vysted" terms modal over the seeded layout (Portfolio|Chart group with ^NSEI chart + volume, Brief SETFNIF50 ₹252.41), CONNECTED pill.

## Batch A — raw/ace7dd7-batch-A.json (terms, portfolio export, watchlist export, open screener)
- 2026-10-03T01:57:47Z idle=1202.5 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Vysted Terminal" vysted=[pid = 45730 pid = 45743 ] entry=R15-UI-009 ace7dd7 pre-batch-A
- Steps: accept terms (768,598); onboarding Skip (502,728) -> 02; Portfolio tab (515,148) -> 03; Portfolio export icon (813,188) -> 04; palette (243,56) "Open Watchlist" down return -> 05; Watchlist export icon (648,194) -> 06; palette "Open Screener" -> 07. All 30 steps ok (raw/ace7dd7-batch-A.log), no rig abort, 6 captures registered in CAPTURES.jsonl.
- ace7dd7-02 / -03 / -05 are intermediate frames (not opened, not used as evidence).
- ace7dd7-04-portfolio-export-clicked.png (opened): Portfolio tab populated — "Portfolio · 2", Market value $4,506.65, Total P&L +$2,106.65 (+87.78%), concentration 74.0%, Sharpe 1.36 / Sortino 1.97 / Max DD -12.4%, AAPL/NVDA correlation, AAPL row $3,336.90; export icon highlighted; status strip reads "Saved /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-round-home-R15-UI-009/Library/Application Support/com.vysted.terminal/exports/csv/vysted-portfolio-portfolio.csv" with a dismiss x. PORTFOLIO SHOWN.
- ace7dd7-06-watchlist-export-clicked.png (opened): Watchlist tab, 7 rows with live prices 769.64, 749.58, 84,613.98, 2,678.73, 233.95, 333.69, 517.53 (symbol column narrow, first letter); status strip under the toolbar "Saved /private/tmp/clau… lokavyasingh-Documents-… terminal/454f42d1-ac9f-… 216c6bad682f/scratchpad… 009/Library/Application Support/com.vysted.term… watchlist.csv" (right edge clipped by the narrow panel; the visible path begins and ends correctly). WATCHLIST SHOWN.
- ace7dd7-07-screener-open.png (opened): Screener tab, universe NIFTY 50 (50 tickers), Run screener button, preset chips, default criteria P/E < 20 AND Market cap > 1000000 AND Sector = Technology, custom formula box at the bottom; no results yet. The criteria builder (shrink-0) fills the panel, so the results table (flex-1, min-h-0) has no room; next batch trims two criteria before running.
- After batch A, `ls -la exports/csv/` -> raw/ace7dd7-exports-ls-after-batchA.txt: vysted-portfolio-portfolio.csv (296 B), vysted-watchlist.csv (420 B), both 07:28 local; header rows -> raw/ace7dd7-csv-headers-after-batchA.txt: portfolio "Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note"; watchlist "Symbol,Asset class,Price,Change %,Provider".

## Batch B — raw/ace7dd7-batch-B.json (trim criteria, run screener, dismiss banner)
- 2026-10-03T02:13:55Z idle=930.9 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Vysted Terminal" vysted=[pid = 45730 pid = 45743 ] entry=R15-UI-009 ace7dd7 pre-batch-B
- Steps: remove Sector criterion (1009,659), remove Market-cap criterion (1009,579) -> 08; Run screener (966,235), wait 45 s -> 09; wait 30 s; dismiss provider banner (1251,104) -> 10. All 12 steps ok (raw/ace7dd7-batch-B.log), no abort.
- ace7dd7-08 / -09 intermediate (not opened, not evidence).
- ace7dd7-10-screener-results-banner-dismissed.png (opened): Screener, NIFTY 50, criterion P/E ratio < 20; "screened 49 of 50 — 1 unavailable, 18 LIVE, 1 UNAVAILABLE — 1 MISSING PE_RATIO, QUOTES 0S AGO · VALUATION 0S AGO"; results header "18 matched · showing top 18 by market cap (49 evaluated, 1 skipped, 456 ms)" with "Export CSV  NIFTY50" at display (828,1237) -> point (530,792). The results table body itself is squeezed to a scrollbar strip at this window height (builder is shrink-0) — adjacent layout note, not this entry. No export clicked yet; exports/csv/ still holds only the portfolio and watchlist files.

## Batch C — raw/ace7dd7-batch-C.json (screener Export CSV)
- 2026-10-03T02:30:48Z idle=933.6 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Vysted Terminal" vysted=[pid = 45730 pid = 45743 ] entry=R15-UI-009 ace7dd7 pre-batch-C
- Step: click "Export CSV" (530,792), wait 5 s -> 11. 3/3 steps ok (raw/ace7dd7-batch-C.log), no abort.
- ace7dd7-11-screener-export-clicked.png (opened): identical screen to 10 — "18 matched · showing top 18 by market cap (49 evaluated, 1 skipped, 456 ms)", "Export CSV  NIFTY50"; NO saved path, no toast, no status text anywhere in the panel.
- Disk after the click (raw/ace7dd7-exports-ls-final.txt, raw/ace7dd7-csv-headers-final.txt): exports/csv/vysted-screener-nifty50.csv 3.5 KB written 08:00 local (= 02:30Z, the click), 18 data rows, header "Symbol,Name,Sector,Industry,Market cap,P/E,Fwd P/E,ROE,D/E,Div yield,Price,1d %,Volume,Currency". Portfolio (2 rows) and watchlist (7 rows) files unchanged.
- Cause (code at ace7dd7, read before driving): ScreenerResultsTable.tsx:283-285 `function downloadScreenerCsv(...): void { void downloadCsv(...) }` discards the ExportResult; the screener has no exportStatus strip (Watchlist/Portfolio do, WatchlistPanel.tsx:335-338, PortfolioPanel.tsx:736-739). A write failure would be equally invisible (unhandled rejection).

## Teardown
- kill 45730 then its children 45744/45745/45746 by pid; `ps -ax` shows none of them and no process from gui-ace7dd7 / the isolated home. No vite started.
- raw/vysted.log copied (isolated log); raw/app-stdout.log.
- real ~/Library/Application Support/com.vysted.terminal mtime after: 1790978102 (= before). No keychain / SecurityAgent dialog appeared in any capture.

## Stops
- one rig precondition refusal: first passive capture exit 4 "frontmost app is 'Finder', not Vysted" (RIG_ABORTS.log 2026-10-03T01:56:50.912485Z) — my app launched unactivated, no human input (idle 1144.8); activated my pid via System Events and continued. No mid-batch abort, no foreign window, no human input.

## Checks
- Watchlist Export CSV shows saved path + file exists: SHOWN (06; vysted-watchlist.csv, header read back).
- Portfolio Export CSV shows saved path + file exists: SHOWN (04; vysted-portfolio-portfolio.csv, header read back).
- Screener Export CSV (after a run) shows saved path: NOT SHOWN (11 — no path, no status; screen unchanged from 10). File exists: yes (vysted-screener-nifty50.csv, 18 rows).
- Shared rewritten write_atomic path (UI-009/UI-025/UI-083): three successful writes under <data dir>/exports/csv/ in the packaged app.

## Verdict: REGRESSED (screener half) — Watchlist and Portfolio hold (saved path on screen, files on disk). Screener writes the file but is silent on screen: to the user it is the original "silent dead control" symptom, because ScreenerResultsTable discards the result and has no status surface. Fix shape: give the screener the same exportStatus strip (Saved <path> / Export failed) as Watchlist/Portfolio.
