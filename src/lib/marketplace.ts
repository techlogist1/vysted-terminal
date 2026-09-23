/**
 * The marketplace catalog — the single registry of every compiled-in plugin and
 * its host-side metadata (FR-050). This is the "primary extensibility model":
 * data providers, panels, and agents are ALL entries here under one
 * install/enable/configure/remove lifecycle (driven by `useMarketplaceStore`
 * over the plugin runtime).
 *
 * Static-import note: Next.js static export can't dynamically import arbitrary
 * plugin code, so the available plugins are compiled into the host build (each
 * imported here) and the marketplace governs their install/enable STATE — first
 * party entries pre-installed + enabled. Genuinely-external
 * (never-compiled) plugins attach over the stdio-MCP framework path (FR-025);
 * that runtime-load is the operator-eyeball gap, documented in the build report.
 */

import type { FunctionComponent } from "react";

import { examplePlugin } from "../../plugins/example";
import exampleManifest from "../../plugins/example/manifest.json";
import { openbbMcpPlugin } from "../../plugins/openbb-mcp";
import openbbMcpManifest from "../../plugins/openbb-mcp/manifest.json";
import { lensesPlugin } from "../../plugins/vysted-lenses";
import lensesManifest from "../../plugins/vysted-lenses/manifest.json";
import { newsPlugin } from "../../plugins/vysted-news";
import newsManifest from "../../plugins/vysted-news/manifest.json";
import { yfinancePlugin } from "../../plugins/yfinance";
import yfinanceManifest from "../../plugins/yfinance/manifest.json";

import type { DiscoveredPlugin } from "@/lib/plugin-runtime";
import type { MarketplaceEntry } from "../../types/marketplace";
import type { PluginManifest } from "../../types/plugin-runtime";
import type { VystedPlugin as Plugin } from "../../types/plugin";

/** A catalog row: the marketplace metadata + the loadable plugin + any panels. */
export interface CatalogRow {
  entry: MarketplaceEntry;
  discovered: DiscoveredPlugin;
  panelComponents?: Record<string, FunctionComponent>;
}

function row(
  entry: MarketplaceEntry,
  manifest: unknown,
  instance: Plugin,
  panelComponents?: Record<string, FunctionComponent>,
): CatalogRow {
  return {
    entry,
    discovered: { manifest: manifest as PluginManifest, instance },
    panelComponents,
  };
}

/**
 * The marketplace catalog, keyed by plugin id. First-party entries are
 * pre-installed (bundled + enabled by default → first run is populated, FR-032).
 */
export const CATALOG_ROWS: CatalogRow[] = [
  // --- First-party, pre-installed (the populated starter set) ---------------
  row(
    {
      pluginId: "vysted-yfinance",
      name: "Yahoo Finance (keyless equities)",
      category: "data",
      description:
        "The no-key equity + fundamentals default. Works out of the box, zero credentials.",
      version: "1.0.0",
      author: "Vysted",
      icon: "line-chart",
      preinstalled: true,
      secretNamespace: "plugin",
      standardModelKeys: ["quote", "ohlcv", "fundamentals"],
      preferenceRank: 50,
    },
    yfinanceManifest,
    yfinancePlugin,
  ),
  row(
    {
      pluginId: "openbb-mcp",
      name: "OpenBB (fundamentals + macro)",
      category: "data",
      description: "Richer fundamentals + macro series via the bundled OpenBB MCP subprocess.",
      version: (openbbMcpManifest as PluginManifest).version,
      author: "OpenBB",
      icon: "database",
      preinstalled: true,
      secretNamespace: "plugin",
      standardModelKeys: ["fundamentals", "macro_series"],
      preferenceRank: 10,
    },
    openbbMcpManifest,
    openbbMcpPlugin,
  ),
  row(
    {
      pluginId: "vysted-lenses",
      name: "Vysted Lenses (agent pack)",
      category: "agent",
      description: "A first-party agent pack — the Quant Tutor lens. The reference agent plugin.",
      version: "1.0.0",
      author: "Vysted",
      icon: "graduation-cap",
      preinstalled: true,
    },
    lensesManifest,
    lensesPlugin,
  ),
  row(
    {
      pluginId: "vysted-news",
      name: "Market News (RSS + optional NewsAPI)",
      category: "data",
      description:
        "Sentiment-scored, symbol-tagged market news. Keyless over RSS out of the box; add a BYOK NewsAPI key for NewsAPI breadth.",
      version: "1.0.0",
      author: "Vysted",
      icon: "newspaper",
      preinstalled: true,
      secretNamespace: "plugin",
      // The NewsAPI key is OPTIONAL — RSS works with no key (FR-034 "needs no
      // key" opt-out). Supplying it upgrades the feed; the hub renders this
      // form generically (SC-007: zero per-source UI), the key is stored under
      // plugin-secret:vysted-news:newsapi_key, and the /news fetch sends it as
      // the X-Vysted-Newsapi-Key header.
      credentialFields: [
        {
          key: "newsapi_key",
          label: "NewsAPI key (optional)",
          type: "password",
          secret: true,
          required: false,
          placeholder: "RSS works without a key",
          help: "Optional. Adds NewsAPI breadth on top of the keyless RSS feeds.",
        },
      ],
      website: "https://newsapi.org/register",
      instructions:
        "News works with no key over RSS. For NewsAPI breadth, register a free key at newsapi.org and paste it here.",
      standardModelKeys: ["news"],
      preferenceRank: 50,
    },
    newsManifest,
    newsPlugin,
  ),
  row(
    {
      pluginId: "vysted-example",
      name: "Example data source",
      category: "data",
      description: "A pedagogical data-source plugin that proves the contract end-to-end.",
      version: (exampleManifest as PluginManifest).version,
      author: "Vysted",
      icon: "box",
      preinstalled: true,
    },
    exampleManifest,
    examplePlugin,
  ),
];

/** The catalog rows keyed by plugin id, for O(1) lookup. */
export const CATALOG_BY_ID: Record<string, CatalogRow> = Object.fromEntries(
  CATALOG_ROWS.map((r) => [r.entry.pluginId, r]),
);

/** Just the marketplace metadata (what the marketplace UI lists). */
export const MARKETPLACE_CATALOG: MarketplaceEntry[] = CATALOG_ROWS.map((r) => r.entry);
