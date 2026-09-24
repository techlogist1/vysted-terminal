// @vitest-environment node
import { describe, expect, it, vi } from "vitest";

// Every binary "exists" and is fresh, so buildSidecar only runs its staleness
// check; rustc is stubbed so no toolchain is needed.
vi.mock("node:fs", async (orig) => ({ ...(await orig()), existsSync: () => true }));
vi.mock("node:child_process", async (orig) => ({
  ...(await orig()),
  execSync: () => "host: test-triple\n",
}));
vi.mock("./sidecar-staleness.mjs", () => ({ isStale: vi.fn(() => false), assertFresh: vi.fn() }));

const { isStale, assertFresh } = await import("./sidecar-staleness.mjs");
const { SIDECAR_SPECS, assertAllFresh, buildSidecar } = await import("./sidecar-specs.mjs");

describe("freshness gate vs builder (R15-RELEASE-006)", () => {
  it("the smoke-test gate checks each binary against the builder's exact source set", () => {
    for (const spec of SIDECAR_SPECS) buildSidecar(spec);
    assertAllFresh();

    expect(isStale.mock.calls).toHaveLength(SIDECAR_SPECS.length);
    expect(assertFresh.mock.calls).toHaveLength(SIDECAR_SPECS.length);
    SIDECAR_SPECS.forEach((spec, i) => {
      const [builtPath, builtDirs, builtOpts] = isStale.mock.calls[i];
      const [gatePath, gateDirs, gateOpts] = assertFresh.mock.calls[i];
      expect(gatePath).toBe(builtPath);
      expect(builtPath).toContain(`${spec.name}-test-triple`);
      expect(gateDirs).toBe(builtDirs);
      expect(gateOpts).toBe(builtOpts);
    });
  });
});
