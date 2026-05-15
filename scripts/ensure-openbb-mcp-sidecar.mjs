// scripts/ensure-openbb-mcp-sidecar.mjs
//
// Idempotently builds the openbb-mcp subprocess into a single-file binary
// that the Tauri Rust core launches via ``Command::new``. Mirrors the shape
// of ``ensure-sidecar.mjs`` and the retired ``ensure-openbb-sidecar.mjs``:
// per-OS venv, PyInstaller --onefile, target-triple-suffixed output, and a
// copy-with-retry guard.
//
// Why a separate script: openbb-mcp-server 1.4.0 transitively pulls
// openbb-core 1.6.x which strictly pins fastapi <0.129 and uvicorn <0.41.
// Those pins are incompatible with the main Vysted sidecar's pins
// (fastapi 0.136, uvicorn 0.46); isolating openbb-mcp into its own venv
// keeps the main sidecar's deps clean.
//
// Phase-2 BLOCKERS history: the prior ``ensure-openbb-sidecar.mjs`` built
// a custom FastAPI subprocess that the main sidecar spawned via Python
// ``subprocess.Popen``. On Windows that path deadlocked indefinitely
// (anyio + PyInstaller ``_MEIPASS`` + Windows handle inheritance — see
// CLAUDE.md Gotcha). Phase 3 replaces both halves: the stock
// ``openbb-mcp-server`` package is the subprocess, and Tauri Rust
// ``Command::new`` spawns it (different handle semantics).
//
// Output: ``src-tauri/binaries/vysted-openbb-mcp-sidecar-<target-triple>[.exe]``
//
// Run via: ``node scripts/ensure-openbb-mcp-sidecar.mjs [--force]``.

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, copyFileSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { platform } from "node:os";

const ROOT = resolve(import.meta.dirname, "..");
const SUBPROCESS_DIR = join(ROOT, "sidecar", "openbb_mcp_subprocess");
const BINARIES_DIR = join(ROOT, "src-tauri", "binaries");
const VENV_DIR = join(SUBPROCESS_DIR, ".venv");
const FORCE = process.argv.includes("--force");

const isWin = platform() === "win32";
const venvBin = isWin ? join(VENV_DIR, "Scripts") : join(VENV_DIR, "bin");
const venvPython = join(venvBin, isWin ? "python.exe" : "python");

/** `rustc -vV` reports the host target triple; Tauri expects it as the binary suffix. */
function targetTriple() {
  const out = execSync("rustc -vV", { encoding: "utf8" });
  const line = out.split("\n").find((l) => l.startsWith("host:"));
  if (!line) throw new Error("could not determine host target triple from `rustc -vV`");
  return line.replace("host:", "").trim();
}

function run(cmd, opts = {}) {
  console.log(`[ensure-openbb-mcp-sidecar] $ ${cmd}`);
  execSync(cmd, { stdio: "inherit", ...opts });
}

/** Synchronous sleep — used only for the copy-retry backoff. */
function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/** Copy a file, retrying on transient locks (antivirus / search indexer). */
function copyWithRetry(src, dest, attempts = 10) {
  for (let i = 1; i <= attempts; i++) {
    try {
      copyFileSync(src, dest);
      return;
    } catch (err) {
      const transient = ["EBUSY", "EPERM", "EACCES"].includes(err.code);
      if (!transient || i === attempts) throw err;
      console.log(
        `[ensure-openbb-mcp-sidecar] ${dest} locked (${err.code}), retry ${i}/${attempts}...`,
      );
      sleepSync(2000);
    }
  }
}

const triple = targetTriple();
const ext = isWin ? ".exe" : "";
const outName = `vysted-openbb-mcp-sidecar-${triple}${ext}`;
const outPath = join(BINARIES_DIR, outName);

if (existsSync(outPath) && !FORCE) {
  console.log(`[ensure-openbb-mcp-sidecar] ${outName} already present — skipping build.`);
  process.exit(0);
}

console.log(`[ensure-openbb-mcp-sidecar] building ${outName} ...`);
mkdirSync(BINARIES_DIR, { recursive: true });

// 1. Create the build venv if missing.
if (!existsSync(venvPython)) {
  const py = isWin ? "python" : "python3";
  run(`${py} -m venv "${VENV_DIR}"`);
}

// 2. Install openbb-mcp-server + build deps. This venv intentionally lives
//    apart from the main sidecar's so the OpenBB strict pins don't collide.
run(`"${venvPython}" -m pip install --upgrade pip`);
run(`"${venvPython}" -m pip install -r "${join(SUBPROCESS_DIR, "requirements.txt")}"`);
run(`"${venvPython}" -m pip install pyinstaller==6.20.0`);

// 3. Build the one-file binary. OpenBB-platform extensions are discovered
//    through importlib.metadata.entry_points() at runtime; PyInstaller's
//    static analysis cannot see those, so each OpenBB sub-package is
//    collected wholesale via --collect-all. The subprocess deliberately
//    avoids the ``openbb`` meta-package (which would generate code into
//    site-packages on first import — fatal under --onefile read-only fs).
const pyinstaller = join(venvBin, isWin ? "pyinstaller.exe" : "pyinstaller");
const buildDir = join(SUBPROCESS_DIR, "build");
const distDir = join(SUBPROCESS_DIR, "dist");
const hidden = [
  "uvicorn.loops.auto",
  "uvicorn.loops.asyncio",
  "uvicorn.protocols.http.auto",
  "uvicorn.protocols.http.h11_impl",
  "uvicorn.protocols.websockets.auto",
  "uvicorn.lifespan.on",
  "uvicorn.lifespan.off",
  "openbb_mcp_server.main",
]
  .map((m) => `--hidden-import=${m}`)
  .join(" ");
const collectAll = [
  "openbb_mcp_server",
  "openbb_core",
  "openbb_equity",
  "openbb_economy",
  "openbb_yfinance",
  "openbb_fred",
  "openbb_fmp",
  "fastmcp",
]
  .map((m) => `--collect-all=${m}`)
  .join(" ");
// fastmcp + mcp inspect their own importlib.metadata at import time, so
// PyInstaller must explicitly bundle their dist-info — otherwise the
// package version probe raises PackageNotFoundError on first import.
const copyMeta = [
  "fastmcp",
  "fastmcp-slim",
  "mcp",
  "openbb-mcp-server",
  "openbb-core",
  "anyio",
  "httpx",
  "starlette",
  "uvicorn",
]
  .map((m) => `--copy-metadata=${m}`)
  .join(" ");
run(
  `"${pyinstaller}" --onefile --clean --noconfirm --name vysted-openbb-mcp-sidecar ` +
    `${hidden} ${collectAll} ${copyMeta} --distpath "${distDir}" --workpath "${buildDir}" ` +
    `--specpath "${buildDir}" main.py`,
  { cwd: SUBPROCESS_DIR },
);

// 4. Copy to src-tauri/binaries with the Tauri target-triple suffix.
const built = join(distDir, isWin ? "vysted-openbb-mcp-sidecar.exe" : "vysted-openbb-mcp-sidecar");
copyWithRetry(built, outPath);
console.log(`[ensure-openbb-mcp-sidecar] wrote ${outPath}`);

// 5. Tidy PyInstaller scratch directories.
rmSync(buildDir, { recursive: true, force: true });
rmSync(distDir, { recursive: true, force: true });
console.log("[ensure-openbb-mcp-sidecar] done.");
