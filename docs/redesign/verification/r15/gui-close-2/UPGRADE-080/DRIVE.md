# UPGRADE-080 (gui-close-2) — on-screen half of the 0.8.0 -> 0.9.0 upgrade

- item: UPGRADE-080 (close-drive-UPGRADE-080, Opus 5.5), second GUI round with the fixed rig (7a07c82f)
- sha: 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056 (r15-launch)
- app: scratchpad/gui-close-2/Applications/Vysted Terminal.app (0.9.0 release bundle, installed fresh from the launch dmg by the lead this round)
- keychain at the attended first launch (fresh-install/FRESH_INSTALL.md): no SecurityAgent process at any 3-4 s reading from 14:27:15 to 14:30:40 IST; no prompt appeared, so the operator had nothing to answer. None is expected now; a new one is a hard stop.
- home: real HOME; data dir: VYSTED_DATA_DIR=scratchpad/gui-close-upgrade-run, a fresh `cp -Rp` (09:03Z) of the lead's snapshot scratchpad/gui-close/upgrade-080-data (byte copy of ~/Library/Application Support/com.vysted.terminal.audit-backup-20260529, last written 22-27 May 2026). Snapshot mtime 1779906083 unchanged by the copy.
- real-data mtime before: com.vysted.terminal 1790978102; audit-backup-20260529 1779906083

## Inventory before launch (raw/before.txt)
One named layout `phase9test` (keys chartDrawings/enabledModules/layout/name; 9 layout panels: 2x chart, chat-sidebar, equity-overview, news, option-pricer, portfolio, settings, watchlist; no watchlist/holdings key), no `__autosave__`, no notes/, no workflows.db. custom_agents 0 rows, plugin_configs 0 rows, data_cache 5, portfolio.db positions 84 rows (AAPL x4 incl. two 1e15 x 1e-8 rows, one -50 x -10 row and row 4 whose note is a long injection string; T001..T080 with quantity n+1 and cost basis 10n). The schema has no portfolio column. audit_log.db could not be opened `-readonly` by sqlite3 (error 14); the first round counted 3 legacy audit_orders rows.

## Presence / timeline
- 09:03:30Z presence pre-launch: idle 300.8 (below 900) -> waited, polling idle in short calls.
- 09:13:35Z presence pre-launch: idle 905.8, sentinel 2026-10-04 12:57:00+00:00, frontmost Zed, no Vysted app -> launched 09:13:35Z, app pid 78599 (raw/launch-time.txt, raw/app-stdout.log).
- Keychain: `pgrep -x SecurityAgent` every 3-4 s through boot (09:13:35-09:15:20Z): never present. No new prompt.
- Data dir proven (raw/sidecar-args.txt): sidecar pid 78616 `vysted-sidecar --port 53692 --data-dir .../scratchpad/gui-close-upgrade-run --cache-dir .../scratchpad/gui-close-upgrade-run`. /health 200 version 0.9.0, openbb-mcp available. sec-edgar-mcp spawned on :53694 but is absent from /health providers (known open medium R15-LEAD-124; not re-filed).
- bounds: Vysted Terminal window id 7579, [116, 43, 1280, 832] points; captures are 2560x1664 (2x).

## Checks

### b01 — cockpit after CONNECTED (batches/b01-cockpit.json, raw/rig-01.log, EXIT=0)
Presence before: 09:15:34Z idle 1024.7, sentinel 12:57:00Z, frontmost Zed, only my app (pid 78599). The rig brought Vysted forward itself.
- `1fddb2b-01-cockpit-boot.png`: cockpit, CONNECTED, header "OLLAMA (LOCAL) · NOT RUNNING — SET UP IN SETTINGS"; Chat 1 empty state; Chart / Equity Overview group; Watchlist (loading skeleton); News (loading); Portfolio panel header **"Portfolio · 81"**, summary "Market value: — (no live quotes) · 81 without a live quote", first table row AAPL qty 10. (Default layout: the 0.8.0 profile had no `__autosave__`.)

