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
// Strategy:
//   1. Pre-flight: refuse to run if vysted-*sidecar* processes are
//      already alive — a prior run leaked, and racing on the same
//      binary file lock would produce noise.
//   2. Resolve the target triple via `rustc -vV` (matches existing
//      ensure-*.mjs scripts).
//   3. For the MAIN sidecar (vysted-sidecar):
//      - Pick a free port, spawn with --port + --data-dir + open stdin
//        (so its stdin-EOF watchdog does not fire and kill it).
//      - Poll http://127.0.0.1:PORT/health for up to 60s.
//      - 200 OK → PASS. Process exit / timeout → FAIL.
//   4. For each MCP subprocess sidecar (vysted-openbb-mcp-sidecar,
//      vysted-sec-edgar-mcp-sidecar):
//      - Spawn with --port (picked) + --no-watchdog (so closing our
//        stdin does not kill it).
//      - Wait ~10s and verify the process is still alive (exit code
//        null). MCP servers don't expose /health; surviving without a
//        crash is the contract.
//   5. Tree-kill every spawned process (Windows: taskkill /F /T /PID;
//      POSIX: process group via `detached: true` + `process.kill(-pid,
//      'SIGKILL')`). Without tree-kill the PyInstaller bootloader's
//      worker survives — CLAUDE.md Gotcha "Smoke-testing the sidecar
//      binary orphans a worker".
//   6. Verify no orphans remain after kill; if any, surface a warning.
//   7. Exit non-zero on first failure with a clear error message
//      naming the broken binary + a hint at the likely missing
//      PyInstaller flag.
//
// Run via: `node scripts/smoke-test-sidecars.mjs`

