# R15-UI-025 — fresh GUI verify at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

- verifier: Opus 5.5 (fresh context, label gui-verify-R15-UI-025); no GUI, no app launch.
- inputs: register entry (title, repro, fix_shape, note), DRIVE.md, captures + raw/ in this folder, CAPTURES.jsonl, presence.log, code at ace7dd7.
- claim under test (title + fix_shape + note): in the packaged macOS app, selecting text in a note and clicking Link opens an inline URL popover (not window.prompt), and applying it sets the link mark on the selection. Carry-forward narrow redrive adds: the stored note written through the rewritten `write_atomic` contains the link.

## Capture registration

All 8 PNGs cited in DRIVE.md hash to a CAPTURES.jsonl row with tool `scripts/rig/rig.py capture`, window_owner `Vysted Terminal`. Presence lines precede each: 01 (03:56:06Z pre-capture-01, idle 1101.6), 02/03 (03:56:33Z pre-batch-A, idle 1129.2), 04-08 (04:12:04Z pre-batch-B, idle 923.3), sentinel valid to 21:43:50Z. Unregistered captures: none.

## Code at ace7dd7 (read)

- `src/modules/notes/NotesToolbar.tsx`: no `prompt(` call; `LinkPopover` (role dialog, aria-label "Edit link", input aria-label "Link URL"); Link button toggles `linkOpen`; apply -> `extendMarkRange("link").setLink({ href })`.
- `eslint.config.*` bans `window.prompt` (restricted property, message names the inline popover).
- `src/modules/notes/notes-persistence.ts:69-71`: general scope -> `general.md` via `invoke("write_text_atomic")`; `src-tauri/src/lib.rs:563` `write_atomic`, `:610` `write_text_atomic`.

## Parts

| Part | Evidence | What it shows | Ruling |
|---|---|---|---|
| Select text in a note | ace7dd7-04-word-selected.png | "breadth" highlighted in the seeded note; Link button idle. | holds |
| Click Link -> inline URL popover | ace7dd7-05-link-popover.png | Link button active; inline popover under the toolbar with a focused input (placeholder "https://…") and an Apply button; no native dialog. | holds |
| Type URL | ace7dd7-06-url-typed.png | Input reads "https://example.com". | holds |
| Apply sets the link mark on the selection | ace7dd7-07-link-applied.png, ace7dd7-08-link-mark-deselected.png | Popover closed; only "breadth" underlined (link mark), rest of the line plain. | holds |
| Stored note contains the link (rc2 write path) | raw/note-after.txt; raw/ace7dd7-blob-after-batchB.json | `R15 GUI round seed note: watch SPY [breadth](https://example.com) and NVDA earnings.` (before: raw/note-before.txt, an unrelated line); blob `notes.general` carries the same markdown link. | holds |
| Batch integrity | raw/ace7dd7-batch-B.json, raw/ace7dd7-batch-B.log | 15 steps (double-click, Link click, type, Return, click-out, captures), all ok. | holds |

## Notes

- App was the `target/debug/bundle/macos/Vysted Terminal.app` bundle built from ace7dd7 (WKWebView, the failing surface); accepted as the packaged app for this WKWebView-only defect.
- Adjacent cosmetic (not this entry): at this split width the popover runs past the Notes panel's right edge, clipping "Apply" to "App" (visible in 05/06). Enter applied the link; a mouse-only user could still click the visible "App" portion. Worth a low follow-up, not a regression of R15-UI-025.

## Verdict: certified

Every part the note names (popover appears, apply sets the link mark) plus the carry-forward stored-note check is shown in registered captures and raw read-backs at ace7dd7.
