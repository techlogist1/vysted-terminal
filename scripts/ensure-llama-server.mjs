// scripts/ensure-llama-server.mjs
//
// Idempotently stages the prebuilt llama.cpp `llama-server` binary (pinned
// build b11429 == release v0.6.0) plus the shared libraries it dlopen's or
// dynamically links, so Tauri's `bundle.externalBin` ("binaries/llama-server")
// and the per-platform resource mappings (tauri.macos.conf.json /
// tauri.windows.conf.json / tauri.linux.conf.json) have something to bundle.
//
// Unlike the Python sidecars (sidecar-specs.mjs), this is not compiled from
// repo source — it's a prebuilt third-party release asset, downloaded once,
// verified by sha256 (computed from the file, checked against the GitHub
// release asset's own `digest`), and re-staged only when the pinned build or
// this script changes (the "simplest form" of scripts/sidecar-staleness.mjs's
// idea: compare against this script's own mtime, same as `extraFiles` does
// for the Python ensure scripts' build recipe).
//
// Layout produced:
//   src-tauri/binaries/llama-server-<triple>[.exe]   (the externalBin)
//   src-tauri/llama-libs/<triple>/<shared libs...>   (git-ignored staging —
//     consumed by tauri.macos.conf.json's bundle.macOS.files (dylibs copied
//     next to the binary in Contents/MacOS, which carries an @loader_path
//     rpath), tauri.windows.conf.json's bundle.resources (DLLs land in
//     $INSTDIR root, next to llama-server.exe, via NSIS's default Windows
//     resource placement), and tauri.linux.conf.json's bundle.resources
//     (.so files land under <resource_dir>/llama-libs/ — the engine writer
//     sets LD_LIBRARY_PATH to that exact path before spawning llama-server;
//     llama-server's own RUNPATH is $ORIGIN, which only resolves when the
//     resource dir and the externalBin share a directory, so the explicit
//     LD_LIBRARY_PATH is still required).
//   src-tauri/llama-libs/.cache/<triple>/            (git-ignored download
//     cache; keeps re-staging offline once the archive has been fetched once)
//
// Each per-triple lib list below was derived by actually downloading b11429's
// three release assets and recursively walking `otool -L` (macOS) /
// `llvm-objdump -p` NEEDED entries (Linux ELF, Windows PE) — see the task
// report for the walk. System libraries (libc, libstdc++, CoreFoundation,
// vulkan-1.dll, libgomp.so.1, ...) are never bundled — they are either part
// of the OS/runtime (vulkan-1.dll is the GPU driver's Vulkan loader; ggml
// dlopen's ggml-vulkan.dll and falls back to CPU without it) or, on Linux,
// assumed present the way llama.cpp's own release tarball itself assumes
// them (it ships none of them either). The ggml-cpu-<arch>.dll/.so variants
// and ggml-vulkan.dll are never imported by any binary's import/NEEDED
// table — ggml dlopen's them at runtime via its backend registry — so
// they're hardcoded here instead of discovered by static linkage analysis.
//
// MSVCP140.dll, VCRUNTIME140.dll and VCRUNTIME140_1.dll ARE bundled app-local
// on the Windows triple (see `copyWindowsCrtRuntime` below): they are not
// part of Windows 10/11 (only the UCRT `api-ms-win-crt-*` ships), and without
// the VC++ 2015-2022 redistributable installed the engine can't start.
// Microsoft permits app-local redistribution of these files as Distributable
// Code, so they ride alongside llama-server.exe like every other staged lib.
//
// Run via: `node scripts/ensure-llama-server.mjs [--force]`

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  createWriteStream,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import https from "node:https";
import { join, resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";

import { BINARIES_DIR, targetTriple } from "./sidecar-specs.mjs";
import { isStale } from "./sidecar-staleness.mjs";
import { signDevBinary } from "./macos-dev-sign.mjs";

const ROOT = resolve(import.meta.dirname, "..");
export const LIB_STAGE_ROOT = join(ROOT, "src-tauri", "llama-libs");
const CACHE_ROOT = join(LIB_STAGE_ROOT, ".cache");

const GGML_CPU_VARIANTS = [
  "alderlake",
  "cannonlake",
  "cascadelake",
  "cooperlake",
  "haswell",
  "icelake",
  "ivybridge",
  "piledriver",
  "sandybridge",
  "sapphirerapids",
  "skylakex",
  "sse42",
  "x64",
  "zen4",
];

// The one table of what each supported target triple downloads, verifies and
// stages. Asset name + sha256 come from the GitHub release asset's own
// `digest` field (`gh api repos/ggml-org/llama.cpp/releases/tags/b11429`),
// re-verified locally against the downloaded bytes before extraction.
export const LLAMA_BUILD = "b11429";
export const ASSET_MAP = {
  "aarch64-apple-darwin": {
    assetName: "llama-b11429-bin-macos-arm64.tar.gz",
    sha256: "740288ec6887be94280a5dfa25b5e23a78285cab104519e6c7e218904ee82459",
    archiveRoot: "llama-b11429",
    binaryName: "llama-server",
    // otool -L closure of llama-server, recursively, minus system frameworks.
    libs: [
      "libllama-server-impl.dylib",
      "libllama-common.0.dylib",
      "libmtmd.0.dylib",
      "libllama.0.dylib",
      "libggml.0.dylib",
      "libggml-cpu.0.dylib",
      "libggml-blas.0.dylib",
      "libggml-metal.0.dylib",
      "libggml-rpc.0.dylib",
      "libggml-base.0.dylib",
    ],
  },
  "x86_64-pc-windows-msvc": {
    assetName: "llama-b11429-bin-win-vulkan-x64.zip",
    sha256: "1bfe78ad9168b79fa02bf67f6af9f5e17a966d824d77238517f7bef12ac73b36",
    archiveRoot: null, // flat zip, no top-level dir
    binaryName: "llama-server.exe",
    // llvm-objdump -p import closure of llama-server.exe (llama-server-impl.dll
    // -> llama-common/mtmd/llama/ggml/ggml-base.dll; ggml-base.dll imports
    // libomp.dll) plus the dlopen-only ggml-vulkan.dll and the 14 ggml-cpu-*
    // microarchitecture variants ggml picks between at runtime.
    libs: [
      "llama-server-impl.dll",
      "llama-common.dll",
      "mtmd.dll",
      "llama.dll",
      "ggml.dll",
      "ggml-base.dll",
      "ggml-vulkan.dll",
      "libomp.dll",
      ...GGML_CPU_VARIANTS.map((v) => `ggml-cpu-${v}.dll`),
    ],
  },
  "x86_64-unknown-linux-gnu": {
    assetName: "llama-b11429-bin-ubuntu-x64.tar.gz",
    sha256: "f6d25dde8f51133143d1453da4fd5f73b145127177612a283bf7995957af3392",
    archiveRoot: "llama-b11429",
    binaryName: "llama-server",
    // llvm-objdump -p NEEDED closure (ELF) plus the dlopen-only ggml-cpu-*
    // variants. No vulkan backend in the ubuntu-x64 asset (CPU-only, same as
    // the Windows asset's CPU fallback tier).
    libs: [
      "libllama-server-impl.so",
      "libllama-common.so.0",
      "libmtmd.so.0",
      "libllama.so.0",
      "libggml.so.0",
      "libggml-base.so.0",
      ...GGML_CPU_VARIANTS.map((v) => `libggml-cpu-${v}.so`),
    ],
  },
};

/** Throws a clear, actionable error for a triple we don't have an asset for. */
export function resolveAsset(triple) {
  const asset = ASSET_MAP[triple];
  if (!asset) {
    const known = Object.keys(ASSET_MAP).join(", ");
    throw new Error(
      `[ensure-llama-server] no llama.cpp b11429 release asset is pinned for target triple ` +
        `"${triple}". Known triples: ${known}. Add a row to ASSET_MAP in ` +
        `scripts/ensure-llama-server.mjs (asset name + sha256 from ` +
        `\`gh api repos/ggml-org/llama.cpp/releases/tags/${LLAMA_BUILD}\`) to support it.`,
    );
  }
  return asset;
}

export function sha256OfFile(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

function outExt(triple) {
  return triple.includes("windows") ? ".exe" : "";
}

export function binaryOutPath(triple) {
  return join(BINARIES_DIR, `llama-server-${triple}${outExt(triple)}`);
}

function markerPath(triple) {
  return join(LIB_STAGE_ROOT, triple, ".staged.json");
}

/**
 * True when `triple` needs (re-)staging: never staged, the staged binary is
 * missing, the pinned asset identity (sha256) changed since the last stage,
 * or this script itself changed (sidecar-staleness.mjs's idea, simplest
 * form — no source tree to walk here, just this script's own mtime).
 */
export function needsStage(triple, { force = false } = {}) {
  if (force) return true;
  const marker = markerPath(triple);
  if (!existsSync(marker) || !existsSync(binaryOutPath(triple))) return true;
  let recorded;
  try {
    recorded = JSON.parse(readFileSync(marker, "utf8"));
  } catch {
    return true;
  }
  if (recorded.sha256 !== ASSET_MAP[triple].sha256) return true;
  return isStale(marker, [], { extraFiles: [import.meta.filename] });
}

/** Node-stdlib download with redirect following (GitHub 302s to a CDN/S3 URL). */
function download(url, destPath, redirectsLeft = 10) {
  return new Promise((res, rej) => {
    const file = createWriteStream(destPath);
    const req = https.get(
      url,
      { headers: { "User-Agent": "vysted-terminal-ensure-script" } },
      (resp) => {
        if (resp.statusCode >= 300 && resp.statusCode < 400 && resp.headers.location) {
          file.close();
          resp.resume();
          if (redirectsLeft <= 0) return rej(new Error(`too many redirects fetching ${url}`));
          return res(download(resp.headers.location, destPath, redirectsLeft - 1));
        }
        if (resp.statusCode !== 200) {
          file.close();
          resp.resume();
          return rej(new Error(`GET ${url} -> HTTP ${resp.statusCode}`));
        }
        resp.pipe(file);
        file.on("finish", () => file.close(() => res()));
      },
    );
    req.on("error", rej);
    file.on("error", rej);
  });
}

/** Extract a .tar.gz or .zip archive into `destDir` using the system `tar`
 * (Windows 10+'s built-in bsdtar handles .zip too — no separate unzip path). */
function extract(archivePath, destDir) {
  mkdirSync(destDir, { recursive: true });
  execFileSync("tar", ["-xf", archivePath, "-C", destDir], { stdio: "inherit" });
}

// The three VC++ 2015-2022 runtime DLLs llama-server.exe / its ggml DLLs
// import but Windows 10/11 doesn't ship (not bundled in ASSET_MAP's libs —
// llama.cpp's own release doesn't ship them either).
const CRT_DLLS = ["msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"];

/** Newest (by numeric dotted-version compare) entry of `dirNames`. */
export function latestVersionDir(dirNames) {
  const cmp = (a, b) => {
    const pa = a.split(".").map(Number);
    const pb = b.split(".").map(Number);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const d = (pa[i] || 0) - (pb[i] || 0);
      if (d !== 0) return d;
    }
    return 0;
  };
  return dirNames.slice().sort(cmp).pop();
}

/**
 * Finds the x64 CRT redist dir inside a Visual Studio install via vswhere,
 * e.g. `...\VC\Redist\MSVC\14.44.35112\x64\Microsoft.VC143.CRT`. Returns
 * null (never throws) when vswhere, the VC.Tools component, or the redist
 * tree isn't present — the caller falls back to System32.
 */
export function findVsCrtRedistDir() {
  const vswhere = join(
    process.env["ProgramFiles(x86)"] || "C:\\Program Files (x86)",
    "Microsoft Visual Studio",
    "Installer",
    "vswhere.exe",
  );
  if (!existsSync(vswhere)) return null;
  let installPath;
  try {
    installPath = execFileSync(
      vswhere,
      [
        "-latest",
        "-products",
        "*",
        "-requires",
        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property",
        "installationPath",
      ],
      { encoding: "utf8" },
    ).trim();
  } catch {
    return null;
  }
  if (!installPath) return null;
  const msvcRoot = join(installPath, "VC", "Redist", "MSVC");
  let versions;
  try {
    versions = readdirSync(msvcRoot).filter((name) => existsSync(join(msvcRoot, name, "x64")));
  } catch {
    return null;
  }
  if (versions.length === 0) return null;
  const x64Dir = join(msvcRoot, latestVersionDir(versions), "x64");
  const crtDir = readdirSync(x64Dir).find((name) => /^Microsoft\.VC\d+\.CRT$/i.test(name));
  return crtDir ? join(x64Dir, crtDir) : null;
}

/**
 * App-local-deploys MSVCP140/VCRUNTIME140/VCRUNTIME140_1 beside
 * llama-server.exe into `stageDir`. Source, in order: (1) a VS x64 CRT
 * redist tree found via vswhere.exe, (2) a fallback to the DLLs already
 * installed in %SystemRoot%\System32 (warns — bundles whatever runtime
 * version happens to be on this machine, not a pinned one). Throws if
 * neither has all three. A Windows build machine always has (1): the Rust
 * msvc toolchain itself requires the MSVC Build Tools.
 *
 * Only runs when actually on Windows. Nothing in this repo cross-stages the
 * Windows triple from another OS (CI stages each triple natively on its own
 * runner) — if that ever changes, this warns and skips instead of failing
 * the whole stage.
 */
export function copyWindowsCrtRuntime(stageDir) {
  const tag = "[ensure-llama-server]";
  if (process.platform !== "win32") {
    console.warn(
      `${tag} skipping app-local VC++ runtime DLLs (msvcp140/vcruntime140/vcruntime140_1) — ` +
        `staging the Windows triple from a non-Windows host. Re-run this script on Windows ` +
        `before shipping a build from here.`,
    );
    return;
  }

  const vsRedistDir = findVsCrtRedistDir();
  const system32 = join(process.env.SystemRoot || "C:\\Windows", "System32");
  let sourceDir;
  if (vsRedistDir && CRT_DLLS.every((dll) => existsSync(join(vsRedistDir, dll)))) {
    sourceDir = vsRedistDir;
  } else if (CRT_DLLS.every((dll) => existsSync(join(system32, dll)))) {
    console.warn(
      `${tag} no VS x64 CRT redist tree found via vswhere — falling back to the runtime ` +
        `already installed in ${system32}. The bundled DLLs will match whatever VC++ ` +
        `redistributable happens to be installed on this machine, not a pinned version.`,
    );
    sourceDir = system32;
  } else {
    throw new Error(
      `${tag} could not find msvcp140.dll, vcruntime140.dll and vcruntime140_1.dll in ` +
        `either a Visual Studio x64 CRT redist tree (via vswhere.exe) or ` +
        `%SystemRoot%\\System32. A Windows build machine needs the MSVC Build Tools ` +
        `("Desktop development with C++") — the same ones the Rust msvc toolchain requires.`,
    );
  }

  for (const dll of CRT_DLLS) {
    copyFileSync(join(sourceDir, dll), join(stageDir, dll));
  }
  console.log(`${tag} staged VC++ runtime DLLs from ${sourceDir}.`);
}

/**
 * Stage `triple`'s llama-server binary + shared libs. Downloads (or reuses a
 * verified cache hit), verifies sha256 BEFORE extracting (mismatch deletes
 * the bad download and throws), extracts, copies only the binary + the
 * declared lib list, signs the binary on macOS (VYSTED_SKIP_DEV_SIGN-aware,
 * handled inside signDevBinary), and writes the staleness marker.
 */
export async function stageTriple(triple, { force = false } = {}) {
  const tag = "[ensure-llama-server]";
  const asset = resolveAsset(triple);

  if (!needsStage(triple, { force })) {
    console.log(`${tag} ${triple}: llama-server present and fresh — skipping.`);
    return;
  }

  mkdirSync(CACHE_ROOT, { recursive: true });
  const archivePath = join(CACHE_ROOT, asset.assetName);

  const cacheHit = existsSync(archivePath) && sha256OfFile(archivePath) === asset.sha256;
  if (cacheHit) {
    console.log(`${tag} ${triple}: using cached ${asset.assetName} (sha256 verified).`);
  } else {
    if (existsSync(archivePath)) rmSync(archivePath, { force: true });
    const url = `https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_BUILD}/${asset.assetName}`;
    console.log(`${tag} ${triple}: downloading ${url} ...`);
    await download(url, archivePath);
    const actual = sha256OfFile(archivePath);
    if (actual !== asset.sha256) {
      rmSync(archivePath, { force: true });
      throw new Error(
        `${tag} sha256 mismatch for ${asset.assetName}: expected ${asset.sha256}, got ${actual}. ` +
          `Deleted the download; not extracting an unverified archive.`,
      );
    }
    console.log(`${tag} ${triple}: sha256 verified.`);
  }

  const extractDir = join(CACHE_ROOT, `${triple}-extracted`);
  rmSync(extractDir, { recursive: true, force: true });
  extract(archivePath, extractDir);
  const srcRoot = asset.archiveRoot ? join(extractDir, asset.archiveRoot) : extractDir;

  const stageDir = join(LIB_STAGE_ROOT, triple);
  rmSync(stageDir, { recursive: true, force: true });
  mkdirSync(stageDir, { recursive: true });

  mkdirSync(BINARIES_DIR, { recursive: true });
  const outBinary = binaryOutPath(triple);
  copyFileSync(join(srcRoot, asset.binaryName), outBinary);
  if (!triple.includes("windows")) chmodSync(outBinary, 0o755);

  for (const lib of asset.libs) {
    copyFileSync(join(srcRoot, lib), join(stageDir, lib));
  }

  if (triple.includes("windows")) {
    copyWindowsCrtRuntime(stageDir);
  }

  if (triple.includes("apple-darwin")) {
    signDevBinary(outBinary, "com.vysted.llama-server");
  }

  writeFileSync(
    markerPath(triple),
    JSON.stringify(
      { sha256: asset.sha256, assetName: asset.assetName, build: LLAMA_BUILD },
      null,
      2,
    ),
  );

  rmSync(extractDir, { recursive: true, force: true });
  console.log(
    `${tag} ${triple}: staged ${basename(outBinary)} + ${asset.libs.length} shared libs.`,
  );
}

async function main() {
  const force = process.argv.includes("--force");
  const triple = targetTriple();
  await stageTriple(triple, { force });
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  main().catch((err) => {
    console.error(err.message || err);
    process.exit(1);
  });
}
