# R15 Stage 0 — Isolation map: running Vysted off the operator's real data

Code-reading only (no process started, stopped or driven; no GUI). Every claim carries a
file:line anchor. Read-only probes used: `ls`/`du` on the data dir, `lsof -iTCP -sTCP:LISTEN`,
and a keys-only dump of `dev-keystore.json` (no secret value read, printed or logged).

Observed live stack at probe time (read-only, untouched): vite `127.0.0.1:5173` (pid 97719),
main sidecar `127.0.0.1:52052` (pid 98007), openbb-mcp `52053` (97815), sec-edgar-mcp `52054`
(97816).

---

## 1. How the data dir is chosen, and whether it can be overridden

### 1.1 The chain

| Step | Where | What happens |
|---|---|---|
| Tauri resolves the dir | `src-tauri/src/lib.rs:116-134` `resolve_data_dir` | `app.path().app_data_dir()`, `create_dir_all`, temp-dir fallback on error |
| Tauri 2.11.1 resolution | `tauri-2.11.1/src/path/desktop.rs:247-251` | `dirs::data_dir()?.join(config.identifier)` |
| `dirs` 6.0.0 on macOS | `dirs-6.0.0/src/mac.rs:7,12` | `home_dir().join("Library/Application Support")` |
| `home_dir()` | `dirs-sys-0.5.0/src/lib.rs:33-37` | **`env::var_os("HOME")` first**, `getpwuid` fallback |
| identifier | `src-tauri/tauri.conf.json:5` | `com.vysted.terminal` |
| Passed to the sidecar | `src-tauri/src/lib.rs:207` | `.args(["--port", …, "--data-dir", &data_dir])` |
| Sidecar consumes it | `sidecar/main.py:148-149` | `os.environ[DATA_DIR_ENV] = args.data_dir` |
| Everything on disk derives from it | `sidecar/config.py:544-549` `get_data_dir()` | reads `VYSTED_DATA_DIR`, else `~/.vysted-terminal` |
| Renderer asks the core | `src-tauri/src/lib.rs:142-151` `get_app_data_dir` | export paths only (`{dataDir}/exports/…`) |

Resolved today: `~/Library/Application Support/com.vysted.terminal`.

### 1.2 Is there an override?

- **Sidecar: yes, first-class.** `VYSTED_DATA_DIR` (`sidecar/config.py:23`) is the only truth
  the Python side has; `--data-dir` merely sets it. Pytest already uses it as the isolation
  lever (`sidecar/tests/test_workspace.py:18`, `test_search_tiers_router.py:41`). A headless
  sidecar on a copied dir needs nothing new.
- **Tauri core: no purpose-built override.** No env var, no CLI flag, no identifier override is
  read anywhere in `src-tauri/src/`. `resolve_data_dir` has exactly one input.
- **But `HOME` works, by construction of the dependency chain above.** Launching the *built*
  binary with `HOME=/some/copy` moves `app_data_dir` → `$HOME/Library/Application Support/com.vysted.terminal`,
  and the sidecar inherits it via `--data-dir`. Honest caveats: it also moves
  `~/Library/Caches/vysted-terminal`, `~/Library/WebKit/vysted-terminal`, and — if used on
  `pnpm tauri:dev` rather than on an already-built binary — `~/.cargo` and the pnpm store, which
  forces a full cold rebuild. **Use it on the binary, never on the dev toolchain invocation.**
  It is a side effect of `dirs`, not a designed seam: do not document it to users as a feature.

### 1.3 A second Tauri instance is *not* blocked by ports

Ports are picked free at boot, not pinned: `pick_free_port()` (`lib.rs:440`) for the main
sidecar, and openbb/sec-edgar each pick their own immediately before spawn (`openbb_mcp.rs:95`,
`sec_edgar_mcp.rs:95`). The collision risk of a second instance is **not** ports — it is
(a) the vite dev server (`vite.config.ts` port 5173 `strictPort: true`), and (b) the shared
SearXNG container `vysted-searxng` on host port 8888 (`sidecar/services/searxng_manager.py:65-70`),
which is global to the machine and is *managed* (created/started/stopped) by whichever sidecar
runs the setup flow. An isolated instance may **read** it; never let one run setup/teardown
while the operator's session is live.

---

## 1a. Smallest honest way to boot a headless main sidecar on a copied data dir

