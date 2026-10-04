# gui-close-3 preflight
- sha: f163d85856c427adeccd1a6919a70400cd3504f4 (git rev-parse --verify 'f163d858^{commit}'); r15-launch ancestor exit 0; contained in 004-r4-experience-rebuild exit 0; git diff --stat src/ src-tauri/ sidecar/ empty
- fixround-wt HEAD == sha, status --porcelain empty
- debug app reused (built 19:10 IST): fixround-wt/src-tauri/target/debug/bundle/macos/Vysted Terminal.app; Contents/MacOS has vysted-terminal + vysted-sidecar, vysted-openbb-mcp-sidecar, vysted-sec-edgar-mcp-sidecar; version 0.9.0
- seed: scratchpad/gui-close-seed (sqlite3 .backup per db except audit_log.db; workspaces/, notes/, fresh dev-keystore.json 0600). watchlist 6 symbols; portfolio positions 0 (workspace portfolios holdings empty); notes/general.md 59 bytes, workspace notes empty. Drivers must seed positions/notes.
- no foreign Vysted GUI app (lsappinfo list | grep -i vysted empty)
- ollama: qwen3:8b, qwen2.5:7b, llama3.1:8b
- presence: idle 3381.8 s; sentinel 2026-10-04 15:40:56+00:00 (21:10 IST)