import { spawn, execSync, execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:net";
import { join, resolve } from "node:path";
import { tmpdir, platform } from "node:os";
import { mkdtemp, rm } from "node:fs/promises";
import { setTimeout as sleep } from "node:timers/promises";

const ROOT = resolve(import.meta.dirname, "..");
const BINARIES_DIR = join(ROOT, "src-tauri", "binaries");

const isWin = platform() === "win32";
const ext = isWin ? ".exe" : "";

/** Boot timeouts — generous because PyInstaller --onefile extraction is slow. */
const MAIN_BOOT_TIMEOUT_MS = 60_000;
const MAIN_POLL_INTERVAL_MS = 500;
const MCP_BOOT_WAIT_MS = 10_000;

/**
 * Track every spawned bootloader PID so the global cleanup handlers can
 * tree-kill them on script exit / SIGINT / SIGTERM. PyInstaller --onefile
 * re-execs a worker child; killing the bootloader does NOT kill the worker
 * on Windows. The Set holds bootloader PIDs; `_killTree` walks the tree.
 */
const _LIVE_PIDS = new Set();
let _CLEANUP_REGISTERED = false;

function _registerCleanup() {
  if (_CLEANUP_REGISTERED) return;
  _CLEANUP_REGISTERED = true;
  const runCleanup = () => {
    for (const pid of _LIVE_PIDS) {
      _killTree(pid);
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

/** Pre-flight: refuse to run if leaked sidecars are alive. */
function _checkNoOrphans() {
  if (isWin) {
    let out = "";
    try {
      out = execFileSync(
        "powershell",
        [
          "-NoProfile",
          "-Command",
          "Get-Process | Where-Object { $_.ProcessName -like 'vysted-*' } | Select-Object -ExpandProperty Id",
        ],
        { encoding: "utf8" },
      );
    } catch {
      return; // PowerShell unavailable — skip the check.
    }
    const pids = out
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (pids.length > 0) {
      throw new Error(
        `[smoke] PRE-FLIGHT: ${pids.length} orphaned vysted-* process(es) already running ` +
          `(PIDs: ${pids.join(", ")}). A prior run leaked workers; racing on the same binary ` +
          `file lock would produce noise. Kill them first:\n` +
          `    Get-Process vysted-* | Stop-Process -Force\n` +
          `Then re-run \`node scripts/smoke-test-sidecars.mjs\`.`,
      );
    }
  } else {
    let out = "";
    try {
      out = execFileSync("pgrep", ["-f", "vysted-.*sidecar"], { encoding: "utf8" });
    } catch {
      return; // pgrep exits 1 when nothing matches — that's the happy path.
    }
    const pids = out
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (pids.length > 0) {
      throw new Error(
        `[smoke] PRE-FLIGHT: ${pids.length} orphaned vysted-* process(es) already running ` +
          `(PIDs: ${pids.join(", ")}). Kill them first: \`pkill -9 -f vysted-.*sidecar\`.`,
      );
    }
  }
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
 * Spawn a child + track its PID for global cleanup. On POSIX `detached: true`
 * makes the child a process-group leader so `process.kill(-pid)` tree-kills.
 * On Windows we rely on `taskkill /T` in `_killTree`.
 */
function _spawnChild(bin, args, captureStream) {
  _registerCleanup();
  const child = spawn(bin, args, {
    stdio: ["pipe", "pipe", "pipe"],
    detached: !isWin,
    windowsHide: true,
  });
  if (child.pid) _LIVE_PIDS.add(child.pid);
  child.on("exit", () => {
    if (child.pid) _LIVE_PIDS.delete(child.pid);
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

  await _teardown(child);
  await rm(dataDir, { recursive: true, force: true });
  if (!healthy) {
    const tail = output().split("\n").slice(-30).join("\n");
    throw new Error(
      `[smoke] vysted-sidecar HUNG — bound the port but /health did not respond within ` +
        `${MAIN_BOOT_TIMEOUT_MS}ms. Tail:\n${tail}`,
    );
  }
  console.log(`[smoke] vysted-sidecar OK (port=${port}).`);
}

/** Test an MCP subprocess sidecar — boots and stays alive for MCP_BOOT_WAIT_MS. */
async function _smokeTestMcpSidecar(name, triple) {
  const bin = _binaryPath(name, triple);
  if (!existsSync(bin)) {
    throw new Error(`[smoke] ${name} binary missing: ${bin}`);
  }
  const port = await _pickFreePort();
  console.log(`[smoke] ${name}: spawning on :${port} (no-watchdog) ...`);
  const { child, output } = _spawnChild(bin, ["--port", String(port), "--no-watchdog"], true);

  let exited = false;
  let exitCode = null;
  let exitSignal = null;
  child.on("exit", (code, signal) => {
    exited = true;
    exitCode = code;
    exitSignal = signal;
  });

  await sleep(MCP_BOOT_WAIT_MS);

  if (exited) {
    const tail = output().split("\n").slice(-30).join("\n");
    await _teardown(child);
    throw new Error(
      `[smoke] ${name} CRASHED within ${MCP_BOOT_WAIT_MS}ms ` +
        `(exit code=${exitCode}, signal=${exitSignal}). Most likely a PyInstaller ` +
        `dist-info gap or data-file gap or hidden-import path drift — audit the ` +
        `--copy-metadata + --collect-data + --hidden-import lists in ` +
        `scripts/ensure-${name.replace("vysted-", "")}.mjs (precedents: v0.7.0 ` +
        `sec-edgar fastmcp removal commit 23da4f3 + collect-data=edgar fix in ` +
        `the housekeeping commit). Tail:\n${tail}`,
    );
  }

  await _teardown(child);
  console.log(`[smoke] ${name} OK (alive after ${MCP_BOOT_WAIT_MS}ms on :${port}).`);
}

async function main() {
  _checkNoOrphans();
  const triple = _rustcTargetTriple();
  console.log(`[smoke] target triple: ${triple}`);
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

  if (failures.length > 0) {
    console.error("\n[smoke] FAILURES:");
    for (const f of failures) console.error(f);
    process.exit(1);
  }
  console.log("\n[smoke] all sidecars booted cleanly.");
}

main().catch((err) => {
  console.error("[smoke] unexpected error:", err);
  process.exit(1);
});
