#!/usr/bin/env python3
"""Vysted GUI rig with operator-presence safety welded in.

Run with the sidecar venv python (it is the only interpreter here with PyObjC):

    sidecar/.venv/bin/python3 scripts/rig/rig.py <subcommand> ...

Every acting subcommand (click/type/key/resize/capture) refuses unless the machine
has been idle long enough AND the Vysted window owns the foreground. There is no
flag to turn that off.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import Quartz
import register_capture as capture_registry

try:
    from AppKit import NSWorkspace
except ImportError:  # pragma: no cover - PyObjC always ships AppKit with Quartz
    NSWorkspace = None

REPO = Path(__file__).resolve().parents[2]
ABORTS = REPO / "docs/redesign/verification/r15/RIG_ABORTS.log"

EXIT_USAGE = 2  # argparse's own code, reused for a combo/step we cannot render
EXIT_PRESENCE = 3
EXIT_SURPRISE = 4

DEFAULT_MIN_IDLE = 900.0
IDLE_FLOOR = 300.0  # VYSTED_RIG_MIN_IDLE may raise the bar, never drop below this
EVENT_TOLERANCE = 1.5  # seconds of slack between our own event and the idle clock
OWNER_MATCH = "vysted"

# Idle is input silence, not absence: measured 2026-09-19, idle climbed past 3480s
# while the operator sat at the machine reading. So "away" must be ASSERTED, not
# inferred -- the operator writes an expiry into this file when he actually leaves.
AWAY_SENTINEL = Path.home() / ".vysted-rig-away"
AWAY_HINT = (
    "no unexpired operator-away sentinel at ~/.vysted-rig-away "
    "(idle reads {idle:.0f}s, but idle is input silence, not absence). "
    "The operator arms it when he leaves:\n"
    "  date -u -v+45M +%Y-%m-%dT%H:%M:%S+00:00 > ~/.vysted-rig-away"
)


class Refused(Exception):
    """Presence gate said no. Nothing happened."""


class Aborted(Exception):
    """Something unexpected owns the screen. Stop and clean up."""


# --- providers (swapped for fakes in test_rig_guard.py) -----------------------


def real_idle() -> float:
    """Seconds since the last human OR synthetic input event (tracks HIDIdleTime)."""
    return Quartz.CGEventSourceSecondsSinceLastEventType(
        Quartz.kCGEventSourceStateCombinedSessionState, Quartz.kCGAnyInputEventType
    )


def real_frontmost() -> str:
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.localizedName() if app else ""


def real_windows() -> list[dict]:
    raw = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    out = []
    for w in raw or []:
        b = w.get("kCGWindowBounds") or {}
        out.append(
            {
                "owner": w.get("kCGWindowOwnerName") or "",
                "id": int(w.get("kCGWindowNumber") or 0),
                "layer": int(w.get("kCGWindowLayer") or 0),
                "bounds": (
                    float(b.get("X", 0)),
                    float(b.get("Y", 0)),
                    float(b.get("Width", 0)),
                    float(b.get("Height", 0)),
                ),
            }
        )
    return out


def real_activate() -> None:
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if is_vysted(app.localizedName()):
            app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
            return


def is_vysted(name: str | None) -> bool:
    return OWNER_MATCH in (name or "").lower()


def real_away(path: Path | None = None) -> datetime | None:
    """Expiry from the operator's away-sentinel; None if absent, expired or garbage."""
    try:
        stamp = datetime.fromisoformat((path or AWAY_SENTINEL).read_text().strip())
    except (OSError, ValueError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp if stamp > datetime.now(timezone.utc) else None


def resolve_min_idle(flag: float | None = None, env: str | None = None) -> float:
    """--min-idle sets the bar; the env var may only RAISE it; never below IDLE_FLOOR."""
    if env is None:
        env = os.environ.get("VYSTED_RIG_MIN_IDLE")
    bar = DEFAULT_MIN_IDLE if flag is None else float(flag)
    if env:
        try:
            bar = max(bar, float(env))
        except ValueError:
            pass
    return max(IDLE_FLOOR, bar)


# --- the guard ---------------------------------------------------------------


class Guard:
    """Presence gate. One instance per run; a batch shares it so `last_event` carries."""

    def __init__(
        self,
        min_idle: float,
        idle=real_idle,
        frontmost=real_frontmost,
        windows=real_windows,
        activate=real_activate,
        away=real_away,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        self.min_idle = min_idle
        self.idle = idle
        self.frontmost = frontmost
        self.windows = windows
        self.activate = activate
        self.away = away
        self.clock = clock
        self.sleep = sleep
        self.last_event: float | None = None

    def presence(self) -> float:
        """Raise Refused unless the operator is provably away."""
        idle = self.idle()
        if self.last_event is None:
            if idle < self.min_idle:
                raise Refused(
                    f"idle {idle:.1f}s < required {self.min_idle:.0f}s - operator may be present"
                )
        else:
            # Our own events reset the idle clock, so compare against them instead:
            # an idle clock younger than our last event means a HUMAN typed/clicked.
            since = self.clock() - self.last_event
            if idle < since - EVENT_TOLERANCE:
                raise Refused(
                    f"human input detected mid-batch: idle {idle:.1f}s but "
                    f"{since:.1f}s since the rig's own last event"
                )
        # Second, independent gate. Re-checked every step, so a sentinel that expires
        # mid-batch stops the run rather than riding to the end.
        if self.away() is None:
            raise Refused(AWAY_HINT.format(idle=idle))
        return idle

    def require_front(self, may_activate: bool = False) -> str:
        name = self.frontmost()
        if is_vysted(name):
            return name
        if may_activate:
            self.activate()
            self.sleep(0.6)
            name = self.frontmost()
            if is_vysted(name):
                return name
        raise Aborted(f"frontmost app is {name!r}, not Vysted")

    def before(self, may_activate: bool = False) -> None:
        self.presence()
        self.require_front(may_activate=may_activate)

    def mark_event(self) -> None:
        """Call right after posting a synthetic input event (click/keystroke)."""
        self.last_event = self.clock()

    def owners(self) -> set[str]:
        return {w["owner"] for w in self.windows() if w["layer"] == 0}

    def check_surprise(self, before: set[str], window_id: int | None = None) -> None:
        """Foreign window appeared, focus moved, or our target window changed hands."""
        new = {o for o in self.owners() - before if not is_vysted(o)}
        if new:
            raise Aborted(f"unexpected window(s) from {sorted(new)}")
        name = self.frontmost()
        if not is_vysted(name):
            raise Aborted(f"frontmost app changed to {name!r} during the action")
        if window_id is not None:
            owner = next(
                (w["owner"] for w in self.windows() if w["id"] == window_id), None
            )
            if not is_vysted(owner):
                raise Aborted(f"captured window {window_id} now belongs to {owner!r}")

    def vysted_window(self) -> dict:
        wins = [w for w in self.windows() if is_vysted(w["owner"]) and w["layer"] == 0]
        if not wins:
            raise Aborted("no on-screen Vysted window")
        return max(wins, key=lambda w: w["bounds"][2] * w["bounds"][3])


def log_abort(reason: str) -> None:
    ABORTS.parent.mkdir(parents=True, exist_ok=True)
    with ABORTS.open("a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} ABORT {reason}\n")


# --- actions -----------------------------------------------------------------


def png_write(image, path: Path) -> None:
    from CoreFoundation import CFURLCreateWithFileSystemPath, kCFAllocatorDefault

    path.parent.mkdir(parents=True, exist_ok=True)
    url = CFURLCreateWithFileSystemPath(kCFAllocatorDefault, str(path), 0, False)
    dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    if dest is None:
        raise RuntimeError("CGImageDestinationCreateWithURL failed")
    Quartz.CGImageDestinationAddImage(dest, image, None)
    if not Quartz.CGImageDestinationFinalize(dest):
        raise RuntimeError(f"failed to write {path}")


def do_capture(guard: Guard, out: Path) -> dict:
    guard.before(may_activate=True)
    before = guard.owners()
    win = guard.vysted_window()
    image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        win["id"],
        Quartz.kCGWindowImageBoundsIgnoreFraming,
    )
    if image is None:
        raise Aborted(f"capture of window {win['id']} returned no image")
    png_write(image, out)
    try:
        guard.check_surprise(before, window_id=win["id"])
    except Aborted:
        out.unlink(missing_ok=True)
        raise
    return capture_registry.register_capture(
        out, "scripts/rig/rig.py capture", guard.frontmost(), win["owner"]
    )


def do_click(guard: Guard, x: float, y: float, double: bool = False) -> None:
    guard.before(may_activate=True)
    before = guard.owners()
    bx, by, _, _ = guard.vysted_window()["bounds"]
    pt = Quartz.CGPointMake(bx + x, by + y)
    for click_state in (1, 2) if double else (1,):
        for kind in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
            ev = Quartz.CGEventCreateMouseEvent(
                None, kind, pt, Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventSetIntegerValueField(
                ev, Quartz.kCGMouseEventClickState, click_state
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
            time.sleep(0.02)
    guard.mark_event()
    guard.check_surprise(before)


KEY_CODES = {
    "return": 36,
    "enter": 36,
    "tab": 48,
    "space": 49,
    "delete": 51,
    "escape": 53,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
}
MODIFIERS = {
    "cmd": "command down",
    "command": "command down",
    "shift": "shift down",
    "opt": "option down",
    "option": "option down",
    "alt": "option down",
    "ctrl": "control down",
    "control": "control down",
}


def osascript(script: str) -> None:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"osascript failed: {r.stderr.strip()}")


def applescript_quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def do_type(guard: Guard, text: str) -> None:
    guard.before(may_activate=True)
    before = guard.owners()
    osascript(
        f'tell application "System Events" to keystroke "{applescript_quote(text)}"'
    )
    guard.mark_event()
    guard.check_surprise(before)


def parse_combo(combo: str) -> str:
    """'cmd+k' -> a System Events verb. Raises on anything it cannot render exactly.

    Dropping an unrecognised modifier or stringifying an unrecognised key name would
    post a DIFFERENT event than the caller asked for -- a silent wrong keystroke into
    the operator's live app. Refuse instead.
    """
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        raise ValueError("empty key combo")
    key, mod_names = parts[-1], parts[:-1]
    unknown = [m for m in mod_names if m not in MODIFIERS]
    if unknown:
        raise ValueError(f"unknown modifier(s) {unknown} in {combo!r}")
    if key in KEY_CODES:
        verb = f"key code {KEY_CODES[key]}"
    elif len(key) == 1:
        verb = f'keystroke "{applescript_quote(key)}"'
    else:
        raise ValueError(
            f"unknown key {key!r} in {combo!r}: expected one character or one of "
            f"{sorted(KEY_CODES)}"
        )
    mods = [MODIFIERS[m] for m in mod_names]
    return f"{verb} using {{{', '.join(mods)}}}" if mods else verb


def do_key(guard: Guard, combo: str) -> None:
    verb = parse_combo(combo)  # parse first: a typo must not spend a gate pass
    guard.before(may_activate=True)
    before = guard.owners()
    osascript(f'tell application "System Events" to {verb}')
    guard.mark_event()
    guard.check_surprise(before)


def do_resize(guard: Guard, w: int, h: int) -> None:
    guard.before(may_activate=True)
    before = guard.owners()
    osascript(
        'tell application "System Events" to tell (first application process whose '
        f"frontmost is true) to set size of front window to {{{w}, {h}}}"
    )
    guard.check_surprise(before)


def run_step(guard: Guard, step: dict) -> None:
    cmd = step.get("cmd")
    if cmd == "click":
        do_click(guard, float(step["x"]), float(step["y"]), bool(step.get("double")))
    elif cmd == "type":
        do_type(guard, step["text"])
    elif cmd == "key":
        do_key(guard, step["combo"])
    elif cmd == "resize":
        do_resize(guard, int(step["w"]), int(step["h"]))
    elif cmd == "capture":
        print(json.dumps(do_capture(guard, Path(step["out"]).resolve())))
    elif cmd == "wait":
        guard.sleep(float(step.get("seconds", 1)))
    else:
        raise ValueError(f"unknown batch step {cmd!r}")


# --- cli ---------------------------------------------------------------------

ACTING_COMMANDS = {"capture", "click", "type", "key", "resize", "batch"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rig.py", description=__doc__)
    p.add_argument(
        "--min-idle", type=float, default=None, help="seconds; floor 300, default 900"
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("idle")
    sub.add_parser("bounds")
    c = sub.add_parser("capture")
    c.add_argument("out")
    k = sub.add_parser("click")
    k.add_argument("x", type=float)
    k.add_argument("y", type=float)
    k.add_argument("--double", action="store_true")
    t = sub.add_parser("type")
    t.add_argument("text")
    ky = sub.add_parser("key")
    ky.add_argument("combo")
    rz = sub.add_parser("resize")
    rz.add_argument("w", type=int)
    rz.add_argument("h", type=int)
    b = sub.add_parser("batch")
    b.add_argument("file")
    a = p.parse_args(argv)

    guard = Guard(resolve_min_idle(a.min_idle))
    try:
        if a.cmd == "idle":
            print(f"{real_idle():.1f}")
        elif a.cmd == "bounds":
            print(json.dumps(guard.vysted_window()))
        elif a.cmd == "capture":
            print(json.dumps(do_capture(guard, Path(a.out).resolve())))
        elif a.cmd == "click":
            do_click(guard, a.x, a.y, a.double)
        elif a.cmd == "type":
            do_type(guard, a.text)
        elif a.cmd == "key":
            do_key(guard, a.combo)
        elif a.cmd == "resize":
            do_resize(guard, a.w, a.h)
        elif a.cmd == "batch":
            steps = json.loads(Path(a.file).read_text())
            for i, step in enumerate(steps):
                run_step(guard, step)
                print(f"step {i} {step.get('cmd')} ok", file=sys.stderr)
    except ValueError as e:
        # A combo/batch-step we cannot render exactly. Nothing was posted.
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_USAGE
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_PRESENCE
    except Aborted as e:
        # Only acting commands write the safety log; a failed `bounds` read must not
        # cry wolf in RIG_ABORTS.log and mask a real presence surprise.
        if a.cmd in ACTING_COMMANDS:
            log_abort(f"{a.cmd}: {e}")
        print(f"ABORT: {e}", file=sys.stderr)
        return EXIT_SURPRISE
    return 0


if __name__ == "__main__":
    sys.exit(main())
