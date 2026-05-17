// scripts/ensure-all-sidecars.mjs
//
// Orchestrator that invokes every per-sidecar ensure script in sequence.
// Wired into tauri.conf.json's beforeDevCommand / beforeBuildCommand AND
// into the CI workflows so a clean checkout builds all three sidecars
// before `tauri build` resolves the `bundle.externalBin` references.
//
// Pre-v0.7.0 only `ensure-sidecar.mjs` was wired; `ensure-openbb-mcp-
// sidecar.mjs` and `ensure-sec-edgar-mcp-sidecar.mjs` were one-off
// scripts the operator ran manually. That worked locally (cached
// binaries in src-tauri/binaries/) but broke CI on every clean checkout
// with "resource path 'binaries/vysted-{openbb,sec-edgar}-mcp-sidecar-
// <triple>' doesn't exist" since the v0.4.0 + v0.6.0 sidecars landed.
//
// Each per-sidecar script is idempotent — fast no-op when the binary
// already exists, unless --force is passed. This orchestrator forwards
// --force to each child.
//
// Run via: `node scripts/ensure-all-sidecars.mjs [--force]`
// Or:      `pnpm sidecars:build` (passes --force)

import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const FORCE = process.argv.includes("--force");

const SCRIPTS = [
  "scripts/ensure-sidecar.mjs",
  "scripts/ensure-openbb-mcp-sidecar.mjs",
  "scripts/ensure-sec-edgar-mcp-sidecar.mjs",
];

for (const script of SCRIPTS) {
  const args = [script];
  if (FORCE) args.push("--force");
  console.log(`[ensure-all-sidecars] → node ${args.join(" ")}`);
  const result = spawnSync("node", args, { stdio: "inherit", cwd: ROOT });
  if (result.status !== 0) {
    console.error(
      `[ensure-all-sidecars] ${script} failed with exit code ${result.status}; aborting.`,
    );
    process.exit(result.status ?? 1);
  }
}

console.log("[ensure-all-sidecars] all sidecars present.");
