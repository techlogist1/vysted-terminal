# R15-UI-083 — GUI drive at ace7dd7 (rc2 candidate, session 3)

- entry: R15-UI-083 (medium) — research brief export: Save .md / Save PDF / Save PNG (was clipboard-only)
- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (gui worktree scratchpad/gui-ace7dd7, HEAD verified)
- app: scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (packaged, tauri:// origin)
- isolated home: scratchpad/gui-round-home-R15-UI-083 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true})
- real ~/Library/Application Support/com.vysted.terminal mtime before: 1790978102
- :5173 free; no Vysted app running at start (05:04Z, lsappinfo empty).

## Code read at ace7dd7 (before driving)
- BriefPanel.tsx:41 imports saveTextArtifact/savePdfArtifact/savePngArtifact; :692-722 handleExportMd/Pdf/Png -> `exports/research/<slug>.{md,pdf,png}`, flashStatus("Saved <path>") for 4.5 s or "Export failed: ...".
- :665-689 `bodySettled` = reducedMotion or settle timer fired for this brief's createdAt; Save PDF/PNG `disabled={!bodySettled}` (:810, :823). Toolbar :788-827, status strip :832-837.
- export-artifact.ts: Tauri path -> invoke get_app_data_dir, then write_text_atomic / write_bytes_atomic at `<dataDir>/exports/<subdir>/<file>`; PNG via html-to-image toPng; Blob fallback only outside Tauri.
- Seed: workspace blob already carries a settled FAST brief (SETFNIF50, markdown + 3 sources + structured). Watchlist lacks MSFT and portfolio is empty -> seeding boot posts R15-UI-009's raw/ace7dd7-seed-post.json (same brief, 7 symbols, 2 holdings, note).

## Presence / steps
- 2026-10-03T05:06:22Z waiting for idle >= 900 (05:05:26Z idle=129.7, 05:06:16Z idle=179.6; the idle clock last reset ~05:03:16Z, matching R15-UI-050's batch C at 05:03:12Z).
- 2026-10-03T05:18:29Z idle=912.9 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] (pre-launch-1b)
- Boot 1 (seeding, no GUI input): pid 6600 at 05:18:31Z; children 6612 vysted-sidecar --port 64528 --data-dir/--cache-dir <isolated home>/Library/Application Support/com.vysted.terminal (ps args), 6610 openbb-mcp 64529, 6611 sec-edgar-mcp 64530; logs/vysted.log under the isolated home. /health ok 0.9.0. GET /workspace/__autosave__ -> raw/ace7dd7-seed-before.json; POST /workspace raw/ace7dd7-seed-post.json (R15-UI-009's ace7dd7 seed) -> {"status":"saved"}; read back 7 symbols incl. MSFT, holdings AAPL 10 @ 180 + NVDA 5 @ 120, brief SETFNIF50 (1456-char markdown). Killed 6600 + 6610/6611/6612 by pid; none left; blob on disk = 7 symbols, 2 holdings, brief SETFNIF50, note. raw/app-stdout-boot1.log, raw/vysted-boot1.log.
- 2026-10-03T05:20:51Z idle=1054.2 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] (pre-launch-2)
- Launch 2 (drive): pid 7353 at 05:20:51Z; children 7375 vysted-sidecar --port 49442 --data-dir/--cache-dir <isolated home>/Library/Application Support/com.vysted.terminal (ps args), 7373 openbb-mcp 49443, 7374 sec-edgar-mcp 49444; 7372 = system WebKit WebContent XPC (ppid 1). /health on :49442 ok 0.9.0. Bounds [116,43,1280,832] -> launched size 1280x832 points (captures 2560x1664, point = pixel/2). Brought my pid 7353 front via System Events (no input event; UI-009/050 precedent).
- 2026-10-03T05:22:54Z idle=1177.2 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[7353 7372] (pre-capture-01)
- ace7dd7-01-boot-passive.png (opened): dark theme; "Welcome to Vysted" terms modal over the seeded layout: Chat 1 | Portfolio/Chart (^NSEI) | Brief with the toolbar "Save .md  Save PDF  Save PNG" and the populated SETFNIF50 brief (₹252.41, P/E 20.35, 52W 238-287, volume 870K). Registry note: this PNG is byte-identical (sha 282de970…) to R15-CODE-AGENT-001/ace7dd7-01-packaged-seeded-layout.png (same seed, same static first frame), so register_capture's sha dedup returned that row and added none for this path; the pre-push gate is sha-keyed, so it is covered. Used only for coordinates.

