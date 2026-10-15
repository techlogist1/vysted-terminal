// scripts/release/assemble-release.mjs
//
// Assembles a GitHub release's upload set from the three OS build jobs'
// raw `tauri build` output: finds the dmg (+ updater .app.tar.gz/.sig), the
// NSIS .exe/.sig and the optional AppImage/.sig, copies each into
// space-free "versioned" names (GitHub Releases rewrites spaces in asset
// filenames on upload, which would silently break a latest.json URL built
// ahead of time) plus the contract's stable names, and writes latest.json
// (Tauri v2 updater format) + SHA256SUMS.txt over the whole assembled set.
//
// Stdlib only. CLI: node assemble-release.mjs --tag v0.10.0
//   --artifacts-dir <dir with the three downloaded build-artifact trees>
//   [--repo owner/repo] [--notes-file path] [--out-dir dir]
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  copyFileSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { join, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const DEFAULT_REPO = "techlogist1/vysted-terminal";
const DEFAULT_TAURI_CONF = fileURLToPath(
  new URL("../../src-tauri/tauri.conf.json", import.meta.url),
);

/** "v0.10.0" -> "0.10.0"; a tag with no leading "v<digit>" passes through unchanged. */
export function versionFromTag(tag) {
  return /^v\d/.test(tag) ? tag.slice(1) : tag;
}

/** GitHub Releases rewrites whitespace in uploaded asset names — replace it ourselves first. */
export function sanitizeName(name) {
  return name.replace(/\s+/g, "-");
}

export function sha256File(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

/**
 * All file paths under `dir`, recursively, skipping macOS app-bundle directories
 * (`.app`) and anything else that is itself a bundle package, not a loose artifact.
 */
export function walkFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name.endsWith(".app") || entry.name.endsWith(".framework")) continue;
      out.push(...walkFiles(full));
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
  return out;
}

/**
 * Finds the per-platform artifact set in a flat list of file paths.
 * Throws for a missing required one; the AppImage pair is optional (its
 * build job is `continue-on-error`, so a red Linux build never blocks).
 */
export function locateArtifacts(files) {
  const find = (re) => files.find((f) => re.test(basename(f)));
  const sigOf = (path) => (path ? files.find((f) => f === `${path}.sig`) : undefined);

  const dmg = find(/\.dmg$/i);
  const macTarGz = find(/\.app\.tar\.gz$/i);
  const macSig = sigOf(macTarGz);
  const winExe = find(/-setup\.exe$/i);
  const winSig = sigOf(winExe);
  const appImage = find(/\.appimage$/i);
  const appImageSig = sigOf(appImage);

  const missing = [];
  if (!dmg) missing.push("macOS .dmg");
  if (!macTarGz) missing.push("macOS updater .app.tar.gz");
  if (macTarGz && !macSig) missing.push(`${basename(macTarGz)}.sig`);
  if (!winExe) missing.push("Windows -setup.exe");
  if (winExe && !winSig) missing.push(`${basename(winExe)}.sig`);
  if (appImage && !appImageSig) missing.push(`${basename(appImage)}.sig`);
  if (missing.length > 0) {
    throw new Error(`assemble-release: missing required artifact(s): ${missing.join(", ")}`);
  }

  return { dmg, macTarGz, macSig, winExe, winSig, appImage, appImageSig };
}

function parseArgs(argv) {
  const args = { repo: DEFAULT_REPO };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    args[key.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = argv[i + 1];
    i += 1;
  }
  return args;
}

/**
 * Copies `srcPath` into `outDir` under both its space-free versioned name and
 * (when given) a fixed stable name. Returns the versioned basename (the one
 * latest.json's URLs are built from).
 */
function copyAsset(srcPath, outDir, stableName) {
  const versionedName = sanitizeName(basename(srcPath));
  copyFileSync(srcPath, join(outDir, versionedName));
  if (stableName) copyFileSync(srcPath, join(outDir, stableName));
  return versionedName;
}

