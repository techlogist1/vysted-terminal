# rc1-gui working log

- 2026-09-25T03:18:28Z GRANT check (first step, before any build/launch).
  - mcp__computer-use__list_granted_applications: com.vysted.desk (Vysted), dev.kdrag0n.MacVirt (OrbStack), com.apple.finder (Finder), com.apple.systempreferences (System Settings).
  - Built app (candidate 1d6511c8 worktree src-tauri/tauri.conf.json): identifier com.vysted.terminal, productName "Vysted Terminal".
  - Granted list does not contain the built app's identifier or name. request_access not called (operator away).
  - Result: DEFERRED. No build, no launch, no sidecar boot, no GUI interaction, operator data untouched.
- A prior presence.log line (03:18:04Z) exists from an earlier attempt; no other artifacts from it (no log, no findings) — nothing to continue.
- Unblock: grant com.vysted.terminal ("Vysted Terminal") to the computer-use session, then rerun this role.
