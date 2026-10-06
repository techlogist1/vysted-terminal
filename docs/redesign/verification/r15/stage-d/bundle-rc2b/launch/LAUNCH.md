# Release launch check — bundle at 1fddb2b1 (lead, 23:47–23:53 IST 3 Oct)

**PASS.** The freshly built, unsigned 0.9.0 bundle reached CONNECTED on its first exec and held it to +342 s, with live data in its panels.

- **Presence:** a background poll waited for idle ≥900 s after an input event at 23:31. At launch, idle was 913.1 s, the sentinel was live to 21:43:50Z, there were 0 Vysted apps, and load was 1.90 (`presence.txt`).
- **Launch:** `VYSTED_DATA_DIR=<scratch>/launch-rc2b-data "<bundle-rc2b>/…/Vysted Terminal.app/Contents/MacOS/vysted-terminal"`. This was the first exec of the binaries built in `../BUILD.md`. App pid 27014, T0 23:47:10.
- **Warm-up (`boot-lines.txt`, `poll.txt`):**
  - openbb-mcp missed attempt 1 and was healthy at about +68 s (startup log line 23:48:18).
  - The main sidecar missed attempts 1 and 2 of 6 and was healthy by +114 s. This is the late-bind path the R15-LEAD-123 fix (270 s budget) exists for.
  - `did not come up` matched 0 lines for the whole run.
  - The poll's `listeners=[]` column is empty because of a tooling gap: lsof was scoped to the app's direct children, and the sidecars are grandchildren. Read health from the core log lines above.
  - The single `/health` curl in `poll.txt` returned "Not Found" because it hit the openbb-mcp port. The first `healthy on` match in the log is openbb's, so this is a script bug, not an app result.
- **sec-edgar-mcp** did not bind within its unchanged 45 s × 2 window and was treated as unavailable, so `/sec` routes return 501. This is the already-filed open medium R15-LEAD-124 and the `--onedir` carry-forward in BLOCKERS.md. It is not new and not a launch blocker.
- **Captures:** window-only, taken with `screencapture -x -o -l 7153`, where window 7153 is owned by pid 27014. All three are registered in CAPTURES.jsonl.
  - `1fddb2b-01-first-launch-early.png` (+64 s): before the bind.
  - `1fddb2b-02-connected.png` (+130 s): CONNECTED in the status bar, the first-run terms dialog shown, watchlist rows loading, and news populated (a POSITIVE +0.36 item).
  - `1fddb2b-03-steady-320s.png` (+342 s): still CONNECTED. The watchlist has live rows (^NSEI 22,421.95 −0.88%; a second row 1,167.70 −1.63%).
- **Terms:** the first-launch terms dialog rendered. The keychain is not redirected under VYSTED_DATA_DIR, and nothing was acknowledged or clicked.
- **Quit:** SIGTERM to pid 27014. The tree [27014 27030 27032] had no process alive 8 s later. The data dir is in scratch.

## Correction (00:08 IST 4 Oct): the launch raised a login-keychain SecurityAgent prompt

At 00:00 IST the GUI-half preflight found a SecurityAgent window frontmost. It was at layer 1000, screen rect 539,206 434x186, and it stopped both GUI drivers. `ps -o lstart` on SecurityAgent pid 27037 gives **Sat Oct 3 23:47:12 2026**, 2 s after this check's exec at T0 23:47:10. This launch caused that prompt.

The cause: `VYSTED_DATA_DIR` moves the data dir only, not the keychain. The release build reads the OS keychain at boot (the first-launch terms ack and the provider keys). This binary is unsigned and freshly built, so it is not in the ACL of the `vysted-terminal` items that an earlier build created, and macOS asked for consent.

The captures did not show the prompt because `screencapture -l <wid>` captures only the app window, by design. "Terms dialog rendered (keychain read only)" above is accurate in the narrow sense: nothing was read, because the read waited on consent and the app was quit first. The window-only method still hid this, and the record above should have said so.

The prompt was not answered or dismissed, and SecurityAgent was not touched. Answering a keychain prompt or stopping a system process is not this run's to do. It stays on screen for the operator to **Deny**. Filed as R15-LEAD-143. Release prep's fresh-install launch will raise the same prompt, so it is operator-attended.
