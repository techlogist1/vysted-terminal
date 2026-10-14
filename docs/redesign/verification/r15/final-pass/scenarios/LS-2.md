# LS-2 — sidecar lifecycle on my own bundle binary (final-cand d38b5d1a)

Binary: `$S/final-cand/src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin`, port 52827, data `$S/ls2-data` (scratch, never the operator's app data). Driver `$S/fam/ls2.sh`; stdin is a fifo held by a recorded `sleep` pid so EOF is the Tauri-core stop signal. Raw: `LS-2/ls2.log`, `boot-{1,2,3}.log`, `taken-port.log`, `second-instance.log`, `after-corrupt.body`.

- **Cold boot:** health 200 after 64 s (boot 1, cold `_MEI` extraction), 28-30 s warm (boots 2-3) — inside the 45 s x 2 budget.
- **EOF stop (x3):** worker exits 3 s after stdin closes, its one child gone, port released, no orphans (`children_left=[]`, `port_free=yes` every time).
- **Persistence:** custom agent (201) and workspace LS2-WS (200) survive a stop/reboot on the same data dir (agent 200, ws 200, list `["LS2-WS"]`).
- **Taken port:** the first attempt (`second-instance.log`) had stdin on /dev/null and exited by the EOF watchdog before binding — inconclusive, not counted. Re-run with stdin held open on a port my own :52825 holds: `[Errno 48] address already in use`, clean uvicorn shutdown, then `Fatal Python error: _enter_buffered_busy ... <stdin>` -> exit 134 (SIGABRT). The holder kept serving (health 200). Non-zero exit is right; dying by abort is not -> **maintainer:6 (low)**.
- **Corruption (my own copies):** truncated `custom_agents.db` (12288->6144), half-written LS2-WS blob (209->104 bytes), 18 garbage bytes over `delegate_runs.db`; reboot -> health 200.
  - Workspace: quarantined as `LS2-WS.vysted-workspace.corrupt-1791021518067` (kept), GET -> 404 with a sentence. R15-DATA-090's fix holds.
  - Runs: SQLite treated the sub-page garbage file as empty and re-initialised it; `/runs` 200 `[]`, a new run creates (201) and cancels (200). Acceptable (nothing to lose in an 18-byte file).
  - Custom agents: `GET /custom-agents`, `GET /custom-agents/custom:ls2-agent` and `POST /custom-agents` all **500** (`sqlite3.DatabaseError: database disk image is malformed`, boot-3.log), permanently, no quarantine; the user cannot create a new agent either -> **maintainer:5 (medium)**, class sibling of R15-DATA-090.
  - The rest of the app keeps working (`/agents` roster 200, `/workspace` 200, `/runs` 200).
- All LS-2 pids stopped by the script (bootloader + sleep per boot; recorded in `$S/fam/pids.txt`).

VERDICT LS-2: finding maintainer:5 maintainer:6
