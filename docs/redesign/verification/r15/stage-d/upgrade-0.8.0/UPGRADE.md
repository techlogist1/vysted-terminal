UPGRADE 0.8.0 → 0.9.0 (sidecar half): PASS. No user-created object was lost or changed in meaning. The app-side half was NOT TESTED (operator-attended).

# Data-dir upgrade proof: 0.8.0 sidecar → 0.9.0 sidecar

- **Prover:** the headless data-upgrade prover, model `claude-opus-5-5` (Opus 5.5, medium effort). The advisor was not consulted.
- **0.8.0:** tag `v0.8.0`, commit `f45019f6aff587dbfa010c147339d5188c5f3ecb` (tag object `696a9f11`).
- **0.9.0:** tag `r15-launch`, commit `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` (tag object `a8fd7d3b`).
- **0.8.0 binary:** built for this run from a detached worktree `<scratchpad>/upgrade-080/wt-080` at `v0.8.0`. The commands were `pnpm install --frozen-lockfile` and then `VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-sidecar.mjs --force`, the main sidecar only, run under that tag's own recipe. The venv was pre-created with Homebrew `python3.13`, because `python3` on this host is 3.14. The build exited 0 (`raw/build-0.8.0.log.tail`). Its sha256 is `7ca16e43…7f918f58`, 90 MB.
- **0.9.0 binary:** `<scratchpad>/bundle-rc2b/src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin`, built from 1fddb2b1. It was used read-only. Its sha256 is `90a8cf92…2c46447`, 87 MB. Both full hashes are in `raw/binaries.sha256`.
- **Data dir:** `<scratchpad>/upgrade-080/data`. Both binaries used this same directory and nothing was copied into it. A supplementary dir, `<scratchpad>/upgrade-080/data-plugins`, was used for plugin config (see Method §5).
- **Ports:** 52150 for 0.8.0 seeding and 52151 for the 0.9.0 first boot. 52152 was the 0.9.0 second boot. 52153 and 52154 were the supplementary plugins run (0.8.0 and 0.9.0).
- **Times (UTC, from `date`):** 0.8.0 ran from 19:19:00 to 19:23:33 on 3 Oct 2026. The 0.9.0 first boot ran from 19:27:25 to 19:29:56. Its `/health` first answered at 19:28:31 (00:58:31 IST), a cold start of about 66 s. The second boot and the plugins run followed, ending at about 19:48 UTC (01:18 IST).
- **Environment:** keyless throughout. Each sidecar ran under `env -i HOME=$HOME PATH=/usr/bin:/bin`, so no provider key could reach it. Nothing secret was used, so nothing is redacted. Paths are sanitized to `<scratchpad>`.

## Method

1. **Seed through 0.8.0's HTTP API only.** The routes come from the `v0.8.0` routers. 0.8.0 was started as `sh -c 'sleep 100000 | <bin> --port 52150 --data-dir <data>'`. It received:
   - `POST /portfolio/positions` ×3: AAPL equity with cost basis and a note, BTC/USDT crypto with cost basis and a note, and NVDA equity. NVDA was then edited with `PUT /portfolio/positions/3` (quantity 40→45, cost 118.9→121.1, note added).
   - `POST /custom-agents` for `custom:dividend-hawk`, with tools `price_data, fundamentals, macro, news, backtest_summary`, which are 0.8.0's whole allow-list.
   - `POST /workflow/save` for `wf-aapl-close-check`, four nodes (`data.fetch_quote → transform.json_path → logic.compare → action.log`) and three edges.
   - `POST /workspace` ×2. **`Main Desk`** is exactly the shape 0.8.0's `serializeWorkspace` writes: `name`, a dockview `layout`, `enabledModules` and `chartDrawings`. **`Research_Desk-2`** is an opaque-passthrough probe that adds the 0.9.0 `watchlist` key (AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT) and a `notes` key. 0.8.0's UI never writes those keys; see the table.
   - `GET /fundamentals/AAPL/ratings/history` so that 0.8.0 writes a real `data_cache.db`, as any real 0.8.0 user's data dir would hold one.

   The payloads are in `raw/seed-payloads/` and the write responses in `raw/seed-080/`.
