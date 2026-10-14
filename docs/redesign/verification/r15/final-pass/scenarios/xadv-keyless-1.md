# xadv-keyless-1 — cold first boot on a stranger's clean profile (no keys, built binaries)

Head under test d38b5d1a2487bd52fe8a7e741a3a5266e3206611; binaries `SCRATCH/final-cand/src-tauri/binaries` (built 14:39-14:41).
Profile `SCRATCH/final-xadv-keyless/data` = empty dir + `dev-keystore.json` `{"secrets": {}, "migrated": true}` (0600). Cache dir `SCRATCH/final-xadv-keyless/cache`.

## Commands (spawn shape = src-tauri/src/lib.rs:400-410: `--port --data-dir --cache-dir` + MCP port env)
```
boot.sh openbb   .../vysted-openbb-mcp-sidecar-aarch64-apple-darwin --port 52901     -> sleep 36286 / worker 36285
boot.sh secedgar .../vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin --port 52902  -> sleep 36292 / worker 36291
VYSTED_OPENBB_MCP_PORT=52901 VYSTED_SEC_EDGAR_MCP_PORT=52902 boot.sh main .../vysted-sidecar-aarch64-apple-darwin \
   --port 52900 --data-dir $K/data --cache-dir $K/cache                               -> sleep 36299 / worker 36298
```
(boot.sh: worker stdin = a fifo held by `sleep 86400`; launched 15:05:09 IST.)

## Cold boot timing (polled in separate calls)
- +10s, +37s, +67s, +76s, +87s, +93s, +129s: main `/health` 000 (no listener); main.log empty (PyInstaller `_MEI` extraction + imports).
- main log: `15:07:57,869 Uvicorn running on http://127.0.0.1:52900` => **~168 s cold** from spawn.
- Contention at the time: another agent spawned a second candidate stack in the same second (pids 36303/36309/36314), the shared final stack (:52800) and the GUI redrive app were live. PREFLIGHT.md records ~2 min for the same binary under similar contention. README promises "a one-time ~30–90s warm-up". Not attributable to the product on this contended box (R1(b)); recorded, not filed. The Tauri core waits 45 s x 2 on each MCP port (CLAUDE.md), and the main sidecar spawn is not gated on that here, so a real app first-launch on a quiet machine is the operator-attended number.

## Read-backs
```
GET /health -> {"status":"ok","service":"vysted-sidecar","version":"0.9.0","providers":{... "quote":"ccxt (nse_direct, nse, bse, yfinance fallback)","openbb-mcp":"available"},"agents_degraded":[]}
GET /mcp/status -> {"ready":true,"toolCount":39,"endpoint":"/mcp","protocolVersion":"2025-11-25"}
GET /agents -> 13 agents: buffett, copilot, dalio, druckenmiller, graham, klarman, lynch, marks, munger, portfolio_advisor, researcher, soros, strategy_critic
```
README says "13 first-party agents" — matches. Version 0.9.0 — matches README "version strings sit at 0.9.0".

Data dir after first boot: only `dev-keystore.json` (unchanged, still `{"secrets": {}, "migrated": true}`, 0600) + `workflows.db`. Cache dir: `data_cache.db`, `fundamentals_cache.db` (fundamentals warm seeded the India universe on a clean profile; log: `fundamentals warm: seeded ... india rows`).
Operator's real data dir mtime unchanged (stat: `Oct 3 03:25:02 2026`), never written.

Note: the dev keystore is read by the Rust core, not the sidecar; the no-keychain-sweep guarantee on a real first launch needs a window (needs_gui item already in the register set: R15-LIFECYCLE-001 / UI-044 class). Not re-tested here.

VERDICT xadv-keyless-1: pass
