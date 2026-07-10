// scripts/smoke-test-sidecars.mjs
//
// Cross-OS smoke-test for every sidecar binary in src-tauri/binaries/.
// The point: catch the v0.6.5-class runtime crash (PyInstaller --onefile
// silently dropping importlib.metadata dist-info → PackageNotFoundError
// during module load) before it ships. CI exercises source-level pytest
// + `tauri build` (packages the binary, never runs it); without this
// step the runtime correctness of the bundled binary is untested.
//
// The lesson cost: v0.6.5 shipped a vysted-sidecar binary that crashed
// at startup with `PackageNotFoundError: fastmcp`; v0.7.0 caught a
// related sec-edgar variant where `--collect-data=edgar` was missing
// and the binary died on `FileNotFoundError: secforms.csv`. Every
// data-bearing panel was broken in production both times, CI green,
// tag pushed. This smoke-test fails the workflow if a similar
// regression sneaks in again.
//
// ATTENDED-SAFE: this script is designed to run WHILE the operator's own
// `vysted-terminal` dev/prod app is alive on the same machine. It NEVER
// inspects, name-matches, or kills any process it did not itself spawn in
// the current run — earlier revisions pre-flighted with a blanket
// `pgrep -f vysted-.*sidecar` scan, which matches the operator's own live
// app sidecars and forces a `pkill -9 -f vysted-.*sidecar` remediation
// (i.e. kills the app you're using to read this message). That is gone.
//
// Strategy:
//   1. Pre-flight: reap only leaked children from a PRIOR RUN OF THIS
//      SCRIPT — read the PID ledger this script itself wrote to a fixed
//      state file, confirm each live PID still carries this script's own
//      marker (env var on Linux; command-name match against the recorded
//      binary elsewhere), and tree-kill ONLY those. A PID this script
//      never recorded (e.g. the operator's running app) is never touched,
//      even if its process name matches.
//   2. Resolve the target triple via `rustc -vV` (matches existing
//      ensure-*.mjs scripts).
//   3. For the MAIN sidecar (vysted-sidecar):
//      - Pick a fresh EPHEMERAL port (bind :0, read back the OS-assigned
//        port, close, reuse — no other process, including the operator's
//        app, can be using it), spawn with --port + --data-dir + a held
//        stdin pipe (so its stdin-EOF watchdog does not fire and kill it)
//        + this script's marker env var.
//      - Poll http://127.0.0.1:PORT/health for up to MAIN_BOOT_TIMEOUT_MS.
//      - 200 OK → PASS. Process exit / timeout → FAIL.
//      - Then assert: /health version matches package.json, the screener
//        universe endpoint, the ICONIKSPEV deterministic resolve, the
//        /agents roster (count > 0), and /mcp/status (this binary's OWN
//        embedded MCP integration reports ready).
//   4. For each MCP subprocess sidecar (vysted-openbb-mcp-sidecar,
//      vysted-sec-edgar-mcp-sidecar):
//      - Spawn on its own fresh ephemeral port + --no-watchdog (so closing
//        our stdin does not kill it) + the marker env var.
//      - TCP-probe the claimed port until it binds (up to
//        MCP_BIND_TIMEOUT_MS) — process-alive is not enough, the UC1
//        silent-non-bind failure needs an actual connect. Then confirm it
//        survives a short settle window (catches bind-then-crash).
//   5. Tree-kill every spawned process (Windows: taskkill /F /T /PID;
//      POSIX: process group via `detached: true` + `process.kill(-pid,
//      'SIGKILL')`) — ONLY processes this run's PID ledger recorded.
//      Without tree-kill the PyInstaller bootloader's worker survives —
//      CLAUDE.md Gotcha "Smoke-testing the sidecar binary orphans a
//      worker". Runs from `exit`/SIGINT/SIGTERM handlers too, so a crash
//      or Ctrl+C still reaps this run's own children.
//   6. Print an ATTENDED-SAFE summary naming every port/PID this run
//      touched, so a diff against `ps aux | grep vysted` before/after
//      proves zero interference with pre-existing processes.
//   7. Exit non-zero on first failure with a clear error message
//      naming the broken binary + a hint at the likely missing
//      PyInstaller flag.
//
// Run via: `node scripts/smoke-test-sidecars.mjs`

import { spawn, execSync, execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createServer, connect as netConnect } from "node:net";
import { basename, join, resolve } from "node:path";
import { tmpdir, platform } from "node:os";
import { mkdtemp, rm } from "node:fs/promises";
import { setTimeout as sleep } from "node:timers/promises";

import { assertFresh } from "./sidecar-staleness.mjs";

const ROOT = resolve(import.meta.dirname, "..");
const BINARIES_DIR = join(ROOT, "src-tauri", "binaries");
const SIDECAR_DIR = join(ROOT, "sidecar");

const isWin = platform() === "win32";
const ext = isWin ? ".exe" : "";

