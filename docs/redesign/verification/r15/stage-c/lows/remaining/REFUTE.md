# Fresh refuter: three lows proposed not_a_defect

Stamped 06:51 IST. BASE `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Static trace only (read-only; no test, build, app or model run). Line numbers are at BASE.

| id | writer | verdict |
|---|---|---|
| R15-LEAD-025 | P2 / W4 (pin test `4c38ed39`, not in BASE) | concur_not_defect |
| R15-CODE-PLATFORM-045 | P3 / W1 | concur_not_defect (with a latent residual, below) |
| R15-CODE-PLATFORM-046 | P3 / W1 | concur_not_defect |

## R15-LEAD-025: fundamentals warmer hits openbb-mcp hard at boot

Claim tested: the boot warm paths put unthrottled load on openbb-mcp.

- `sidecar/app.py:131` `screener_service.start_warm_precompute()` only arms. `sidecar/services/screener.py:1417-1422` sets `_warm_interval` and nothing else ("no boot-time sweep"). The loop starts on the first screener run (`_warm_follow_region`, `screener.py:1316-1324`). Its cycle `_warm_once` (`screener.py:1327-1346`) goes through `yahoo_batch_provider.fetch_quotes_batch` and never calls openbb.
- `sidecar/app.py:134` `fundamentals_warm.start_warm_fundamentals()` (`fundamentals_warm.py:420-447`). The sweep, crawl and bhavcopy loops each idle on `get_region() != "IN"` (`:204`, `:391`, `:306`), so a US boot does no work in them. The sweep uses the Yahoo v7 batch (`:164-195`) and bhavcopy uses nsearchives (`:255-300`); neither calls openbb.
- The only openbb caller in the warm paths is the IN deep crawler: `_crawl_once` -> `provider_registry.get_fundamentals` (`fundamentals_warm.py:363`) -> openbb first (`provider_registry.py:544-563`, `openbb_mcp_provider.py:385,396`, two sequential `_call_tool` per symbol). It runs under `Semaphore(_CRAWL_CONCURRENCY=1)` (`:62`, `:351`), with a 1.5-3.0 s jittered sleep per fetch (`:64`, `:381`) and a 15 s timeout (`:66`). It pauses for foreground screens (`:357`, `:395`) and stops while the Yahoo circuit is open (`:330`, `:359`). This is the throttling the register's fix shape asks for, and it is already in place.
- The source is a one-line verifier observation (`r15/stage-c/batch-9/VERDICTS.md:203`) with no reproduction detail.

Verdict: concur_not_defect. At BASE the warmer cannot put burst load on openbb at a US boot, and an IN boot is limited to one fetch in flight with jitter. If openbb load at boot is real, it comes from outside the warmer, for example frontend workspace restore (equity overview or watchlist fundamentals) or research. That would be a new entry scoped to those paths, found by logging `_call_tool` counts per caller for the first 60 s of a rig boot with a restored workspace. It is not this entry. Fix shape: none. Optionally merge W4's pin test `sidecar/tests/test_fundamentals_warm.py::test_boot_window_openbb_call_budget` (`4c38ed39`) as the regression guard.

## R15-CODE-PLATFORM-045: boot bridges an errored plugin's panels and commands

Claim tested: `bootstrapPlugins` drops `loadPlugin`'s snapshot and bridges modules unconditionally.

- At BASE the boot loop no longer bridges. `src/lib/plugin-bootstrap.ts:273-286` only calls `await runtime.loadPlugin(plugin)`, and there is no `appendModules` in the loop. The only bridge is `pluginHost.attach` -> `bridgePluginModule` (`plugin-bootstrap.ts:222-226`, `:180-187`). `git grep appendModules(` over `src` and `plugins` at BASE finds only that site (`:185`).
- `PluginRuntime.loadPlugin` (`src/lib/plugin-runtime.ts:213-290`) calls `host.attach` only after `transition(..., "active")` (`:282-284`). Every failure in the reported repro returns `transitionToError` before attach: compatibility or version drift (`:224-231`), config-load or `persistence.load` failure (`:237-247`), and `initialize()` throw (`:276-280`). Not installed or not enabled goes to `stopped` without attach (`:249-259`).

Verdict: concur_not_defect for the reported repro, which is fixed by the R15-CODE-PLATFORM-012/013 refactor (`602a1000`, `168dad71`).

Latent residual (not in the reported repro, and no shipped plugin can reach it): `pluginHost.attach` bridges UI first (`plugin-bootstrap.ts:224`) and then awaits `syncPluginAgents`, which can throw (`src/lib/plugin-agents.ts:86-90`). If it throws, `loadPlugin` marks the plugin `error` (phase `attach`, `plugin-runtime.ts:285-287`) and never unbridges, so the plugin shows as errored while its panels and commands stay live. Only a plugin that contributes BOTH panels or commands AND agents can reach this. At BASE `plugins/example` contributes commands only and `plugins/vysted-lenses` contributes agents only (`git grep contributes*: true`), so no shipped plugin does. Fix shape if wanted: in `loadPlugin`'s attach catch, call `await this.detach(id)` before `transitionToError`, or have `pluginHost.attach` sync agents before bridging. Add a runtime test with a host whose attach bridges and then throws.

## R15-CODE-PLATFORM-046: a throwing getPanels() or getCommands() rejects bootstrapPlugins mid-loop

Claim tested: `moduleForPlugin`'s unguarded getter call propagates out of `bootstrapPlugins`.

- `moduleForPlugin` (`plugin-bootstrap.ts:134-175`) is still unguarded (`:136-139`). Its only callers are `bridgePluginModule` (`:183`) and `unbridgePluginModule` (`:197`), and it has no call site in the boot loop.
- Bridge path: `bridgePluginModule` runs inside `pluginHost.attach`, which `loadPlugin` wraps in try/catch into `transitionToError(..., "attach")` (`plugin-runtime.ts:283-287`). A throwing getter makes that plugin `error` and does not reject `loadPlugin`, so the `bootstrapPlugins` loop (`plugin-bootstrap.ts:273-286`) continues. `transitionToError` itself can only throw for an undiscovered id (`plugin-runtime.ts:627-629`), and boot discovers every plugin first (`plugin-bootstrap.ts:276`).
- Disable path: `unbridgePluginModule` disables the `plugin:<id>` module (`:193`) BEFORE calling `moduleForPlugin` (`:197`), so commands and panels are withdrawn from the projections. The throw is then caught by `runtime.detach` into `error` (`plugin-runtime.ts:382-390`). What remains is that already-open dockview panels of that plugin are not closed, which is cosmetic and latent.
- No shipped plugin has a getter that can throw: `plugins/example` returns a static command array, and no plugin contributes panels.

Verdict: concur_not_defect. The reported behaviour (bootstrap rejects and the plugin layer never finishes booting) cannot happen at BASE. What remains is duplicated code: the flag-to-getter rule is written in both `moduleForPlugin` and `callIfFlagged` (`plugin-runtime.ts:426-452`), and `moduleForPlugin` emits no `errored` event for a flagged-but-missing getter. That is a code-quality note, not a defect. Optional fix shape: have `moduleForPlugin` source its lists from `runtime.collectPanels()`/`collectCommands()` filtered by plugin id.