Two variants. **Both** need the stdin watchdog held open: `run_http` starts
`_exit_when_parent_closes_stdin` (`sidecar/main.py:141`, body at `:71-87`) which does
`sys.stdin.buffer.read()` then `os._exit(0)`. Under a non-interactive shell stdin is
`/dev/null` → EOF → instant silent exit 0. `docs/redesign/LESSONS.md:52-54` records this for
the PyInstaller binary; it applies identically to the source run. The fix is a live pipe.

```bash
# ---- 0. make the isolated copy (safe against the operator's LIVE WAL databases) ----
SRC="$HOME/Library/Application Support/com.vysted.terminal"
ISO="/tmp/claude-501/vysted-iso/data"          # or any scratch path you own
mkdir -p "$ISO/workspaces" "$ISO/searxng"

# SQLite: never cp a live WAL db. .backup against a read-only URI is atomic and safe.
for db in data_cache fundamentals_cache portfolio plugins custom_agents delegate_runs audit_log; do
  [ -f "$SRC/$db.db" ] && sqlite3 "file:$SRC/$db.db?mode=ro" ".backup '$ISO/$db.db'"
done

# Non-SQLite state worth copying (see §2 for what each is)
cp "$SRC/workspaces/__autosave__.vysted-workspace" "$ISO/workspaces/"
[ -f "$SRC/searxng/settings.yml" ] && cp "$SRC/searxng/settings.yml" "$ISO/searxng/"
cp -R "$SRC/notes" "$ISO/" 2>/dev/null

# DELIBERATELY NOT COPIED: dev-keystore.json (secrets), exports/ (43 MB of user output),
# mcp-endpoint.json (regenerated per boot). See §2 and the keychain trap in §2.4.

# ---- 1a-A. run from SOURCE (fast, no build, picks up the uncommitted 3 Sep hot patch) ----
cd /Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar
sleep 86400 | ./.venv/bin/python3 main.py \
    --host 127.0.0.1 --port 52152 --data-dir "$ISO" \
    > /tmp/claude-501/vysted-iso/sidecar.log 2>&1 &
# cwd MUST be sidecar/ — main.py does a flat `from app import app` (sidecar/main.py:28)

# ---- 1a-B. run the SHIPPED PyInstaller binary (tests the real artifact) ----
sleep 86400 | /Users/lokavyasingh/Documents/dev/vysted-terminal/src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin \
    --host 127.0.0.1 --port 52152 --data-dir "$ISO" \
    > /tmp/claude-501/vysted-iso/sidecar.log 2>&1 &
# Cold --onefile boot is ~60 s on this Mac (LESSONS.md:54) — poll, don't assume.

# ---- 2. wait for it ----
until curl -sf http://127.0.0.1:52152/health >/dev/null; do sleep 2; done
curl -s http://127.0.0.1:52152/health          # route: sidecar/routers/health.py:12
```