### b02 — make room for the Portfolio panel, open Settings (batches/b02-panels-settings.json, raw/rig-02.log, EXIT=0)
Presence before: 09:16:55Z idle 1105.8, sentinel 12:57:00Z, frontmost Vysted Terminal (mine), only my app.
- `1fddb2b-02-news-closed.png`: News closed; Watchlist now shows the app's default list (^NSEI, RELIANCE.NS, TCS.NS, HDFCBANK.NS; the 0.8.0 profile had no watchlist); Portfolio "· 81", Market value $3,336.90, Total P&L +$1,836.90 (+122.46%), 80 without a live quote, RISK row.
- `1fddb2b-03-portfolio-full-column.png`: Watchlist closed; Portfolio fills the right column: AAPL 10 ($3,336.90, EOD badge), T001 2, T002 3, T003 4, T004 5, T005 6, T006 7, T007 8, T008 9, T009 10 — quantities match before.txt rows 1, 5-13.
- `1fddb2b-04-settings-open.png`: Settings (top-right icon) opens as a tab in the centre group ("2 more" overflow chip), context chip "CONTEXT: SETTINGS"; the Portfolio group widened and now shows AVG COST: AAPL 10 @ $150.00, T001 2 @ ₹10.00, T002 3 @ ₹20.00 ... T010 11 @ ₹100.00 — cost bases match before.txt. AI Providers section heading visible with the first row "Anthropic — No key yet". The Sections jump nav is collapsed to "SECTIONS ⋯" at this width.

