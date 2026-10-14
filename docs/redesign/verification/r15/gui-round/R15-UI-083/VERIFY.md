# R15-UI-083 — fresh GUI verify at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

- Verifier: Opus 5.5 (claude-opus-5-5), fresh context, label gui-verify-R15-UI-083. No GUI, no app launch.
- Claim (title + fix_shape): the brief exports to real files (Save .md via saveTextArtifact, Save PDF/PNG via savePdfArtifact/savePngArtifact) and the PDF/PNG raster is taken only from a settled brief (BRIEF-2 cannot recur). Note's GUI check: the PDF/PNG raster of a settled brief renders correctly in the WKWebView.

## Registration check (shasum -a 256 vs CAPTURES.jsonl)

| File | sha256 (prefix) | Row | Used |
|---|---|---|---|
| ace7dd7-01-boot-passive.png | 282de970 | only under R15-CODE-AGENT-001/ace7dd7-01 (taken 2026-10-02T23:55:48Z), no row for this path | no (coordinates only per DRIVE) |
| ace7dd7-02-cockpit-brief-settled.png | 380d13fa | only under R15-CODE-AGENT-001/ace7dd7-03 (taken 2026-10-02T23:56:23Z, a different launch 5.5 h earlier) | no — not load-bearing; 03/04/05 show the same settled brief |
| ace7dd7-03-save-md-status.png | 43f053fb | rig.py capture, owner Vysted Terminal, 05:23:56Z | yes |
| ace7dd7-04-save-pdf-status.png | d04962ec | rig.py capture, owner Vysted Terminal, 05:24:02Z | yes |
| ace7dd7-04b-save-pdf-status-late.png | 63c394fa | rig.py capture, owner Vysted Terminal, 05:24:04Z | yes (same content as 04) |
| ace7dd7-05-save-png-status.png / 05b | dcc669e7 | rig.py capture, owner Vysted Terminal, 05:24:12Z | yes |
| raw/ace7dd7-export-setfnif50.png | 421cb12d | vysted-export, 05:24:49Z | yes (app-exported file) |

Presence: presence.log line 74 `2026-10-03T05:23:44Z idle=1227.5 sentinel … front=Vysted Terminal vysted=[7353 7372] entry=R15-UI-083 pre-batch-A` precedes every used capture.

## Code at ace7dd7 (src/modules/research/BriefPanel.tsx)
Toolbar carries Save .md / Save PDF / Save PNG; handlers call saveTextArtifact / savePdfArtifact / savePngArtifact into `research/<slug>.{md,pdf,png}` and flash `Saved <path>`; PDF/PNG are `disabled={!bodySettled}`, where `bodySettled` is reduced-motion or a timer sized to the stagger math (items x STAGGER + DUR.fast + 60 ms) keyed to the brief's createdAt.

## Per part

1. **Three file-export actions exist on a populated brief** — 03/04/05: Brief toolbar shows `Save .md  Save PDF  Save PNG` over the populated SETFNIF50 brief (₹252.41, P/E 20.35, 52W 238-287, volume 870K). The clipboard-only repro is gone. HOLDS.
2. **Save .md writes a file** — 03: Save .md highlighted, strip `SAVED /PRIVATE/TMP/CLAUDE-501/-USERS-LOKAVYASING…` (ellipsized). raw/ace7dd7-exports-stat.txt: `setfnif50.md` 1988 B at 10:53:54 IST (= the .md click, 05:23:54Z) under the isolated `exports/research/`. raw/ace7dd7-export-setfnif50.md read back: title, Mode/Symbol/sources/as-of line, full synthesis. HOLDS.
3. **Save PDF writes a settled raster** — 04/04b: Save PDF highlighted, its own `SAVED …` strip (the .md flash's 4.5 s timer had lapsed per batch timing). Stat: `setfnif50.pdf` 7,450,598 B at 10:54:02 IST. I rendered raw/ace7dd7-export-setfnif50.pdf (3 A4 pages) myself with PDFKit to scratchpad: p1 header chips, archived/refresh card, keyless-search card, metric cards, heading; p2 Snapshot, What it is, start of Risks and fit; p3 rest of Risks and fit, Data limits, Sources 1-3, then white page remainder. Every block fully opaque, no faded or missing mid-stagger block. HOLDS.
4. **Save PNG writes a settled raster** — 05: Save PNG highlighted, `SAVED …` strip. Stat: `setfnif50.png` 392,228 B at 10:54:10 IST. raw/ace7dd7-export-setfnif50.png (registered vysted-export, 788x3150) opened: whole brief top to Sources 3 on the dark panel background, all blocks fully opaque, nothing half-rendered. HOLDS.
5. **Writes land through write_atomic in the packaged app** — the three files exist under the isolated data dir's `exports/research/` with mtimes matching each click; no Export failed strip in any capture. HOLDS.

## Adjacent notes (not this entry's defect)
- The status strip truncates in a 1/3-width Brief panel, so the file name is not visible on screen (full path is in the strip's title tooltip). Cosmetic.
- The disabled-before-settle state of PDF/PNG was not captured (the seeded brief had settled before the first click); the code gate is present and the rasters show a settled brief, which is what the note's GUI check asks.
- The PDF's last page has a white remainder below the dark content (page fill not extended). Cosmetic.

## Ruling: CERTIFIED
Every part the note names is visible in registered captures and raw read-backs: three real file exports, each reporting its saved path, and both rasters (PDF, PNG) show the fully settled brief.