// Main-sidecar boot budget. The --onefile binary cold-extracts its `_MEI*`
// (89 MB — the largest of the three) AND runs the FastMCP Streamable-HTTP
// lifespan before /health serves; that's ~90s cold on an M1 (Phase 9.5 S0-1).
// The prior 60s only ever passed because the binary was warm/stale (pre the
// staleness-aware ensure fix, the main sidecar was rarely rebuilt). 120s covers
// the cold start with headroom; a warm boot returns in a couple seconds.
const MAIN_BOOT_TIMEOUT_MS = 120_000;
const MAIN_POLL_INTERVAL_MS = 500;
// MCP bind budget — aligned with the Rust supervisor's MCP_PORT_WAIT_SECS(45) x
// MCP_PORT_WAIT_ATTEMPTS(2) = 90s. A cold `_MEI*` extraction binds at ~34s
// isolated on an M1 (Phase 9.5 measurement); 90s covers contended cold boots.
const MCP_BIND_TIMEOUT_MS = 90_000;
// After binding, confirm the process survives a short settle window (catches a
// bind-then-immediately-crash).
const MCP_SETTLE_MS = 3_000;

// ATTENDED-SAFE marker: every child THIS script spawns carries this env var.
// It is a fixed, stable string (not per-run) so a SUBSEQUENT invocation's
// pre-flight can recognize "a process this script's family of runs spawned"
// on the rare platform where env introspection of another PID is possible
// (Linux `/proc/<pid>/environ`). The actual scoping guarantee, though,
// comes from `_STATE_FILE` below — we only ever *inspect* a PID that this
// exact script already wrote to that file itself; we never scan the system
// process table by name.
const _SMOKE_MARKER_ENV = "VYSTED_SMOKE_TEST_MARKER";
const _SMOKE_MARKER = "vysted-smoke-test-v1";

// Fixed (not per-run) path so a crashed prior run's ledger is discoverable
// by the next run's pre-flight.
const _STATE_DIR = join(tmpdir(), "vysted-smoke-test");
const _STATE_FILE = join(_STATE_DIR, "live-children.json");

