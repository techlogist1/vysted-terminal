# R7 Rebuild — Lessons (corrections + confirmed approaches)

Consulted before each phase; appended as the run learns.

## Carried in from memory / prior runs

- `pnpm ci-local` needs the venv on PATH on this Mac: `PATH=sidecar/.venv/bin:$PATH pnpm ci-local`.
- Computer-use grants the app **click-only** tier (name contains "Terminal"): no typing, no key-presses, no drag. Drive via clicks (toolbar "⊞ Open panel" opens the palette, empty-state quick-load buttons); verify typed/agent flows via the sidecar FastAPI + Playwright MCP.
- WKWebView caches compiled CSS under `~/Library/Caches/vysted-terminal/` (runtime bundle id = productName). After token changes: kill app, `rm -rf ~/Library/Caches/vysted-terminal ~/Library/WebKit/vysted-terminal` + `.next`, relaunch. Verify served CSS with curl.
- After `pnpm tauri:dev` relaunch the window may not paint — click the macOS **Window menu** to surface it; full layout restores once sidecar connects.
- Headless Chrome on localhost renders the same CSS for palette-faithful proof when the webview is occluded/throttled.
- A stale sidecar binary has produced false verification positives repeatedly — rebuild + restart before every verification round.
- Never pipe long-running commands through head/tee in the foreground (deadlock + masked exit code); run in background with job tracking.
- Worktree teammates have historically written into the lead's main worktree — check `git worktree list` + `git branch` before lead work after dispatch and before integrating.

## Learned during R8

- `codesign --force` on a RUNNING executable fails (text file busy) — any "sign it after
  launch" watcher is structurally broken and fails silently. The only reliable dev-signing
  point is between build and exec: a cargo `runner` (src-tauri/.cargo/config.toml →
  scripts/macos-dev-sign-run.sh) signs-then-execs every dev binary. Cargo discovers
  `.cargo/config.toml` from the INVOCATION cwd, so the runner applies to the Tauri CLI
  (cargo from src-tauri/) but not to repo-root `cargo test --manifest-path` (CI untouched).
- A timed-out/unanswered keychain SecurityAgent prompt records NOTHING — the same prompt
  returns on the next fresh binary even with a byte-identical designated requirement. The
  "Always Allow" (with password) must actually be clicked once; only then is the
  trusted-application entry recorded against the stable DR.
- File-keychain items carry a `partition_id` ACL entry pinning specific CDHASHES — with a
  self-signed identity (no team id) every fresh binary triggers ONE securityd evaluation
  pass on its first key read: a keychain dialog shows ~10-50s, then SELF-DISMISSES AS ALLOW
  (the cert-based trusted-app entry validates). No interaction needed — never type the
  password into these; only a prompt surviving >60s is a real regression. Dead ACL entries
  from past ad-hoc Always-Allows (~165 found) are pruned by having the SIGNED APP rewrite
  its own items (get→delete→set via its IPC) — no password, secrets never leave the app.
- THE BRIDGE-WEDGE ROOT CAUSE: touching the tauri-mcp socket while the webview is still
  booting wedges the debug server PERMANENTLY for that app instance (requests then hang —
  even list_windows). Recipe that works: launch → wait for the "Bridge already initialized"
  console line in the dev log → wait 45 more seconds → ONE probe. Never poll the socket
  during boot.
- AppleScript `System Events` keystrokes are TRUSTED input that reaches the composer; pair
  with a Quartz `CGEventPost` clicker (sidecar venv python) for clicks at window-relative
  coordinates. ⌘K does not reach the palette this way, but clicking "⊞ Open panel" + typing
  does; dockview tab clicks at strip coordinates work but tabs REFLOW — re-crop before
  clicking. The composer textarea sits at ~(100, 762) and the depth stops at ~(186/202/218, 821) in a 1280×832 window.
- The model can ESCALATE research depth via its tool arg above the slider floor — prompts
  like "use your research tool at ultra depth" exercise deep/ultra without clicking the
  slider.
- The composer QUEUE makes serial gate batteries cheap: type all prompts while the first
  streams; they drain one by one. Watch brief publications by polling the autosave blob's
  brief.createdAt (a watcher script archiving each new brief gives per-run regression
  artifacts for free).
- PyInstaller-binary stdin watchdog: running the sidecar binary by hand exits 0 instantly
  (stdin EOF → os.\_exit(0)); hold stdin open (`sleep 1000 | binary …`) to test boots. Cold
  onefile boot is ~60s on this Mac.

