// scripts/ensure-openbb-mcp-sidecar.mjs
//
// Idempotently builds the openbb-mcp subprocess into a single-file binary that
// the Tauri Rust core spawns. It has its own venv because openbb-core pins
// fastapi/uvicorn below the main sidecar's pins. The recipe lives in
// sidecar-specs.mjs.
//
// Output: src-tauri/binaries/vysted-openbb-mcp-sidecar-<target-triple>[.exe]
// Run via: node scripts/ensure-openbb-mcp-sidecar.mjs [--force]

import { SIDECAR_SPECS, buildSidecar } from "./sidecar-specs.mjs";

buildSidecar(
  SIDECAR_SPECS.find((s) => s.name === "vysted-openbb-mcp-sidecar"),
  { force: process.argv.includes("--force") },
);
