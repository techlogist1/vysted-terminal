# rc1-vshard-1 working log (gate round 5)
- candidate 633f844071d972b337f4c3526d86555c80df0568 verified in worktree rc1-round-5-9bc600e-fix-int
- own sidecar :52601, data dir scratchpad/rc1-round-5-data-rc1-vshard-1, sleep pid 87635, worker 87636; /health ok
- 16:47 took Ollama lock for AGENT-011 llama run (curl POST to own :52601; vy.py refuses non-GET outside 52100-52399 so vy.py invoke cannot target :52601). Lock dir vanished while my run was still live (another holder removed it) - harness note.
- 16:50 mis-boot on :52602 (owned by vshard-2) exited on bind; killed my own sleep 4894 only. Second own sidecar :52611 (openbb-mcp pointed at closed :52698) sleep pid 5099 worker 5100, for LIFECYCLE-005.
- Keyless search engines all blocked from this host (DDG timeout, Brave 429, Mojeek 403) and Yahoo 429s — environment.
- 16:55 Ollama lock for AGENT-013 Delegate run (copilot, llama3.1:8b) on own :52601 -> done 16:59:50; lock released by trap.
- DATA-016/DATA-093/UI-003/DATA-056/DATA-074/AGENT-058/LIFECYCLE-007 checked (live on own :52601 where the host allowed, in-process otherwise). UI-003 probe agent custom:vshard1-ui003 created+deleted on own sidecar data dir only.
- 17:0x stopped own sidecars: killed sleep 87635 and 5099 only; workers exited; :52601/:52611 no longer listening.
- Outputs: verifier/shard-1.md, verifier/shard-1-evidence/, findings/rc1-vshard-1.json (8 findings).
