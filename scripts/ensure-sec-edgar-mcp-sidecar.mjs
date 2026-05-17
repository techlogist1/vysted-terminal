// scripts/ensure-sec-edgar-mcp-sidecar.mjs
//
// Idempotently builds the sec-edgar-mcp subprocess into a single-file binary
// that the Tauri Rust core launches via ``Command::new``. Mirrors the shape
// of ``ensure-openbb-mcp-sidecar.mjs``: per-OS venv, PyInstaller --onefile,
// target-triple-suffixed output, and a copy-with-retry guard.
//
// Why a separate script: sec-edgar-mcp is its own MCP server with its own
// dependency tree. Isolating it into its own venv preserves the v0.4.0
// pattern (openbb-mcp-server precedent) so a future upstream bump cannot
// drag a shared transitive dependency through the main sidecar's pins.
//
// Output: ``src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-<target-triple>[.exe]``
//
// Run via: ``node scripts/ensure-sec-edgar-mcp-sidecar.mjs [--force]``.

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, copyFileSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { platform } from "node:os";

const ROOT = resolve(import.meta.dirname, "..");
const SUBPROCESS_DIR = join(ROOT, "sidecar", "sec_edgar_mcp_subprocess");
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
  console.log(`[ensure-sec-edgar-mcp-sidecar] $ ${cmd}`);
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
        `[ensure-sec-edgar-mcp-sidecar] ${dest} locked (${err.code}), retry ${i}/${attempts}...`,
      );
      sleepSync(2000);
    }
  }
}

const triple = targetTriple();
const ext = isWin ? ".exe" : "";
const outName = `vysted-sec-edgar-mcp-sidecar-${triple}${ext}`;
const outPath = join(BINARIES_DIR, outName);

if (existsSync(outPath) && !FORCE) {
  console.log(`[ensure-sec-edgar-mcp-sidecar] ${outName} already present — skipping build.`);
  process.exit(0);
}

console.log(`[ensure-sec-edgar-mcp-sidecar] building ${outName} ...`);
mkdirSync(BINARIES_DIR, { recursive: true });

// 1. Create the build venv if missing.
if (!existsSync(venvPython)) {
  const py = isWin ? "python" : "python3";
  run(`${py} -m venv "${VENV_DIR}"`);
}

// 2. Install sec-edgar-mcp + build deps. This venv lives apart from the main
//    sidecar's to keep dep trees isolated (precedent: openbb-mcp).
run(`"${venvPython}" -m pip install --upgrade pip`);
run(`"${venvPython}" -m pip install -r "${join(SUBPROCESS_DIR, "requirements.txt")}"`);
run(`"${venvPython}" -m pip install pyinstaller==6.20.0`);

// 3. Build the one-file binary. sec-edgar-mcp's server module discovers
//    its tools through @mcp.tool() registration at import time, so unlike
//    OpenBB it does not need a --collect-all blast. However, fastmcp +
//    mcp inspect their own importlib.metadata at import time so we copy
//    their dist-info eagerly (same precaution as the openbb-mcp script).
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
  "sec_edgar_mcp.server",
]
  .map((m) => `--hidden-import=${m}`)
  .join(" ");
// sec-edgar-mcp 1.0.8 imports the official ``mcp`` SDK (not ``fastmcp``).
// The fastmcp references were copy-pasted from the openbb-mcp script
// template and silently failed CI on clean checkouts (``--copy-metadata
// =fastmcp`` raises PackageNotFoundError because fastmcp isn't in this
// venv). Keep ``mcp`` in copy-metadata so importlib.metadata lookups for
// the MCP SDK succeed inside the --onefile binary.
const collectAll = ["sec_edgar_mcp"].map((m) => `--collect-all=${m}`).join(" ");
const copyMeta = ["mcp", "sec-edgar-mcp", "anyio", "httpx", "starlette", "uvicorn"]
  .map((m) => `--copy-metadata=${m}`)
  .join(" ");
run(
  `"${pyinstaller}" --onefile --clean --noconfirm --name vysted-sec-edgar-mcp-sidecar ` +
    `${hidden} ${collectAll} ${copyMeta} --distpath "${distDir}" --workpath "${buildDir}" ` +
    `--specpath "${buildDir}" main.py`,
  { cwd: SUBPROCESS_DIR },
);

// 4. Copy to src-tauri/binaries with the Tauri target-triple suffix.
const built = join(
  distDir,
  isWin ? "vysted-sec-edgar-mcp-sidecar.exe" : "vysted-sec-edgar-mcp-sidecar",
);
copyWithRetry(built, outPath);
console.log(`[ensure-sec-edgar-mcp-sidecar] wrote ${outPath}`);

// 5. Tidy PyInstaller scratch directories.
rmSync(buildDir, { recursive: true, force: true });
rmSync(distDir, { recursive: true, force: true });
console.log("[ensure-sec-edgar-mcp-sidecar] done.");
