import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// R15-CODE-FRONTEND-038: export-artifact.ts's dynamic import of sidecar-client
// was ineffective — 40+ other modules already import it statically, so Vite
// could never split it into its own chunk (Vite prints
// [INEFFECTIVE_DYNAMIC_IMPORT] and the module still lands in the main bundle).
// Source-scan regression: a static import must be present and no dynamic
// `import("@/lib/sidecar-client")` may return.
describe("export-artifact.ts sidecar-client import", () => {
  const source = readFileSync(path.resolve(__dirname, "export-artifact.ts"), "utf-8");

  it("imports sidecar-client statically", () => {
    expect(source).toMatch(/^import \{ getSidecarBaseUrl \} from "@\/lib\/sidecar-client";$/m);
  });

  it("never dynamically imports sidecar-client", () => {
    expect(source).not.toMatch(/import\(["']@\/lib\/sidecar-client["']\)/);
  });
});
