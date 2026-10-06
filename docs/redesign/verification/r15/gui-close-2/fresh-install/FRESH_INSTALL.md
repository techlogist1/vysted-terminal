# Fresh install and first launch of the 0.9.0 release bundle, second run (operator-attended start)

**Verdict: PASS. No login-keychain prompt appeared, so the operator had nothing to answer.**

- **Sentinel.** The operator said "I am away from the Mac from now" and asked the lead to arm the sentinel. `~/.vysted-rig-away` was armed at 14:27:00 IST, expiring 2026-10-04T12:57:00+00:00 (18:27 IST, 4 h).
- **Source.** The launch dmg `<scratchpad>/bundle-rc2b/src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg`, sha256 `9940d41b7ed6725a…`. This is the file uploaded to the draft release `v0.9.0`; the first run on 4 Oct recorded the full hash and size.
- **Install (new, clean location).** `hdiutil attach -nobrowse -readonly`, `ditto` of `Vysted Terminal.app` into `<scratchpad>/gui-close-2/Applications/` (a path never used before; not `/Applications`, which holds the operator's 0.8.0 copy), then detach. Bundle version 0.9.0, id `com.vysted.terminal`.
- **Launch.** `open -n --env VYSTED_DATA_DIR=<scratchpad>/gui-close-2/data` at 14:27:12 IST, into an empty data dir.
- **Keychain prompt (R15-LEAD-143).** The lead checked `pgrep -x SecurityAgent` every 3–4 s from 14:27:15 to 14:30:40 IST (3 min 28 s). There was no SecurityAgent process at any reading. The first run's "Always Allow" (01:55 IST) evidently covered this byte-identical binary at a new path too. The operator was standing by for the first two minutes; no prompt came, so no answer was given.
- **Health.** The sidecar was `--data-dir <scratchpad>/gui-close-2/data` on 127.0.0.1:52099, and `/health` returned `version 0.9.0`, `openbb-mcp: available` at 14:30:40. sec-edgar-mcp did not bind within 45 s x 2 and was treated as unavailable (`/sec` routes 501). This is the open medium R15-LEAD-124 (contended cold extraction), seen again here: `data/logs/vysted.log` 08:58:44Z.
- **Capture.** `01-first-launch.png` (2560x1664) is a window-only capture of the app's own window (`screencapture -x -o -l 7519`), registered in `CAPTURES.jsonl`. It shows the cockpit CONNECTED with Ollama (local) qwen2.5 7b, the Chat 1 empty state with "Try this" prompts, the Chart/Equity Overview, Watchlist (loading), News and an empty Portfolio.
- **Quit.** pid 75120 and its sidecars were quit by pid at 14:31:15; ports 52099–52101 are free. The real data dir mtime was 1790978102, unchanged.
- **Test-method note (as in the first run).** The terms acknowledgement lives in the login keychain, so this tests a fresh install, not a first-run profile. The true first run is UI-7 on an isolated HOME.
