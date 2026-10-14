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
// MSVCP140.dll, vulkan-1.dll, libgomp.so.1, ...) are never bundled — they are
// either part of the OS/runtime or, on Linux, assumed present the way
// llama.cpp's own release tarball itself assumes them (it ships none of
// them either). The ggml-cpu-<arch>.dll/.so variants and ggml-vulkan.dll are
// never imported by any binary's import/NEEDED table — ggml dlopen's them at
// runtime via its backend registry — so they're hardcoded here instead of
// discovered by static linkage analysis.
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
