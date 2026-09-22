# R15 Stage 0 — isolated stack, booted (session 3, 2026-09-23)

Booted per `ISOLATION_MAP.md` §1a-A (source run) + the openbb/sec-edgar parity note. Nothing
touched the operator's live data dir (`~/Library/Application Support/com.vysted.terminal`) or
live keychain — all reads were `sqlite3 ... mode=ro` `.backup`, never `cp` on a WAL db.

ISO root: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vysted-iso`
Data dir: `$ISO/data`

## What was copied (and what wasn't)

```bash
SRC="$HOME/Library/Application Support/com.vysted.terminal"
for db in data_cache fundamentals_cache portfolio plugins custom_agents delegate_runs; do
  sqlite3 "file:$SRC/$db.db?mode=ro" ".backup '$ISO/data/$db.db'"
done
cp "$SRC/workspaces/__autosave__.vysted-workspace" "$ISO/data/workspaces/"
cp "$SRC/searxng/settings.yml" "$ISO/data/searxng/"
cp -R "$SRC/notes" "$ISO/data/"
printf '{\n  "secrets": {},\n  "migrated": true\n}\n' > "$ISO/data/dev-keystore.json"
chmod 600 "$ISO/data/dev-keystore.json"
```

- `audit_log.db` — **not copied**, by design (§6.5 append-only; isolated profile starts with
  zero audit rows).
- `dev-keystore.json` — **not copied from SRC**; instead seeded fresh with `migrated: true` and
  an empty secrets map (ISOLATION_MAP.md §2.4) so first boot never sweeps the operator's real OS
  keychain. This isolated profile is genuinely keyless.
- `exports/`, `mcp-endpoint.json` — deliberately excluded (regenerated / zero behavioural value).

## Boot commands (exact)

MCP subprocesses first, parity with the Rust core's own spawn order (`lib.rs:482-485`):

```bash
cd /Users/lokavyasingh/Documents/dev/vysted-terminal
sleep 86400 | src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin --port 52153 \
    > "$ISO/openbb-mcp.log" 2>&1 &
sleep 86400 | src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin --port 52154 \
    > "$ISO/sec-edgar-mcp.log" 2>&1 &
```

Main sidecar, from source (picks up any uncommitted hot patch — ISOLATION_MAP.md observation 4):

```bash
cd /Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar
export VYSTED_OPENBB_MCP_PORT=52153
export VYSTED_SEC_EDGAR_MCP_PORT=52154
sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52152 --data-dir "$ISO/data" \
    > "$ISO/sidecar.log" 2>&1 &
```

## PIDs / ports

Full record: `$ISO/pids.json`.

| Role | Sleep pid (kill this) | Worker pid | Port |
|---|---|---|---|
| Main sidecar | 43764 (restarted 2026-09-23 for the num_ctx fix; was 37894) | 43765 (was 37895; `bash -c` wrapper 43762) | 52152 |
| openbb-mcp | 37799 | 37800 (bootloader) / 37808 (worker) | 52153 |
| sec-edgar-mcp | 37801 | 37802 (bootloader) / 37809 (worker) | 52154 |

Both MCP binaries were checked for staleness before spawn: `find sidecar -iname "*openbb*"/"*edgar*" -type f -newer <binary>` (excluding `.venv`/cache dirs) returned **0** newer source
files for either — both binaries are current against `sidecar/openbb_mcp_subprocess/` and
`sidecar/sec_edgar_mcp_subprocess/`. `scripts/sidecar-staleness.mjs` exports functions
(`isStale`, `assertFresh`, `newestSourceMtime`) but has no CLI entry point (no `process.argv`
handling), so the check above was done by hand via `find -newer` instead, per the task's
fallback instruction. Same check against the main sidecar binary
(`vysted-sidecar-aarch64-apple-darwin`, 19 Sep 06:26): also 0 newer files under `sidecar/` — the
shipped binary is *not* stale here, but we still booted from source per the task's instruction
(1a-A), since a source run provably includes anything uncommitted.

## Health

`GET /health` returned `ok` in <1s from process start (source run, no PyInstaller `_MEI`
extraction — contrast the ~10-60s cold boot the map documents for the shipped binary):

```json
{"status":"ok","service":"vysted-sidecar","version":"0.8.0","providers":{"analyst_rating":"openbb-mcp (yfinance fallback)","balance_sheet":"openbb-mcp (yfinance fallback)","cash_flow":"openbb-mcp (yfinance fallback)","fundamentals":"openbb-mcp (yfinance fallback)","income_statement":"openbb-mcp (yfinance fallback)","macro_series":"openbb-mcp","ohlcv":"ccxt (nse_direct, nse, bse, yfinance fallback)","quote":"ccxt (nse_direct, nse, bse, yfinance fallback)","openbb-mcp":"available"}}
```

`"openbb-mcp":"available"` confirms the MCP env-var wiring worked (contrast the map's degraded
default: unset `VYSTED_OPENBB_MCP_PORT` → yfinance-only fallback). A direct probe of
`/sec/filings/AAPL` returned `422` (validation error on params), not `501` — confirming the
sec-edgar-mcp route is live too (the map's degraded default without `VYSTED_SEC_EDGAR_MCP_PORT`
is a flat `501`).

## Search / SearXNG status — what changed vs the DOCKER_STATE.md baseline

`r15/stage0/DOCKER_STATE.md` (recorded earlier this session, before Docker was started) had:
Docker daemon not running, `/search/searxng/status` → `not_installed_docker` (`"docker CLI found
but the daemon is not running"`), `/search/status` tier `t1_keyless`.

Now, with the operator's Docker/OrbStack up and `vysted-searxng` running on `127.0.0.1:8888`:

```
GET /search/status
{"tier":"t1_keyless","available":true,"engines":[{"id":"ddg",...},{"id":"brave",...},{"id":"mojeek",...}]}

GET /search/searxng/status
{"state":"ready","detail":"SearXNG serving JSON search at http://127.0.0.1:8888","reason":null,
 "port":8888,"url":"http://127.0.0.1:8888","container":"running","container_name":"vysted-searxng",
 "image":"searxng/searxng","docker":{"cli_present":true,"daemon_running":true,"runtime":"Docker Engine - Community"}}
```

**What changed:** `/search/searxng/status.state` went `not_installed_docker` → `ready`, and the
`docker.daemon_running` flag flipped `false` → `true`, with `container` now `running`. **What did
not change:** `/search/status.tier` stayed `t1_keyless` — SearXNG readiness alone does not
promote the active search tier; that's a separate selection this drive did not probe further
(observation only, not acted on). This isolated sidecar only *read* the shared SearXNG
container's status; nothing here started, stopped, or reconfigured Docker or the container, per
the boundary rule.

## How to stop the stack

Kill the three **sleep** pids (closes each subprocess's stdin → its own watchdog exits it
cleanly; never `kill -9` a PyInstaller bootloader):

```bash
kill 43764 37799 37801
```

The stack was left **running** at the end of this session (per the task's instruction), with the
local-lane's ollama model unloaded (see `LOCAL_LANE_PROOF.md`).
