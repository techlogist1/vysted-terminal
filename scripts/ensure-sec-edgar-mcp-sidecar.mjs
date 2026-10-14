// scripts/ensure-sec-edgar-mcp-sidecar.mjs
//
// Idempotently builds the sec-edgar-mcp subprocess into a single-file binary
// that the Tauri Rust core spawns, in its own venv. The recipe lives in
// sidecar-specs.mjs.
//
// Output: src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-<target-triple>[.exe]
// Run via: node scripts/ensure-sec-edgar-mcp-sidecar.mjs [--force]

import { SIDECAR_SPECS, buildSidecar } from "./sidecar-specs.mjs";

buildSidecar(
  SIDECAR_SPECS.find((s) => s.name === "vysted-sec-edgar-mcp-sidecar"),
  { force: process.argv.includes("--force") },
);
