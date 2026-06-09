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

## Learned during R7

- WKWebView serves STALE JS modules from its NetworkCache even through location.reload() — after any frontend edit that must be live-verified, restart the whole `pnpm tauri:dev` stack with `rm -rf ~/Library/Caches/vysted-terminal ~/Library/WebKit/vysted-terminal` first. Curl the Vite URL to confirm what's actually served vs what the webview shows.
- The portaled cmdk palette never hot-applies (now under Vite too).
- The computer-use screenshot/click filter binds to the app BUNDLE PATH — a dev binary outside the granted bundle renders black and rejects clicks. Eyes = `screencapture -x -R<win>`, hands = tauri-plugin-mcp socket (/tmp/r7rig.js: evaluate_script/fill/click/press_key/console+network logs). press_key cmd+k does NOT trigger the palette (synthetic keydown lacks trusted meta) — click the "⊞ Open panel" toolbar button instead.
- The smoke-test pre-flight kills on ANY running vysted processes — stop the dev app before running it.
- macOS bash 3.2: no ${var,,} lowercasing in scripts.