2. **Read every object back on 0.8.0** (`raw/readback-080/`, JSON with sorted keys). Then stop it by pid, confirm with `ps`, and dump every `.db` with `raw/dbdump.sh`: `sqlite3 -readonly .schema`, `PRAGMA user_version`, per-table row counts and per-file sha256. That dump is `raw/db-080/`, and the user-table rows are in `rows_*.json`.
3. **Start 0.9.0 on the same dir:** `--port 52151 --data-dir <data> --cache-dir <data>`. The `--cache-dir` mirrors the 0.9.0 Tauri spawn (`src-tauri/src/lib.rs:401-408`); on macOS `app_local_data_dir == app_data_dir`. `/health` reported `"version":"0.9.0"`. The same objects were read through the 1fddb2b1 routes, none of which moved, plus `/custom-agents/tool-ids`, `/workflow/node-types` and `/workflow/schedules` (`raw/readback-090/`). The sidecar was dumped while live (`raw/db-090-live/`) and again after stopping (`raw/db-090/`). The read-backs were diffed in `raw/readback-diff.txt`.
4. **Second 0.9.0 boot (port 52152).** This tests migration idempotence. All read-backs were byte-identical to the first 0.9.0 boot (`raw/readback-090-reboot/`), row counts were unchanged (`raw/db-090-reboot/`), and no second backup or cache clear happened.
5. **Supplementary: plugin config.** `plugins.db` is the only user store whose 0.9.0 migration adds a column (`ALTER TABLE … ADD COLUMN installed`), and it is outside the brief's object list. The main dir had already been migrated, and re-running 0.8.0 on it would be a downgrade. The same method was therefore run on a fresh dir `data-plugins`: 0.8.0 `POST /plugins/{id}/config` ×2 (`yfinance` enabled with settings, and `vysted-news` disabled with settings and a granted secret *id*), read back, stopped and dumped; then 0.9.0 read the configs back, was stopped and dumped. The evidence is in `raw/plugins/`.

Every process was stopped by pid and its `sleep` stdin holder by name. After each stop `pgrep` found none and `lsof` showed ports 52150-52154 free.

## Per-object verdicts

