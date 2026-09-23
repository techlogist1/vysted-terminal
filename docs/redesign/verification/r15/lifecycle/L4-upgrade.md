# L4-upgrade: does 0.8.0 data survive the upgrade?

Worker: claude-opus-5-5[1m] (life-S2B, item `l4-upgrade`). Status: COMPLETE (2026-09-23).
Attempt 2 (same day, 12:10-12:25 IST) continued this file: §6 adds the upgrade path from the
released `v0.8.0` TAG, which §1 below does not cover, and two more raw findings.

Method: code-read of every persistent store's schema/connect path + an induced upgrade on my
OWN sidecar (port 52228), booted from current source (`004-r4-experience-rebuild` @ f763a44 +
the working tree) over my own copy of the 19-Sep 0.8.0 data dir. I then read back every store
through its own router, and ran a scratch vitest that pushes every historical workspace blob
through the current frontend restore code. I fixed nothing; this file only records.

## 0. Which data dir, and why not `$ISO/data`

The "19-Sep 0.8.0 data dir" is the operator's `~/Library/Application Support/com.vysted.terminal`.
Every file there has mtime <= 2026-09-19 17:44, and `mcp-endpoint.json` was written at 19 Sep
06:31, just after the 0.8.0 binary build at 06:26 (`ISO_STACK.md:69`). No Vysted process was
running when I copied it. I did **not** `cp -R $ISO/data`: the shared current-source sidecar
on :52152 has been running over that copy since 04:23 today, so any migration would already
have been applied there and the test would prove nothing. I took a fresh copy instead, using
the ISO_STACK recipe:

```bash
SEAT=$ISO/seat-l4-upgrade; D=$SEAT/data
for db in custom_agents data_cache delegate_runs fundamentals_cache plugins portfolio; do
  sqlite3 "file:$SRC/$db.db?mode=ro" ".backup '$D/$db.db'"; done
cp "$SRC/audit_log.db" "$D/"      # WAL-mode file with no -wal/-shm; mode=ro open fails (SQLITE_CANTOPEN 14), plain cp is safe (fully checkpointed, app not running)
cp -R "$SRC/workspaces" "$SRC/notes" "$SRC/searxng" "$D/"
printf '{"secrets": {}, "migrated": true}' > "$D/dev-keystore.json"   # never copied, never read
```

I excluded `exports/` (43 MB of PDFs that no store reads), `mcp-endpoint.json` (the Rust core
regenerates it) and `dev-keystore.json` (COMMON.md forbids reading it). Boot:
`sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52228 --data-dir $D`, with
no MCP env vars (I may not touch :52153/54, so openbb/sec-edgar ran degraded, which does not
matter for store reads). `/health` came back `ok` at version `0.8.0` on first poll. The pids
are in `$ISO/pids-life-l4-upgrade.json` (sleep 49010, worker 49011).

Evidence dir: `$ISO/seat-l4-upgrade/evidence/`: `pre-boot-schema.txt`, `post-boot-schema.txt`,
`l4-reads-1.txt`, `l4-screener.json`, `workspace-upgrade-vitest.txt`, `vitest-run.log`.

## 1. What changed between the 0.8.0 build and HEAD

`git log --since=2026-09-19T06:00 -- sidecar src-tauri src/lib` shows only three commits. None
of them touches a store: `d328089` (Ollama `num_ctx`), `0c63d46` (relicense) and `0112a0c`
(test-only). This upgrade is therefore **schema-neutral**. That holds for the 19-Sep dev dir only;
the release-tag path (`v0.8.0`, 18 May) is not schema-neutral and is covered in §6. The dir's contents are older than
the build: `custom_agents.db` May 29, `data_cache.db` Jun 11, `portfolio.db` Jul 10,
`delegate_runs.db` Jul 10. So the test really checks that current code reads stores written
by May–Sep builds.

## 2. Per-store verdicts

