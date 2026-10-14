import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, cleanup, act, within } from "@testing-library/react";
import { invokeShim, KEYCHAIN, FETCHES, sleep, text } from "./mocks";

vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));

import { bootstrapPlugins } from "@/lib/plugin-bootstrap";
import { usePluginsStore } from "@/store/plugins";
import { useMarketplaceStore } from "@/store/marketplace";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";
import { PluginManagerPanel } from "@/components/PluginManagerPanel";
import { MarketplacePanel } from "@/modules/marketplace/MarketplacePanel";

const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c-q/plugins-replay.json";
const log: Record<string, unknown> = {};
const save = () => fs.writeFileSync(OUT, JSON.stringify(log, null, 1));
const BASE = "http://127.0.0.1:52222";
const persisted = async () => (await (await fetch(`${BASE}/plugins`)).json()) as { plugin_id: string; enabled: boolean; installed: boolean; granted_secret_ids: string[] }[];
const states = () => usePluginsStore.getState().plugins.map((p) => `${p.manifest.id}:${p.state}${p.errorMessage ? `(${p.errorMessage.slice(0, 80)})` : ""}`);
const pluginModules = () => useModulesStore.getState().modules.filter((m) => m.id.startsWith("plugin:")).map((m) => m.id);
let dispose: (() => void) | null = null;

test("P1 boot + Plugin Manager populated", async () => {
  await act(async () => { dispose = await bootstrapPlugins(); await sleep(3000); });
  const { container } = render(<PluginManagerPanel />);
  await act(async () => { await sleep(500); });
  log.P1 = { panelText: text(container).slice(0, 2500), states: states(), pluginModules: pluginModules(), persisted: await persisted(),
    fetches: FETCHES.map((f) => `${f.m} ${f.url} -> ${f.status}`).slice(0, 80) };
  save();
});

test("P2 Plugin Manager toggle OFF on 'Example' -> what persists, what leaves", async () => {
  cleanup();
  const { container } = render(<PluginManagerPanel />);
  await act(async () => { await sleep(300); });
  const before = FETCHES.length;
  const sw = container.querySelector('input[role="switch"][aria-label^="Example"]') as HTMLInputElement | null
    ?? (Array.from(container.querySelectorAll('input[role="switch"]')).find((i) => /example/i.test(i.getAttribute("aria-label") ?? "")) as HTMLInputElement | undefined) ?? null;
  const modsBefore = pluginModules();
  if (sw) { fireEvent.click(sw); }
  await act(async () => { await sleep(1500); });
  log.P2 = { switchFound: !!sw, switchLabel: sw?.getAttribute("aria-label"), statesAfter: states(), pluginModulesBefore: modsBefore, pluginModulesAfter: pluginModules(),
    requestsDuringToggle: FETCHES.slice(before).map((f) => `${f.m} ${f.url} -> ${f.status} ${f.body ? JSON.stringify(f.body).slice(0, 160) : ""}`),
    persistedAfter: (await persisted()).find((p) => p.plugin_id === "vysted-example"),
    rowText: text(sw?.closest("li")).slice(0, 300) };
  // simulated relaunch: tear down and re-bootstrap from the SAME sidecar persistence
  dispose?.();
  await act(async () => { dispose = await bootstrapPlugins(); await sleep(2500); });
  log.P2_afterRelaunch = { example: states().filter((s) => s.startsWith("vysted-example")) };
  save();
});

test("P3 Marketplace populated + disable/enable/remove on non-broker plugins + news configure", async () => {
  cleanup();
  await act(async () => { await useMarketplaceStore.getState().refresh(); });
  const { container } = render(<MarketplacePanel />);
  await act(async () => { await sleep(800); });
  const sections = Array.from(container.querySelectorAll("section[aria-label]")).map((s) => `${s.getAttribute("aria-label")}: ${s.querySelectorAll("li").length}`);
  const cards = Array.from(container.querySelectorAll("li")).map((li) => text(li).slice(0, 160));
  const ops: Record<string, unknown> = {};
  for (const [op, id] of [["disable", "vysted-example"], ["enable", "vysted-example"], ["remove", "vysted-example"], ["install", "vysted-example"]] as const) {
    const before = FETCHES.length;
    await act(async () => { await (useMarketplaceStore.getState() as unknown as Record<string, (id: string) => Promise<void>>)[op](id); await sleep(500); });
    ops[`${op}:${id}`] = { stateFor: useMarketplaceStore.getState().stateFor(id), runtime: states().filter((s) => s.startsWith(id)),
      persisted: (await persisted()).find((p) => p.plugin_id === id), pluginModules: pluginModules(),
      requests: FETCHES.slice(before).map((f) => `${f.m} ${f.url} -> ${f.status}`) };
  }
  // News: configure a fake NewsAPI key through the store (in-memory keychain shim)
  const beforeCfg = FETCHES.length;
  await act(async () => { await useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "R15CANARY-newsapi-fake" }); await sleep(800); });
  ops["configure:vysted-news"] = { stateFor: useMarketplaceStore.getState().stateFor("vysted-news"), keychainAccounts: [...KEYCHAIN.keys()],
    persisted: (await persisted()).find((p) => p.plugin_id === "vysted-news"),
    requests: FETCHES.slice(beforeCfg).map((f) => `${f.m} ${f.url} -> ${f.status}`) };
  // Plugin Manager empty-state CTA wiring (Open Marketplace) - which id does it pass?
  const spy = vi.spyOn(useWorkspaceStore.getState(), "openPanel");
  log.P3 = { sections, cards, ops };
  // Configure form UI for news: open and read labels
  cleanup();
  const r2 = render(<MarketplacePanel />);
  await act(async () => { await sleep(300); });
  const cfgBtn = r2.container.querySelector('button[aria-label^="Configure News"], button[aria-label^="Configure"]') as HTMLButtonElement | null;
  if (cfgBtn) { fireEvent.click(cfgBtn); await act(async () => { await sleep(200); }); }
  (log.P3 as Record<string, unknown>).configureForm = { button: cfgBtn?.getAttribute("aria-label"), formText: text(cfgBtn?.closest("li")).slice(0, 600) };
  (log.P3 as Record<string, unknown>).openPanelSpyCalls = spy.mock.calls;
  save();
  dispose?.();
});