| Object | 0.8.0 store | 0.9.0 read path | Verdict | Evidence |
|---|---|---|---|---|
| Portfolio positions ×3 (AAPL equity, BTC/USDT crypto, NVDA equity edited by PUT) | `portfolio.db` `positions` | `GET /portfolio/positions` | **Preserved.** Byte-identical: ids 1-3, qty, cost basis, asset class, `opened_at` and notes, including the PUT edit. The file is now the legacy ledger, and the 0.9.0 router is GET-only. The app imports it once into the workspace-blob portfolio (R15-LIFECYCLE-009, `src/modules/portfolio/api.ts:77-82`); that import is app-side and NOT TESTED here. | `readback-diff.txt`, `db-*/rows_portfolio.json` |
| Note (0.8.0 has no notes surface; the user's notes live on positions) | `positions.note` | same | **Preserved.** Both position notes come back verbatim. | as above |
| Custom agent `custom:dividend-hawk` | `custom_agents.db` | `GET /custom-agents`, `GET /custom-agents/custom:dividend-hawk` | **Preserved.** Byte-identical, including `created_at`/`updated_at`. All 5 stored tool ids resolve on 0.9.0. Four are on `/custom-agents/tool-ids` (`price_data, fundamentals, news, backtest_summary`). `macro` is a catalog alias of `macro_series` (`catalog.py:617-618`), which `agent_runtime.py:1783` resolves at invoke. The read shape returns the stored list verbatim. `default_provider` `anthropic` is still a registry provider. The agent is absent from `/agents` on both versions (12 → 13 first-party), which is unchanged behaviour. | `readback-090/custom_agent.json`, `tool_ids.json`, `agents_summary.txt` |
| Saved workflow `wf-aapl-close-check` | `workflows.db` | `GET /workflow/saved`, `GET /workflow/saved/{id}` | **Preserved.** The spec is byte-identical. The list gains an empty `"unreadable": []` envelope key, which is a wire-shape addition, not a content change. `version` 1 equals `WORKFLOW_SPEC_VERSION` 1, so the row is not refused, and all four node types are registered on 0.9.0 (`/workflow/node-types`, 24 types). | `readback-diff.txt`, `node_types.json` |
| Workspace `Main Desk` (0.8.0 serializer shape: layout, enabledModules, chartDrawings) | `workspaces/Main Desk.vysted-workspace` | `GET /workspace`, `GET /workspace/Main%20Desk` | **Preserved.** Read-back is byte-identical and the file on disk is byte-identical. The name with a space keeps the same stem under the new encoder, so no legacy-stem rename fired. Upgrading the blob from schema v0 (`migrateWorkspace`) is frontend work and NOT TESTED here. | `readback-diff.txt`, `db-090/files.sha256` |
| Watchlist | **none in 0.8.0.** The watchlist was an in-memory Zustand store (`src/store/symbols.ts`, "never persisted") that reset to the defaults every launch. 0.8.0 has no watchlist route. | — | **N/A: nothing to lose.** A 0.8.0 user has no persisted watchlist. As an opaque-passthrough probe, the `Research_Desk-2` blob carried a `watchlist` (7 entries) plus `notes`. 0.9.0 returned it byte-identical and the file on disk is byte-identical. | `readback-090/workspace_probe.json` |
| Saved workspace/layout list | `workspaces/` | `GET /workspace` | **Preserved:** `["Main Desk","Research_Desk-2"]`. | `workspace_list.json` |
| Plugin configs ×2 (supplementary dir) | `plugins.db` `plugin_configs` | `GET /plugins`, `GET /plugins/{id}/config` | **Migrated.** `enabled`, `settings` and `granted_secret_ids` are identical for both. The new column `installed` was added by ALTER and backfilled to `1`/`true` for both rows. That is the documented default ("any config persisted before this column existed reads as installed"), and it matches 0.8.0, which had no uninstalled state. `vysted-news` stays `enabled:false`. | `plugins/readback-*`, `plugins/db-*/rows_plugins.json` |
| Price/analyst cache | `data_cache.db` | n/a (regenerable) | **Migrated, then cleared by design.** `ensure_build` found no build row, backed up the data dir, cleared `cache` and recorded `build=0.9.0`. Row count went from 1 to 2 (fresh rows from the 0.9.0 boot). This is not user data. | `sidecar-0.9.0.log.txt` lines 6-7 |
| Broker / trading state | none written: trading needs credentials, and the run was keyless | — | **Not seeded.** D81 removed trading permanently, so 0.9.0 has no reader for it. | — |

## Schema diff (0.8.0 → 0.9.0, main dir)

| DB | user_version | Tables (rows) 0.8.0 → 0.9.0 | DDL change |
|---|---|---|---|
| `portfolio.db` | 0 → 1 | positions 3 → 3 | none (versioning only) |
| `custom_agents.db` | 0 → 1 | custom_agents 1 → 1 | none |
| `workflows.db` | 0 → 1 | workflows 1 → 1; **+schedules 0** | `CREATE TABLE schedules (…)` |
| `data_cache.db` | 0 → 1 | cache 1 → 2 (cleared then refilled); **+meta 1** | `+INDEX cache_updated_at`, `+TABLE meta` |
| `plugins.db` (supplementary) | 0 → 1 | plugin_configs 2 → 2 | `ADD COLUMN installed INTEGER NOT NULL DEFAULT 1` |
| `fundamentals_cache.db` | — → 1 | new: fundamentals 6157 (seed pack) | new regenerable cache |

New non-DB items are `resolver_masters/` (NSE/BSE instrument masters, regenerable) and **`backups/unversioned-2026-10-04/`**. That backup is the pre-upgrade copy 0.9.0 takes before touching anything (R15-LIFECYCLE-024). Its user files are **byte-identical to the 0.8.0 stop state** (`raw/backup-unversioned.sha256` vs `raw/db-080/files.sha256`). Only `data_cache.db-wal/-shm` differ, because 0.9.0 opens and migrates the cache before it takes the copy; the cache is regenerable. It is named `unversioned-<date>` because 0.8.0 recorded no build row. A rollback to 0.8.0 is possible from it.

## Log findings

- `sidecar-0.9.0.log.txt`: **0 tracebacks**, and no migration, schema, corrupt or quarantine messages besides the two expected `data_cache` INFO lines (backup taken, cache cleared). All 13 ERROR lines are `yfinance: HTTP Error 404` for BSE `.BO` symbols from the background fundamentals warm-up. The 16 WARNINGs are the 13 matching `provider_registry` fall-throughs plus three NSE fetch failures (`nse_symbol_change` ×2, `nse_bhavcopy` ×1). All of it is network noise unrelated to the upgrade.
- `sidecar-0.9.0-reboot.log.txt` and `sidecar-0.9.0-plugins.log.txt`: 0 tracebacks and 0 non-yfinance ERRORs. The reboot log has no `data_cache` clear and no backup, so the build row persisted and the migrations are idempotent.
- `sidecar-0.8.0*.log`: clean uvicorn access logs.
- Incidental: the 0.9.0 boot probed a local search endpoint on `127.0.0.1:8888` (GET, 200). That listener was not started by this run. It was read-only and was not touched.

## Overall verdict: **PASS (sidecar half)**

- Every object seeded through 0.8.0 reads back on 0.9.0 with the same content: positions and notes, custom agent, saved workflow, both workspace files, and plugin configs (supplementary dir).
- The only shape changes are additive: the workflow list's `unreadable: []` envelope and plugins' `installed: true`. Neither alters meaning.
- The user-table rows are byte-identical before and after.
- A verified pre-upgrade backup exists, and a second boot changes nothing.
- The only discarded data is the regenerable price cache, which is cleared by design.
- The watchlist has no 0.8.0 persistence, so there was nothing to carry. Its 0.9.0 storage (the workspace blob) passes through the sidecar intact.

## NOT TESTED: app-side half (operator-attended)

The items below need the installed release app. The release app raises a login-keychain consent prompt at launch (**R15-LEAD-143**), so it cannot run headless or unattended, and this prover was also barred from the GUI, the keychain and the operator's real data dirs.

- **Workspace blob restore in the UI.** `deserializeWorkspace` and `migrateWorkspace` upgrade a schema-v0 (0.8.0) blob such as `Main Desk`: layout, enabled modules and chart drawings, with the default watchlist on first 0.9.0 launch.
- **Legacy positions import** (R15-LIFECYCLE-009). The app reads `GET /portfolio/positions` once into the blob portfolio. The sidecar half of this, returning the rows unchanged, is proven above. The UI import and its once-only guard are not. There is a unit pin at `src/lib/workspace.test.ts:1721` ("v0.8.0 rows"), but it is not evidence from a run.
- **Dev-keystore / OS-keychain migration** of BYOK keys and disclaimer acks (`src-tauri/src/keychain.rs`).
- **First launch of the installed `.app`** over a real 0.8.0 `~/Library/Application Support/com.vysted.terminal`, including the Tauri `--data-dir`/`--cache-dir` resolution and any `com.vysted.desk` carry-over.
