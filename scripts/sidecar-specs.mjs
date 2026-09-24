// scripts/sidecar-specs.mjs
//
// The one table of what each sidecar binary is built from, and the one builder
// that turns a row into a binary (R15-CODE-PLATFORM-026). The three
// `ensure-*-sidecar.mjs` scripts, the `ensure-all-sidecars.mjs` orchestrator and
// the smoke-test freshness gate all read SIDECAR_SPECS, so adding a sidecar is a
// new row here plus its `bundle.externalBin` entry and `.gitignore` lines.
//
// PyInstaller `--onefile` silently drops whatever a flag below does not name
// (dist-info, package data, plain data dirs), and the binary still builds, so
// every flag carries the reason it exists. `sidecar-specs.test.mjs` pins each
// row's PyInstaller command byte-for-byte.

import { execFileSync, execSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { platform } from "node:os";

import { ensureBuildVenv } from "./build-python.mjs";
import { isStale } from "./sidecar-staleness.mjs";
import { signDevBinary } from "./macos-dev-sign.mjs";

const ROOT = resolve(import.meta.dirname, "..");
const SIDECAR_DIR = join(ROOT, "sidecar");
const OPENBB_DIR = join(SIDECAR_DIR, "openbb_mcp_subprocess");
const SEC_EDGAR_DIR = join(SIDECAR_DIR, "sec_edgar_mcp_subprocess");
export const BINARIES_DIR = join(ROOT, "src-tauri", "binaries");

const isWin = platform() === "win32";
const ext = isWin ? ".exe" : "";

const flags = (flag, values) => values.map((v) => `${flag}=${v}`);

// uvicorn resolves its loop/protocol implementations dynamically, so the
// relevant submodules are hinted explicitly.
const UVICORN_HIDDEN = [
  "uvicorn.loops.auto",
  "uvicorn.loops.asyncio",
  "uvicorn.protocols.http.auto",
  "uvicorn.protocols.http.h11_impl",
  "uvicorn.protocols.websockets.auto",
  "uvicorn.lifespan.on",
  "uvicorn.lifespan.off",
];

// Plain data the main sidecar loads at runtime. --onefile only collects Python
// modules, so each dir needs an explicit --add-data or it is silently absent:
// - `agents/` (no __init__.py; services/agent_runtime.py reads it by path):
//   without it every first-party agent is missing and /agents returns []
//   (Phase 8 L3-agents-dir-not-bundled).
// - `services/screener_universes/` and `services/resolver_masters/` are
//   packages, but their JSON/.json.gz data is not collected: without them the
//   screener returns 502 "missing universe snapshot" (Phase 9 S2) and the symbol
//   resolver loads empty masters (Pass B / B1). The dest mirrors the package
//   path so importlib.resources resolves inside the frozen binary.
// - `config/` holds model_registry.json (services/model_registry.py loads it
//   from `sys._MEIPASS/config`); absent, the loader raises at startup.
// SOURCE is absolute because PyInstaller resolves it against --specpath (the
// build/ dir), not cwd. The separator is ';' on Windows and ':' on POSIX, and
// the value is quoted because cmd.exe treats an unquoted ';' as a command
// separator and silently splits the pyinstaller call in two.
const MAIN_ADD_DATA = [
  [join(SIDECAR_DIR, "agents"), "agents"],
  [join(SIDECAR_DIR, "services", "screener_universes"), "services/screener_universes"],
  [join(SIDECAR_DIR, "services", "resolver_masters"), "services/resolver_masters"],
  [join(SIDECAR_DIR, "config"), "config"],
];

// Editing the build recipe must invalidate every binary.
const RECIPE_FILES = [
  import.meta.filename,
  join(import.meta.dirname, "sidecar-staleness.mjs"),
  join(import.meta.dirname, "build-python.mjs"),
];

const SPECS = [
  {
    name: "vysted-sidecar",
    kind: "main",
    sourceDir: SIDECAR_DIR,
    requirements: "requirements-dev.txt",
    pipExtras: [],
    identifier: "com.vysted.sidecar",
    addData: MAIN_ADD_DATA,
    // The two MCP subprocess dirs build from their own rows.
    excludeDirs: [OPENBB_DIR, SEC_EDGAR_DIR],
    pyinstallerFlags: [
      ...flags("--hidden-import", UVICORN_HIDDEN),
      // fastmcp + mcp call importlib.metadata.version() on import; without
      // their dist-info the binary raises PackageNotFoundError at startup
      // (v0.7.0 F6). anyio/httpx/starlette/uvicorn ride along for the same probe.
      ...flags("--copy-metadata", ["fastmcp", "mcp", "anyio", "httpx", "starlette", "uvicorn"]),
      // curl_cffi ships a native libcurl-impersonate library plus CA data that
      // --onefile discovers neither of; --collect-all bundles both.
      ...flags("--collect-all", ["curl_cffi"]),
      ...MAIN_ADD_DATA.map(([src, dest]) => `--add-data "${src}${isWin ? ";" : ":"}${dest}"`),
    ],
  },
  {
    // openbb-mcp-server pulls openbb-core, which pins fastapi/uvicorn below the
    // main sidecar's pins, hence its own venv and binary.
    name: "vysted-openbb-mcp-sidecar",
    kind: "mcp",
    sourceDir: OPENBB_DIR,
    requirements: "requirements.txt",
    pipExtras: ["pyinstaller==6.20.0"],
    identifier: "com.vysted.openbb-mcp-sidecar",
    addData: [],
    excludeDirs: [],
    pyinstallerFlags: [
      // openbb-mcp-server 1.4.0 exports `main` from openbb_mcp_server.app.app.
      ...flags("--hidden-import", [...UVICORN_HIDDEN, "openbb_mcp_server.app.app"]),
      // OpenBB extensions are discovered through entry_points() at runtime,
      // which static analysis cannot see, so each sub-package is collected
      // wholesale. The `openbb` meta-package is avoided on purpose: it generates
      // code into site-packages on first import, fatal on a read-only --onefile fs.
      ...flags("--collect-all", [
        "openbb_mcp_server",
        "openbb_core",
        "openbb_equity",
        "openbb_economy",
        "openbb_yfinance",
        "openbb_fred",
        "openbb_fmp",
        "fastmcp",
      ]),
      ...flags("--copy-metadata", [
        "fastmcp",
        "fastmcp-slim",
        "mcp",
        "openbb-mcp-server",
        "openbb-core",
        "anyio",
        "httpx",
        "starlette",
        "uvicorn",
      ]),
    ],
  },
  {
    // sec-edgar-mcp has its own dependency tree; its own venv keeps an upstream
    // bump from dragging a shared transitive dep through the main sidecar's pins.
    name: "vysted-sec-edgar-mcp-sidecar",
    kind: "mcp",
    sourceDir: SEC_EDGAR_DIR,
    requirements: "requirements.txt",
    pipExtras: ["pyinstaller==6.20.0"],
    identifier: "com.vysted.sec-edgar-mcp-sidecar",
    addData: [],
    excludeDirs: [],
    pyinstallerFlags: [
      ...flags("--hidden-import", [...UVICORN_HIDDEN, "sec_edgar_mcp.server"]),
      ...flags("--collect-all", ["sec_edgar_mcp"]),
      // `edgar` (from the edgartools dist) loads CSV reference data through
      // pkgutil at import time (edgar/reference/data/secforms.csv); without
      // --collect-data the binary dies on FileNotFoundError (v0.7.0 smoke test).
      ...flags("--collect-data", ["edgar"]),
      ...flags("--collect-submodules", ["edgar"]),
      // sec-edgar-mcp uses the official `mcp` SDK, not fastmcp: copying fastmcp
      // metadata here fails the build on a clean venv. Dist-info goes under the
      // install name (edgartools), not the import name.
      ...flags("--copy-metadata", [
        "mcp",
        "sec-edgar-mcp",
        "edgartools",
        "anyio",
        "httpx",
        "starlette",
        "uvicorn",
      ]),
    ],
  },
];

export const SIDECAR_SPECS = SPECS.map((spec) => ({
  ...spec,
  stale: {
    dirs: [spec.sourceDir],
    opts: { excludeDirs: spec.excludeDirs, extraFiles: RECIPE_FILES },
  },
}));

/** `rustc -vV` reports the host target triple; Tauri expects it as the binary suffix. */
export function targetTriple() {
  const out = execSync("rustc -vV", { encoding: "utf8" });
  const line = out.split("\n").find((l) => l.startsWith("host:"));
  if (!line) throw new Error("could not determine host target triple from `rustc -vV`");
  return line.replace("host:", "").trim();
}

export function binaryPath(name, triple) {
  return join(BINARIES_DIR, `${name}-${triple}${ext}`);
}

const venvBin = (spec) => join(spec.sourceDir, ".venv", isWin ? "Scripts" : "bin");

/** The full PyInstaller command line for one spec (run with cwd = spec.sourceDir). */
export function pyinstallerCommand(spec) {
  const pyinstaller = join(venvBin(spec), isWin ? "pyinstaller.exe" : "pyinstaller");
  const buildDir = join(spec.sourceDir, "build");
  const distDir = join(spec.sourceDir, "dist");
  return (
    `"${pyinstaller}" --onefile --clean --noconfirm --name ${spec.name} ` +
    `${spec.pyinstallerFlags.join(" ")} --distpath "${distDir}" --workpath "${buildDir}" ` +
    `--specpath "${buildDir}" main.py`
  );
}

/** Synchronous sleep, used only for the copy-retry backoff. */
function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/**
 * Build `spec` into src-tauri/binaries/<name>-<triple>[.exe]. A fast no-op when
 * the binary exists and is newer than its source, unless `force`.
 */
export function buildSidecar(spec, { force = false } = {}) {
  const tag = `[ensure-${spec.name.replace(/^vysted-/, "")}]`;
  const run = (cmd, opts = {}) => {
    console.log(`${tag} $ ${cmd}`);
    execSync(cmd, { stdio: "inherit", ...opts });
  };

  const outPath = binaryPath(spec.name, targetTriple());
  const outName = basename(outPath);
  // Staleness-aware no-op (Phase 9.5 S0-2): a source edit always reaches the bundle.
  const present = existsSync(outPath);
  const stale = present && isStale(outPath, spec.stale.dirs, spec.stale.opts);
  if (present && !force && !stale) {
    console.log(`${tag} ${outName} present and fresh — skipping build.`);
    return;
  }
  if (stale && !force) {
    console.log(`${tag} ${outName} is STALE (source newer than binary) — rebuilding.`);
  }

  console.log(`${tag} building ${outName} ...`);
  mkdirSync(BINARIES_DIR, { recursive: true });

  // 1. Build venv on Python 3.13 (recreated if it is any other version).
  const venvDir = join(spec.sourceDir, ".venv");
  const venvPython = join(venvBin(spec), isWin ? "python.exe" : "python");
  ensureBuildVenv(venvDir, venvPython, run);

  // 2. Dependencies.
  run(`"${venvPython}" -m pip install --upgrade pip`);
  run(`"${venvPython}" -m pip install -r "${join(spec.sourceDir, spec.requirements)}"`);
  for (const extra of spec.pipExtras) run(`"${venvPython}" -m pip install ${extra}`);

  // Every copy-metadata target must be installed, or PyInstaller dies mid-build
  // with a bare PackageNotFoundError (R15-LEAD-001). Name the missing ones up front.
  const copyMeta = spec.pyinstallerFlags
    .filter((f) => f.startsWith("--copy-metadata="))
    .map((f) => f.slice("--copy-metadata=".length));
  const missingMeta = execFileSync(
    venvPython,
    [
      "-c",
      "import importlib.metadata as m, sys; " +
        "print(' '.join(d for d in sys.argv[1:] if not any(True for _ in m.distributions(name=d))))",
      ...copyMeta,
    ],
    { encoding: "utf8" },
  ).trim();
  if (missingMeta) {
    throw new Error(
      `${tag} --copy-metadata targets not installed in ${venvDir}: ${missingMeta}. ` +
        `Check the pins in ${join(spec.sourceDir, spec.requirements)}.`,
    );
  }

  // 3. The one-file binary.
  run(pyinstallerCommand(spec), { cwd: spec.sourceDir });

  // 4. Copy to src-tauri/binaries with the target-triple suffix. A fresh .exe
  //    is often held briefly by antivirus or the search indexer (EBUSY/EPERM).
  const built = join(spec.sourceDir, "dist", spec.name + ext);
  for (let i = 1; ; i++) {
    try {
      copyFileSync(built, outPath);
      break;
    } catch (err) {
      if (!["EBUSY", "EPERM", "EACCES"].includes(err.code) || i === 10) throw err;
      console.log(`${tag} ${outPath} locked (${err.code}), retry ${i}/10...`);
      sleepSync(2000);
    }
  }
  console.log(`${tag} wrote ${outPath}`);
  signDevBinary(outPath, spec.identifier);

  // 5. Tidy PyInstaller scratch directories.
  rmSync(join(spec.sourceDir, "build"), { recursive: true, force: true });
  rmSync(join(spec.sourceDir, "dist"), { recursive: true, force: true });
  console.log(`${tag} done.`);
}
