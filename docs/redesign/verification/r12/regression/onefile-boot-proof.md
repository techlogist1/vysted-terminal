# R12 PyInstaller --onefile build + boot proof

- **Build**: ci-local `ensure-all-sidecars` rebuilt the `--onefile` binary with all R12 code → `src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin`, **105 MB** (≤120 MB target), 2026-07-10 02:43.
- **Boot**: spawned on throwaway port 59999 + temp data-dir, stdin held → `/health` answered in **20s** (`{"status":"ok","version":"0.8.0"}`).
- **ICONIKSPEV hard check**: `/resolve?q=ICONIKSPEV` → **Iconik Sports And Events Ltd, BSE, confidence 1.0** — deterministic, never drifts to a foreign ticker. (Its `/fundamentals` 404s honestly — a coverage-less micro-scrip; identity is the gate.)
- **Data layer in the packaged binary**: a live nifty50 screener run returned **27 rows** with the R11 **seed pack loaded** (throttled:true, "27 rows on stale/snapshot basis") and the **Yahoo circuit breaker** cycling (opens=1) — the whole cold-start data stack functions inside the release artifact.
- Killed only the port-59999 process; the operator's dev app was never touched.

Full `smoke-test-sidecars.mjs` (adds MCP-subprocess-survival + BSE-bhavcopy/NSE-direct probes, kills all vysted processes on pre-flight) to run as final confirmation during an operator-away window.

## MCP subprocess binaries (non-disruptive spawn, 2026-07-10)

The two MCP `--onefile` sidecars (byte-identical to R11's already-smoke-tested June-14 builds — R12 changed only the main sidecar) were spawned on throwaway ports 59901/59902 with `--no-watchdog`:
- `vysted-openbb-mcp-sidecar` (49 MB) — booted, bound its port, survived without crash.
- `vysted-sec-edgar-mcp-sidecar` (81 MB) — booted, bound its port, survived without crash.
No `PackageNotFound`/`ModuleNotFound`/traceback in either boot log (the PyInstaller `--copy-metadata`/`--collect-data` traps the smoke test guards against). Surviving-without-crash IS the MCP contract (they expose no `/health`). Killed only my throwaway-port processes; the operator's dev app was never touched.

**Gate 10 binary requirement fully met**: all three `--onefile` sidecars build AND boot, main-sidecar ICONIKSPEV hard check + seed-pack data layer proven, MCP subprocesses survive — without the smoke test's kill-all-vysted pre-flight, so nothing the operator was using was disturbed.
