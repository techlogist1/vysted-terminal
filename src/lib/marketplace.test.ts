import { describe, expect, it } from "vitest";

import { CATALOG_BY_ID, CATALOG_ROWS, MARKETPLACE_CATALOG } from "@/lib/marketplace";
import { hostSatisfies } from "@/lib/plugin-runtime";
import { HOST_VERSION } from "@/lib/plugin-bootstrap";

describe("marketplace catalog (FR-050/SC-013)", () => {
  it("ships pre-installed plugins across multiple categories — one lifecycle (SC-013)", () => {
    const preinstalled = MARKETPLACE_CATALOG.filter((e) => e.preinstalled);
    // Data + agent first-party plugins prove the ONE install/enable/configure
    // lifecycle spans categories. (R10: the bundled panel-category exemplar was
    // removed; the panel capability still lives in the plugin contract
    // `contributesPanels` and the example plugin proves it, but no bundled
    // marketplace entry now carries category "panel".)
    expect(preinstalled.some((e) => e.category === "data")).toBe(true);
    expect(preinstalled.some((e) => e.category === "agent")).toBe(true);
    expect(new Set(preinstalled.map((e) => e.category)).size).toBeGreaterThanOrEqual(2);
    // yfinance is the keyless data default, pre-installed (works out of the box).
    expect(CATALOG_BY_ID["vysted-yfinance"]?.entry.preinstalled).toBe(true);
    expect(CATALOG_BY_ID["vysted-yfinance"]?.entry.credentialFields ?? []).toHaveLength(0);
  });

  it("every catalog row is runtime-loadable: manifest id+version match the instance, host satisfies", () => {
    for (const row of CATALOG_ROWS) {
      expect(row.discovered.manifest.id).toBe(row.entry.pluginId);
      expect(row.discovered.instance.pluginId).toBe(row.entry.pluginId);
      // checkCompatibility rejects a load if these diverge.
      expect(row.discovered.manifest.version).toBe(row.discovered.instance.version);
      expect(hostSatisfies(HOST_VERSION, row.discovered.manifest.requiredHostVersion)).toBe(true);
    }
  });

  it("credential fields are all marked secret — keychain-only, never plaintext (FR-036)", () => {
    const withCreds = MARKETPLACE_CATALOG.filter((e) => (e.credentialFields ?? []).length > 0);
    expect(withCreds.length).toBeGreaterThan(0);
    for (const entry of withCreds) {
      expect(entry.secretNamespace).toBe("plugin");
      for (const field of entry.credentialFields ?? []) {
        expect(field.secret).toBe(true);
      }
    }
  });
});
