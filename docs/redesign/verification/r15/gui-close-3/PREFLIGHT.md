# gui-close-3 preflight (attempt 2, 2026-10-04 19:57 IST)
- sha: `git rev-parse --verify '9f6bd4be^{commit}'` = 9f6bd4be5837aa982f2fb0828899856e275503cc; is-ancestor r15-launch exit 0; is-ancestor branch exit 0; `git diff --stat <sha> 004-r4-experience-rebuild -- src/ src-tauri/ sidecar/` empty.
- wt: HEAD equals sha, `status --porcelain` empty.
- debug_app (reused, no build): fixround-wt/src-tauri/target/debug/bundle/macos/Vysted Terminal.app; Contents/MacOS has vysted-terminal + vysted-sidecar, vysted-openbb-mcp-sidecar, vysted-sec-edgar-mcp-sidecar.
- seed: scratchpad/gui-close-seed; 7 dbs via sqlite3 .backup (audit_log.db excluded), workspaces/, notes/, dev-keystore.json = {"secrets": {}, "migrated": true} 0600.
- populated: watchlist 6 symbols (SPY QQQ BTC/USDT ETH/USDT NVDA AAPL); notes/general.md 59 bytes; portfolio positions 0 rows and workspace holdings [] -> drivers must seed a position.
- ollama (curl :11434/api/tags): qwen3:8b, qwen2.5:7b, llama3.1:8b.
- presence: rig.py idle=51.6; rig.real_away()=2026-10-04 15:57:21+00:00 (= 21:27 IST); lsappinfo list | grep vysted: none (no foreign Vysted app).
