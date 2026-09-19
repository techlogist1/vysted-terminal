"""Guard tests for scripts/rig/rig.py — all providers injected, no real GUI touched.

sidecar/.venv/bin/python3 -m pytest scripts/rig/test_rig_guard.py
"""

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import rig  # noqa: E402

ARMED = datetime.now(timezone.utc) + timedelta(minutes=45)


def guard(
    idle=10_000.0,
    front="vysted-terminal",
    windows=None,
    activate=None,
    min_idle=900.0,
    away=ARMED,
):
    """Guard wired to fakes. `idle`/`front`/`away` accept a list to script reads."""
    clock = [0.0]
    wins = (
        windows
        if windows is not None
        else [
            {
                "owner": "vysted-terminal",
                "id": 1,
                "layer": 0,
                "bounds": (0, 0, 1280, 832),
            }
        ]
    )

    def pop(v):
        return (lambda: v.pop(0)) if isinstance(v, list) else (lambda: v)

    g = rig.Guard(
        min_idle=min_idle,
        idle=pop(idle),
        frontmost=pop(front),
        windows=(lambda: wins) if not callable(wins) else wins,
        activate=activate or (lambda: None),
        away=pop(away),
        clock=lambda: clock[0],
        sleep=lambda _s: None,
    )
    g.tick = lambda dt: clock.__setitem__(0, clock[0] + dt)
    return g


# --- threshold resolution ----------------------------------------------------


def test_default_min_idle_is_900():
    assert rig.resolve_min_idle(None, env=None) == 900.0


def test_env_can_raise_the_bar():
    assert rig.resolve_min_idle(None, env="1800") == 1800.0


def test_env_cannot_lower_the_bar():
    assert rig.resolve_min_idle(None, env="5") == 900.0
    assert rig.resolve_min_idle(600.0, env="5") == 600.0


def test_nothing_goes_below_the_300s_floor():
    assert rig.resolve_min_idle(0.0, env="1") == rig.IDLE_FLOOR
    assert rig.resolve_min_idle(-100.0, env=None) == rig.IDLE_FLOOR


def test_garbage_env_is_ignored():
    assert rig.resolve_min_idle(None, env="not-a-number") == 900.0


# --- presence ----------------------------------------------------------------


def test_presence_refuses_when_operator_may_be_present():
    with pytest.raises(rig.Refused, match="operator may be present"):
        guard(idle=5.0).presence()


def test_presence_passes_when_idle_enough():
    assert guard(idle=901.0).presence() == 901.0


def test_presence_refuses_exactly_at_the_boundary_minus_epsilon():
    with pytest.raises(rig.Refused):
        guard(idle=899.9).presence()


# --- away sentinel: idle is input silence, not absence -----------------------


def test_a_huge_idle_reading_alone_does_not_open_the_gate():
    # Measured live 2026-09-19: idle 5185s with the operator AT the machine.
    with pytest.raises(rig.Refused, match="operator-away sentinel"):
        guard(idle=5185.0, away=None).presence()


def test_away_sentinel_is_rechecked_every_step():
    # Armed at batch start, expired by the second step -> the batch stops there.
    g = guard(idle=[10_000.0, 10_000.0], away=[ARMED, None])
    g.presence()
    with pytest.raises(rig.Refused, match="operator-away sentinel"):
        g.presence()


