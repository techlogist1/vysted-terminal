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

- tauri-plugin-mcp `evaluate_script` evaluates in EXPRESSION context — a script starting with `const` fails ("Unexpected keyword 'const'"); wrap everything in an IIFE `(()=>{ … })()`.
- dockview tabs do NOT switch on a synthetic `click` — dispatch the full pointer sequence (pointerdown/mousedown/pointerup/mouseup/click) on the `.dv-default-tab` element.
- React-controlled inputs need the native value setter + `input` event (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set`).
- Quartz window capture: system python3 lacks PyObjC — use `sidecar/.venv/bin/python3` for /tmp/rigcap.py (matches `kCGWindowOwnerName` contains "vysted").
- Window resize for narrow-width testing: `osascript … System Events … set size of front window` works (no accessibility fight on this Mac); the app window clamps at ~960px min width.
- The operator's autosave workspace blob is a regression-evidence goldmine — `brief` rides the blob, so a failing published brief survives restarts (r8/regression-brief-*.json).

## Learned during R7

- WKWebView serves STALE JS modules from its NetworkCache even through location.reload() — after any frontend edit that must be live-verified, restart the whole `pnpm tauri:dev` stack with `rm -rf ~/Library/Caches/vysted-terminal ~/Library/WebKit/vysted-terminal` first. Curl the Vite URL to confirm what's actually served vs what the webview shows.
- The portaled cmdk palette never hot-applies (now under Vite too).
- The computer-use screenshot/click filter binds to the app BUNDLE PATH — a dev binary outside the granted bundle renders black and rejects clicks. Eyes = `screencapture -x -R<win>`, hands = tauri-plugin-mcp socket (/tmp/r7rig.js: evaluate_script/fill/click/press_key/console+network logs). press_key cmd+k does NOT trigger the palette (synthetic keydown lacks trusted meta) — click the "⊞ Open panel" toolbar button instead.
- The smoke-test pre-flight kills on ANY running vysted processes — stop the dev app before running it.
- macOS bash 3.2: no ${var,,} lowercasing in scripts.
- The tauri-plugin-mcp socket bridge WEDGES (requests hang, not refuse) after Vite HMR re-runs the bridge init ("Bridge already initialized" warn) — restart the whole dev stack after ANY frontend change before driving the rig; never interleave merges with rig-driven verification.
