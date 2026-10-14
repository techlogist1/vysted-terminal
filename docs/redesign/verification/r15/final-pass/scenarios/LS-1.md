# LS-1 first run from a clean profile on the production bundle's sidecars

Binaries: booted from final-cand/src-tauri/binaries; `shasum -a 256` proves they are byte-identical to the bundle's Contents/MacOS copies (LS-1/sha256.txt: vysted-sidecar 2b5bfd59..., openbb-mcp 326d8d26..., sec-edgar-mcp aa91bee7...).
Profile: EMPTY dir final-stranger-maintainer holding only dev-keystore.json = `{"secrets": {}, "migrated": true}` (chmod 600).
Spawn order as the core: openbb-mcp :52821, sec-edgar-mcp :52822, main :52820 with VYSTED_OPENBB_MCP_PORT/VYSTED_SEC_EDGAR_MCP_PORT exported; stdin held by a sleep each (scratchpad/fam/launch.sh, pids scratchpad/fam/pids.txt).

## Timed cold boot
Start 14:46:23. openbb :52821 bound by 14:48:26 (~2 min). main :52820 and sec-edgar :52822 not listening at 14:49:56, listening at 14:50:38 => cold bind 213-255 s for all three. REHEARSAL.md measured ~40 s main / ~60 s all three. Cause seen live: XprotectService at 71.5% CPU (ps) while the workers sat at 0% CPU holding freshly extracted _MEI .so files (lsof) — first exec of freshly built, unnotarised binaries, plus other agents' stacks running. Within the 285 s main budget the R15-LEAD-123 fix set (src-tauri lib.rs 45 s x 6 + 15 s; sidecar-client.ts READY_DEADLINE_MS 300_000), but the margin was 30-70 s. Attached to R15-LEAD-123 as evidence (open at this sha in the snapshot; fixed at 004 head), not a new entry.

## Endpoints (LS-1/*.json)
- /health: status ok, version 0.9.0 (= package.json at the sha), openbb-mcp available, agents_degraded [].
- /agents: 13.
- /mcp/status: ready true, toolCount 39 (the smoke test asserts > 0; the shared preflight stack and the in-process list_tools also read 39).
- /system/ollama/status: running, models qwen3:8b, qwen2.5:7b, llama3.1:8b.
- /system/local-model-recommendation: device M1 Pro 16 GiB, candidates with green verdicts.
- /llm/providers: ollama requires_key false.
- Keyless local lane answers: copilot on llama3.1:8b via Ollama, no key, under the lock: LS-1/local-turn.stdout — done/finish_reason stop in 53.6 s, reply "I'm a terminal copilot that can assist with analyzing stocks ...".

## Data dir after boot + one turn (LS-1/datadir-after.txt)
data_cache.db(+wal/shm), fundamentals_cache.db, workflows.db, resolver_masters/{bse,nse}_instruments.json, dev-keystore.json unchanged `{"secrets": {}, "migrated": true}`. No audit_log.db, no secrets written. (No mcp-endpoint.json: written by the Rust core, not present headless — expected per ISOLATION_MAP 2.3.)

## GUI first run
Not run by this pass (DECISIONS 5.9: a HOME= launch leaks WKWebView files into the real ~/Library; REHEARSAL finding 1 / R15-UI-044). Operator-attended under R15-LIFECYCLE-001 (needs_gui) — steps in NEEDS_GUI.md.

VERDICT LS-1: pass