/** Read the PID ledger; `[]` on any read/parse failure (never blocks a run). */
function _readState() {
  try {
    const parsed = JSON.parse(readFileSync(_STATE_FILE, "utf8"));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Persist the PID ledger; best-effort — a write failure must never fail the run. */
function _writeState(entries) {
  try {
    mkdirSync(_STATE_DIR, { recursive: true });
    writeFileSync(_STATE_FILE, JSON.stringify(entries, null, 2));
  } catch {
    // Non-fatal — worst case a future run's scoped pre-flight misses this entry.
  }
}

function _recordChild(pid, binaryBaseName) {
  const entries = _readState();
  entries.push({ pid, binary: binaryBaseName, marker: _SMOKE_MARKER, spawnedAt: Date.now() });
  _writeState(entries);
}

function _forgetChild(pid) {
  const entries = _readState().filter((e) => e.pid !== pid);
  _writeState(entries);
}

/**
 * Track every spawned bootloader PID so the global cleanup handlers can
 * tree-kill them on script exit / SIGINT / SIGTERM. PyInstaller --onefile
 * re-execs a worker child; killing the bootloader does NOT kill the worker
 * on Windows. The Set holds bootloader PIDs; `_killTree` walks the tree.
 * `_SPAWN_LOG` is a human-readable record (binary/port/pid) of everything
 * this run spawned, printed in the ATTENDED-SAFE summary at the end.
 */
const _LIVE_PIDS = new Set();
const _SPAWN_LOG = [];
let _CLEANUP_REGISTERED = false;

function _registerCleanup() {
  if (_CLEANUP_REGISTERED) return;
  _CLEANUP_REGISTERED = true;
  const runCleanup = () => {
    // Only ever touches PIDs THIS run spawned and is still tracking — never
    // a name-based system scan. Safe to run unconditionally, including on a
    // machine where the operator's own vysted-* processes are alive.
    for (const pid of _LIVE_PIDS) {
      _killTree(pid);
      _forgetChild(pid);
    }
    _LIVE_PIDS.clear();
  };
  // `exit` runs synchronously and last — guarantees orphan cleanup on
  // any path including uncaught throws. SIGINT/SIGTERM let interactive
  // Ctrl+C / `kill` paths exit cleanly.
  process.on("exit", runCleanup);
  process.on("SIGINT", () => {
    runCleanup();
    process.exit(130);
  });
  process.on("SIGTERM", () => {
    runCleanup();
    process.exit(143);
  });
}

/**
 * Cross-OS tree-kill of a process and any descendants. On Windows the
 * PyInstaller bootloader spawns a worker child; `process.kill(pid)`
 * only signals the bootloader and the worker survives as an orphan.
 * `taskkill /F /T /PID` walks the tree. On POSIX we rely on the
 * spawn `detached: true` + a negative PID kill to signal the whole
 * process group.
 */
function _killTree(pid) {
  if (!pid) return;
  try {
    if (isWin) {
      execFileSync("taskkill", ["/F", "/T", "/PID", String(pid)], { stdio: "ignore" });
    } else {
      try {
        process.kill(-pid, "SIGKILL");
      } catch {
        process.kill(pid, "SIGKILL");
      }
    }
  } catch {
    // Process may already be gone — that's fine.
  }
}

/** True if `pid` is a live process this user can signal. */
function _isPidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * Best-effort confirmation that a live PID recorded in a PRIOR run's ledger
 * is still that same spawned-by-us process (defends against PID reuse
 * between the crash and this pre-flight — an unrelated process could have
 * been assigned the same PID since). On Linux this reads the process's own
 * `/proc/<pid>/environ` for the exact marker env var this script sets on
 * every child. macOS/Windows have no non-root way to read another process's
 * environment, so those platforms fall back to a command-name match against
 * the binary THIS SAME LEDGER ENTRY recorded — still scoped to a PID we
 * ourselves wrote down, never a system-wide name scan.
 */
async function _confirmOwnedByMarker(entry) {
  if (platform() === "linux") {
    try {
      const environ = readFileSync(`/proc/${entry.pid}/environ`, "utf8");
      return environ.split("\0").includes(`${_SMOKE_MARKER_ENV}=${entry.marker}`);
    } catch {
      return false;
    }
  }
  if (isWin) {
    try {
      const out = execFileSync(
        "powershell",
        [
          "-NoProfile",
          "-Command",
          `(Get-Process -Id ${entry.pid} -ErrorAction SilentlyContinue).Path`,
        ],
        { encoding: "utf8" },
      ).trim();
      return out.length > 0 && out.endsWith(entry.binary);
    } catch {
      return false;
    }
  }
  try {
    const out = execFileSync("ps", ["-p", String(entry.pid), "-o", "comm="], {
      encoding: "utf8",
    }).trim();
    return out.length > 0 && out.endsWith(entry.binary);
  } catch {
    return false;
  }
}

/**
 * Scoped orphan pre-flight (CLAUDE.md Gotcha: "a pre-flight orphan check").
 * Reaps ONLY children a PRIOR RUN OF THIS SCRIPT recorded in `_STATE_FILE`
 * and failed to clean up (e.g. a hard crash, SIGKILL of the node process
 * itself). This is the replacement for the old blanket
 * `pgrep -f vysted-.*sidecar` scan: that scan matched every vysted-*sidecar*
 * process on the box BY NAME, including the operator's own running app, and
 * told the operator to `pkill -9 -f vysted-.*sidecar` to proceed — killing
 * the app they're using. This function never inspects, matches, or touches
 * any PID it did not itself write to its own ledger file in a previous run.
 */
async function _scopedOrphanPreflight() {
  const entries = _readState();
  if (entries.length === 0) {
    console.log(
      "[smoke] pre-flight (ATTENDED-SAFE): no leaked children from a prior smoke-test " +
        "run's PID ledger — nothing to reap. (This check never inspects processes it did " +
        "not itself spawn, so it cannot see — and will never touch — the operator's own " +
        "running vysted-terminal app.)",
    );
    return;
  }
  let reaped = 0;
  let stale = 0;
  for (const entry of entries) {
    if (!_isPidAlive(entry.pid)) {
      stale += 1;
      continue; // already gone — just a dangling ledger row
    }
    const owned = await _confirmOwnedByMarker(entry);
    if (owned) {
      console.warn(
        `[smoke] pre-flight: reaping a leaked child from a PRIOR RUN OF THIS SCRIPT ` +
          `(pid=${entry.pid}, binary=${entry.binary}) — confirmed via this script's own ` +
          `marker, tree-killing.`,
      );
      _killTree(entry.pid);
      reaped += 1;
    } else {
      // Alive, but the marker/command-name doesn't match what we recorded —
      // the PID was almost certainly reassigned to an unrelated process
      // (possibly the operator's own app) since the ledger row was written.
      // Never touch it; just drop the stale row.
      console.log(
        `[smoke] pre-flight: dropping stale ledger row for pid=${entry.pid} — a live ` +
          `process now holds that PID but does not match this script's marker (PID reuse), ` +
          `so it is left untouched.`,
      );
      stale += 1;
    }
  }
  _writeState([]); // every row has been resolved (reaped or dropped) above
  if (reaped > 0) {
    await sleep(500); // let the OS release file locks after the reap
  }
  console.log(
    `[smoke] pre-flight (ATTENDED-SAFE) complete: reaped ${reaped} leaked child(ren), ` +
      `dropped ${stale} stale/unowned ledger row(s).`,
  );
}

/** Probe an HTTP GET endpoint with a single timeout. */
async function _httpGetOk(url, timeoutMs = 1500) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { signal: ctrl.signal });
    return resp.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

/** GET a JSON endpoint with a single timeout; null on any failure. */
async function _httpGetJson(url, timeoutMs = 5000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { signal: ctrl.signal });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  } finally {
    clearTimeout(t);
  }
}

/**
 * No-SLA probe of the BSE EOD BhavCopy endpoint (WS6). The keyless BSE provider
 * (`sidecar/services/bse_provider.py`) assembles EOD history from this daily
 * full-universe dump. This is a LIVE reachability check ONLY: BSE rate-limits,
 * geo-fences, and does not publish a file on a weekend/holiday/not-yet-closed
 * day, and CI/sandbox often has no outbound network — so a miss WARNS and never
 * fails the smoke run. It exists purely to flag a URL-shape regression early.
 */
async function _probeBseBhavcopyNoSla() {
  // Yesterday in IST (UTC+5:30) — a plausibly-published recent trading day.
  const istNow = new Date(Date.now() + 5.5 * 3600 * 1000);
  istNow.setUTCDate(istNow.getUTCDate() - 1);
  const ymd =
    `${istNow.getUTCFullYear()}` +
    `${String(istNow.getUTCMonth() + 1).padStart(2, "0")}` +
    `${String(istNow.getUTCDate()).padStart(2, "0")}`;
  const url =
    `https://www.bseindia.com/download/BhavCopy/Equity/` +
    `BhavCopy_BSE_CM_0_0_0_${ymd}_F_0000.CSV`;
  console.log(`[smoke] BSE bhavcopy probe (no-SLA): GET ${url} ...`);
  try {
    const ok = await _httpGetOk(url, 4000);
    if (ok) {
      console.log("[smoke] BSE bhavcopy probe OK (endpoint reachable).");
    } else {
      console.warn(
        `[smoke] WARN: BSE bhavcopy probe did not return 200 (no-SLA — not a failure). ` +
          `Common + benign: weekend/holiday/not-yet-published day, geo-fence, or no ` +
          `outbound network in CI. Only investigate if the URL SHAPE changed.`,
      );
    }
  } catch (err) {
    console.warn(
      `[smoke] WARN: BSE bhavcopy probe errored (no-SLA — not a failure): ` +
        `${err instanceof Error ? err.message : String(err)}`,
    );
  }
}

