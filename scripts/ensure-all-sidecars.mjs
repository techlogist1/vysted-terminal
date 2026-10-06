// scripts/ensure-all-sidecars.mjs
//
// Orchestrator that builds every sidecar in SIDECAR_SPECS, in order. Wired into
// tauri.conf.json's beforeDevCommand / beforeBuildCommand AND the CI workflows,
// so a clean checkout builds all of them before `tauri build` resolves the
// `bundle.externalBin` references (pre-v0.7.0 only the main sidecar was wired
// and CI broke on every clean checkout).
//
// Each build is a fast no-op when its binary is present and fresh, unless
// --force is passed.
//
// Run via: `node scripts/ensure-all-sidecars.mjs [--force]`
// Or:      `pnpm sidecars:build` (passes --force)

import { SIDECAR_SPECS, buildSidecar } from "./sidecar-specs.mjs";

const force = process.argv.includes("--force");

for (const spec of SIDECAR_SPECS) {
  console.log(`[ensure-all-sidecars] → ${spec.name}${force ? " --force" : ""}`);
  try {
    buildSidecar(spec, { force });
  } catch (err) {
    console.error(`[ensure-all-sidecars] ${spec.name} failed: ${err.message}; aborting.`);
    process.exit(1);
  }
}

console.log("[ensure-all-sidecars] all sidecars present.");
