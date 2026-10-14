# R15-UI-050 GUI verify at ace7dd7

- verifier: fresh Opus (claude-opus-5-5), label gui-verify-R15-UI-050; no GUI, no app launch
- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd
- claim (title + fix_shape): Notes slash-menu two-line rows no longer sit in a fixed 32px row; rows are `min-h-8 ... py-1`, descriptions stay inside their own row, the active background does not cut the next item.
- GUI check named by the note: whether a two-line row still clips (visual).

## Code at ace7dd7

`src/modules/notes/NotesPanel.tsx:396` slash popup row: `flex min-h-8 w-full flex-col items-start justify-center px-3 py-1`; two `text-caption` spans (title, description, :407-408); active row `bg-charcoal-800`. No fixed `h-8` on the row.

## Capture registration (sha256 vs CAPTURES.jsonl, tool `scripts/rig/rig.py capture`, window_owner `Vysted Terminal`)

| capture | sha256 (prefix) | registered | presence line before |
|---|---|---|---|
| ace7dd7-09-slash-menu-open.png | 2fbc3393 | yes, 05:03:16Z | 05:03:12Z idle=922.3, front=Vysted Terminal (pre-batch-C) |
| ace7dd7-10-slash-menu-down2-active.png | 7cd351fc | yes, 05:03:18Z | same |
| ace7dd7-01, -02, -06 | registered | not load-bearing (no slash menu) |
| ace7dd7-03, -04, -05, -07, -08 | bytes equal 02/06, no CAPTURES row under their own paths | unregistered, ignored (DRIVE.md also marks them not evidence) |

## Per part

1. Slash menu open, two-line rows not clipped: ace7dd7-09 (opened). "/" on a new empty line, menu directly below. Heading 1/2/3, Bullet List, Numbered List each show title over a grey description fully inside the row with clear space before the next title. Task List's description wraps and the row grows to three lines, unclipped. Blockquote at the bottom edge is the menu's scroll container (scrollbar visible), not a row clip. Ruling: holds.
2. Active row background does not cut the next item: ace7dd7-10 (opened). After down x2 the highlight is on Heading 3; it covers "Heading 3" and "Small section heading" and ends above "Bullet List", whose text is intact. Ruling: holds.
3. Raw read-back: raw/ace7dd7-batch-C.log, 13 steps ok, both captures emitted with the registered sha256s. Holds.

Not part of this GUI check: the fix_shape's render-test pin (headless, already ruled in batch-9).

## Verdict

certified — the defect (fixed h-8 two-line rows overrunning, active background cutting the next row) is absent in registered captures 09 and 10; rows size to content at ace7dd7.