## Batch A — raw/ace7dd7-batch-A.json (terms, onboarding skip, Save .md, Save PDF, Save PNG)
- 2026-10-03T05:23:44Z idle=1227.5 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[7353 7372] (pre-batch-A)
- Steps: terms (768,598); wait 4; onboarding Skip (502,728); wait 5; capture 02; Save .md (1024,184); wait 1.5; capture 03; wait 4 (lets the .md status's 4.5 s timer lapse); Save PDF (1123,184); wait 2.5; capture 04; wait 2; capture 04b; wait 5; Save PNG (1221,184); wait 2.5; capture 05; wait 2; capture 05b. EXIT=0, no abort (raw/ace7dd7-batch-A.log). 05b is byte-identical to 05 (sha dedup, same as 01).
- ace7dd7-02-cockpit-brief-settled.png (opened): modals gone; populated cockpit: ^NSEI chart with MA 20/50/200, MACD, RSI, Volume, a Trend drawing; Brief panel fully rendered (FAST · SETFNIF50 · 3 sources, EOD as of 2026-09-13, metric cards ₹252.41 -₹0.20 (-0.08%) NSE_DIRECT, P/E 20.35, 52W 238-287, volume 870K, heading "SBI-ETF Nifty 50 (SETFNIF50)", Snapshot bullets). Save .md / Save PDF / Save PNG all shown enabled.
- ace7dd7-03-save-md-status.png (opened): Save .md button highlighted; status strip under the toolbar "SAVED /PRIVATE/TMP/CLAUDE-501/-USERS-LOKAVYASING…" (uppercase mono, ellipsized by the 1/3-width panel, so the file name is not visible on screen). Context switched to "CONTEXT: BRIEF".
- ace7dd7-04-save-pdf-status.png and 04b (opened): Save PDF highlighted; the same "SAVED /PRIVATE/TMP/CLAUDE-501/…" strip — the .md message's timer had lapsed before the click, so this strip is the PDF's own report. Brief unchanged (no mid-animation fade).
- ace7dd7-05-save-png-status.png (opened): Save PNG highlighted; "SAVED /PRIVATE/TMP/CLAUDE-501/…" strip again.
- Disk (raw/ace7dd7-exports-ls.txt, raw/ace7dd7-exports-stat.txt): <isolated data dir>/exports/research/setfnif50.md 1988 B at 10:53:54 IST (=05:23:54Z, the .md click), setfnif50.pdf 7,450,598 B at 05:24:02Z (PDF click), setfnif50.png 392,228 B at 05:24:10Z (PNG click). Each file's mtime matches its click, so each "Saved" strip corresponds to its own write through the rewritten write_atomic.
- Copies: raw/ace7dd7-export-setfnif50.md (title, Mode/Symbol/sources/as-of line, full synthesis, Sources appendix with 3 titled URLs), raw/ace7dd7-export-setfnif50.pdf (PDF 1.3, 3 A4 pages), raw/ace7dd7-export-setfnif50.png (788x3150, registered with register_capture.py --tool vysted-export, sha 421cb12d…).
- raw/ace7dd7-export-setfnif50.png (opened): the whole settled brief on the dark panel bg — header chips, archived/refresh card, keyless-search card, metric cards, heading, Snapshot, What it is, Risks and fit, Data limits, Sources 1-3. Every block is fully opaque; no faded or half-rendered (mid-stagger) block; prose width-capped.
- PDF read back by rendering its 3 pages with Quartz to scratchpad (not repo evidence): p1 header chips + metric cards + heading; p3 end of Risks and fit, Data limits, Sources 1-3, then the blank page remainder. All text fully opaque, same settled layout as the PNG.

## Teardown
- kill 7353, then 7373/7374/7375 by pid; ps shows none; lsappinfo has no Vysted entry; no process from gui-ace7dd7 or the isolated home left. No vite started. No Ollama call made (seeded brief), so no local-model lock taken.
- raw/vysted.log (isolated log), raw/app-stdout.log, raw/app-stdout-boot1.log, raw/vysted-boot1.log: 0 keychain/SecurityAgent lines; no keychain or SecurityAgent dialog in any capture.
- Real ~/Library/Application Support/com.vysted.terminal mtime: before 1790978102, after 1790978102 (unchanged).

## Stops
- None. No rig refusal, no abort, no foreign window, no human input. (Wait 05:05-05:18Z for idle >= 900 after R15-UI-050's last batch.)

## Checks
- Settled populated brief on screen: SHOWN (02).
- Save .md reports its path + file under exports/: SHOWN (03; setfnif50.md, content read back).
- Save PDF reports its path + file under exports/: SHOWN (04; setfnif50.pdf, 3 pages, settled).
- Save PNG reports its path + file under exports/: SHOWN (05; setfnif50.png registered, settled brief, not mid-animation).
- Adjacent note (not this entry's defect): the status strip is ellipsized in a 1/3-width Brief panel, so the on-screen text shows only the path's start (the full path rides the strip's title tooltip); the file name is confirmed on disk.

## Verdict: HOLDS — the original repro (clipboard-only, no file export) is gone: the Brief toolbar carries Save .md / Save PDF / Save PNG; each click reports "Saved <path>" and writes exports/research/setfnif50.{md,pdf,png} through the rewritten write_atomic; the PNG and PDF rasters show the fully settled brief.
