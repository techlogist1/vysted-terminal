# Release launch check — bundle at a9b954af (lead, 12:10–12:14 IST 3 Oct)

- Presence: idle 1214.5 s, sentinel to 21:43:50Z, frontmost Finder, 0 Vysted apps (presence.log line "launch-check rc2").
- Launch: `VYSTED_DATA_DIR=<scratch>/launch-rc2-data "<bundle-rc2>/…/Vysted Terminal.app/Contents/MacOS/vysted-terminal"` (P3 data-dir override; first exec of the freshly built, unsigned binaries). Load 2.5–3.2.
- Result: **FAIL — reproduces R15-LEAD-123 on a near-idle machine.** `boot-lines.txt`: main sidecar "not up yet on port 56202 after attempt 1/2 (45s)" then "did not come up"; sec-edgar-mcp "did not bind … within 45s x 2 attempts; treating as unavailable". At +2 min `curl /health` on :56202 → 200 `version 0.9.0` while the window shows "SIDECAR ERROR — THE DATA ENGINE DID NOT COME UP ON PORT 56202." and every panel errors (capture `a9b954a-01-release-first-launch-failed.png`, registered).
- First-launch terms dialog rendered (keychain not redirected under VYSTED_DATA_DIR; read only, no ack given).
- Quit: SIGTERM to the app pid; the whole tree exited. Data dir in scratch.
- Isolation: 7 WebKit/Caches files under the real `~/Library/{WebKit,Caches}/com.vysted.terminal` were modified (the shared dev store, not the installed com.vysted.desk copy) — DECISIONS §5.9, left in place.
