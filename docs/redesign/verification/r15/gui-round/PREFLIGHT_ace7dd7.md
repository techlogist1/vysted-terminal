# GUI-round preflight at ace7dd76 (rc2 candidate)
- sha ace7dd768c3b809b0e72b20b20cfc94eea2368bd: ancestor of 004-r4-experience-rebuild (git merge-base --is-ancestor OK)
- worktree: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-ace7dd7 (git worktree add --detach)
- build: pnpm install --frozen-lockfile; node scripts/ensure-all-sidecars.mjs; pnpm tauri build --debug --bundles app -> all exit 0 (logs/ace7dd7-*)
- app: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (MacOS: vysted-terminal + 3 sidecars)
- dev binary: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-ace7dd7/src-tauri/target-devurl/debug/vysted-terminal (cargo build exit 0); sidecars beside it: see notes
- seed: scratchpad/gui-round-seed rebuilt fresh from vysted-iso/data (sqlite .backup per db except audit_log.db, workspaces/, notes/, searxng/settings.yml, fresh dev-keystore.json 0600). Watchlist 6 symbols, notes 1 file (general.md, 59 B), portfolio positions = 0 (MISSING) -> seed_populated=false
- presence: see presence.log (ace7dd7 line); no Vysted app running; 5173 free
- needs_gui: 11 entries (register order)