/**
 * No-SLA probe of the NSE exchange-direct lane (R7 Component 2). The
 * `sidecar/services/nse_provider.py` lane talks to www.nseindia.com through a
 * curl_cffi Chrome-impersonated session with the cookie dance (warm-up on `/`,
 * then `api/historicalOR/cm/equity`). Node's fetch has the wrong TLS
 * fingerprint for NSE's Akamai edge, so this probe shells out to the sidecar
 * venv's python + curl_cffi — the EXACT transport the provider uses. LIVE
 * reachability check ONLY: NSE geo-fences, rate-limits, and blocks datacenter
 * IPs, and CI/sandbox often has no outbound network — a miss WARNS and never
 * fails the smoke run. It exists to flag an endpoint-SHAPE regression early
 * (the legacy api/historical/cm/equity path already died with a 503 once).
 */
async function _probeNseDirectNoSla() {
  const venvPy = join(
    SIDECAR_DIR,
    ".venv",
    ...(isWin ? ["Scripts", "python.exe"] : ["bin", "python"]),
  );
  if (!existsSync(venvPy)) {
    console.warn(
      "[smoke] WARN: NSE direct probe skipped (no-SLA): sidecar venv python not found " +
        `at ${venvPy} — the probe needs curl_cffi for NSE's TLS fingerprint check.`,
    );
    return;
  }
  const code = [
    "import sys, time",
    "try:",
    "    from curl_cffi import requests",
    "except Exception as exc:",
    "    print('SKIP curl_cffi unavailable:', exc); sys.exit(0)",
    "from datetime import date, timedelta",
    "s = requests.Session(impersonate='chrome')",
    "r = s.get('https://www.nseindia.com/', timeout=15)",
    "print('WARMUP', r.status_code)",
    "time.sleep(1.2)",
    "to = date.today(); frm = to - timedelta(days=10)",
    "r = s.get('https://www.nseindia.com/api/historicalOR/cm/equity',",
    "          params={'symbol': 'RELIANCE', 'series': '[\"EQ\"]',",
    "                  'from': frm.strftime('%d-%m-%Y'), 'to': to.strftime('%d-%m-%Y')},",
    "          headers={'Accept': '*/*',",
    "                   'Referer': 'https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE'},",
    "          timeout=15)",
    "print('STATUS', r.status_code)",
    "if r.status_code == 200:",
    "    rows = (r.json() or {}).get('data') or []",
    "    print('ROWS', len(rows))",
  ].join("\n");
  console.log("[smoke] NSE direct probe (no-SLA): historicalOR/cm/equity via curl_cffi ...");
  try {
    const out = execFileSync(venvPy, ["-c", code], { encoding: "utf8", timeout: 60_000 });
    const status = /STATUS (\d+)/.exec(out)?.[1];
    const rows = /ROWS (\d+)/.exec(out)?.[1];
    if (status === "200" && Number(rows) > 0) {
      console.log(`[smoke] NSE direct probe OK (HTTP 200, ${rows} EOD rows).`);
    } else if (out.includes("SKIP")) {
      console.warn(`[smoke] WARN: NSE direct probe skipped (no-SLA): ${out.trim()}`);
    } else {
      console.warn(
        `[smoke] WARN: NSE direct probe did not return rows (no-SLA — not a failure). ` +
          `Common + benign: geo-fence/edge ACL, holiday, or no outbound network. ` +
          `Only investigate if the URL SHAPE changed. Output:\n${out.trim()}`,
      );
    }
  } catch (err) {
    console.warn(
      `[smoke] WARN: NSE direct probe errored (no-SLA — not a failure): ` +
        `${err instanceof Error ? err.message : String(err)}`,
    );
  }
}

/** Single TCP-connect probe to 127.0.0.1:port — true if something is listening. */
function _tcpConnectOk(port, timeoutMs = 1000) {
  return new Promise((resolveP) => {
    const socket = netConnect({ host: "127.0.0.1", port, timeout: timeoutMs });
    socket.on("connect", () => {
      socket.destroy();
      resolveP(true);
    });
    socket.on("error", () => resolveP(false));
    socket.on("timeout", () => {
      socket.destroy();
      resolveP(false);
    });
  });
}

/**
 * Poll a port until something binds it or the deadline passes. Returns
 * `{ bound, exited }`. Short-circuits the moment the port binds (matches the
 * Rust supervisor's `wait_for_port_with_retries`). `isExited` lets us bail
 * early if the child dies before binding.
 */
async function _waitForBind(port, timeoutMs, isExited) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (isExited()) return { bound: false, exited: true };
    if (await _tcpConnectOk(port)) return { bound: true, exited: false };
    await sleep(1000);
  }
  return { bound: false, exited: isExited() };
}

