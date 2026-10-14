# GUI-close preflight
- sha: git rev-parse 1fddb2b1^{commit} == r15-launch^{commit} == 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056
- bundle-rc2b worktree: HEAD equals sha, status --porcelain empty
- debug build: VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build --debug --bundles app (log logs/debug-build.log) -> bundle-rc2b/src-tauri/target/debug/bundle/macos/Vysted Terminal.app; Contents/MacOS has vysted-terminal + vysted-sidecar, vysted-openbb-mcp-sidecar, vysted-sec-edgar-mcp-sidecar
- seed: scratchpad/gui-close-seed (sqlite .backup of 8 dbs minus audit_log.db, workspaces/, notes/, dev-keystore.json {"secrets": {}, "migrated": true} 0600)
- seed content: watchlist SPY QQQ BTC/USDT ETH/USDT NVDA AAPL; note general.md present; portfolio positions = 0 (workspace holdings empty, portfolio.db positions 0 rows) -> drivers must seed a position
- ollama: qwen3:8b, qwen2.5:7b, llama3.1:8b
- presence: idle 27.5 s; sentinel 2026-10-03 23:25:36+00:00 (now ~20:35 UTC, unexpired); no vysted apps in lsappinfo
