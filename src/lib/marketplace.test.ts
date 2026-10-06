import { afterEach, describe, expect, it, vi } from "vitest";

const sidecarGetMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, sidecarGet: sidecarGetMock };
});

import {
  CATALOG_BY_ID,
  CATALOG_ROWS,
  fetchDataSourceDeclarations,
  INDIA_DATA_LANES,
  MARKETPLACE_CATALOG,
  REGISTRY_PROVIDER_ID,
} from "@/lib/marketplace";
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

describe("fetchDataSourceDeclarations (C19, R15-CODE-PLATFORM-072/R15-DATA-077)", () => {
  afterEach(() => {
    sidecarGetMock.mockReset();
  });

  it("maps the wire's snake_case fields to the frontend contract, keyed by provider id", async () => {
    sidecarGetMock.mockResolvedValue({
      providers: [
        {
          id: "yfinance",
          keys: ["quote", "ohlcv", "fundamentals"],
          rank: 50,
          available: true,
          asset_classes: ["equity"],
          region: [],
        },
        {
          id: "nse_direct",
          keys: ["quote", "ohlcv"],
          rank: 15,
          available: true,
          asset_classes: ["equity"],
          region: ["IN"],
        },
      ],
    });
    const declarations = await fetchDataSourceDeclarations();
    expect(sidecarGetMock).toHaveBeenCalledWith("/data-sources");
    expect(declarations.yfinance).toEqual({
      id: "yfinance",
      keys: ["quote", "ohlcv", "fundamentals"],
      rank: 50,
      available: true,
      assetClasses: ["equity"],
      region: [],
    });
    // India lane fixture round-trips too — the panel's "India data lanes"
    // section renders directly off this shape.
    expect(declarations.nse_direct).toEqual({
      id: "nse_direct",
      keys: ["quote", "ohlcv"],
      rank: 15,
      available: true,
      assetClasses: ["equity"],
      region: ["IN"],
    });
  });

  it("degrades to an empty map on a fetch failure — never a stale hand row", async () => {
    sidecarGetMock.mockRejectedValue(new Error("offline"));
    await expect(fetchDataSourceDeclarations()).resolves.toEqual({});
  });

  it("REGISTRY_PROVIDER_ID only maps plugins genuinely backed by provider_registry", () => {
    expect(REGISTRY_PROVIDER_ID["vysted-yfinance"]).toBe("yfinance");
    expect(REGISTRY_PROVIDER_ID["openbb-mcp"]).toBe("openbb-mcp");
    // News/agent packs route through their own MCP/RSS surface, not the resolver.
    expect(REGISTRY_PROVIDER_ID["vysted-news"]).toBeUndefined();
    expect(REGISTRY_PROVIDER_ID["vysted-lenses"]).toBeUndefined();
  });

  it("declares the three India keyless lanes with a stable id (matches the resolver)", () => {
    expect(INDIA_DATA_LANES.map((l) => l.id)).toEqual(["nse_direct", "nse", "bse"]);
  });
});