export async function assemble({
  tag,
  artifactsDir,
  repo = DEFAULT_REPO,
  notesFile,
  outDir,
  tauriConf = DEFAULT_TAURI_CONF,
}) {
  if (!tag) throw new Error("assemble-release: --tag is required");
  if (!artifactsDir) throw new Error("assemble-release: --artifacts-dir is required");
  const version = versionFromTag(tag);
  // latest.json's version drives the updater's comparison: a tag that disagrees with the version the
  // binaries were built with makes every install loop on "update available" (or never see one).
  const builtVersion = JSON.parse(readFileSync(tauriConf, "utf8")).version;
  if (builtVersion !== version) {
    throw new Error(
      `assemble-release: tag ${tag} (version ${version}) does not match tauri.conf.json version ${builtVersion}; bump every version source before tagging`,
    );
  }
  const resolvedOutDir = outDir ?? join(artifactsDir, "assembled");
  mkdirSync(resolvedOutDir, { recursive: true });

  const files = walkFiles(artifactsDir);
  const { dmg, macTarGz, macSig, winExe, winSig, appImage, appImageSig } = locateArtifacts(files);
  // The .app.tar.gz carries no version in its name; the dmg, setup.exe and AppImage do.
  const unversioned = [dmg, winExe, appImage]
    .filter(Boolean)
    .map((f) => basename(f))
    .filter((name) => !name.includes(`_${version}_`));
  if (unversioned.length > 0) {
    throw new Error(
      `assemble-release: built asset(s) do not carry version ${version}: ${unversioned.join(", ")}`,
    );
  }

  const macTarGzVersioned = copyAsset(macTarGz, resolvedOutDir);
  copyAsset(macSig, resolvedOutDir);
  copyAsset(dmg, resolvedOutDir, "Vysted-Terminal-macOS-AppleSilicon.dmg");
  const winExeVersioned = copyAsset(winExe, resolvedOutDir);
  copyAsset(winSig, resolvedOutDir);
  copyAsset(winExe, resolvedOutDir, "Vysted-Terminal-Windows-x64-Setup.exe");

  let appImageVersioned;
  if (appImage) {
    appImageVersioned = copyAsset(appImage, resolvedOutDir);
    copyAsset(appImageSig, resolvedOutDir);
    copyAsset(appImage, resolvedOutDir, "Vysted-Terminal-Linux-x86_64.AppImage");
  }

  const resolvedNotesFile = notesFile ?? `docs/RELEASE_NOTES_v${version}.md`;
  const notes = existsSync(resolvedNotesFile)
    ? readFileSync(resolvedNotesFile, "utf8")
    : "See the GitHub release page for details.";

  const assetUrl = (name) => `https://github.com/${repo}/releases/download/${tag}/${name}`;
  const platforms = {
    "darwin-aarch64": {
      signature: readFileSync(macSig, "utf8"),
      url: assetUrl(macTarGzVersioned),
    },
    "windows-x86_64": {
      signature: readFileSync(winSig, "utf8"),
      url: assetUrl(winExeVersioned),
    },
  };
  if (appImage) {
    platforms["linux-x86_64"] = {
      signature: readFileSync(appImageSig, "utf8"),
      url: assetUrl(appImageVersioned),
    };
  }

  const latestJson = {
    version,
    notes,
    pub_date: new Date().toISOString(),
    platforms,
  };
  const latestJsonPath = join(resolvedOutDir, "latest.json");
  writeFileSync(latestJsonPath, `${JSON.stringify(latestJson, null, 2)}\n`);

  const assetNames = readdirSync(resolvedOutDir).sort();
  const sumsPath = join(resolvedOutDir, "SHA256SUMS.txt");
  const sums = assetNames
    .filter((name) => name !== "SHA256SUMS.txt")
    .map((name) => `${sha256File(join(resolvedOutDir, name))}  ${name}`)
    .join("\n");
  writeFileSync(sumsPath, `${sums}\n`);

  return { outDir: resolvedOutDir, latestJsonPath, sumsPath, files: readdirSync(resolvedOutDir) };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const result = await assemble(args);
  console.log(`[assemble-release] wrote ${result.files.length} files to ${result.outDir}`);
  for (const f of result.files.sort()) console.log(`  ${f}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error("[assemble-release] failed:", err.message);
    process.exit(1);
  });
}
