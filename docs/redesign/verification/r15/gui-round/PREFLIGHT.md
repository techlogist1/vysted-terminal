# GUI-round preflight (d38b5d1)
- sha d38b5d1a2487bd52fe8a7e741a3a5266e3206611: ancestor of 004-r4-experience-rebuild (git merge-base --is-ancestor OK; git fetch ran)
- worktree: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-d38b5d1 (git worktree add --detach)
- build: pnpm install --frozen-lockfile; node scripts/ensure-all-sidecars.mjs; pnpm tauri build --debug --bundles app -> EXIT=0 (logs/d38b5d1-*.log)
- app_path: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-d38b5d1/src-tauri/target/debug/bundle/macos/Vysted Terminal.app ; Contents/MacOS has vysted-terminal + vysted-sidecar + vysted-openbb-mcp-sidecar + vysted-sec-edgar-mcp-sidecar
- dev_binary: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-d38b5d1/src-tauri/target-devurl/debug/vysted-terminal (cargo build, no custom-protocol; sidecars beside it, built by build.rs) 
- seed: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-round-seed re-created from vysted-iso/data (sqlite3 .backup per db minus audit_log.db; workspaces/, notes/, searxng/settings.yml; dev-keystore.json {"secrets": {}, "migrated": true}, 0600)
- seed contents: watchlist 6 symbols (SPY QQQ BTC/USDT ETH/USDT NVDA AAPL) in autosave workspace; notes/general.md 59 bytes; portfolio.db positions = 0 rows and workspace portfolios holdings = [] -> seed_populated=false (missing: >=1 portfolio position)
- presence: idle 3486.0 s; sentinel 2026-10-03 21:43:50+00:00; frontmost SecurityAgent; no vysted apps; :5173 free; load avg 1.73 2.37 2.84 at 12:48 (uptime)
- entries: R15-LIFECYCLE-001 high, R15-LIFECYCLE-008 high, R15-UI-022 medium all needs_gui
