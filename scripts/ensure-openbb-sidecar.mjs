// scripts/ensure-openbb-sidecar.mjs
//
// Idempotently builds the OpenBB subprocess into a single-file binary that
// the main Vysted sidecar launches lazily on first OpenBB request. Mirrors
// the structure of `ensure-sidecar.mjs` — same target-triple pattern, same
// copy-retry guard, same PyInstaller --onefile invocation. Lives as a
// separate script because OpenBB's strict version pins (fastapi <0.129,
// uvicorn <0.41) are incompatible with the main sidecar's pins, so OpenBB
// gets its own venv and its own bundled binary (Tier 2 per plan §A2 +
// BLOCKERS-C.md).
//
// Output: src-tauri/binaries/vysted-openbb-sidecar-<target-triple>[.exe]
//
// Run via: `node scripts/ensure-openbb-sidecar.mjs [--force]`.

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, copyFileSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { platform } from "node:os";

const ROOT = resolve(import.meta.dirname, "..");
const SUBPROCESS_DIR = join(ROOT, "sidecar", "openbb_subprocess");
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
  console.log(`[ensure-openbb-sidecar] $ ${cmd}`);
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
        `[ensure-openbb-sidecar] ${dest} locked (${err.code}), retry ${i}/${attempts}...`,
      );
      sleepSync(2000);
    }
  }
}

const triple = targetTriple();
const ext = isWin ? ".exe" : "";
const outName = `vysted-openbb-sidecar-${triple}${ext}`;
const outPath = join(BINARIES_DIR, outName);

if (existsSync(outPath) && !FORCE) {
  console.log(`[ensure-openbb-sidecar] ${outName} already present — skipping build.`);
  process.exit(0);
}

console.log(`[ensure-openbb-sidecar] building ${outName} ...`);
mkdirSync(BINARIES_DIR, { recursive: true });

// 1. Create the build venv if missing.
if (!existsSync(venvPython)) {
  const py = isWin ? "python" : "python3";
  run(`${py} -m venv "${VENV_DIR}"`);
}

// 2. Install OpenBB subprocess + build deps. This venv intentionally lives
//    apart from the main sidecar's so the OpenBB strict pins don't collide.
run(`"${venvPython}" -m pip install --upgrade pip`);
run(`"${venvPython}" -m pip install -r "${join(SUBPROCESS_DIR, "requirements.txt")}"`);
run(`"${venvPython}" -m pip install pyinstaller==6.20.0`);

// 3. Build the one-file binary. OpenBB extensions are discovered through
//    importlib.metadata.entry_points() at runtime — PyInstaller's static
//    analysis cannot see those, so each OpenBB sub-package is collected
//    wholesale via --collect-all. The subprocess deliberately avoids the
//    `openbb` meta-package (which would generate code into site-packages on
//    first import — fatal under --onefile read-only fs).
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
]
  .map((m) => `--hidden-import=${m}`)
  .join(" ");
const collectAll = [
  "openbb_core",
  "openbb_equity",
  "openbb_economy",
  "openbb_yfinance",
  "openbb_fred",
  "openbb_fmp",
]
  .map((m) => `--collect-all=${m}`)
  .join(" ");
run(
  `"${pyinstaller}" --onefile --clean --noconfirm --name vysted-openbb-sidecar ` +
    `${hidden} ${collectAll} --distpath "${distDir}" --workpath "${buildDir}" ` +
    `--specpath "${buildDir}" main.py`,
  { cwd: SUBPROCESS_DIR },
);

// 4. Copy to src-tauri/binaries with the Tauri target-triple suffix.
const built = join(distDir, isWin ? "vysted-openbb-sidecar.exe" : "vysted-openbb-sidecar");
copyWithRetry(built, outPath);
console.log(`[ensure-openbb-sidecar] wrote ${outPath}`);

// 5. Tidy PyInstaller scratch directories.
rmSync(buildDir, { recursive: true, force: true });
rmSync(distDir, { recursive: true, force: true });
console.log("[ensure-openbb-sidecar] done.");
