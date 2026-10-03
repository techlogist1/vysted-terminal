# GUI-round preflight at 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056 (r15-rc2)
- git: 1fddb2b1 resolves to full sha above; ancestor of 004-r4-experience-rebuild (merge-base --is-ancestor OK).
- worktree: scratchpad/gui-1fddb2b (new). install, ensure-all-sidecars, `pnpm tauri build --debug --bundles app` OK; logs logs/1fddb2b-*.log.
- app: <worktree>/src-tauri/target/debug/bundle/macos/Vysted Terminal.app; MacOS has vysted-terminal + 3 sidecars.
- dev binary: <worktree>/src-tauri/target-devurl/debug/vysted-terminal (cargo build OK, 42s).
- seed: scratchpad/gui-round-seed from vysted-iso/data (no audit_log.db present). Watchlist 6 symbols, general note (1), portfolio positions = 0 (missing: position).
- presence: idle 1566.4 s; sentinel 2026-10-03 21:43:50+00:00; frontmost SecurityAgent; no vysted apps; 5173 free. Load avg 3.51 at start, 7.62 during build.
- entries: R15-LIFECYCLE-008 high needs_gui; R15-UI-022 medium needs_gui.