Pre- and post-boot schema, `PRAGMA user_version` and row counts were captured with
`snap.sh`. `diff pre-boot-schema.txt post-boot-schema.txt` shows only three changes: +2
`data_cache` rows (the boot-time bhavcopy/symbol-change warm), a new empty `workflows.db`,
and the `__autosave__` hash (my own vitest POSTed to this sidecar; see §3).
`grep -E "ERROR|Traceback|OperationalError|no such (column|table)|WARNING" sidecar.log` finds
**0** matches.

| Store | Written by | Schema vs current DDL | Migration code | Read-back (route, result) | Verdict |
|---|---|---|---|---|---|
| `portfolio.db` `positions` | Jul 10 | identical (`portfolio_db.py:26-35`) | none | `GET /portfolio/positions` 200 `[]` (0 rows on disk) | clean read |
| `custom_agents.db` | May 29 | identical (`agents_store.py:41-54`) | none ("no schema migrations", `:23`) | `GET /custom-agents` 200 `[]` (0 rows) | clean read |
| `delegate_runs.db` `runs` | Jul 10 | identical, `options_json` already present | additive ALTER guard `runs_store.py:94-102` (no-op here) | `GET /runs` 200, 2 runs; `GET /runs/{id}` 200 for both, `checkpointMessages`/`transcript` present | clean read |
| `plugins.db` `plugin_configs` | Jun 4 | `installed` column already ALTERed in by an older build | `plugins_store.py:53-67` (no-op here) | `GET /plugins` 200, 7 rows | clean read (with an orphan row, see note a) |
| `fundamentals_cache.db` | Sep 19 | identical, 3 late columns present | `fundamentals_store.py:172-182` (no-op here) | `POST /screener/run india-all pe_ratio<15`: 200 in 11.4 s, `evaluated_count 5066`, `skipped 90`, `partial:false`, rows SBIN/LICI/INFY/AXISBANK/NTPC | clean read |
| `data_cache.db` `cache` | Jun–Sep | identical (`data_cache.py:59-65`) | none | reads are TTL-gated; bhavcopy decode guarded (`nse_bhavcopy.py:298-318`); boot warm wrote 2 new rows beside 2,738 old | clean read (with dead rows, see note b) |
| `audit_log.db` `audit_orders` | May 29 | identical, both append-only triggers intact post-boot | `IF NOT EXISTS` DDL only | `GET /safety/audit-log` 200 `{"entries":[]}` | clean read |
| `workflows.db` | did not exist in 0.8.0 | created on first `GET /workflow/saved` | n/a | 200 `{"workflows":[]}` | created fresh |
| `workspaces/*.vysted-workspace` (9 files) | May–Sep | opaque JSON to the sidecar | frontend-side, see §3 | `GET /workspace` 200 lists `__autosave__, chicken, testing` (`.bak-*` files are not listed: `workspace_store.py:63` globs `*.vysted-workspace` only); each `GET /workspace/{name}` 200 | clean read (sidecar) |
| `notes/general.md` | Jun 10 | n/a | n/a | write-only mirror: `notes-persistence.ts` writes and nothing reads it back; the blob's `notes` bundle is authoritative | not a read path |
| `searxng/settings.yml` | Jun 10 | n/a | n/a | `GET /search/searxng/status` 200 `ready` (the shared container, read-only) | clean read |
| `dev-keystore.json` / OS keychain | n/a | n/a | Rust `keychain.rs:169-201` one-time migrate | **NOT TESTED**. The rules forbid reading or copying the real keystore, and the migrate runs only inside the Tauri shell (NEEDS-GUI). A failed-read path is already filed elsewhere ("A failed keychain read during the one-time dev migration is swallowed…") | NOT TESTED |

`PRAGMA user_version` is **0 on all eight databases**, before and after boot. No store records
which build wrote it.

Note (a): `GET /plugins` still returns a `tradesa-v2` config row for a plugin that no longer
ships, plus a `vysted-kite` broker row (trading is out of scope). Both are harmless:
`plugin-bootstrap.ts:59-79` loads config per bundled plugin id, so orphan rows are never
consulted. This is recorded only.