- tauri-plugin-mcp `evaluate_script` evaluates in EXPRESSION context — a script starting with `const` fails ("Unexpected keyword 'const'"); wrap everything in an IIFE `(()=>{ … })()`.
- dockview tabs do NOT switch on a synthetic `click` — dispatch the full pointer sequence (pointerdown/mousedown/pointerup/mouseup/click) on the `.dv-default-tab` element.
- React-controlled inputs need the native value setter + `input` event (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set`).
- Quartz window capture: system python3 lacks PyObjC — use `sidecar/.venv/bin/python3` for /tmp/rigcap.py (matches `kCGWindowOwnerName` contains "vysted").
- Window resize for narrow-width testing: `osascript … System Events … set size of front window` works (no accessibility fight on this Mac); the app window clamps at ~960px min width.
- The operator's autosave workspace blob is a regression-evidence goldmine — `brief` rides the blob, so a failing published brief survives restarts (r8/regression-brief-\*.json).

## Learned during R7

- WKWebView serves STALE JS modules from its NetworkCache even through location.reload() — after any frontend edit that must be live-verified, restart the whole `pnpm tauri:dev` stack with `rm -rf ~/Library/Caches/vysted-terminal ~/Library/WebKit/vysted-terminal` first. Curl the Vite URL to confirm what's actually served vs what the webview shows.
- The portaled cmdk palette never hot-applies (now under Vite too).
- The computer-use screenshot/click filter binds to the app BUNDLE PATH — a dev binary outside the granted bundle renders black and rejects clicks. Eyes = `screencapture -x -R<win>`, hands = tauri-plugin-mcp socket (/tmp/r7rig.js: evaluate_script/fill/click/press_key/console+network logs). press_key cmd+k does NOT trigger the palette (synthetic keydown lacks trusted meta) — click the "⊞ Open panel" toolbar button instead.
- The smoke-test pre-flight kills on ANY running vysted processes — stop the dev app before running it.
- macOS bash 3.2: no ${var,,} lowercasing in scripts.
- The tauri-plugin-mcp socket bridge WEDGES (requests hang, not refuse) after Vite HMR re-runs the bridge init ("Bridge already initialized" warn) — restart the whole dev stack after ANY frontend change before driving the rig; never interleave merges with rig-driven verification.

## Learned during R9

- Capture-scale trap: rigcap PNGs are 2560×1664 (2×) but render at varying thumb
  widths — window coords = thumb_x × (1280 / thumb_width). Mis-scaling cost three
  silent mis-clicks (palette, composer, radios). Measure from the FILE pixels.
- The composer's right-anchored control cluster SHIFTS with the model-name width
  ("Grok 4.3" vs "DeepSeek V4 Flash") — re-measure the depth pill per model.
- Palette Enter selects the FIRST row ("Ask agent: …"), which routes the text to
  chat — click the Open/Action row instead.
- ci-local's final stage (`cd sidecar && python …`) breaks a RELATIVE venv PATH
  entry — use `PATH=/abs/path/sidecar/.venv/bin:$PATH`.
- bseindia.com `AttachLive` PDF serving is INTERMITTENT (4-byte responses, then
  4kB with figures minutes later) — the digital-twin fallback can flake per run;
  nsearchives is the reliable host.
- A keyless `/agents/*/invoke` curl (no provider arg) routes to the agent's
  ollama default and silently cold-loads a 4GB model on this M1 — always pass
  `provider` in probes.
- The tauri-plugin-mcp socket was dead-on-arrival on every R9 stack (zero bytes
  even for list_windows on a fresh boot, no HMR involved) — the trusted
  CGEvent/AppleScript rig + Quartz capture is the only dependable drive path.
- The autosave-blob PRUNE trick (keep settings-class fields, drop session debris)
  resets the cockpit but the provider default may demote through restore guards —
  set `defaultProviderId` on the FULL post-boot blob with the app stopped.

## Learned during the R9 keychain dev-keystore work

- The partition-list wildcard (`-S "apple:,apple-tool:,codesign:,cdhash:"`) does NOT remove
  the per-cdhash SecurityAgent dialog for a self-signed identity (no Team ID → bare
  `cdhash:` isn't a wildcard). Measured: a fresh dev cdhash still flashed, once for ~77s
  (past the 60s "regression" line). The fix is to leave the keychain in dev, not to keep
  tuning the ACL.
- DEV SECRETS NOW LIVE IN A FILE: `keychain.rs` has a `cfg(debug_assertions)` file backend
  (`<app-data-dir>/dev-keystore.json`, 0600, git-ignored). `keychain_set/get/delete` →
  file in dev, OS keychain in release. The ONLY keychain call site is `keychain.rs`; the
  sidecars never read it (zero python `keyring` imports). `keychain_migrate` copies
  keychain→file once (guard checked BEFORE any read — putting it after re-raised the dialog
  every boot). To re-run migration: delete `dev-keystore.json` and reboot dev.
- A keychain read SELF-DISMISSES-AS-ALLOW only while the app is IDLE on the keychain. A
  background watcher polling `CGWindowListCopyWindowInfo` / `screencapture` during the
  dialog makes the read return `errSecUserCanceled` ("User canceled the operation")
  instead. When verifying keychain reads, STOP the prompt-watcher during the read and poll
  only the filesystem; re-arm the watcher afterward (post-migration there are no reads, so
  it can't interfere).
- `spawn_blocking` for a keychain read returns errors where an inline async-command read
  succeeds — the macOS auth context differs by thread. Read keychain inline on the command.
- macOS `errUserCanceled` is -128; a hostile/early read surfaces as
  `"Platform secure storage failure: User canceled the operation."` via keyring v3.
- `cargo test --release` runs the dev-keystore release-path assertion
  (`release_never_uses_dev_keystore`); ci-local's `cargo test` (debug) does not exercise
  the release arm, so run the release test separately when changing the backend split.
- After a `tauri dev` relaunch the WKWebView can paint WHITE (occlusion-throttled). Surface
  it: bring frontmost, click the Dock tile if minimized, or RESIZE the window (forces a
  WKWebView relayout/repaint) — then drive it.

## R13 — operator presence
- **The presence check is per-GUI-leg, not per-run.** R13 booted on an "operator asleep" premise and drove GUI for ~35 minutes without re-checking HIDIdleTime; the operator was in fact at the machine, and a repaint capture caught his private session (deleted immediately, never committed — D75). The rule that survives: check HIDIdleTime IMMEDIATELY BEFORE every click/keystroke/capture batch, arm the ≥25-min idle monitor at run START, and treat any frontmost-window surprise in a capture as a hard stop.
- A WKWebView white window after cache-clear relaunch may need SECONDS-later repaint, and the window you nudge may not be the window in front — verify with `--bounds` + a region capture BEFORE sending any synthetic event when presence state is uncertain.
