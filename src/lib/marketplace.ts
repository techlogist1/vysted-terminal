/**
 * The marketplace catalog — the single registry of every compiled-in plugin and
 * its host-side metadata (FR-050). This is the "primary extensibility model":
 * brokers, data providers, panels, and agents are ALL entries here under one
 * install/enable/configure/remove lifecycle (driven by `useMarketplaceStore`
 * over the plugin runtime).
 *
 * Static-import note: Next.js static export can't dynamically import arbitrary
 * plugin code, so the available plugins are compiled into the host build (each
 * imported here) and the marketplace governs their install/enable STATE — first
 * party entries pre-installed + enabled, the seven broker plugins available but
 * NOT pre-installed (FR-051: no broker registered at boot). Genuinely-external
 * (never-compiled) plugins attach over the stdio-MCP framework path (FR-025);
 * that runtime-load is the operator-eyeball gap, documented in the build report.
 */

import type { FunctionComponent } from "react";

import { examplePlugin } from "../../plugins/example";
import exampleManifest from "../../plugins/example/manifest.json";
import alpacaPlugin from "../../plugins/brokers/alpaca";
import alpacaManifest from "../../plugins/brokers/alpaca/manifest.json";
import { angelOnePlugin } from "../../plugins/brokers/angelone";
import angeloneManifest from "../../plugins/brokers/angelone/manifest.json";
import ccxtExecPlugin from "../../plugins/brokers/ccxt-exec";
import ccxtManifest from "../../plugins/brokers/ccxt-exec/manifest.json";
import { dhanPlugin } from "../../plugins/brokers/dhan";
import dhanManifest from "../../plugins/brokers/dhan/manifest.json";
import ibPlugin from "../../plugins/brokers/ib";
import ibManifest from "../../plugins/brokers/ib/manifest.json";
import { kitePlugin } from "../../plugins/brokers/kite";
import kiteManifest from "../../plugins/brokers/kite/manifest.json";
import oandaPlugin from "../../plugins/brokers/oanda";
import oandaManifest from "../../plugins/brokers/oanda/manifest.json";
import { openbbMcpPlugin } from "../../plugins/openbb-mcp";
import openbbMcpManifest from "../../plugins/openbb-mcp/manifest.json";
// E11 (R10): the third first-party panel plugin was removed entirely in this track.

import type { DiscoveredPlugin } from "@/lib/plugin-runtime";
import type { CredentialField, MarketplaceEntry } from "../../types/marketplace";
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

/** BYOK api-key + secret pair — the common broker credential shape. */
function keySecretFields(): CredentialField[] {
  return [
    { key: "api_key", label: "API Key", type: "text", secret: true, required: true },
    { key: "api_secret", label: "API Secret", type: "password", secret: true, required: true },
  ];
}

/**
 * The marketplace catalog, keyed by plugin id. First-party entries are
 * pre-installed (bundled + enabled by default → first run is populated, FR-032);
 * the seven broker entries are available-but-not-pre-installed (FR-051).
 *
 * The third first-party preinstalled entry (a panel plugin) was removed in R10 E11.
 */