**Degradations of a hand-started sidecar** (state them in any result, don't hide them):

- `VYSTED_OPENBB_MCP_PORT` unset → the openbb provider falls back to yfinance
  (`sidecar/services/openbb_mcp_provider.py:93,175`).
- `VYSTED_SEC_EDGAR_MCP_PORT` unset → `/sec` routes 501
  (`sidecar/services/sec_filings_provider.py:63,127`).
- For parity, spawn both MCP binaries the same way (they take only `--port`:
  `openbb_mcp.rs:101`, `sec_edgar_mcp.rs:101`) and export the two env vars **before** starting
  the main sidecar — the Rust core joins both spawns first for exactly this reason
  (`lib.rs:482-485`).
- Kill it by killing the `sleep` (closes stdin → the watchdog exits the worker, no orphaned
  `_MEI` lock). Never `kill -9` the PyInstaller bootloader.

---

## 1b. Driving the frontend in a plain browser / Playwright

**There is a browser-mode fallback and it is the only seam needed.**
`src/lib/sidecar-client.ts:90-99` `resolvePortToBaseUrl`: when `__TAURI_INTERNALS__` is absent
from `window`, a `?sidecar-port=NN` query param resolves the base URL to `http://127.0.0.1:NN`;
otherwise it falls through to `invoke("get_sidecar_port")`. `getSidecarBaseUrl()` (`:114-123`)
is the single seam — a repo-wide grep for hardcoded `127.0.0.1:`/`localhost:` in `src/` finds
only that file, two `http://127.0.0.1:0` plugin sentinels
(`plugin-bootstrap.ts:228`, `plugin-runtime.ts:106`) and the Ollama default
(`llm-providers.ts:73`). Nothing else bypasses it.

CORS is wide open on the sidecar (`sidecar/app.py:302-306`, `allow_origins=["*"]`), so any
origin — including a `file://` null origin — reaches an isolated sidecar.

```bash
# Cheapest: reuse the vite dev server that is ALREADY running (serves the same bundle;
# the query param points the app at YOUR isolated sidecar, not the operator's 52052).
open_url="http://localhost:5173/?sidecar-port=52152"

# headless Chrome, no GUI, own profile
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --window-size=1920,1080 \
  --user-data-dir=/tmp/claude-501/vysted-iso/chrome \
  --screenshot=/tmp/claude-501/vysted-iso/shot.png \
  "$open_url"

# If you need a vite that does not depend on the operator's: config pins 5173 with
# strictPort, so pass an explicit port (CLI overrides server.port):
#   pnpm exec vite --port 5273      → http://localhost:5273/?sidecar-port=52152
# Or build once and serve out/ statically (vite.config.ts base:"./" → relative assets):
#   pnpm build && pnpm exec vite preview --port 5273 --outDir out
```

**Hard limits of browser mode — the drive plan must route around these, not discover them:**

1. **Keyed chat sends do not work in a browser.** `ChatSidebar.tsx:789` awaits
   `getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider))`, which is `invoke("keychain_get")`
   (`src/lib/keychain.ts:64-67`). Outside Tauri `invoke` rejects, and there is **no try/catch
   around that call** in `handleSend` (scan of 760–1120 finds the next `try {` well below it) —
   so the send dies as an unhandled rejection with no status line. Only the keyless lane
   (ollama, `requiresKey:false`) survives a browser send. Keyed agent drives must go straight
   at the sidecar API (§4).
2. **Onboarding overlay renders every browser boot.** `useOnboardingStore.refresh`
   (`src/store/onboarding.ts:38-47`) catches the keychain rejection and sets `seen:false`;
   the overlay mounts at `src/app/page.tsx:293`.
3. **Provider key status is `"unknown"`, not `"missing"`** (`src/store/provider-keys.ts:37-44`),
   so key-gated UI reads differently than in the app.
4. Export helpers (`write_text_atomic`/`write_bytes_atomic`, `lib.rs:287,318`) and desktop
   notifications are Tauri commands — inert in a browser (`export-artifact.ts:27` guards).

---

## 2. What lives in the data dir

Measured `~/Library/Application Support/com.vysted.terminal` — 54 MB total.

| Path | Size | Written by | Copy for a faithful profile? |
|---|---|---|---|
| `data_cache.db` (+ `-wal` 4.1 MB, `-shm` 33 K) | 2.7 MB | `services/data_cache.py:86` | **Yes** — quotes/news/OHLC cache; skipping it means every drive is a cold network hit |
| `fundamentals_cache.db` | 2.7 MB | `services/fundamentals_store.py:161` | **Yes** — the profile/fundamentals cache the data battery reads |
| `portfolio.db` | 12 K | `services/portfolio_db.py:41` | Yes if portfolio P&L matters |
| `plugins.db` | 12 K | `services/plugins_store.py:60` | Yes — enabled/installed plugin state |
| `custom_agents.db` | 12 K | `services/agents_store.py:59` | Yes — user-authored agents (affects roster counts) |
| `delegate_runs.db` | 20 K | `services/runs_store.py:91` | Optional — durable Delegate run history |
| `audit_log.db` | 25 K | `services/audit_log.py:43` | **No — and never write to a copy.** Append-only DDL with `RAISE(ABORT)` triggers (CLAUDE.md §6.5). Gate 8 asserts zero rows; start the isolated profile with none |
| `workflows.db` | — (absent here; present in `~/.vysted-terminal`) | `services/workflow_store.py:38` | Created lazily on first workflow save |
| `workspaces/__autosave__.vysted-workspace` | 8.2 K | sidecar `/workspace` POST ← `lib/workspace.ts:541-556` | **Yes** — this is where the composer lane lives (§3) |
| `workspaces/*.bak-r7…r11`, `chicken`, `testing` | 220 K total | manual/past runs | No |
| `dev-keystore.json` | 521 B, `0600` | `src-tauri/src/keychain.rs:101,133-143` | **No — secrets.** See §2.4 |
| `mcp-endpoint.json` | 95 B | `lib.rs:184-193`, only on a confirmed-healthy sidecar | No — regenerated |
| `searxng/settings.yml` | 488 B | `services/searxng_manager.py:472` | Yes if exercising SearXNG |
| `notes/general.md` | 59 B | notes panel via `write_text_atomic` | Optional |
| `exports/` | **43 MB** | export helpers (`get_app_data_dir` → `{dataDir}/exports`) | **No** — 80% of the dir's size, zero behavioural value |

`~/.vysted-terminal` (3.5 MB) also exists — that is `get_data_dir()`'s fallback
(`config.py:547`) used whenever the sidecar runs **without** `VYSTED_DATA_DIR`: pytest without
the fixture, and any hand-run sidecar that forgets `--data-dir`. **Always pass `--data-dir`**
or a headless drive silently reads/writes that stale shared dir instead of your copy.

### 2.3 What a CLEAN profile is, and what first boot creates

A clean profile is **an empty directory** (or a non-existent one — both Rust `create_dir_all`
at `lib.rs:127` and Python `mkdir(parents=True, exist_ok=True)` at `config.py:548` create it).
Nothing is seeded. First boot then creates, lazily and independently:

- the dir itself + `workspaces/` (`config.py:552-556`);
- each `*.db` on that store's first call — every store resolves its path **per call**, so
  nothing is created until used (`runs_store.py:11`, `agents_store.py:66`, `plugins_store.py:75`);
- `mcp-endpoint.json` once the sidecar answers `/health` (`lib.rs:260-265`);
- `dev-keystore.json` on the first `keychain_set` **or the migration** (§2.4);
- `searxng/settings.yml` only when SearXNG setup runs;
- `exports/`, `notes/` on first use.

No autosave blob exists, so `restoreLastSessionOrDefault` 404s and applies the default layout
(`lib/workspace.ts:500-533`) — which is exactly the keyless landing described in §3.

### 2.4 The clean-profile keychain trap (isolation-critical)

A dev build with **no `dev-keystore.json`** does not stay key-free. `src/app/page.tsx:60` calls
`migrateDevKeystore()` on mount → `keychain_migrate` (`keychain.rs:348`) → `dev_keystore::migrate`,
whose guard is `if store.migrated { return }` (`keychain.rs:180-186`). With no file, `migrated`
is `false`, so it **sweeps the operator's real OS keychain** for every account in
`devKeystoreMigrationAccounts()` (`src/lib/keychain.ts:135` and the list at `:78-120`: ten LLM
providers, three brokers × five fields, the ToS ack, plugin/MCP secrets) and writes what it
finds into the isolated profile. The in-code comment at `keychain.rs:355-359` notes this read can
take ~140 s of idle-then-re-read and can raise a SecurityAgent dialog.

**Mitigation for any clean-profile or stranger test — seed the guard before first boot:**

```bash
printf '{\n  "secrets": {},\n  "migrated": true\n}\n' > "$ISO/dev-keystore.json"
chmod 600 "$ISO/dev-keystore.json"
```

(`migrated` is a plain `bool` — `keychain.rs:103-112`.) With that in place the profile is
genuinely keyless, the operator's keychain is never touched, and the "stranger with no keys"
lifecycle question from the brief tests the real thing.

The operator's live keystore holds accounts for **deepseek, openai, openrouter** plus
`app-meta:onboarding-complete` and `broker:_meta:first-launch-tos` (names read via a
keys-only dump; no value was read, printed or logged). Those three are the funded providers
for the run's budget planning.

---

## 3. The composer's provider/model lane, and every path that lands it on keyless

### 3.1 Where it is persisted

- **Provider**: `useLLMProvidersStore.defaultProviderId`, seed value **`"ollama"`**
  (`src/store/llm-providers.ts:135`). Serialized at `lib/workspace.ts:203`, restored at `:278-280`.
  It does **not** move the dockview layout, so it has its own autosave subscription
  (`src/app/page.tsx:136-140`).
- **Model**: `useModelSelectionStore.overrides` (`src/store/model-selection.ts:141`), effective
  value = `overrides[provider] ?? DEFAULT_MODEL_BY_PROVIDER[provider]` (`:115-120`). Serialized
  at `workspace.ts:215-216` with a trust marker `modelOverridesV` (`MODEL_OVERRIDES_VERSION = 3`,
  `workspace.ts:174`).
- Storage medium: the **autosave workspace blob** on the sidecar
  (`{dataDir}/workspaces/__autosave__.vysted-workspace`), written by `autosaveLayout()`
  (`workspace.ts:541-556`). Not localStorage, not a settings store.
- `GET /llm/providers` → `refresh()` (`llm-providers.ts:137-152`) replaces only the
  **catalog**; it never reads or writes `defaultProviderId`.

### 3.2 Clean boot lands on: `ollama` / `qwen2.5:7b`

No blob → the store seed `"ollama"` (`llm-providers.ts:135`) stands, and
`modelFor("ollama")` → `DEFAULT_MODEL_BY_PROVIDER.ollama` = `"qwen2.5:7b"`
(`model-selection.ts:31`). That is the keyless lane. The brief's suspicion is confirmed as
**the designed clean-boot behaviour**, not a bug on its own — the bug candidates are the
demotion paths below, which reach the same state from a *non*-clean profile.

### 3.3 Every code path that can demote to the keyless lane (no fixes applied)

| # | Path | Anchor | Effect |
|---|---|---|---|
| D1 | Store seed | `store/llm-providers.ts:135` | Any boot that never runs a successful restore ends on `ollama` |
| D2 | **Restore skipped entirely on an unknown panel component** | `lib/workspace.ts:471-480`, `:512-515` | `layoutReferencesUnknownComponent` checks the blob's `contentComponent` ids against `useModulesStore.getState().modules` **read at call time** — and returns `true` (unknown) when the layout has no `panels` key at all (`:474-476`). On `true` → `applyDefaultLayout` + `return false` **without calling `deserializeWorkspace`**, discarding *every* persisted setting for that boot: provider, model overrides, watchlist, search tier. `bootstrapPlugins()` is fire-and-forget at `app/page.tsx:85` while `PanelHost` mounts in the same render, so a plugin panel that registers slowly loses the race. **Prime suspect.** |
| D3 | **Restore skipped on any fetch/parse failure** | `lib/workspace.ts:522-533` | A sidecar that is not ready when `PanelHost` mounts (cold `--onefile` boot is ~60 s) → `console.warn` + default layout, same total discard as D2 |
| D4 | **The demotion becomes permanent on the next layout change** | `components/PanelHost.tsx:166,188-193` + `lib/workspace.ts:203` | Autosave is wired in the `.finally()` of the restore *regardless of whether it succeeded*; the next `onDidLayoutChange` writes `defaultProviderId: "ollama"` back into the blob. One transient D2/D3 permanently erases the operator's lane. This is the mechanism behind LESSONS.md:92-94 ("the provider default may demote through restore guards") |
| D5 | Falsy guard on restore | `lib/workspace.ts:278` | `if (workspace.defaultProviderId)` — a blob where the field is absent or `""` silently keeps the seed rather than erroring |
| D6 | Model-override trust gate | `lib/workspace.ts:312-318` | A blob written by a build with `modelOverridesV` ≠ 3 drops **all** model overrides → live defaults (`qwen2.5:7b` under ollama) |
| D7 | Onboarding "run a local model" | `components/OnboardingFlow.tsx:484-486` | `setDefaultProviderId("ollama")` + `setModel(...)` + `autosaveLayout()` — legitimate, but on a clean profile the overlay always renders (`page.tsx:293`, `store/onboarding.ts:38-47`), so one stray activation pins keyless |
| D8 | Persona/agent provider demotion | `modules/chat/ChatSidebar.tsx:122-142` | An agent pinned to a provider whose key probes `"missing"` falls back to `defaultProviderId` — which is `ollama` whenever D1–D4 have fired |

Note D8's input: in browser mode the probe returns `"unknown"`, not `"missing"`
(`store/provider-keys.ts:41-43`), so D8 does **not** reproduce outside the Tauri shell.

### 3.4 Setting the lane without the GUI

LESSONS.md:92-94 prescribes editing the **full post-boot blob with the app stopped** — D4 is
why: any partial/pruned blob written while the app runs gets overwritten by the live store.
The blob is plain JSON at `{dataDir}/workspaces/__autosave__.vysted-workspace`; set
`defaultProviderId` and, for the model, both `modelOverrides` and `modelOverridesV: 3` or D6
drops them.

---

## 4. How BYOK keys reach the sidecar (for headless API drives, no value printed)

**Two distinct transports — do not conflate them.**

| Purpose | Transport | Anchor |
|---|---|---|
| Chat / agent LLM key | **request BODY** field `api_key` | `modules/chat/streaming.ts:140` (`/llm/chat`), `:166` (`/agents/{id}/invoke`); contract `sidecar/models/agent.py:81`; consumed `sidecar/routers/agents.py:97` → `config.set_request_llm_creds` (`config.py:163`) |
| Tier-B research OpenRouter key | **header** `X-Vysted-Openrouter-Key` | `lib/search-headers.ts:96`; parsed `sidecar/app.py:268` → `config.set_request_openrouter_search_key` (`config.py:417`) |
| Read-only plugin secrets (e.g. news) | header (`X-Vysted-Newsapi-Key`) | `lib/sidecar-client.ts:151`, `lib/marketplace.ts:149` |
| Region / research tier / searxng url / per-stop model map | headers | `app.py:260-270`; `lib/search-headers.ts:94-97` |

All of them are per-request ContextVars, reset on the way out, never persisted
(`config.py:145-171`, `:408-424`). The sidecar **cannot** read the keychain — `keychain.rs` is
the only call site and there are no Python `keyring` imports.

Header/body names the drive needs:
`X-Vysted-Region`, `X-Vysted-Research-Tier` (`tier_a`|`tier_b`), `X-Vysted-Searxng-Url`,
`X-Vysted-Openrouter-Key`, `X-Vysted-Research-Models` (`normal=…,deep=…,ultra=…`).

### 4.1 Supplying a key in-process without ever printing it

Read it straight out of the isolated (or real, read-only) `dev-keystore.json` in the same
process that issues the request — never through a shell variable, a log line or a `curl -v`:

```bash
/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python3 - <<'PY'
import json, os, urllib.request
KEYSTORE = os.path.expanduser("~/Library/Application Support/com.vysted.terminal/dev-keystore.json")
key = json.load(open(KEYSTORE))["secrets"]["llm-provider:openrouter"]   # never printed
body = json.dumps({
    "prompt": "…",
    "provider": "openrouter",
    "model": "openai/gpt-5.6-luna",
    "api_key": key,               # BODY, per streaming.ts:166 / models/agent.py:81
    "mode": "agent",
}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:52152/agents/concierge/invoke", data=body,
    headers={
        "Content-Type": "application/json",
        "X-Vysted-Region": "IN",
        "X-Vysted-Research-Tier": "tier_a",
        # "X-Vysted-Openrouter-Key": key,   # only for tier_b research
    })
print(urllib.request.urlopen(req).status)   # status only — never echo the body's key
PY
```

Guard rails, all already asserted in-repo: responses never echo credentials
(`test_<plugin>_router.py` per CLAUDE.md); a keyless `/agents/*/invoke` with **no** `provider`
arg silently cold-loads a 4 GB ollama model on this M1 (LESSONS.md:87-89) — **always pass
`provider` explicitly in every probe.**

---

## Observations recorded, not acted on (Stage 0 is read-only)

1. **D2+D4 is a real data-loss shape**, not just a lane annoyance: one transient restore
   failure permanently rewrites the operator's autosave blob with store seeds. Belongs in the
   register (owning subsystem: frontend/workspace) — it is the most plausible mechanical cause
   of "the composer reverted to the keyless lane".
2. **`ChatSidebar.tsx:789` has no try/catch** around `getSecret`, so any keychain rejection
   (browser mode, revoked ACL, keystore unreadable) kills the send silently with no status
   line. Register candidate; also the hard blocker on browser-mode keyed drives.
3. **CLAUDE.md is stale on the frontend build tool**: it says "Next.js 16 (App Router, static
   export)", but `package.json` scripts are `dev = vite` / `build = vite build` and
   `vite.config.ts` owns the dev server at 5173. Fold into the single CLAUDE.md commit the
   brief authorises.
4. **The shipped main sidecar binary is dated 3 Sep 17:09**, the same day as the uncommitted
   hot patch — a verification round run against `src-tauri/binaries/vysted-sidecar-*` may or may
   not include that patch. LESSONS.md:12 ("a stale sidecar binary has produced false positives
   repeatedly") applies; the source run (1a-A) is the one that provably includes it.
5. The `playwright` MCP server failed to connect this session (`CONNECT_TIMEOUT` after 30 s) —
   the headless-Chrome command in §1b is the fallback that needs no MCP.
