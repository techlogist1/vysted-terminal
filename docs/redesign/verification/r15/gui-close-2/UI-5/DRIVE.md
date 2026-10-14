# UI-5 drive (gui-close-2) — fitLayoutTemplate at three viewports

- Item: UI-5 (final-pass NEEDS_GUI "final-adv-maintainer — UI-5 (fitLayoutTemplate)")
- SHA: 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056
- App: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/bundle-rc2b/src-tauri/target/debug/bundle/macos/Vysted Terminal.app
- Home: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-close-home-UI-5 (not created — see Presence)
- Launch: not launched
- Real data dir mtime at start: 1790978102

## Presence

Role started 12:48:11Z. Sentinel expires 12:57:00Z. Idle at 12:48:18Z was 185.9 s
(the UI-7 drive's last rig input). Idle cannot reach 900 s before ~13:00Z, after the
sentinel expires, so no guarded rig call can be allowed inside this sentinel. Re-checks
per the 30-minute rule follow (presence.log lines tagged "UI-5").

Re-checks every ~100 s from 12:48:31Z to 13:18:18Z (presence.log, tags
pre-launch-check-01 through recheck-18-final). The sentinel printed None from 12:57:06Z
(expired at 12:57:00Z, not re-armed). Idle first passed 900 s at 13:00:43Z (931.4), by
which time there was no sentinel. From 13:06:00Z the frontmost app was loginwindow (the
screen locked). At no point were idle >= 900 and a live sentinel true together. The 30-minute
window ran out, so the drive was never allowed.

## Checks

No batch ran. The app was not launched, no isolated home was built, and there are no captures.

| Check | Result |
|---|---|
| 1920x1080: research-cockpit + macro-scan applied/downgraded, dockview width, populated capture | not_driven |
| 1280x800: same | not_driven |
| 1024x768: same | not_driven |

## Real data

mtime at start 1790978102, at end 1790978102 (unchanged; stat only).

## Stops

- presence: the sentinel expired 12:57:00Z, 8 minutes 49 seconds after this role started. Idle
  had been reset by UI-7's last rig input, so it stood at 185.9 s, and it could not reach 900 s
  before expiry. Screen locked (loginwindow) from 13:06Z.

## Verdict

operator_present. Under the presence rule, this verdict covers "presence never allowed it
within 30 min"; it does not mean a human was seen at the machine. No findings.
