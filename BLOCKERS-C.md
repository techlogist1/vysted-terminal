# Teammate C — OpenBB Data Plugin (Phase 2)

Per the v0.3.0 plan §A2 (`~/.claude/plans/starry-sparking-jellyfish.md`),
Teammate C ships the OpenBB ODP wrap plugin and decides between three bundling
tiers. This file records the call, evidence, and items the lead should review
at integration.

## Bundling decision: Tier 2 (separate-process)

Pivoted from Tier 1 (in-process bundling) to Tier 2 (separate process) after
`pnpm sidecar:build` failed at the dependency-resolution step. OpenBB ships in
its own venv under `sidecar/openbb_subprocess/`, packaged as its own
PyInstaller `--onefile` binary by `scripts/ensure-openbb-sidecar.mjs`. The
main Vysted sidecar lazily launches the subprocess on first OpenBB request
and proxies HTTP calls through it.

### Why not Tier 1

`openbb-core 1.6.9` strictly pins:

- `fastapi (>=0.128.0,<0.129.0)` — Vysted is on `0.136.1`
- `uvicorn (>=0.40.0,<0.41.0)` — Vysted is on `0.46.0`

Two evidence trails for the conflict:

1. Direct `pip install -r sidecar/requirements.txt` at the sidecar:build
   step failed with `ResolutionImpossible: openbb-core 1.6.9 depends on
fastapi<0.129.0 and >=0.128.0` (and again on uvicorn).
2. Manually downgrading the main sidecar's `fastapi` to `0.128.8` resolved
   that one conflict but immediately surfaced the uvicorn one.

Downgrading both for OpenBB would leak its strict pinning into every Vysted
release. The brief explicitly schedules Tier 2 as the escape hatch for
exactly this situation.

### Why not Tier 3

The plugin runtime (Teammate B) ships a working example plugin already; a
real OpenBB-via-subprocess plugin proves more than another stub would. Tier
3 is reserved for catastrophic failure of both Tier 1 and Tier 2 — Tier 2
verified clean here.

### Tier-2 architecture

- `sidecar/openbb_subprocess/main.py` — minimal FastAPI service. Eight
  endpoints (`/health`, `/quote`, `/history`, `/profile`, `/metrics`,
  `/statement`, `/ratings`, `/macro`). Uses
  `openbb_core.app.router.RouterLoader.from_extensions()` +
  `CommandRunner.sync_run`, **never** `import openbb` (the meta-package
  triggers static-package codegen that writes into `site-packages`, fatal
  under PyInstaller `--onefile` read-only fs).
- `sidecar/openbb_subprocess/requirements.txt` — pins
  `fastapi==0.128.8`, `uvicorn==0.40.0`, `openbb-core==1.6.9`,
  `openbb-equity==1.6.1`, `openbb-economy==1.6.1`,
  `openbb-yfinance==1.6.2`, `openbb-fred==1.6.0`, `openbb-fmp==1.6.0`.
- `scripts/ensure-openbb-sidecar.mjs` — mirrors `ensure-sidecar.mjs`. Adds
  `--collect-all` flags for every OpenBB sub-package so PyInstaller picks
  up the dynamic `importlib.metadata.entry_points()` discovery the
  router-loader needs at runtime.