/** Pick a free port on 127.0.0.1 by binding to 0 + reading the assigned port. */
function _pickFreePort() {
  return new Promise((resolveP, rejectP) => {
    const server = createServer();
    server.unref();
    server.on("error", rejectP);
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      const port = typeof addr === "object" && addr ? addr.port : 0;
      server.close(() => resolveP(port));
    });
  });
}

function _rustcTargetTriple() {
  const out = execSync("rustc -vV", { encoding: "utf8" });
  const line = out.split("\n").find((l) => l.startsWith("host:"));
  if (!line) throw new Error("could not determine host target triple from `rustc -vV`");
  return line.replace("host:", "").trim();
}

function _binaryPath(name, triple) {
  return join(BINARIES_DIR, `${name}-${triple}${ext}`);
}

/**
 * Canonical version string (CLAUDE.md "Version lives in many sources"
 * gotcha) — `package.json` is the bump location `/health`'s version is
 * meant to trace back to via `sidecar/app.py FastAPI(version=...)`.
 */
function _packageVersion() {
  return JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")).version;
}

/**
 * Spawn a child + track its PID for global cleanup. On POSIX `detached: true`
 * makes the child a process-group leader so `process.kill(-pid)` tree-kills.
 * On Windows we rely on `taskkill /T` in `_killTree`. Every child carries
 * `_SMOKE_MARKER_ENV` (ATTENDED-SAFE: identifies it as ours, never used to
 * match anything OTHER than a PID this exact run already holds a handle to)
 * and stdio stays `"pipe"` — the parent's `child.stdin` Writable is never
 * `.end()`-ed, so the pipe is held open for the binary's stdin-EOF watchdog
 * (main sidecar) until this run explicitly tree-kills the child.
 */
function _spawnChild(bin, args, captureStream) {
  _registerCleanup();
  const child = spawn(bin, args, {
    stdio: ["pipe", "pipe", "pipe"],
    detached: !isWin,
    windowsHide: true,
    env: { ...process.env, [_SMOKE_MARKER_ENV]: _SMOKE_MARKER },
  });
  const binName = basename(bin);
  if (child.pid) {
    _LIVE_PIDS.add(child.pid);
    _recordChild(child.pid, binName);
    _SPAWN_LOG.push({ binary: binName, pid: child.pid, args });
  }
  child.on("exit", () => {
    if (child.pid) {
      _LIVE_PIDS.delete(child.pid);
      _forgetChild(child.pid);
    }
  });
  const buffers = [];
  if (captureStream) {
    child.stdout.on("data", (d) => buffers.push(d));
    child.stderr.on("data", (d) => buffers.push(d));
  }
  return { child, output: () => Buffer.concat(buffers).toString("utf8") };
}

/** Tear down a child via tree-kill + wait briefly for the OS to release. */
async function _teardown(child) {
  if (child.pid) _killTree(child.pid);
  // Brief wait so the OS releases the binary file lock before any
  // subsequent rebuild step (e.g. when `pnpm ci-local` chains
  // ensure-sidecar.mjs after the smoke-test). PyInstaller workers
  // exit shortly after the bootloader receives SIGKILL.
  await sleep(500);
}

