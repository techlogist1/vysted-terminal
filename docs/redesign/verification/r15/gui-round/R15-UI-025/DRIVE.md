# R15-UI-025 — GUI drive at ace7dd7 (rc2 candidate, session 3)

- entry: R15-UI-025 (medium) — Notes toolbar Link was a silent no-op in the macOS app (window.prompt unimplemented in WKWebView); fix = inline URL popover.
- carry-forward: CARRY_FORWARD_rc2.md lists R15-UI-025 as **redrive (narrow)**: popover + link mark unchanged; the stored-note write (`persistNoteMd` -> `safeFilename` -> `write_text_atomic` -> rewritten `write_atomic`) must be re-confirmed (raw/note-after.txt).
- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (gui worktree scratchpad/gui-ace7dd7, HEAD verified)
- app: scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (packaged binary)
- isolated home: scratchpad/gui-round-home-R15-UI-025 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true})
- real ~/Library/Application Support/com.vysted.terminal mtime before: 1790978102

## Code read at ace7dd7 (before driving)

- NotesToolbar.tsx:122-197 `LinkPopover`: role=dialog aria-label "Edit link", autofocused input (aria-label "Link URL", placeholder "https://…"), Enter or Apply -> `onApply(value.trim())`; Remove only when a link exists; click-outside/Escape close.
- NotesToolbar.tsx:221-243, 357-374: Link button toggles `linkOpen`; `applyLink` -> `editor.chain().focus().extendMarkRange("link").setLink({ href }).run()`; button `active={editor.isActive("link")}`.
- NotesPanel.tsx:157-191: editor update -> 600 ms debounce -> `flush` -> store `setGeneral` + `persistNoteMd(scope, md)`.
- notes-persistence.ts:61-74: `{get_app_data_dir}/notes/general.md` (no scope) via `invoke("write_text_atomic")`; lib.rs:563 `write_atomic`, :610 `write_text_atomic`.
- raw/note-before.txt = seed's notes/general.md before launch.

## Presence / steps

- 2026-10-03T03:52:57Z idle=912.7 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] (pre-launch-1)
- Boot 1 (seeding): pid 80881 at 2026-10-03T03:52:57Z; children 80893 vysted-sidecar --port 58035 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal (--cache-dir same), 80891 openbb-mcp 58036, 80892 sec-edgar-mcp 58037; logs/vysted.log under the isolated home. GET /workspace/__autosave__ -> raw/ace7dd7-seed-before.json (portfolio|chart + brief, no Notes panel); POST /workspace raw/ace7dd7-seed-post.json (R15-UI-009's ace7dd7 seed: 7 watchlist symbols AAPL/MSFT/NVDA/SPY/QQQ/BTC/USDT/ETH/USDT, holdings AAPL 10 @ 180 + NVDA 5 @ 120, general note "R15 GUI round seed note: watch SPY breadth and NVDA earnings."; changed for this entry: Notes panel added to leaf 1 and active, agent dock collapsed) -> {"status":"saved"}. Killed 80881 + 80891/80892/80893 by pid; none left; blob on disk carries the notes panel, 7 symbols, the note. raw/app-stdout-boot1.log, raw/vysted-boot1.log (0 keychain/SecurityAgent lines).
- 2026-10-03T03:55:07Z idle=1042.3 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] (pre-launch-2)
- Launch 2 (drive): pid 81599 at 2026-10-03T03:55:13Z; children 81611 vysted-sidecar --port 59326 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal (ps args), 81609 openbb-mcp 59327, 81610 sec-edgar-mcp 59328; 81608 is the WebKit WebContent XPC lsappinfo lists with it. /health on :59326 -> 200. Window bounds [116,43,1280,832] -> launched size 1280x832 points (captures 2560x1664). Launched unactivated (Finder front); brought my pid 81599 front via System Events `set frontmost` (no input event), as R15-UI-009/022 did.
- 2026-10-03T03:56:06Z idle=1101.6 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[81599 81608] (pre-capture-01)
- ace7dd7-01-boot-passive.png (opened): dark theme; "Welcome to Vysted" terms modal over the seeded layout: Portfolio | Chart | Notes tabs (Notes active), Notes panel with General scope, toolbar H1 H2 H3 B I code lists quote ..., the seed note text; Brief SETFNIF50 ₹252.41 on the right; CONNECTED pill.

