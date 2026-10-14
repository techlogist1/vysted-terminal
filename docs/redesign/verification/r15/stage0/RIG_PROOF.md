# RIG_PROOF — presence safety, demonstrated by refusal

**Date:** 2026-09-19 · **Tool:** `scripts/rig/rig.py` · **Branch:** `worktree-agent-rig`

The operator was physically at the machine for this entire session. **No click, keystroke,
capture, resize or app activation was performed.** The deliverable today is the *refusal*:
every guarded path was exercised and every one declined without side effects.

## 1. Unguarded reads work

```
$ rig.py idle
1990.6
exit=0
$ rig.py bounds
{"owner": "vysted-terminal", "id": 13553, "layer": 0, "bounds": [116.0, 44.0, 1280.0, 832.0]}
exit=0
```

`idle` and `bounds` are pure reads (`CGEventSourceSecondsSinceLastEventType`,
`CGWindowListCopyWindowInfo`) and are deliberately not gated.

## 2. Every guarded action refuses, exit 3, no side effect

```
$ rig.py --min-idle 99999 capture /tmp/rig-proof.png
REFUSED: idle 1991.3s < required 99999s - operator may be present
exit=3
$ rig.py --min-idle 99999 click 100 762
REFUSED: idle 1991.6s < required 99999s - operator may be present
exit=3
$ rig.py --min-idle 99999 type hello
REFUSED: idle 1992.0s < required 99999s - operator may be present
exit=3
$ rig.py --min-idle 99999 key cmd+k
REFUSED: idle 1992.4s < required 99999s - operator may be present
exit=3
$ rig.py --min-idle 99999 resize 1280 832
REFUSED: idle 1992.7s < required 99999s - operator may be present
exit=3
$ rig.py --min-idle 99999 batch /tmp/rig-batch.json   # [click, type]
REFUSED: idle 2051.7s < required 99999s - operator may be present
exit=3
```

The batch refused at **step 0** — no `step 0 ... ok` line was emitted.

## 3. The env var cannot lower the bar

```
$ VYSTED_RIG_MIN_IDLE=1 rig.py --min-idle 99999 capture /tmp/rig-proof2.png
REFUSED: idle 2052.0s < required 99999s - operator may be present
exit=3
```

`resolve_min_idle` is `max(300, flag, env)` (`scripts/rig/rig.py:104-114`): the env var can
only raise the bar, and nothing resolves below the 300s floor.

## 4. Nothing was written

```
"/tmp/rig-proof.png": No such file or directory
"/tmp/rig-proof2.png": No such file or directory
"docs/redesign/verification/r15/RIG_ABORTS.log": No such file or directory
"docs/redesign/verification/r15/CAPTURES.jsonl": No such file or directory
```

A refusal is not an abort: it produces no capture, no `CAPTURES.jsonl` row, and no
`RIG_ABORTS.log` line.

## 5. Earlier in the session the DEFAULT bar refused too

The first proof pass ran before idle crossed 900s, so it exercised the shipped default with
no `--min-idle` override:

```
$ rig.py capture /tmp/should-not-exist-rig.png
REFUSED: idle 864.0s < required 900s - operator may be present
exit=3
$ rig.py click 100 762
REFUSED: idle 864.3s < required 900s - operator may be present
exit=3
$ rig.py key "cmd+k"
REFUSED: idle 864.6s < required 900s - operator may be present
exit=3
```

Once idle passed 900s, every subsequent live invocation pinned `--min-idle 99999` so that
no real GUI event could fire while the operator was present.

## 6. Guard logic under test (27 tests, injected providers)

```
$ sidecar/.venv/bin/python3 -m pytest scripts/rig/test_rig_guard.py
27 passed in 0.33s
```

Covering, among others:

- `test_batch_aborts_when_a_human_touches_the_machine` — 30s since the rig's own event but
  the idle clock reads 1s ⇒ a human typed ⇒ `Refused`.
- `test_batch_tolerates_the_rigs_own_events_resetting_the_idle_clock` — the complement, so
  the detector is not merely always-on.
- `test_frontmost_surprise_deletes_the_capture` — capture succeeds, then frontmost is
  another app ⇒ `Aborted` **and the PNG is unlinked**.
- `test_presence_gate_runs_before_activation` — with the operator present, `activate` is
  never called; the rig will not pull the Vysted window forward.
- `test_cli_exposes_no_flag_to_disable_the_guard` — source contains no `--force`,
  `--no-guard`, `--unsafe`, `--skip-presence`.

## 7. Capture path verified without capturing the screen

Capturing a real window would have photographed the operator's session, so the path was
verified in two safe halves:

- `CGWindowListCreateImage(..., 999999, ...)` on a non-existent window id → `None`,
  confirming the binding is live and that a missing window yields no image.
- `png_write` driven with a **synthetic** 8×8 `CGBitmapContext` image → 161-byte PNG,
  sha256 `d5ad30168283d558…`. The CGImageDestination write path works.

`do_capture` passes a single window id with `kCGWindowListOptionIncludingWindow`
(`scripts/rig/rig.py:247-252`); there is no code path that captures the desktop.

---

## Finding for the lead — idle is not absence

`HIDIdleTime` measures input silence, not human presence. **Measured today:** the operator
was at the machine continuously, and idle climbed **207s → 2052s** purely because he was not
typing. The shipped 900s default was crossed around the 15-minute mark *while he was sitting
there.* This is the same hole that produced the R13 private-screen capture (D75) — a longer
idle threshold narrows it but never closes it.

What genuinely protects the operator in this build is not the idle bar:

- **Foreground gate** — Vysted must own the foreground, so the rig cannot act while the
  operator is in their mail, Messages or 1Password.
- **Mid-batch human detector** — the moment they touch anything, the batch aborts.
- **Surprise detector** — any new foreign window or focus change deletes the capture.

**Decision requested.** If the lead wants a hard guarantee rather than a heuristic, the cheap
upgrade is an explicit operator-away sentinel required *in addition* to idle: a file (e.g.
`~/.vysted-rig-away`) carrying an expiry timestamp that the operator writes when he leaves,
checked in `Guard.presence()`. That is ~5 lines and makes "away" an operator assertion rather
than an inference. I did not bake it in because it changes the contract this job specified and
would silently make the rig refuse every run until the lead knows about it.

Second, smaller decision: `resize` currently targets `front window of the frontmost process`
via System Events (`rig.py:341-348`) rather than the Vysted window id. The foreground gate
means the frontmost process is Vysted whenever the call runs, so it is safe — but it is
indirect, and worth replacing with an AX-by-window-id call if resize ever runs on a machine
with multiple Vysted windows.