### b03 — Portfolio scroll by keyboard focus, then Settings -> Sections -> Advanced (batches/b03-portfolio-scroll-advanced.json, raw/rig-03.log, EXIT=0)
The rig has no scroll-wheel step, so the table was scrolled by focus: click the Note field, then Tab (Add, then each row's Edit and Delete buttons; the browser scrolls the focused button into view). No button was activated. Presence before (logged by the detached waiter): 09:32:09Z idle 910.0, sentinel 12:57:00Z, frontmost Vysted Terminal, only my app.
- `1fddb2b-05-portfolio-scroll-tab18.png`: focus on T008 Edit; AAPL 10 @ $150.00 (price $333.69, EOD), T001-T010 (qty 2-11, ₹10-₹100).
- `1fddb2b-06-…tab36.png`: rows T007-T021 (qty 8-22, ₹70-₹210), focus T017. The summary line now reads "Market value: — (no live quotes) · 81 without a live quote" (AAPL's EOD quote dropped between b02 and b03; see findings).
- `1fddb2b-07-…tab54.png`: T015-T029 (16-30, ₹150-₹290).
- `1fddb2b-08-…tab72.png`: T023-T037 (24-38, ₹230-₹370).
- `1fddb2b-09-…tab90.png`: T031-T045 (32-46, ₹310-₹450).
- `1fddb2b-10-…tab108.png`: T039-T053 (40-54, ₹390-₹530).
- `1fddb2b-11-…tab126.png`: T055-T069 (56-70, ₹550-₹690). T054 fell between captures 10 and 11; it is shown in b04.
- `1fddb2b-12-…tab144.png`: T063-T077 (64-78, ₹630-₹770).
- `1fddb2b-13-…tab162.png`: T066-T080 (67-81, ₹660-₹800); T080 is the last row, focus on its Edit.
- `1fddb2b-14-…tab180.png`: same end of table, focus has left the table.
- `1fddb2b-15-settings-sections-menu.png`: "SECTIONS ⋯" open: AI Providers, Research, Region & locale, Keybindings, Advanced.
- `1fddb2b-16-settings-advanced.png`: Advanced section: Integrations (the "Open Market" button is clipped at the group edge), then Layouts with the "Save current layout as…" field and the "Start with" card; the list itself is below the fold.
Every row read on screen matches before.txt's symbol, quantity and cost basis. What the panel does NOT show: the three AAPL lots ids 2-4 (qty 1e15 @ 1e-8 twice, and -50 @ -10). The header says "Portfolio · 81", while the ledger has 84 rows.

### b04 — T054, then try to reach the Layouts list by focus (batches/b04-T054-layouts-providers.json, raw/rig-04.log, EXIT=0)
Presence before: 09:48:43Z idle 907.8, sentinel 12:57:00Z, frontmost Zed (no human input; the rig brought Vysted forward itself), only my app.
**The dock layout had changed between b03 (09:33Z) and b04.** Settings is now a wide tab in the centre group, beside Chart / Equity Overview. Portfolio is a narrow group on the right (form stacked, the selector truncated to "P("). The full chip nav AI PROVIDERS / RESEARCH / REGION & LOCALE / KEYBINDINGS / ADVANCED is shown. Window bounds were unchanged ([116, 43, 1280, 832]). No input reached the app between the batches (idle climbed steadily to 907.8). The exact cause is not established; see findings (low). So b04's fixed-coordinate clicks landed somewhere other than planned. The first click hit the narrow Portfolio form, and 110 Tabs moved focus inside the Portfolio table. The second click hit the AI Providers list (the Groq row's label area, not a control). Tab and Shift+Tab only move focus; nothing was activated. Every capture shows the providers unchanged and no dialog.
- `1fddb2b-17-portfolio-T054.png`: the new layout; Portfolio narrow, summary back to "Market value: $3,336.90 · Total P&L +$1,836.90 (+122.46%) · 80 without a live quote". T054 is not legible here (the narrow table shows only the action column).
- `1fddb2b-18-layouts-focus-input.png`: Settings, AI Providers. **Anthropic "No key yet", OpenAI "No key yet", Google Gemini "No key yet", Groq "No key yet", each with an "Add key" button; Ollama (local) "No key required (local)" ✓ DEFAULT**; a DeepSeek row is cut off at the bottom. Context chip "SETTINGS".
- `1fddb2b-19-layouts-tab1.png` / `1fddb2b-21-layouts-tab3.png` / `1fddb2b-22-layouts-tab4.png`: focus walks the Groq row (up arrow, DEFAULT, Add key); the providers are unchanged.
- `1fddb2b-23-settings-shifttab8.png`: focus on OpenAI's Add key; `1fddb2b-24-…shifttab16.png`: focus on the KEYBINDINGS chip; `1fddb2b-25-…shifttab24.png`: focus moved to the chat composer's "Normal" depth control; `1fddb2b-29-…shifttab56.png` and `1fddb2b-33-…shifttab88.png`: focus in the Portfolio table's action column. The providers are unchanged in all of them.
- Not opened, not relied on: 1fddb2b-20, -26, -27, -28, -30, -31, -32 (more of the same Shift+Tab walk).
- Opened later: `1fddb2b-20-layouts-tab2.png` (focus on Groq's down arrow) and `1fddb2b-27-settings-shifttab40.png` (focus in the Portfolio action column). The providers are unchanged in both. Still not opened, not relied on: -26, -28, -30, -31, -32.

### b05 — AI Providers in full width, then Advanced -> Layouts (batches/b05-providers-advanced.json, raw/rig-05.log, EXIT=0)
Presence before: 10:04:48Z idle 914.5, sentinel 12:57:00Z, frontmost Vysted Terminal (mine), only my app.
- `1fddb2b-34-before-b05.png`: passive capture of the state b04 left (the same wide-Settings layout).
- `1fddb2b-35-ai-providers.png`: the AI PROVIDERS chip jumped to the section. Fallback-order rows and their state: **Anthropic No key yet · OpenAI No key yet · Google Gemini No key yet · Groq No key yet · Ollama (local) No key required (local), ✓ DEFAULT · DeepSeek ✓ Key configured (Update key + delete icon) · xAI No key yet · OpenRouter ✓ Key configured** (cut off at the bottom edge). Only configured/not-configured state is shown; no value is on screen, and none was read or recorded. That state comes from the login keychain this release build reads, not from the copied data dir.
- `1fddb2b-36-advanced-chip-focused.png`: after 4 Tabs from the AI PROVIDERS chip, the focus ring is on ADVANCED (the panel scrolled back to the top to show the focused chip).
- `1fddb2b-37-advanced-layouts.png`: Return on ADVANCED jumped there: Integrations ("Open Marketplace", unclipped at this width), **Layouts: "Save current layout as…", Save, Reset to default, Start with = "Last session", one saved layout row `phase9test` with LOAD and ×**, then "Autosave slot: __autosave__ (hidden; restored on launch)". This matches before.txt: one named layout, `phase9test`.

### b06 — load phase9test (batches/b06-load-phase9test.json, raw/rig-06.log, EXIT=0)
Presence before: 10:20:00Z idle 908.0, sentinel 12:57:00Z, frontmost Vysted Terminal (mine), only my app.
- `1fddb2b-38-before-load.png`: Advanced -> Layouts, `phase9test` row with LOAD / ×. Centre tabs: Chart, Equity Overview, Settings. Portfolio is the narrow right group.
- `1fddb2b-39-phase9test-loaded.png`: after the LOAD click (pt 924,639) the dock was rebuilt to phase9test's grid (raw/phase9test-layout.txt). The centre group has Chart, Equity Overview, Option Pricer plus "2 more" overflow (the second chart and Settings); Settings is the active tab, as saved. The right column is stacked Watchlist (^NSEI unavailable; RELIANCE.NS 1,167.70 −1.63%, EOD as of 2026-10-01), News (a Pulse by Zerodha item, POSITIVE +0.66), and Portfolio ("Portfolio · 81", AAPL 10 first). Option Pricer and Watchlist were not in the pre-load layout, so the load really restored the saved panels. One difference: the saved grid has the AI Assistant chat under Watchlist in the right branch. 0.9.0 shows chat only as the left agent pane ("Chat 1", CONTEXT: SETTINGS), so there is no chat panel in the dock. This is consistent with the 003 rebuild moving chat into the agent sidebar, and no panel reference was lost (observation, not a finding).
- `1fddb2b-40-phase9test-settled.png`: 5 s later, identical: stable, no error toast.

## Quit and real-data check
- At 10:21:37Z I sent SIGTERM to pid 78599 (my app) only. Its children 78614, 78616 (sidecar), 78627 and 78628 all exited within the poll. Afterwards: no process path matching my run copy or install, and `lsappinfo` lists 0 "Vysted Terminal" apps.
- Real `~/Library/Application Support/com.vysted.terminal` mtime: 1790978102 before and after (stat only; never opened). The snapshot `gui-close/upgrade-080-data` mtime stayed at 1779906083, so the run used only the copy `gui-close-upgrade-run`.
- No SecurityAgent prompt at any point. No chat turn sent, no research run, Ollama never reached.

## Checks
| Check | Result | Capture |
|---|---|---|
| Cockpit after CONNECTED | shown | 1fddb2b-01 |
| Portfolio shows the legacy positions with the same symbols/qty/cost | shown (81 of 84; the 3 invalid AAPL lots are dropped, see finding) | 1fddb2b-04..14 |
| Every valid row read while scrolling | shown except T054 (between captures; HTTP cross-check equal) | 1fddb2b-05..14 |
| Settings -> Advanced -> Layouts lists phase9test | shown | 1fddb2b-37 |
| Loading phase9test restores its panels | shown | 1fddb2b-39, -40 |
| Notes | n/a (the 0.8.0 profile has no notes) | — |
| AI Providers configured/not-configured, no value | shown | 1fddb2b-35 |
| Real dir mtime unchanged after quit | shown (1790978102 = 1790978102) | — |

## Findings
1. (low) 3 of the 84 legacy positions are silently dropped on the 0.8.0 -> 0.9.0 import. These are AAPL ids 2 and 4 (qty 1e15, above the 1e12 ceiling) and id 3 (qty −50, cost −10). The panel shows "Portfolio · 81" with no notice. Because the portfolios blob is now written, they never re-import. The ledger (GET /portfolio/positions) still holds all 84. Cause: `setAll` -> `normalizeHolding`/`validateHolding` in src/store/portfolios.ts. These are deliberately hostile fixture rows, so dropping them is defensible; the silence is the issue.
2. (low) The dock layout proportions changed between b03 and b04 with no input reaching the app (captures 16 -> 17). Bounds were unchanged; the cause is not established.
3. (low) At narrow group widths Settings clips "Open Marketplace" / "Add key" with horizontal overflow (captures 04, 16).
4. (observation) AAPL's EOD quote moves in and out of the Portfolio summary between captures ($3,336.90 in 02/05/17; "no live quotes" in 06-14 and 39).

## Stops
None.

## Verdict
holds. Every on-screen item of the UPGRADE-080 brief was shown on the release app against a copy of the 0.8.0 profile. The real data dir was never touched.
