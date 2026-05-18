// scripts/ensure-sidecar.mjs
//
// Idempotently builds the Python sidecar into a single-file binary that Tauri
// picks up via `bundle.externalBin`. Wired into tauri.conf.json's
// beforeDevCommand / beforeBuildCommand, so a bare `pnpm tauri dev` builds the
// sidecar on first run. Fast no-op when the binary already exists, unless --force.
//
// Output: src-tauri/binaries/vysted-sidecar-<target-triple>[.exe]

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, copyFileSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { platform } from "node:os";

const ROOT = resolve(import.meta.dirname, "..");
const SIDECAR_DIR = join(ROOT, "sidecar");
const BINARIES_DIR = join(ROOT, "src-tauri", "binaries");
const VENV_DIR = join(SIDECAR_DIR, ".venv");
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
  console.log(`[ensure-sidecar] $ ${cmd}`);
  execSync(cmd, { stdio: "inherit", ...opts });
}

/** Synchronous sleep — used only for the copy-retry backoff. */
function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/**
 * Copy a file, retrying on transient locks. A freshly built .exe is often held
 * briefly by antivirus or the search indexer, which surfaces as EBUSY/EPERM.
 */
function copyWithRetry(src, dest, attempts = 10) {
  for (let i = 1; i <= attempts; i++) {
    try {
      copyFileSync(src, dest);
      return;
    } catch (err) {
      const transient = ["EBUSY", "EPERM", "EACCES"].includes(err.code);
      if (!transient || i === attempts) throw err;
      console.log(`[ensure-sidecar] ${dest} locked (${err.code}), retry ${i}/${attempts}...`);
      sleepSync(2000);
    }
  }
}

const triple = targetTriple();
const ext = isWin ? ".exe" : "";
const outName = `vysted-sidecar-${triple}${ext}`;
const outPath = join(BINARIES_DIR, outName);

if (existsSync(outPath) && !FORCE) {
  console.log(`[ensure-sidecar] ${outName} already present — skipping build.`);
  process.exit(0);
}

console.log(`[ensure-sidecar] building ${outName} ...`);
mkdirSync(BINARIES_DIR, { recursive: true });

// 1. Create the build venv if missing.
if (!existsSync(venvPython)) {
  const py = isWin ? "python" : "python3";
  run(`${py} -m venv "${VENV_DIR}"`);
}

// 2. Install sidecar + build dependencies.
run(`"${venvPython}" -m pip install --upgrade pip`);
run(`"${venvPython}" -m pip install -r "${join(SIDECAR_DIR, "requirements-dev.txt")}"`);

// 3. Build the one-file binary with PyInstaller. uvicorn resolves its loop/protocol
//    implementations dynamically, so the relevant submodules are hinted explicitly.
const pyinstaller = join(venvBin, isWin ? "pyinstaller.exe" : "pyinstaller");
const buildDir = join(SIDECAR_DIR, "build");
const distDir = join(SIDECAR_DIR, "dist");
const hidden = [
  "uvicorn.loops.auto",
  "uvicorn.loops.asyncio",
  "uvicorn.protocols.http.auto",
  "uvicorn.protocols.http.h11_impl",
  "uvicorn.protocols.websockets.auto",
  "uvicorn.lifespan.on",
  "uvicorn.lifespan.off",
]
  .map((m) => `--hidden-import=${m}`)
  .join(" ");
// fastmcp + mcp inspect their own importlib.metadata at import time
// (FastMCP's __init__.py calls version("fastmcp") to expose the
// __version__ attribute). Without --copy-metadata the --onefile binary
// raises PackageNotFoundError at startup — bug surfaced in v0.7.0 F6
// graph-diagnosis. anyio + httpx + starlette + uvicorn included
// defensively since the openbb-mcp subprocess already needs them
// metadata-bundled and the cost is negligible.
const copyMeta = ["fastmcp", "mcp", "anyio", "httpx", "starlette", "uvicorn"]
  .map((m) => `--copy-metadata=${m}`)
  .join(" ");
// `agents/` is a plain directory (no __init__.py) loaded at runtime via
// `Path(__file__).resolve().parent.parent / "agents"` in
// services/agent_runtime.py. PyInstaller --onefile only auto-discovers
// Python packages; plain data dirs need explicit --add-data. Without
// this, every named first-party agent (Buffett, Dalio, Druckenmiller,
// Graham, Klarman, Lynch, Marks, Munger, Portfolio Advisor) is silently
// absent at runtime — /agents returns []. Phase 8 L3 finding
// L3-agents-dir-not-bundled. PyInstaller's --add-data syntax is OS-
// specific: ';' separator on Windows, ':' on POSIX. The value MUST be
// quoted because cmd.exe interprets ';' as a command separator if
// unquoted, silently splitting the pyinstaller invocation into two
// half-commands that both fail to run (stdout/stderr blank, exit 1).
// PyInstaller resolves SOURCE in --add-data relative to --specpath, not cwd.
// Since --specpath is the build/ subdirectory, use an absolute SOURCE so
// 'agents' resolves regardless of where PyInstaller's spec-file lives.
const addDataSep = isWin ? ";" : ":";
const agentsAbsPath = join(SIDECAR_DIR, "agents");
const addData = [[agentsAbsPath, "agents"]]
  .map(([src, dest]) => `--add-data "${src}${addDataSep}${dest}"`)
  .join(" ");
run(
  `"${pyinstaller}" --onefile --clean --noconfirm --name vysted-sidecar ` +
    `${hidden} ${copyMeta} ${addData} --distpath "${distDir}" --workpath "${buildDir}" ` +
    `--specpath "${buildDir}" main.py`,
  { cwd: SIDECAR_DIR },
);

// 4. Copy to src-tauri/binaries with the Tauri target-triple suffix.
const built = join(distDir, isWin ? "vysted-sidecar.exe" : "vysted-sidecar");
copyWithRetry(built, outPath);
console.log(`[ensure-sidecar] wrote ${outPath}`);

// 5. Tidy PyInstaller scratch directories.
rmSync(buildDir, { recursive: true, force: true });
rmSync(distDir, { recursive: true, force: true });
console.log("[ensure-sidecar] done.");