## Batch A — raw/ace7dd7-batch-A.json (terms)

- 2026-10-03T03:56:33Z idle=1129.2 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[81599 81608] (pre-batch-A)
- Steps: accept terms (768,598); capture 02; onboarding Skip position (502,728) (precedent; no onboarding card appeared, the click landed in the empty editor area below the note); capture 03. All steps exit 0 (raw/ace7dd7-batch-A.log), no abort. 02 intermediate (not opened).
- ace7dd7-03-after-onboarding.png (opened): modal gone. Notes panel: General scope, toolbar H1 H2 H3 | B I <> | bullet/ordered/task lists | quote, code block | **Link** (chain icon, display x 671) | [ ] wikilink; note text "R15 GUI round seed note: watch SPY breadth and NVDA earnings."; Brief populated (₹252.41, P/E 20.35, 52W 238-287).

## Batch B — raw/ace7dd7-batch-B.json (select word, Link, popover, apply)

- 2026-10-03T04:12:04Z idle=923.3 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[81599 81608] (pre-batch-B)
- Steps (points = capture-03 display px x 0.64): double-click "breadth" (307.2,305.9) -> 04; Link button (429.4,261.8) -> 05; type "https://example.com" -> 06; key return -> wait 2 s -> 07; click empty editor area (320,512) -> wait 3 s -> 08. All 15 steps exit 0 (raw/ace7dd7-batch-B.log), no abort.
- ace7dd7-04-word-selected.png (opened): "breadth" highlighted (selection) in the note line; Link button idle.
- ace7dd7-05-link-popover.png (opened): Link button now shown active (filled background); an inline popover directly under the toolbar's Link button, over the note line: a text input with a focused caret and placeholder "https://…" and an "App[ly]" button. No native prompt/dialog. Adjacent cosmetic observation (not this entry's defect): at this split width the popover (w-64, anchored left at the Link button) runs past the Notes panel's right edge, so the Apply button is clipped to "App"; Enter applies, which is the path used.
- ace7dd7-06-url-typed.png (opened): the input reads "https://example.com" with the caret after it.
- ace7dd7-07-link-applied.png (opened): popover closed; "breadth" is now underlined (link mark) in the note line; Link button shown active (cursor inside the link).
- ace7dd7-08-link-mark-deselected.png (opened): same — "breadth" underlined as a link, rest of the line plain; the Link button still shows active (the click landed below the editor's content box, so the cursor stayed in the link).
- Read-back: raw/note-after.txt = `<isolated home>/.../com.vysted.terminal/notes/general.md` after the batch: `R15 GUI round seed note: watch SPY [breadth](https://example.com) and NVDA earnings.` (84 bytes, mtime 2026-10-03T04:12:10Z, inside the batch window; before: raw/note-before.txt, the seed's unrelated tatasteel line). That file is written only by `persistNoteMd` -> `invoke("write_text_atomic")` -> `write_atomic`, so the rewritten rc2 write path ran and produced the link. Autosave blob (raw/ace7dd7-blob-after-batchB.json, GET /workspace/__autosave__ on MY sidecar :59326) notes.general carries the same markdown link.

## Teardown

- kill 81599, then 81609/81610/81611 by pid; ps shows none of them and no process from gui-ace7dd7's bundle or the isolated home; lsappinfo lists no Vysted app. No vite started (packaged binary).
- raw/vysted.log copied (isolated log; 0 keychain/SecurityAgent lines); raw/app-stdout.log, raw/app-stdout-boot1.log, raw/vysted-boot1.log.
- real ~/Library/Application Support/com.vysted.terminal mtime after: 1790978102 (= before). No keychain / SecurityAgent dialog in any capture.

## Stops

- None. No rig refusal, no abort, no foreign window, no human input during either batch.

## Checks

- (1) Select a word, click Link: an inline URL popover appears (no window.prompt no-op): SHOWN — 04, 05.
- (2) Type https://example.com and apply: the selection carries the link mark: SHOWN — 06, 07, 08.
- (3) The stored note under the isolated data dir contains the link (rc2 write_atomic path): SHOWN — raw/note-after.txt `[breadth](https://example.com)`, plus the autosave blob.

## Verdict: HOLDS — popover, link mark and stored-note link all shown in the packaged ace7dd7 app and read back from the isolated data dir.
