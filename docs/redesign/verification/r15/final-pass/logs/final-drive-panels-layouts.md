# final-drive-panels-layouts working log

- Head under test d38b5d1a. Own sidecar :52843 from final-cand/sidecar source, data dir scratchpad/final-data-final-drive-panels-layouts (seed copy, keyless: 0 secrets), MCP 52801/52802. sleep pid 80271, worker 80272. Booted 16:28 IST.
- Reads -> shared :52800; writes -> :52843.
- Replayed all 299 census calls (P-http-replay.jsonl). Status diffs are in P-census-vs-final.txt and explained in drives/panels-layouts.md.
- Extra probes are in P-http-extra.jsonl and F-*.txt. Layout and workspace probe ran on a real dockview grid in jsdom: L-layouts-probe.json and L-workspace-roundtrip.json.
- Harness fixes (not product issues): import dockview, not dockview-core; wrap the component in DockviewApi; register vystedModules before load.
- Local-model narrative ran once, under /tmp/vysted-r15-ollama.lock (llama3.1:8b); lock released.
- Findings: nd-1 custom-arrange false success (medium), nd-2 workspace .bak resurrection (low), reg-1 regression of R15-UI-094 (low). Attached R15-DATA-030 and R15-DATA-061 in ATTACHED.json.
- No new NEEDS_GUI entries. The carried rows (node-editor canvas and palette, chart draw gesture, native Layout menu click) are the census rows.
- 16:42 IST: stopped own sidecar (kill 80271, the recorded sleep pid). Worker 80272 exited and :52843 is free.
