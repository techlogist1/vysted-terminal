// scripts/ensure-sidecar.mjs
//
// Idempotently builds the Python sidecar into a single-file binary that Tauri
// picks up via `bundle.externalBin`. Fast no-op when the binary is present and
// newer than its source, unless --force. The recipe lives in sidecar-specs.mjs.
//
// Output: src-tauri/binaries/vysted-sidecar-<target-triple>[.exe]

import { SIDECAR_SPECS, buildSidecar } from "./sidecar-specs.mjs";

buildSidecar(
  SIDECAR_SPECS.find((s) => s.name === "vysted-sidecar"),
  { force: process.argv.includes("--force") },
);