/** Test the main sidecar — boots + /health 200 within MAIN_BOOT_TIMEOUT_MS. */
async function _smokeTestMainSidecar(triple) {
  const bin = _binaryPath("vysted-sidecar", triple);
  if (!existsSync(bin)) {
    throw new Error(`[smoke] main sidecar binary missing: ${bin}`);
  }
  const port = await _pickFreePort();
  const dataDir = await mkdtemp(join(tmpdir(), "vysted-smoke-"));
  console.log(`[smoke] vysted-sidecar: spawning on :${port} ...`);
  const { child, output } = _spawnChild(bin, ["--port", String(port), "--data-dir", dataDir], true);

  let exited = false;
  let exitCode = null;
  let exitSignal = null;
  child.on("exit", (code, signal) => {
    exited = true;
    exitCode = code;
    exitSignal = signal;
  });

  const url = `http://127.0.0.1:${port}/health`;
  const deadline = Date.now() + MAIN_BOOT_TIMEOUT_MS;
  let healthy = false;
  while (Date.now() < deadline) {
    if (exited) {
      const tail = output().split("\n").slice(-30).join("\n");
      await _teardown(child);
      await rm(dataDir, { recursive: true, force: true });
      throw new Error(
        `[smoke] vysted-sidecar CRASHED before /health was ready ` +
          `(exit code=${exitCode}, signal=${exitSignal}). Most likely a PyInstaller ` +
          `dist-info gap — add the missing package to --copy-metadata in ` +
          `scripts/ensure-sidecar.mjs (precedent: v0.7.0 fastmcp fix in ` +
          `commit cf96031). Tail of stdout/stderr:\n${tail}`,
      );
    }
    if (await _httpGetOk(url)) {
      healthy = true;
      break;
    }
    await sleep(MAIN_POLL_INTERVAL_MS);
  }

  if (!healthy) {
    const tail = output().split("\n").slice(-30).join("\n");
    await _teardown(child);
    await rm(dataDir, { recursive: true, force: true });
    throw new Error(
      `[smoke] vysted-sidecar HUNG — bound the port but /health did not respond within ` +
        `${MAIN_BOOT_TIMEOUT_MS}ms. Tail:\n${tail}`,
    );
  }
  console.log(`[smoke] vysted-sidecar /health OK (port=${port}).`);

  // Correct-version assertion (CLAUDE.md "Version lives in many sources"
  // gotcha) — /health's version field must trace back to package.json, the
  // canonical bump location; a mismatch means the frozen binary was built
  // from a different version tag than this checkout's HEAD.
  const healthBody = await _httpGetJson(url, 5000);
  const expectedVersion = _packageVersion();
  const actualVersion = healthBody && healthBody.version;
  const versionOk = actualVersion === expectedVersion;

  // Screener universe probe — verifies the services/screener_universes/
  // JSON data files were bundled via --add-data. Without the --add-data
  // entry, importlib.resources cannot find sp500.json inside the frozen
  // binary and the endpoint returns 502. This gate ensures the L3-agents-
  // dir-not-bundled class of regression can never silently re-enter for
  // screener universes. Precedent: Phase 9 S2 finding; fix in
  // scripts/ensure-sidecar.mjs addData array.
  const universeUrl = `http://127.0.0.1:${port}/screener/universe?id=sp500`;
  console.log(`[smoke] vysted-sidecar: probing screener universe endpoint ...`);
  const universeOk = await _httpGetOk(universeUrl, 5000);

  // ICONIKSPEV resolve check (R7 Component 4, HARD) — verifies the regenerated
  // BSE scrip master under services/resolver_masters/ rides the frozen binary
  // AND that resolution is deterministic + internally consistent. ICONIKSPEV is
  // a BSE-only group-X micro-cap: the bundled-master path answers offline with
  // a CONSISTENT BSE identity (exchange "BSE" ↔ yahoo_symbol ".BO", confidence
  // 1.0). The historic defect — exchange "NSE" with yahoo "ICONIKSPEV.BO" at
  // 0.6 — meant the live fallback fired because the seeded master was a 2-row
  // placeholder; any regression to that state fails the smoke run here.
  const resolveUrl = `http://127.0.0.1:${port}/resolve?q=ICONIKSPEV&region=IN`;
  console.log(`[smoke] vysted-sidecar: probing ICONIKSPEV resolution (masters-only) ...`);
  const resolveBody = await _httpGetJson(resolveUrl, 5000);
  const resolved = resolveBody && resolveBody.ok === true ? resolveBody.resolved : null;
  const resolveOk =
    resolved !== null &&
    resolved.symbol === "ICONIKSPEV" &&
    resolved.exchange === "BSE" &&
    resolved.yahoo_symbol === "ICONIKSPEV.BO" &&
    resolved.region === "IN" &&
    resolved.confidence === 1.0;

  // /agents load-bearing roster probe (CLAUDE.md deferred carry-forward:
  // "verify load-bearing endpoints (/agents count > 0)"). An empty roster
  // means the first-party agent JSON directory never made it into the
  // frozen binary (agents/ --add-data gap) or agent_runtime.list_agents()
  // failed to populate its registry at import time.
  const agentsUrl = `http://127.0.0.1:${port}/agents`;
  console.log(`[smoke] vysted-sidecar: probing /agents roster ...`);
  const agentsBody = await _httpGetJson(agentsUrl, 5000);
  const agentsCount = Array.isArray(agentsBody) ? agentsBody.length : 0;

  // /mcp/status probe — the main sidecar's OWN embedded FastMCP surface
  // (mounted at /mcp, services/mcp_server.py), DISTINCT from the two
  // separately-spawned MCP subprocess sidecars tested below. Proves the
  // in-process MCP integration bound its tool catalog, not just that
  // uvicorn is serving plain HTTP.
  const mcpStatusUrl = `http://127.0.0.1:${port}/mcp/status`;
  console.log(`[smoke] vysted-sidecar: probing /mcp/status (own MCP integration) ...`);
  const mcpStatusBody = await _httpGetJson(mcpStatusUrl, 5000);
  const mcpReady = mcpStatusBody && mcpStatusBody.ready === true;

  // /history/ICONIKSPEV probe (no-SLA) — the full bhavcopy lane needs live BSE
  // (rate-limited, geo-fenced, holiday-gapped, often no outbound net in CI), so
  // real EOD bars are a bonus signal, never a gate. The offline equivalent is
  // pinned by sidecar/tests/test_history.py::
  // test_history_iconikspev_serves_real_bars_from_bhavcopy.
  const historyUrl = `http://127.0.0.1:${port}/history/ICONIKSPEV?timeframe=1d&range=1mo`;
  console.log(`[smoke] vysted-sidecar: probing /history/ICONIKSPEV (no-SLA, live BSE) ...`);
  const historyBody = await _httpGetJson(historyUrl, 30000);
  if (historyBody && Array.isArray(historyBody.bars) && historyBody.bars.length > 0) {
    console.log(
      `[smoke] /history/ICONIKSPEV OK (${historyBody.bars.length} EOD bars, ` +
        `provider=${historyBody.provider}).`,
    );
  } else {
    console.warn(
      `[smoke] WARN: /history/ICONIKSPEV returned no bars (no-SLA — not a failure). ` +
        `Benign when BSE is unreachable from this network; reason=` +
        `${historyBody ? JSON.stringify(historyBody.reason) : "<no response>"}.`,
    );
  }

  await _teardown(child);
  await rm(dataDir, { recursive: true, force: true });
  if (!versionOk) {
    throw new Error(
      `[smoke] vysted-sidecar FAILED version check: /health reported version ` +
        `${JSON.stringify(actualVersion)}, expected ${JSON.stringify(expectedVersion)} ` +
        `(package.json, the canonical version-bump source). The bundled binary was built ` +
        `from a different version tag — rebuild via \`pnpm sidecars:build\` after a version ` +
        `bump, per the CLAUDE.md "Version lives in many sources" gotcha.`,
    );
  }
  console.log(`[smoke] vysted-sidecar version OK (${actualVersion}).`);
  if (!universeOk) {
    throw new Error(
      `[smoke] vysted-sidecar FAILED screener universe probe: ` +
        `GET ${universeUrl} did not return HTTP 200. ` +
        `Root cause: services/screener_universes/ JSON data files are not bundled ` +
        `in the PyInstaller --onefile binary. Fix: add the universe dir to the ` +
        `addData array in scripts/ensure-sidecar.mjs — mirror the agents/ --add-data ` +
        `precedent (Phase 8 L3-agents-dir-not-bundled) with dest ` +
        `"services/screener_universes" so importlib.resources resolves the package ` +
        `correctly inside the frozen binary. Then rebuild with \`pnpm sidecars:build\`.`,
    );
  }
  console.log(`[smoke] vysted-sidecar screener universe OK.`);
  if (!resolveOk) {
    throw new Error(
      `[smoke] vysted-sidecar FAILED ICONIKSPEV resolve probe: ` +
        `GET ${resolveUrl} → ${JSON.stringify(resolved)}. ` +
        `Expected the deterministic BSE identity {symbol:"ICONIKSPEV", exchange:"BSE", ` +
        `yahoo_symbol:"ICONIKSPEV.BO", region:"IN", confidence:1}. Root cause is one of: ` +
        `(a) services/resolver_masters/bse_instruments.json not bundled (--add-data gap ` +
        `in scripts/ensure-sidecar.mjs), (b) the master regressed to the 2-row placeholder ` +
        `(rerun sidecar/services/resolver_masters/regenerate_bse_master.py), or (c) the ` +
        `resolver lost its BSE exact-ticker stage (services/symbol_resolver.py).`,
    );
  }
  console.log(`[smoke] vysted-sidecar ICONIKSPEV resolution OK (deterministic BSE identity).`);
  if (agentsCount <= 0) {
    throw new Error(
      `[smoke] vysted-sidecar FAILED /agents roster probe: GET ${agentsUrl} returned ` +
        `${agentsCount} agents (expected > 0) — body: ${JSON.stringify(agentsBody)}. Root ` +
        `cause is likely the first-party agent JSON directory not bundled (agents/ ` +
        `--add-data gap in scripts/ensure-sidecar.mjs) or ` +
        `services/agent_runtime.list_agents() failing to populate its registry inside the ` +
        `frozen binary. (CLAUDE.md deferred carry-forward: "/agents count > 0".)`,
    );
  }
  console.log(`[smoke] vysted-sidecar /agents roster OK (${agentsCount} agents).`);
  if (!mcpReady) {
    throw new Error(
      `[smoke] vysted-sidecar FAILED /mcp/status probe: GET ${mcpStatusUrl} → ` +
        `${JSON.stringify(mcpStatusBody)}. Expected {ready:true,...} — the embedded FastMCP ` +
        `surface (services/mcp_server.py) never bound its tool catalog inside the frozen ` +
        `binary.`,
    );
  }
  console.log(
    `[smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=` +
      `${mcpStatusBody.toolCount}).`,
  );
}

