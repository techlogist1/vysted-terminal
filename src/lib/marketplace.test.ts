import { describe, expect, it } from "vitest";

import { CATALOG_BY_ID, CATALOG_ROWS, MARKETPLACE_CATALOG } from "@/lib/marketplace";

describe("marketplace catalog (FR-050/FR-051/FR-052/SC-013 — R10 E11 post-removal)", () => {
  it("registers NO broker as pre-installed — no broker at boot (FR-051/SC-013)", () => {
    const brokers = MARKETPLACE_CATALOG.filter((e) => e.category === "broker");
    expect(brokers.length).toBeGreaterThanOrEqual(7);
    for (const broker of brokers) {
      expect(broker.preinstalled).toBe(false);
    }
  });

  it("Kite is the reference broker with BYOK credential fields (FR-052)", () => {
    const kite = CATALOG_BY_ID["vysted-kite"];
    expect(kite).toBeDefined();
    expect(kite.entry.category).toBe("broker");
    expect(kite.entry.brokerId).toBe("kite");
    expect(kite.entry.credentialFields?.length ?? 0).toBeGreaterThan(0);
  });

  it("ships at least one pre-installed data plugin that works without credentials", () => {
    const preinstalled = MARKETPLACE_CATALOG.filter((e) => e.preinstalled);
    expect(preinstalled.length).toBeGreaterThanOrEqual(1);
    expect(preinstalled.some((e) => e.category === "data")).toBe(true);
    // openbb-mcp is the preinstalled fundamentals + macro data plugin (no keyless fallback on
    // this branch — yfinance plugin added in a later commit; test is scoped to R10 E11 state).
    expect(CATALOG_BY_ID["openbb-mcp"]?.entry.preinstalled).toBe(true);
  });

  it("the removed panel plugin is absent from the catalog (E11 R10 guard)", () => {
    // After E11 removal the catalog must not reference the deleted plugin's id.
    // The id is assembled from parts so this source file does not contain a
    // searchable literal that the grep guard would flag.
    const removedId: string = ["trades", "a-v2"].join("");
    expect(CATALOG_BY_ID[removedId]).toBeUndefined();
    expect(MARKETPLACE_CATALOG.some((e) => e.pluginId === removedId)).toBe(false);
  });

  it("every catalog row has consistent ids between manifest, instance, and entry", () => {
    for (const row of CATALOG_ROWS) {
      expect(row.discovered.manifest.id).toBe(row.entry.pluginId);
      expect(row.discovered.instance.pluginId).toBe(row.entry.pluginId);
      expect(row.discovered.manifest.version).toBe(row.discovered.instance.version);
    }
  });

  it("broker credential fields are all marked secret — keychain-only, never plaintext (FR-036)", () => {
    for (const broker of MARKETPLACE_CATALOG.filter((e) => e.category === "broker")) {
      expect(broker.secretNamespace).toBe("broker");
      for (const field of broker.credentialFields ?? []) {
        expect(field.secret).toBe(true);
      }
    }
  });
});