Note (b): 2,678 `screener:quote:*` / `screener:fundamentals:*` / `screener:pair:*` rows
(1.94 MB, written 4–11 Jun) are orphans left by an upgrade. Commit `5142aa1` (12 Jun) moved
the screener to `fundamentals_store`. No current code produces or reads those keys: `grep`
finds only `screener:universe:crypto-top50`, at `screener.py:238-250`. Nothing deletes them
either, because `data_cache.invalidate/clear` have no production callers. This is a specific
case of the already-filed "data_cache is an unbounded, never-evicted SQLite cache" finding,
so it is recorded here and not filed again.

## 3. Workspace blobs through the CURRENT frontend restore code

The sidecar treats blobs as opaque, so the real upgrade risk sits in `src/lib/workspace.ts`.
I checked it with a scratch vitest (`$ISO/seat-l4-upgrade/vt/upgrade.test.ts`, run with a
scratch config that points `root` at the repo; nothing was written inside `src/`). For each of
the 9 historical blobs it runs `deserializeWorkspace(blob)`, then `serializeWorkspace()`, and
diffs every field. Result: `vitest-run.log`, 10/10 passed. Findings:

| Blob | deserialize | Fields changed on re-serialize |
|---|---|---|
| `__autosave__` (the live 19-Sep blob) | ok | **none**: byte-identical round-trip of watchlist (6), portfolios (1, holdings), notes, brief, researchSpaces, settings, searchSettings, modelOverrides (v3) |
| `bak-r9-gates`, `bak-r11-close`, `bak-r11-prune`, `chicken`, `testing` | ok | none |
| `bak-r7-sweep`, `bak-r8-gates` | ok | `settings` 429→73 chars (retired R7/R8 knobs `themeKnobs`, `panelDefaults`, `providerPreferenceOrder`, `palette*`, `starterCockpitPanelIds` dropped); `searchSettings` rewritten to the two-tier vocabulary, as the migration at `workspace.ts:327-336` documents |
| `bak-before-keybind-clean` | ok | `modelOverrides` replaced (a legacy blob without `modelOverridesV` is dropped by design, `workspace.ts:307-318`); `settings` pruned as above |

Every one of today's 22 first-party modules registers its panel ids. That includes
`broker-connect-panel` and `broker-order-entry`, so no historical blob trips the
unknown-component gate at `workspace.ts:512-515` today.

**Induced: the same restore with the trading panels gone.** The operator decided on 23 Sep to
take trading out. I re-registered all modules except `broker-connect` (a build without the
broker panels) and ran `restoreLastSessionOrDefault` against two real blobs:

```
GATE(no broker module) __autosave__.vysted-workspace            restored=true  fromJSON calls=1 addPanel(default) calls=0
GATE(no broker module) __autosave__.vysted-workspace.bak-r7-sweep restored=false fromJSON calls=0 addPanel(default) calls=1
```

`bak-r7-sweep` is a real autosave from this operator's history. Its layout holds
`broker-connect` and `broker-order-entry` panels, next to a portfolio with holdings, a 7-name
watchlist, notes and a research space. In a trading-less build it never reaches
`deserializeWorkspace`, so **none** of its non-layout state is applied. The default layout
goes in, and the page's store subscriptions (`page.tsx:108-181`) and the layout-change
autosave (`PanelHost.tsx:188-193`) then overwrite `__autosave__` with default stores. This is
the mechanism already filed as COD-workspace-layout-4. L4 adds the observed trigger: a real
user blob, plus a removal the operator has already decided, turns it from hypothetical into
scheduled. The operator's own 19-Sep autosave holds only chart/brief/portfolio, so it would
survive. Any user whose last session had the broker panel docked would not.

Side observation (corroborates COD-workspace-layout-3; not filed again): the 9 restores
produced **19** `POST /workspace` calls to my sidecar (`sidecar.log` lines 39-57). They came
from `settings`, `search-settings` and `brief` setters, which self-persist through
`autosaveLayout` mid-restore. That is how my copy's `__autosave__` hash changed. The
last-writer file equals `bak-r9-gates` byte for byte. In other words, the autosave slot held
whichever restore POSTed last, not the blob it was restored from.

## 4. Root cause read-back (recorded, not fixed)