export const CATALOG_ROWS: CatalogRow[] = [
  // --- First-party, pre-installed (the populated starter set) ---------------
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

  // --- Brokers — available, NONE pre-installed (FR-051) ---------------------
  row(
    {
      pluginId: "vysted-kite",
      name: "Kite Connect (Zerodha)",
      category: "broker",
      description:
        "The reference broker plugin — genuine read-only Kite Connect OAuth + granular positions/holdings/margins. Read-only; no order execution.",
      version: "0.1.0",
      author: "Vysted",
      icon: "candlestick-chart",
      preinstalled: false,
      brokerId: "kite",
      secretNamespace: "broker",
      website: "https://kite.trade/",
      instructions:
        "Create a Kite Connect app at kite.trade to get your API key + secret, then connect (a daily access-token login).",
      credentialFields: keySecretFields(),
    },
    kiteManifest,
    kitePlugin,
  ),
  row(
    {
      pluginId: "vysted-dhan",
      name: "Dhan",
      category: "broker",
      description: "Read-only Dhan account + positions. Read-only; no order execution.",
      version: (dhanManifest as PluginManifest).version,
      author: "Vysted",
      icon: "candlestick-chart",
      preinstalled: false,
      brokerId: "dhan",
      secretNamespace: "broker",
      credentialFields: [
        { key: "client_id", label: "Client ID", type: "text", secret: true, required: true },
        {
          key: "access_token",
          label: "Access Token",
          type: "password",
          secret: true,
          required: true,
        },
      ],
    },
    dhanManifest,
    dhanPlugin,
  ),
  row(
    {
      pluginId: "vysted-angelone",
      name: "Angel One",
      category: "broker",
      description: "Read-only Angel One account + positions. Read-only; no order execution.",
      version: (angeloneManifest as PluginManifest).version,
      author: "Vysted",
      icon: "candlestick-chart",
      preinstalled: false,
      brokerId: "angelone",
      secretNamespace: "broker",
      credentialFields: keySecretFields(),
    },
    angeloneManifest,
    angelOnePlugin,
  ),
  row(
    {
      pluginId: "broker-alpaca",
      name: "Alpaca",
      category: "broker",
      description: "Read-only Alpaca account + positions. Read-only; no order execution.",
      version: (alpacaManifest as PluginManifest).version,
      author: "Vysted",
      icon: "candlestick-chart",
      preinstalled: false,
      brokerId: "alpaca",
      secretNamespace: "broker",
      credentialFields: keySecretFields(),
    },
    alpacaManifest,
    alpacaPlugin,
  ),
  row(
    {
      pluginId: "broker-ib",
      name: "Interactive Brokers",
      category: "broker",
      description: "Read-only IBKR account + positions. Read-only; no order execution.",
      version: (ibManifest as PluginManifest).version,
      author: "Vysted",
      icon: "candlestick-chart",
      preinstalled: false,
      brokerId: "ib",
      secretNamespace: "broker",
      credentialFields: keySecretFields(),
    },
    ibManifest,
    ibPlugin,
  ),
  row(
    {
      pluginId: "broker-oanda",
      name: "OANDA",
      category: "broker",
      description: "Read-only OANDA account + positions. Read-only; no order execution.",
      version: (oandaManifest as PluginManifest).version,
      author: "Vysted",
      icon: "candlestick-chart",
      preinstalled: false,
      brokerId: "oanda",
      secretNamespace: "broker",
      credentialFields: [
        { key: "account_id", label: "Account ID", type: "text", secret: true, required: true },
        {
          key: "access_token",
          label: "Access Token",
          type: "password",
          secret: true,
          required: true,
        },
      ],
    },
    oandaManifest,
    oandaPlugin,
  ),
  row(
    {
      pluginId: "ccxt-exec",
      name: "Crypto exchange (ccxt)",
      category: "broker",
      description: "Read-only crypto-exchange account via ccxt. Read-only; no order execution.",
      version: (ccxtManifest as PluginManifest).version,
      author: "Vysted",
      icon: "bitcoin",
      preinstalled: false,
      brokerId: "ccxt-bybit",
      secretNamespace: "broker",
      credentialFields: keySecretFields(),
    },
    ccxtManifest,
    ccxtExecPlugin,
  ),
];

/** The catalog rows keyed by plugin id, for O(1) lookup. */
export const CATALOG_BY_ID: Record<string, CatalogRow> = Object.fromEntries(
  CATALOG_ROWS.map((r) => [r.entry.pluginId, r]),
);

/** Just the marketplace metadata (what the marketplace UI lists). */
export const MARKETPLACE_CATALOG: MarketplaceEntry[] = CATALOG_ROWS.map((r) => r.entry);
