// scripts/sidecar-staleness.mjs
//
// Shared staleness detection for the three `ensure-*-sidecar.mjs` build
// scripts. The build trap (Phase 9.5 finding S0-2): each ensure script's
// guard was `if (existsSync(outPath) && !FORCE) skip` — it only checked that
// the binary EXISTS, never whether it was STALE relative to its source. Because
// `tauri.conf.json`'s `beforeBuildCommand` runs `ensure-all-sidecars` WITHOUT
// `--force`, a build could silently re-bundle a sidecar binary older than
// HEAD's sidecar source and fake a green pass (this produced the false
// #91/#65 regression failures in the Phase 9.5 re-audit).
//
// Fix: make the no-op staleness-aware. `isStale(binary, sourceDirs)` returns
// true when any tracked source file under `sourceDirs` is newer than the built
// binary (or the binary is missing). The ensure scripts rebuild when stale even
// without `--force`, so a source edit always reaches the bundle; a no-change run
// stays a fast no-op so `pnpm tauri dev` ergonomics are preserved.
//
// `assertFresh(...)` is the complementary CI gate: it throws when a binary
// predates its source, so a freshness violation fails loudly rather than
// shipping silently (belt-and-suspenders with the auto-rebuild).

import { statSync, readdirSync } from "node:fs";
import { join } from "node:path";

// Build scratch / cache / venv dirs that never affect the shipped binary.
const IGNORE_DIRS = new Set([
  ".venv",
  "build",
  "dist",
  "__pycache__",
  ".pytest_cache",
  ".ruff_cache",
  ".mypy_cache",
  "node_modules",
  ".git",
]);

// File kinds that, when edited, can change the built binary: Python source,
// dependency manifests, packaging config, and bundled data (JSON universes,
// agent definitions, CSVs).
const SOURCE_EXT = /\.(py|txt|toml|cfg|ini|json|csv)$/i;

/**
 * Walk `dir` recursively and return the newest mtime (ms) of any file matching
 * SOURCE_EXT. `excludeDirs` is a list of absolute paths to prune (used to keep
 * the main sidecar's walk from descending into the MCP subprocess dirs, which
 * have their own ensure scripts).
 */
function newestMtime(dir, excludeDirs, acc) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return acc.t; // unreadable / missing dir contributes nothing
  }
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue;
      if (excludeDirs.includes(full)) continue;
      newestMtime(full, excludeDirs, acc);
    } else if (entry.isFile() && SOURCE_EXT.test(entry.name)) {
      const m = statSync(full).mtimeMs;
      if (m > acc.t) acc.t = m;
    }
  }
  return acc.t;
}

/**
 * Newest source mtime (ms) across `sourceDirs` plus any `extraFiles`
 * (e.g. the ensure script itself + this module — editing the build recipe
 * must also invalidate the binary).
 */
export function newestSourceMtime(sourceDirs, { excludeDirs = [], extraFiles = [] } = {}) {
  const dirs = Array.isArray(sourceDirs) ? sourceDirs : [sourceDirs];
  const acc = { t: 0 };
  for (const d of dirs) newestMtime(d, excludeDirs, acc);
  for (const f of extraFiles) {
    try {
      const m = statSync(f).mtimeMs;
      if (m > acc.t) acc.t = m;
    } catch {
      /* missing extra file contributes nothing */
    }
  }
  return acc.t;
}

/**
 * True when `outPath` is missing or older than the newest source file —
 * i.e. a rebuild is required even without `--force`.
 */
export function isStale(outPath, sourceDirs, opts = {}) {
  let binMtime;
  try {
    binMtime = statSync(outPath).mtimeMs;
  } catch {
    return true; // not built yet
  }
  return newestSourceMtime(sourceDirs, opts) > binMtime;
}

/**
 * CI gate: throw a descriptive error when `outPath` predates its source.
 * Used by `smoke-test-sidecars.mjs` so a stale-bundle slip fails loudly.
 */
export function assertFresh(outPath, sourceDirs, opts = {}) {
  let binMtime;
  try {
    binMtime = statSync(outPath).mtimeMs;
  } catch {
    throw new Error(`sidecar binary missing: ${outPath} — run \`pnpm sidecars:build\``);
  }
  const newest = newestSourceMtime(sourceDirs, opts);
  if (newest > binMtime) {
    const ageS = ((newest - binMtime) / 1000).toFixed(0);
    throw new Error(
      `STALE SIDECAR: ${outPath} predates its source by ~${ageS}s. ` +
        `A source file changed after the binary was built. ` +
        `Run \`pnpm sidecars:build\` (force-rebuild) before bundling.`,
    );
  }
}
