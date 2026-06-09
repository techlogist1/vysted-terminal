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