def test_real_away_reads_the_sentinel_file(tmp_path):
    p = tmp_path / "away"
    assert rig.real_away(p) is None, "absent file must not open the gate"
    p.write_text("not-a-timestamp")
    assert rig.real_away(p) is None, "garbage must not open the gate"
    p.write_text((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
    assert rig.real_away(p) is None, "an expired sentinel must not open the gate"
    p.write_text(ARMED.isoformat())
    assert rig.real_away(p) == ARMED


def test_real_away_treats_a_naive_timestamp_as_utc(tmp_path):
    p = tmp_path / "away"
    p.write_text(ARMED.replace(tzinfo=None).isoformat())
    assert rig.real_away(p) == ARMED


# --- mid-batch: the rig's own events vs a human's ----------------------------


def test_batch_tolerates_the_rigs_own_events_resetting_the_idle_clock():
    g = guard(idle=[1000.0, 2.0])
    g.before()  # batch start: real idle passes
    g.mark_event()
    g.tick(2.0)
    g.presence()  # idle 2.0 ~= 2.0s since our own click -> fine


def test_batch_aborts_when_a_human_touches_the_machine():
    # 30s since our last event, but the idle clock says 1s -> someone else typed.
    g = guard(idle=[1000.0, 1.0])
    g.before()
    g.mark_event()
    g.tick(30.0)
    with pytest.raises(rig.Refused, match="human input detected mid-batch"):
        g.presence()


def test_batch_allows_slack_inside_the_tolerance():
    g = guard(idle=[1000.0, 9.0])
    g.before()
    g.mark_event()
    g.tick(10.0)
    g.presence()  # 9.0 >= 10.0 - 1.5


def test_batch_steps_share_one_guard_so_the_detector_survives(monkeypatch):
    # If a refactor gave each step its own Guard, last_event would reset and the
    # human detector would fall back to the raw idle bar -- which a huge idle
    # reading always passes. This is the regression that would go unnoticed.
    monkeypatch.setattr(rig.Quartz, "CGPointMake", lambda x, y: (x, y))
    monkeypatch.setattr(rig.Quartz, "CGEventCreateMouseEvent", lambda *a: object())
    monkeypatch.setattr(rig.Quartz, "CGEventSetIntegerValueField", lambda *a: None)
    monkeypatch.setattr(rig.Quartz, "CGEventPost", lambda *a: None)
    monkeypatch.setattr(rig.time, "sleep", lambda _s: None)
    g = guard(idle=[10_000.0, 1.0])
    rig.run_step(g, {"cmd": "click", "x": 10, "y": 10})
    assert g.last_event is not None
    g.tick(30.0)
    with pytest.raises(rig.Refused, match="human input detected mid-batch"):
        rig.run_step(g, {"cmd": "click", "x": 20, "y": 20})


# --- foreground --------------------------------------------------------------


def test_require_front_aborts_on_a_foreign_app():
    with pytest.raises(rig.Aborted, match="Spotify"):
        guard(front="Spotify").require_front()


def test_require_front_may_activate_only_when_asked():
    called = []
    g = guard(front=["Spotify", "vysted-terminal"], activate=lambda: called.append(1))
    assert g.require_front(may_activate=True) == "vysted-terminal"
    assert called == [1]


def test_require_front_aborts_if_activation_does_not_take():
    g = guard(front=["Finder", "Finder"], activate=lambda: None)
    with pytest.raises(rig.Aborted):
        g.require_front(may_activate=True)


def test_presence_gate_runs_before_activation():
    # A present operator must never get their window yanked to the front.
    called = []
    g = guard(idle=5.0, front="Spotify", activate=lambda: called.append(1))
    with pytest.raises(rig.Refused):
        g.before(may_activate=True)
    assert called == []


# --- surprise detection ------------------------------------------------------

VYSTED_WIN = {
    "owner": "vysted-terminal",
    "id": 1,
    "layer": 0,
    "bounds": (0, 0, 1280, 832),
}


def test_surprise_on_a_new_foreign_window():
    wins = [VYSTED_WIN]
    g = guard(windows=lambda: wins)
    before = g.owners()
    wins.append({"owner": "1Password", "id": 9, "layer": 0, "bounds": (0, 0, 400, 300)})
    with pytest.raises(rig.Aborted, match="1Password"):
        g.check_surprise(before)


def test_no_surprise_when_vysted_opens_another_window():
    wins = [VYSTED_WIN]
    g = guard(windows=lambda: wins)
    before = g.owners()
    wins.append(
        {"owner": "vysted-terminal", "id": 2, "layer": 0, "bounds": (0, 0, 400, 300)}
    )
    g.check_surprise(before)


def test_surprise_when_focus_moves_away_mid_action():
    g = guard(front=["Messages"])
    with pytest.raises(rig.Aborted, match="frontmost app changed"):
        g.check_surprise({"vysted-terminal"})


def test_surprise_when_the_captured_window_is_not_ours():
    g = guard(
        windows=lambda: [
            VYSTED_WIN,
            {"owner": "Mail", "id": 7, "layer": 0, "bounds": ()},
        ]
    )
    with pytest.raises(rig.Aborted, match="now belongs to"):
        g.check_surprise({"vysted-terminal", "Mail"}, window_id=7)


# --- capture -----------------------------------------------------------------


def test_frontmost_surprise_deletes_the_capture(tmp_path, monkeypatch):
    out = tmp_path / "shot.png"
    monkeypatch.setattr(rig.Quartz, "CGWindowListCreateImage", lambda *a: object())
    monkeypatch.setattr(rig, "png_write", lambda _img, p: p.write_bytes(b"fake-png"))
    # before() sees Vysted; check_surprise() then sees the operator's own app in front.
    g = guard(idle=[10_000.0], front=["vysted-terminal", "Messages"])
    with pytest.raises(rig.Aborted, match="frontmost app changed"):
        rig.do_capture(g, out)
    assert not out.exists(), "a capture taken during a surprise must not survive"


def test_capture_refused_early_writes_nothing(tmp_path):
    out = tmp_path / "shot.png"
    with pytest.raises(rig.Refused):
        rig.do_capture(guard(idle=3.0), out)
    assert not out.exists()


def test_capture_registers_a_row(tmp_path, monkeypatch):
    out = tmp_path / "shot.png"
    monkeypatch.setattr(rig.capture_registry, "CAPTURES", tmp_path / "CAPTURES.jsonl")
    monkeypatch.setattr(rig.Quartz, "CGWindowListCreateImage", lambda *a: object())
    monkeypatch.setattr(rig, "png_write", lambda _img, p: p.write_bytes(b"fake-png"))
    row = rig.do_capture(guard(), out)
    assert set(row) == {
        "sha256",
        "path",
        "tool",
        "frontmost_app",
        "window_owner",
        "taken_at",
    }
    assert row["window_owner"] == "vysted-terminal"
    assert (tmp_path / "CAPTURES.jsonl").read_text().count("\n") == 1


def test_another_tool_registers_into_the_same_registry(tmp_path, monkeypatch):
    # scripts/rig/register_capture.py is the CLI the browser harness calls; it must
    # work from a python with no PyObjC, so the registry may not depend on Quartz.
    png = tmp_path / "browser.png"
    png.write_bytes(b"fake-png")
    monkeypatch.setattr(
        rig.capture_registry, "CAPTURES", tmp_path / "CAPTURES.jsonl", raising=True
    )
    assert rig.capture_registry.main([str(png), "--tool", "browse.py"]) == 0
    row = json.loads((tmp_path / "CAPTURES.jsonl").read_text())
    assert row["tool"] == "browse.py"
    assert row["sha256"] == hashlib.sha256(b"fake-png").hexdigest()
    src = Path(rig.capture_registry.__file__).read_text()
    assert "Quartz" not in src and "AppKit" not in src


def test_registering_a_missing_file_is_a_usage_error(tmp_path):
    with pytest.raises(SystemExit) as e:
        rig.capture_registry.main([str(tmp_path / "nope.png"), "--tool", "browse.py"])
    assert e.value.code == 2


def test_no_vysted_window_is_an_abort():
    with pytest.raises(rig.Aborted, match="no on-screen Vysted window"):
        guard(
            windows=lambda: [
                {"owner": "Finder", "id": 3, "layer": 0, "bounds": (0, 0, 1, 1)}
            ]
        ).vysted_window()


def test_vysted_window_picks_the_largest():
    wins = [
        {"owner": "vysted-terminal", "id": 1, "layer": 0, "bounds": (0, 0, 100, 100)},
        {"owner": "vysted-terminal", "id": 2, "layer": 0, "bounds": (0, 0, 1280, 832)},
    ]
    assert guard(windows=lambda: wins).vysted_window()["id"] == 2


# --- the safety log only records safety events -------------------------------


def test_only_acting_commands_write_the_safety_log():
    assert not {"idle", "bounds"} & rig.ACTING_COMMANDS
    assert {"capture", "click", "type", "key", "resize", "batch"} <= rig.ACTING_COMMANDS


def test_a_failed_bounds_read_does_not_cry_wolf(tmp_path, monkeypatch):
    log = tmp_path / "RIG_ABORTS.log"
    monkeypatch.setattr(rig, "ABORTS", log)
    monkeypatch.setattr(rig.Quartz, "CGWindowListCopyWindowInfo", lambda *a: [])
    assert rig.main(["bounds"]) == rig.EXIT_SURPRISE
    assert not log.exists(), "a read failure must not land in the presence-safety log"


# --- key combos: refuse rather than post a different event -------------------


def test_combo_renders_modifiers_and_key_codes():
    assert rig.parse_combo("cmd+k") == 'keystroke "k" using {command down}'
    assert rig.parse_combo("return") == "key code 36"
    assert (
        rig.parse_combo("CMD+Shift+p")
        == 'keystroke "p" using {command down, shift down}'
    )


def test_an_unknown_modifier_is_refused_not_silently_dropped():
    # Silently dropping it would send a bare "k" into the operator's live app.
    with pytest.raises(ValueError, match="unknown modifier"):
        rig.parse_combo("hyper+k")


def test_an_unknown_key_name_is_refused_not_typed_as_text():
    # Otherwise "f5" would be typed as the two characters f and 5.
    with pytest.raises(ValueError, match="unknown key"):
        rig.parse_combo("f5")
    with pytest.raises(ValueError, match="empty key combo"):
        rig.parse_combo("+")


def test_a_bad_combo_never_reaches_the_gate_or_osascript(monkeypatch):
    monkeypatch.setattr(
        rig, "osascript", lambda _s: pytest.fail("osascript must not run")
    )
    g = guard()
    g.before = lambda **_k: pytest.fail("the gate must not be spent on a typo")
    with pytest.raises(ValueError):
        rig.do_key(g, "hyper+k")


def test_cli_reports_a_bad_combo_as_a_usage_error(monkeypatch):
    monkeypatch.setattr(
        rig, "osascript", lambda _s: pytest.fail("osascript must not run")
    )
    assert rig.main(["key", "hyper+k"]) == rig.EXIT_USAGE
    assert rig.EXIT_USAGE not in (rig.EXIT_PRESENCE, rig.EXIT_SURPRISE)


# --- there is no escape hatch ------------------------------------------------


def test_cli_exposes_no_flag_to_disable_the_guard():
    src = (
        Path(rig.__file__).read_text() + Path(rig.capture_registry.__file__).read_text()
    )
    for hatch in ("--force", "--no-guard", "--unsafe", "--skip-presence", "--yes"):
        assert hatch not in src