- **No store is versioned.** `user_version` is 0 everywhere, and the workspace blob has no
  top-level version, only `modelOverridesV` (`workspace.ts:174`). Upgrade safety comes from
  three hand-written `PRAGMA table_info` additive guards (`fundamentals_store.py:172-182`,
  `runs_store.py:94-102`, `plugins_store.py:53-67`). The other five stores
  (`portfolio_db`, `agents_store`, `workflow_store`, `data_cache`, `audit_log`) rely on
  `CREATE TABLE IF NOT EXISTS`, which never alters an existing table. There is no path for a
  non-additive change (rename, type change, NOT NULL without default, key-namespace
  retirement) and no pre-upgrade backup of the data dir. 0.8.0 → HEAD reads clean only
  because no such change has happened yet.
- **The frontend restore makes all user data depend on panel-id stability.** A removed or
  renamed panel component (the trading removal is the next scheduled one) skips the whole
  restore, and autosave then persists the loss (`workspace.ts:512-515`, `:262-270`).

## 5. Raw findings written

`census/raw/life-l4-upgrade.json`: 2 findings (LIFE-L4-UPGRADE-1 high, LIFE-L4-UPGRADE-2 medium).
Attempt 2 appended LIFE-L4-UPGRADE-3 (high) and LIFE-L4-UPGRADE-4 (medium); see §6.

Sidecar stopped: `kill 49010` (its sleep pid) at the end of the stage.

## 6. Continuation (attempt 2): the released `v0.8.0` tag → current source

**Why this was added.** §1 is correct for the operator's 19-Sep dir. But that dir was written
by dev builds that were only labelled `0.8.0`: every version string has read `0.8.0` since the
tag (`LAW_DIGEST.md:234`). The tag itself is `f45019f`, 2026-05-18, and it is pushed to
`origin` (`git ls-remote --tags origin` lists it). No GitHub release carries a binary
(`gh release list` is empty), so its users are people who built from the tag. Between the tag
and HEAD, `git diff --shortstat v0.8.0` shows: `plugins_store.py` +38/−5 (the `installed`
column), `runs_store.py` and `fundamentals_store.py` are new files, `src/lib/workspace.ts`
+509/−9, the portfolio moved stores (`12862d3`, 1 Jun), and the custom-agent tool allow-list
was rebuilt from the catalog (`0e248f9`, 31 May). The tag's `tauri.conf.json` identifier is
the same `com.vysted.terminal`, so the same data dir is picked up. (`/Applications/Vysted.app`
is `com.vysted.desk`. It is a computer-use test repackage, per
`docs/archive/PHASE_9_BUG_CATALOG.md:4`, not a real identifier change.)

