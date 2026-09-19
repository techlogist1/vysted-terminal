# scripts/rig — the Vysted GUI rig

Durable replacement for the `/tmp/rigcap.py` + ad-hoc clicker scripts that earlier runs
kept outside the repo (and lost on every reboot). Presence safety lives **inside the
tool**, not in a runbook, because a runbook is what failed in R13.

Run it with the sidecar venv python — it is the only interpreter on this Mac with PyObjC:

```
sidecar/.venv/bin/python3 scripts/rig/rig.py <subcommand>
```

## Subcommands

| Command                | Guarded | What it does                                                                                                                      |
| ---------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `idle`                 | no      | seconds since the last input event (tracks `HIDIdleTime`)                                                                         |
| `bounds`               | no      | `{owner,id,layer,bounds}` of the Vysted window                                                                                    |
| `capture OUT.png`      | **yes** | `CGWindowListCreateImage` of **only** the Vysted window id, then appends a row to `docs/redesign/verification/r15/CAPTURES.jsonl` |
| `click X Y [--double]` | **yes** | Quartz `CGEventPost`; X/Y are **window-relative**, converted via `bounds`                                                         |
| `type "text"`          | **yes** | AppleScript System Events keystroke (trusted input — reaches WKWebView)                                                           |
| `key "cmd+k"`          | **yes** | same, with modifiers; `return/tab/escape/space/delete/arrows` go via key code                                                     |
| `resize W H`           | **yes** | System Events `set size of front window` (app clamps at ~960px min width)                                                         |
| `batch FILE.json`      | **yes** | a list of the above as one guarded batch; `{"cmd":"wait","seconds":N}` also allowed                                               |

`capture` never touches the full screen — it passes a single window id with
`kCGWindowListOptionIncludingWindow`. There is no code path that captures the desktop.

`register_capture.py PNG --tool NAME` is the same registry as a CLI, for tools that take
their own screenshots (the headless browser harness). Stdlib-only on purpose — no PyObjC —
so a scratch venv can call it. It registers provenance; it never captures anything.

## Presence safety

Checked before **every** guarded action, and before **every step** of a batch:

1. **Away sentinel.** `~/.vysted-rig-away` must hold an ISO timestamp in the future — the
   operator writes it when he _actually leaves_. Absent, expired or garbage ⇒ refuse.
   Re-read every step, so a sentinel that expires mid-batch stops the run there. This gate
   exists because idle is input silence, not absence (see the ceiling note below): away is
   **asserted**, never inferred.
   ```
   date -u -v+45M +%Y-%m-%dT%H:%M:%S+00:00 > ~/.vysted-rig-away
   ```
2. **Idle gate.** Refuse unless idle ≥ `--min-idle` (default **900s**). `VYSTED_RIG_MIN_IDLE`
   may only **raise** the bar; nothing can go below the **300s** floor. Exit code **3**,
   nothing is written.
3. **Mid-batch human detector.** The rig's own synthetic events reset the idle clock, so
   after the first action the gate stops comparing to the raw bar and instead compares idle
   against time since the rig's own last event (1.5s tolerance). Idle younger than our last
   event ⇒ a _human_ touched the machine ⇒ refuse, exit **3**.
4. **Foreground gate.** Vysted must own the foreground. The rig may `activate` it only on
   the first step and only after gates 1–3 have already passed — a present operator never
   gets their window yanked forward.
5. **Surprise detector.** After each action: no new window from a foreign app, frontmost
   still Vysted, and (for a capture) the captured window id still owned by Vysted. On any
   surprise the batch **aborts**, the capture file is **deleted**, exit **4**, and a line
   lands in `docs/redesign/verification/r15/RIG_ABORTS.log`.

Gates 1 and 2 are **independent and both required** — a huge idle reading alone does not
open the gate, and an armed sentinel alone does not either.

**There is no flag to disable any of this.** `test_rig_guard.py` asserts the source
contains no `--force` / `--no-guard` / `--unsafe` / `--skip-presence` escape hatch.

Exit codes: `0` ok · `2` bad key combo / batch step (nothing posted) · `3` refused
(presence) · `4` aborted (surprise).

A key combo is rendered before the gate is touched and **refused** if any part is
unrecognised — `hyper+k` does not degrade to a bare `k`, and `f5` is not typed as text.

### Known ceiling — idle ≠ absence

`HIDIdleTime` measures _input silence_, not human presence. An operator reading the screen
for 15 minutes reads as "away" and the 900s bar opens. Measured during this run: the
operator was physically at the machine the whole time and idle still climbed 207s → 2052s.
That is exactly why gate 1 exists: the idle bar is a secondary filter, not the guarantee.
Behind it, gate 4 means the rig cannot act while the operator is in their mail, and gate 3
aborts the instant they touch anything.

Residual hole: the sentinel is armed for a _window_, so an operator who returns early is
covered only by gates 3–5. Closing that needs a real presence signal (camera/lock state),
which is not worth the dependency.

## Tests

```
sidecar/.venv/bin/python3 -m pytest scripts/rig/test_rig_guard.py
```

27 tests, all providers injected — no real click, keystroke or capture happens. This file
sits outside CI's pytest rootdir (`cd sidecar && pytest`), so it never runs on Linux where
Quartz does not exist.

## Re-measure checklist (run once the operator is genuinely away)

Earlier runs recorded conflicting capability claims across rig generations. Before trusting
any of these, re-measure and record the result in `LESSONS.md`:

- [ ] **Typing into the WKWebView composer.** `rig.py type "hello"` with the composer
      focused. R7 said tauri-mcp `fill` worked; R9 said the socket bridge was dead on
      arrival and AppleScript keystrokes were the only path. Confirm which is true today.
- [ ] **`cmd+k` palette.** `rig.py key "cmd+k"`. Recorded as NOT working twice (synthetic
      keydown lacks trusted meta) — if it still fails, clicking the "⊞ Open panel" toolbar
      button is the fallback. Note that AppleScript System Events _is_ trusted input, so
      this may now pass where tauri-mcp `press_key` did not.
- [ ] **In-webview drag** (dockview tab reorder, node-editor palette→canvas). Needs a
      CGEvent drag sequence (mouse-down, several mouse-dragged, mouse-up), which `click`
      does not do — add a `drag` subcommand only if this is actually needed.
- [ ] **Capture scale.** Confirm the PNG is 2× (2560×1664 for a 1280×832 window). Window
      coords = `file_px × (1280 / file_width)`. Mis-scaling cost three silent mis-clicks in R9.
- [ ] **Screen Recording permission.** If a capture comes back black/empty, the venv
      python's parent process lacks the grant — that is a permission problem, not a rig bug.