/**
 * Test an MCP subprocess sidecar — must (a) not crash, and (b) actually BIND
 * its port within MCP_BIND_TIMEOUT_MS. The prior gate only checked "process
 * alive after 10s", which is shallow: a subprocess can be alive but never bind
 * (the exact UC1 silent-failure — Phase 8 UC1-*-not-listening, Phase 9.5 UC1).
 * The TCP-bind probe closes that gap (BLOCKERS.md L3/L4 carry-forward).
 */
async function _smokeTestMcpSidecar(name, triple) {
  const bin = _binaryPath(name, triple);
  if (!existsSync(bin)) {
    throw new Error(`[smoke] ${name} binary missing: ${bin}`);
  }
  const port = await _pickFreePort();
  console.log(`[smoke] ${name}: spawning on :${port} (no-watchdog), probing port bind ...`);
  const { child, output } = _spawnChild(bin, ["--port", String(port), "--no-watchdog"], true);

  let exited = false;
  let exitCode = null;
  let exitSignal = null;
  child.on("exit", (code, signal) => {
    exited = true;
    exitCode = code;
    exitSignal = signal;
  });

  const { bound } = await _waitForBind(port, MCP_BIND_TIMEOUT_MS, () => exited);

  if (exited) {
    const tail = output().split("\n").slice(-30).join("\n");
    await _teardown(child);
    throw new Error(
      `[smoke] ${name} CRASHED before binding ` +
        `(exit code=${exitCode}, signal=${exitSignal}). Most likely a PyInstaller ` +
        `dist-info gap or data-file gap or hidden-import path drift — audit the ` +
        `--copy-metadata + --collect-data + --hidden-import lists in ` +
        `scripts/ensure-${name.replace("vysted-", "")}.mjs (precedents: v0.7.0 ` +
        `sec-edgar fastmcp removal commit 23da4f3 + collect-data=edgar fix in ` +
        `the housekeeping commit). Tail:\n${tail}`,
    );
  }

  if (!bound) {
    const tail = output().split("\n").slice(-30).join("\n");
    await _teardown(child);
    throw new Error(
      `[smoke] ${name} did NOT bind 127.0.0.1:${port} within ${MCP_BIND_TIMEOUT_MS}ms ` +
        `(process alive but never listening — the UC1 silent-non-bind failure). ` +
        `The bundled binary's cold _MEI* extraction + heavy imports overran the bind ` +
        `budget. Consider the --onedir packaging fix (BLOCKERS.md "Phase 9.5 UC1"). Tail:\n${tail}`,
    );
  }

  // Bound — confirm it survives a short settle window (catches bind-then-crash).
  await sleep(MCP_SETTLE_MS);
  if (exited) {
    const tail = output().split("\n").slice(-30).join("\n");
    await _teardown(child);
    throw new Error(
      `[smoke] ${name} bound :${port} then EXITED within ${MCP_SETTLE_MS}ms ` +
        `(exit code=${exitCode}, signal=${exitSignal}). Tail:\n${tail}`,
    );
  }

  await _teardown(child);
  console.log(`[smoke] ${name} OK (bound :${port}, survived settle window).`);
}