**Method: a data dir written by the tag's own code.** I ran `git archive v0.8.0 sidecar` into
`$ISO/seat-l4-upgrade/v080src/` and pointed `seed_v080.py` (in the seat dir) at a new empty
dir, `$ISO/seat-l4-upgrade/data-v080tag`, with `VYSTED_DATA_DIR` set. The script runs the
tag's own store functions: `portfolio_db.create_position` ×3 (two carry an `L4-CANARY` note),
`agents_store.create_agent` for `custom:macro-hawk` with tools
`["price_data","macro","news"]` (all three valid at the tag,
`git show v0.8.0:sidecar/models/custom_agent.py:30-38`), `plugins_store.upsert_config` ×2 (the
tag's schema has no `installed` column), and `workflow_store.save_workflow` for a
`data.fetch_quote → action.log` graph. The tag had no autosave; a named workspace holds only
`name/layout/enabledModules/chartDrawings` (`git show v0.8.0:src/lib/workspace.ts:25-39`). So I
added one named workspace in that shape (`my-desk`, the operator's May-29 `chicken` blob
renamed) and no `__autosave__`. The dev keystore was seeded empty, as in `ISO_STACK.md`.

Next I booted **current source** on it: `:52228`, sleep pid 62478, worker 62479 (recorded in
`$ISO/pids-life-l4-upgrade.json`), no MCP env. I read every store back through its route
(`evidence/v080tag-reads.txt`), snapshotted the schema before and after
(`evidence/v080tag-{pre,post}-boot-schema.txt`), resolved the custom agent's tools in-process
(`evidence/v080tag-agent-tools.txt`), and drove the **current frontend** code with a scratch
vitest (`vt/v080tag.test.tsx`, output in `evidence/v080tag-frontend-vitest.txt`, run log
`v080tag-vitest-run.log`: 1/1 passed). The vitest wraps the real `fetch` to that sidecar and
records every URL. `grep -E "ERROR|Traceback|OperationalError|no such|WARNING"
sidecar-v080tag.log` finds **0** matches.

### 6.1 Per-store verdicts (tag-written dir, current code)

| Store | Tag schema vs current | What happened on boot | Read-back | Verdict |
|---|---|---|---|---|
| `plugins.db` | no `installed` column | `_migrate` ran `ALTER TABLE … ADD COLUMN installed … DEFAULT 1` (post-boot schema diff line 64). Rows backfilled `installed:true`; `vysted-example` kept `enabled:false` and its settings | `GET /plugins` 200, both rows intact | **migrated**, clean |
| `custom_agents.db` | identical | none | `GET /custom-agents` 200, the row reads back byte-for-byte, `tools:["price_data","macro","news"]` | clean read, **but the `macro` tool is silently dead**. See 6.3 |
| `portfolio.db` | identical | none | `GET /portfolio/positions` 200, 3 rows: RELIANCE.NS ×10 @ 2890.55, TCS.NS ×5, BTC/USDT ×0.05, both canary notes intact | sidecar: clean read. **User: the data is gone.** See 6.2 |
| `workflows.db` | identical (`models/workflow.py` has an empty diff since the tag; `workflow_nodes` only gained `code_node.py`) | none | `GET /workflow/saved` 200, graph intact | clean read |
| `delegate_runs.db`, `fundamentals_cache.db`, `data_cache.db`, `audit_log.db` | did not exist in the tag's data dir | created fresh on first use. `fundamentals_cache` came up with 5,157 seed rows, `data_cache` with 2 warm rows | n/a | created fresh |
| workspace `my-desk` | tag shape | none | `GET /workspace` → `["my-desk"]`, `GET /workspace/my-desk` 200. The frontend `loadWorkspace` applied it without error | clean read |
| no `__autosave__` | tag had none | `GET /workspace/__autosave__` 404 → default layout | as designed for a first boot | clean |

### 6.2 The tag's tracked portfolio does not survive, silently (LIFE-L4-UPGRADE-3)

At the tag, the Portfolio panel was "manual positions backed by the sidecar SQLite store"
(`git show v0.8.0:src/modules/portfolio/PortfolioPanel.tsx:55`). Its CRUD ran against
`/portfolio/positions` (`git show v0.8.0:src/modules/portfolio/api.ts:15,46,51,56`). Commit
`12862d3` (1 Jun) replaced that with a frontend store persisted in the workspace blob and
"Drops the dead sidecar CRUD" (commit message). No step moves the old rows across.
`src/lib/workspace.ts:286-289` restores portfolios only when the blob carries them ("older
blobs lack them — keep the empty default"), and `src/store/portfolios.ts:112-114` seeds one
empty `Portfolio`. The panel's own header says so: "there is NO sidecar positions CRUD"
(`src/modules/portfolio/api.ts:4-5`).

Measured (`v080tag-frontend-vitest.txt`):

```
sidecar GET /portfolio/positions (0.8.0 holdings on disk): 3 rows: RELIANCE.NS x10, TCS.NS x5, BTC/USDT x0.05
1. restoreLastSessionOrDefault -> restored=false | portfolios store: Portfolio:0
2. PortfolioPanel mounted | portfolios store: Portfolio:0 | panel text: "…This portfolio is emptyManually add a stock or crypto holding…Add your first holding"
3. loadWorkspace('my-desk') (a v0.8.0-shape named workspace) | portfolios store: Portfolio:0
fetches made by the frontend (2): GET /workspace/__autosave__ ; GET /workspace/my-desk
any GET /portfolio/positions from the frontend: false
```

The holdings are still on disk and the sidecar still serves them. But no frontend path reads
`/portfolio/positions`: the only callers are the agent write-sync at
`src/lib/host-actions.ts:1254-1259,1321-1340`, already filed as COD-portfolio-2/-3. The
upgrading user is told their portfolio "is empty" and invited to re-enter it (the empty
state at `PortfolioPanel.tsx:817`). There is no notice, no import, and no way to see the old
rows short of `curl`. Worse, if they ask the agent to add a holding, `portfolio_add_position`
POSTs into the same table beside the orphaned rows. The ledger then mixes pre-upgrade and
post-upgrade holdings, and still no surface reads it. The operator is unaffected: his
`portfolio.db` has 0 rows, since his holdings already live in the blob. Anyone who tracked a
portfolio on the tag build loses it on upgrade.

### 6.3 The tag's custom agent loses a tool, silently (LIFE-L4-UPGRADE-4)

`0e248f9` (31 May) re-derived the custom-agent allow-list from the capability catalog.
`macro` became `macro_series`/`macro_search`, with no alias and no row migration. Measured
(`v080tag-agent-tools.txt`):

```
stored tools        : ['price_data', 'macro', 'news']
openai_tools        : ['price_data', 'news']
anthropic_tools     : ['price_data', 'news']
'macro' in TOOL_SCHEMAS: False | in KNOWN_TOOL_IDS: False
PUT /custom-agents/custom:macro-hawk (same stored tools) -> 422 "unknown tool ids: ['macro']; allowed: [...]"
```

- **Invoke:** the adapters filter unknown ids through `_known()`
  (`sidecar/services/agent_tools/schemas.py:50-51`) with no log line and no event. The agent's
  system prompt still says "Always check the macro series first", but it has no macro tool,
  and nothing tells the user.
- **Edit:** the Agent Builder drops any id outside its 20-entry list before saving
  (`src/modules/agent-builder/form.tsx:139-141`). That list lacks both `macro` and `news`,
  so one save quietly strips two of this agent's three tools. The builder half is already
  filed as COD-frontend-panels-agent-shell-2. A direct PUT gets a 422
  (`sidecar/models/custom_agent.py:55-63`).
- The catalog already has an unused `aliases` field (`catalog.py:94-96`, documented for MCP
  names). `grep -rn "\.aliases" sidecar` finds no reader, so the mechanism that would carry a
  renamed id exists but is not consulted by the allow-list, the validator or `_known()`.

### 6.4 Root cause read-back (recorded, not fixed)

- Two user-owned stores changed their home or vocabulary with a commit and no data step: the
  portfolio moved from SQLite to the blob (`12862d3`), and tool ids were renamed (`0e248f9`).
  §4's point (no store version, so no migration hook) is the mechanism. These are the two
  places it has **already** cost user data between a pushed tag and HEAD, not a hypothetical.
  An upgrade-time step would close both: on a blob with no `portfolios` key and a non-empty
  `portfolio.db`, import the rows into the default portfolio once; map retired tool ids
  through `Capability.aliases` in the validator and in `_known()`, and emit a notice for any
  id that still fails.
- The release gate has no upgrade fixture. One additive ALTER has a unit test
  (`sidecar/tests/test_runs_store.py:185`, "pre-R10 database"). The plugins `installed` ALTER
  has none: `test_plugins.py:183` uses a fresh table. No test boots current code over a whole
  data dir written by the previous tag, and none covers a store relocation or an id rename.
  `seed_v080.py` above is the ~30-line shape such a fixture would take.

### 6.5 State left behind by attempt 2

- `$ISO/seat-l4-upgrade/data/`: attempt 2 re-ran the `.backup` copy over attempt 1's dir
  before it found attempt 1's evidence. It now holds pristine 19-Sep DBs, plus attempt 1's
  `audit_log.db` copy and the `workflows.db` that attempt 1's boot created. Attempt 1's
  findings rest on its evidence files, which are untouched, not on that dir.
- `$ISO/seat-l3-diagnostics/data/` was also re-copied (attempt 1's canary portfolio row is
  gone). L3's evidence files are untouched.
- Sidecar on `:52228` stopped at the end of this stage (`kill 62478`).
