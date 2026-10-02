# GUI-round preflight
- sha 9368c626b76f4a4aa6a319e30b2841d0cd2a4d9b: ancestor of 004-r4-experience-rebuild (git merge-base --is-ancestor, OK)
- worktree: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-9368c62 (git worktree add --detach)
- build: pnpm install --frozen-lockfile; node scripts/ensure-all-sidecars.mjs; pnpm tauri build --debug --bundles app -> PACKAGED_OK (logs/)
- app: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-9368c62/src-tauri/target/debug/bundle/macos/Vysted Terminal.app; Contents/MacOS has vysted-terminal + 3 sidecars
- dev binary: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-9368c62/src-tauri/target-devurl/debug/vysted-terminal (cargo build, sidecars beside it)
- seed: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-round-seed (sqlite .backup per db except audit_log.db, workspaces/, notes/, searxng/settings.yml, fresh dev-keystore.json). Watchlist 6 symbols in workspace blob, notes 1 file, portfolio positions = 0 (MISSING) -> seed_populated=false
- presence: idle=1510.6 sentinel=2026-10-03 21:43:50+00:00 front="LSDisplayName"="Finder" 5173=free
- needs_gui entries: 11 (R15-CODE-AGENT-001, LIFECYCLE-001/008, UI-009/022/025/050/083/084, DOCS-024, LIFECYCLE-040)