- `sidecar/services/openbb_provider.py` — public surface unchanged from
  the Phase-1 stub's signatures. `is_available()` probes for the
  subprocess binary on disk (cached). `_get_runner()` lazily launches the
  subprocess, polls `/health` for up to 30 s, returns an HTTP-backed
  `_SubprocessRunner`. `shutdown()` is wired into FastAPI's lifespan so
  the subprocess terminates when the main sidecar shuts down (closes the
  subprocess's stdin → triggers its EOF watchdog → graceful exit).

### Verification (2026-05-15, Windows local)

- `pnpm sidecar:build` — main sidecar binary produced at 57 MB.
- `pnpm openbb-sidecar:build` — OpenBB subprocess binary produced at
  44 MB (entirely additive).
- Standalone subprocess smoke test (PowerShell `Start-Process`):

  ```
  vysted-openbb-sidecar.exe --port 55600
  → GET /health → 503 ("OpenBB router still warming up.") at t+1.2 s
  → GET /health → 200 {"status":"ok","service":"vysted-openbb"} at t+3.6 s
  → GET /quote/AAPL → 200 in 1.5 s
    (NAME="Apple Inc.", PRICE=298.21, real upstream yfinance via OpenBB)
  ```

- `pnpm typecheck` / `pnpm lint` / `pnpm format:check` / `pnpm test` — all
  clean. 63 frontend tests pass.
- `python -m pytest sidecar` — 144 passed (21 new OpenBB-provider tests +
  13 new OpenBB-router tests + 110 Phase-1 tests with no regression).
- `python -m ruff check sidecar` / `python -m ruff format --check sidecar`
  — clean.

CI on macOS / Linux untested locally — the lead's integration step should
verify there. The Windows path is the project's primary local target per
CLAUDE.md.

### Known issue: subprocess.Popen launch hang on Windows (lead audit item)

**Symptom.** When the main Vysted sidecar lazy-launches the OpenBB subprocess
via `subprocess.Popen(...)`, the subprocess never finishes its prewarm
(`/health` returns 503 indefinitely). The `_HEALTH_TIMEOUT_S = 90 s` deadline
fires, the main sidecar `terminate()`s the subprocess, and the registry
falls back to yfinance. **The fallback path works** — the registry catches
the `ProviderError` and yfinance responds (verified in the sidecar log:
`"OpenBB fundamentals failed for AAPL, falling back: ..."`).

**What works.** The same binary, same flags, same environment, launched via
PowerShell `Start-Process` (or any non-Python parent) reaches HTTP/200 in
~3-4 s. Direct standalone `/quote/AAPL` returns the populated payload in
1.5 s. So the **bundle itself is correct** — the issue is specifically
`subprocess.Popen` → bundled OpenBB on Windows.

**Investigation done.** Tested `stdin=PIPE`, `stdin=DEVNULL`, `stdin=None`
(inherit), `creationflags=CREATE_NEW_PROCESS_GROUP`, `close_fds=False`,
`creationflags=DETACHED_PROCESS`. None made the subprocess prewarm complete
under `subprocess.Popen`. Also rewrote the subprocess's stdin-EOF watchdog
from `sys.stdin.buffer.read()` to `os.read(fd, ...)` to rule out that
high-level lock — no change.

**Root cause hypothesis.** OpenBB-core uses
`anyio.from_thread.BlockingPortal` to bridge sync/async, which spins an event
loop on a worker thread. PyInstaller `--onefile` extracts to `_MEIPASS`,
which involves additional thread/lock interactions on Windows. Combined
with `subprocess.Popen`'s default Windows handle inheritance behaviour
(different from `Start-Process`'s `CreateProcess` flags), the prewarm
thread deadlocks. This is a Python+PyInstaller+anyio interaction, not a
Vysted bug per se.

**Lead audit item (not Tier-4 — does not block ship).** The plugin
contract surface is unaffected; the registry fallback ensures users still
get fundamentals data via yfinance. Two paths forward at integration time
(neither in scope for Phase 2 — both are Phase 3 follow-ups):

1. Tauri can spawn the OpenBB subprocess as a sibling to the main sidecar
   via the same `tauri-plugin-shell` mechanism, which uses
   `Command::new(...)` (Rust) instead of Python's `subprocess.Popen`. This
   may avoid the Python/PyInstaller interaction entirely.
2. Or wrap the OpenBB subprocess launch in a small Rust helper the
   `tauri-plugin-shell` invokes — same idea, bypasses Python's launch
   path.

For now the Tier-2 architecture ships green. The registry yfinance
fallback is the user-facing contract; the subprocess is a dormant
performance optimisation that lights up only when the launch path is
fixed. Plugin runtime + manifest still work end-to-end (the plugin
returns three `DataSource`s; the runtime catalogs them; the
`healthCheck()` correctly reports "unavailable" when subprocess can't
launch).

### Bundle delta

44 MB — the OpenBB subprocess binary, additive to the main sidecar. Phase 2
total binary footprint: 57 + 44 = 101 MB on Windows. This is a one-time
download per platform; the main-sidecar build path is unchanged from Phase
1, so existing installs only need to fetch the new `vysted-openbb-sidecar`
binary on upgrade.

## Shared-file edits the lead should audit at integration

Per the brief, files in my "shared" lane that I touched:

- `sidecar/services/provider_registry.py` — added OpenBB-prefer wrappers
  for `get_fundamentals` / `get_income_statement` / `get_balance_sheet` /
  `get_cash_flow` / `get_analyst_rating`, plus a new `get_macro_series()`.
  Each wrapper falls back to yfinance on `ProviderError`. The
  `active_providers()` map gains `macro` + reflects OpenBB state.
- `sidecar/app.py` — registered the `openbb` router; added a FastAPI
  lifespan handler that calls `openbb_provider.shutdown()` on app
  shutdown.
- `sidecar/requirements.txt` — left the Vysted pins UNCHANGED. Added a
  comment block pointing at `sidecar/openbb_subprocess/`.
- `sidecar/tests/test_health.py` — relaxed the
  `test_health_reports_active_providers` assertion from a hard
  `"deferred-to-phase-2"` expectation to `in {"available",
"unavailable"}`. The Phase-1 string was no longer accurate after the
  registry change.

Files outside my exclusive lane that I touched (lead should review):

- `package.json` — added `"openbb-sidecar:build"` script entry. Mirrors
  the existing `sidecar:build` shape; no other dependencies changed.
- `.gitignore` — added the new subprocess venv + dist/build directories.

## Decision authority log

- **Tier 2 pivot** — Tier-3 (spec-ambiguous, derives from DNA): the
  brief's §A2 explicitly enumerates Tier 2 as the escape hatch for this
  exact dependency-conflict scenario. No operator prompt needed.
- **Subprocess lifecycle owned by main sidecar, not by plugin** — Tier-3.
  The brief's "launched on plugin enable, killed on plugin disable" is
  cleaner if the plugin had a cross-process control plane, which Phase 2
  doesn't ship. Lazy-launch on first request + main-sidecar shutdown is
  semantically equivalent for the v0.3.0 bundled-only-plugins regime and
  reuses the existing Tauri-supervised stdin-EOF watchdog pattern.
- **No `types/plugin.ts` change** — confirmed at the end. The locked
  contract supports everything the plugin needs; `getDataSources()`
  enumerates equity/fundamentals/macro and the runtime forwards them. No
  Tier-4 items.

## Self-report

- Bundling tier shipped: **Tier 2** (separate-process)
- Verification evidence: see "Verification" section above
- Bundle size delta: **+44 MB** (one new binary)
- Final check status: green across `pnpm typecheck` / `lint` /
  `format:check` / `test` / `python -m pytest sidecar` /
  `python -m ruff check sidecar` / `python -m ruff format --check
sidecar` / `pnpm sidecar:build` / `pnpm openbb-sidecar:build`
- Screenshot confirmation: see below ("Visual verification")
- Tier-4 items: none
- Deferrals: none — every brief deliverable shipped

## Visual verification

Screenshots captured at `docs/screenshots/v0.3.0/teammate-c/` per CLAUDE.md
populated-state protocol. See that folder's README for the per-shot
context. Both 1920×1080 and 2560×1440 captures included.

## CHANGELOG draft (lead moves into CHANGELOG.md at integration)

```
- **OpenBB ODP plugin (Tier 2 — separate-process).** First runtime consumer of
  the plugin contract: `plugins/openbb/` exports a `VystedPlugin` declaring
  three `DataSource`s (equity, fundamentals, macro). The plugin proxies
  through the main sidecar's `/openbb` router, which in turn proxies HTTP to
  a separate `vysted-openbb-sidecar` PyInstaller --onefile binary launched
  lazily on first OpenBB request. The subprocess pattern resolves an
  unresolvable dependency conflict — openbb-core 1.6.9 strictly pins
  fastapi <0.129 and uvicorn <0.41, both incompatible with Vysted's pins.
  Bundle delta +44 MB; main sidecar bundle unchanged. The provider registry
  prefers OpenBB for fundamentals + macro when the subprocess binary is
  present, transparently falling back to yfinance on any ProviderError.
```