/**
 * Freshness gate (Phase 9.5 build-trap fix S0-2): fail loudly if any bundled
 * sidecar binary predates its source. The staleness-aware ensure scripts now
 * auto-rebuild, but this gate is the belt-and-suspenders that catches a stale
 * binary that slipped in via a cached/committed bundle bypassing the ensure
 * step — exactly the failure that produced false #91/#65 regressions in the
 * Phase 9.5 re-audit.
 */
function _assertAllFresh(triple) {
  const staleness = join(ROOT, "scripts", "sidecar-staleness.mjs");
  const checks = [
    {
      name: "vysted-sidecar",
      dirs: SIDECAR_DIR,
      opts: {
        excludeDirs: [
          join(SIDECAR_DIR, "openbb_mcp_subprocess"),
          join(SIDECAR_DIR, "sec_edgar_mcp_subprocess"),
        ],
        extraFiles: [join(ROOT, "scripts", "ensure-sidecar.mjs"), staleness],
      },
    },
    {
      name: "vysted-openbb-mcp-sidecar",
      dirs: join(SIDECAR_DIR, "openbb_mcp_subprocess"),
      opts: { extraFiles: [join(ROOT, "scripts", "ensure-openbb-mcp-sidecar.mjs"), staleness] },
    },
    {
      name: "vysted-sec-edgar-mcp-sidecar",
      dirs: join(SIDECAR_DIR, "sec_edgar_mcp_subprocess"),
      opts: { extraFiles: [join(ROOT, "scripts", "ensure-sec-edgar-mcp-sidecar.mjs"), staleness] },
    },
  ];
  for (const c of checks) {
    assertFresh(_binaryPath(c.name, triple), c.dirs, c.opts);
  }
  console.log("[smoke] freshness gate: all bundled sidecar binaries are newer than their source.");
}

async function main() {
  console.log(
    "[smoke] ATTENDED-SAFE MODE: every sidecar this run spawns uses a freshly-picked " +
      "ephemeral port and is tree-killed only via THIS run's own PID ledger " +
      `(${_STATE_FILE}). It never inspects, name-matches, or kills any pre-existing ` +
      "vysted-* process by name — including the operator's own running vysted-terminal " +
      "app, if one is up. Safe to run alongside it.",
  );
  await _scopedOrphanPreflight();
  const triple = _rustcTargetTriple();
  console.log(`[smoke] target triple: ${triple}`);
  _assertAllFresh(triple);
  const failures = [];

  for (const fn of [
    () => _smokeTestMainSidecar(triple),
    () => _smokeTestMcpSidecar("vysted-openbb-mcp-sidecar", triple),
    () => _smokeTestMcpSidecar("vysted-sec-edgar-mcp-sidecar", triple),
  ]) {
    try {
      await fn();
    } catch (err) {
      failures.push(err instanceof Error ? err.message : String(err));
    }
  }

  // No-SLA external probes — run regardless of sidecar results, never fail.
  await _probeBseBhavcopyNoSla();
  await _probeNseDirectNoSla();

  const spawnSummary = _SPAWN_LOG.map((s) => `${s.binary}(pid=${s.pid})`).join(", ") || "none";
  if (failures.length > 0) {
    console.error("\n[smoke] FAILURES:");
    for (const f of failures) console.error(f);
    console.error(
      `\n[smoke] ATTENDED-SAFE: this run spawned and fully tore down: ${spawnSummary}. ` +
        "No pre-existing vysted-* process (e.g. the operator's running app) was inspected " +
        "or touched, even though the run failed.",
    );
    process.exit(1);
  }
  console.log("\n[smoke] all sidecars booted cleanly.");
  console.log(
    `[smoke] ATTENDED-SAFE: this run spawned and fully tore down ${_SPAWN_LOG.length} ` +
      `child process(es) on freshly-picked ephemeral ports: ${spawnSummary}. Zero ` +
      "interaction with any pre-existing vysted-* process — safe to have run alongside " +
      "the operator's live app.",
  );
}

main().catch((err) => {
  console.error("[smoke] unexpected error:", err);
  process.exit(1);
});
