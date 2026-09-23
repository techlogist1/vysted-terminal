import { vi, test } from "vitest";
import fs from "fs";
import { render, cleanup, act, screen, fireEvent, within } from "@testing-library/react";

const SCR = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c";
const PORT = 52222;
window.history.replaceState({}, "", `/?sidecar-port=${PORT}`);
const keychain = new Map<string, string>();
const invokes: { cmd: string; args?: Record<string, unknown> }[] = [];
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string, args?: Record<string, unknown>) => {
    invokes.push({ cmd, args: cmd.startsWith("keychain") ? { account: args?.account, secret: args?.secret ? "<redacted>" : undefined } : args });
    if (cmd === "keychain_set") { keychain.set(String(args!.account), String(args!.secret)); return; }
    if (cmd === "keychain_get") return keychain.get(String(args!.account)) ?? null;
    if (cmd === "keychain_delete") { keychain.delete(String(args!.account)); return; }
    if (cmd === "get_sidecar_port") return PORT;
    throw new Error(`invoke ${cmd} not available in harness`);
  }),
}));
(URL as any).createObjectURL = (b: Blob) => { (globalThis as any).__lastBlob = b; return "blob:x"; };
(URL as any).revokeObjectURL = () => {};
const anchorClicks: string[] = [];
HTMLAnchorElement.prototype.click = function () { anchorClicks.push(this.download); };

import { SettingsPanel } from "@/components/SettingsPanel";
import { PluginManagerPanel } from "@/components/PluginManagerPanel";
import { MarketplacePanel } from "@/modules/marketplace/MarketplacePanel";
import { useSettingsStore } from "@/store/settings";
import { useKeybindingsStore } from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";
import { usePluginsStore } from "@/store/plugins";
import { useMarketplaceStore } from "@/store/marketplace";
import { bootstrapPlugins, HOST_VERSION } from "@/lib/plugin-bootstrap";
import { vystedModules as ALL_MODULES } from "@/modules";

const OUT = `${SCR}/out/settings-plugins-replay.json`;
const log: Record<string, unknown> = {};
function save(label: string, v: unknown) { log[label] = v; fs.writeFileSync(OUT, JSON.stringify(log, null, 1)); }
const wait = (ms: number) => act(async () => { await new Promise((r) => setTimeout(r, ms)); });
const text = (el: Element | null) => (el?.textContent ?? "").replace(/\s+/g, " ").trim();
const realFetch = globalThis.fetch;
const netlog: { method: string; url: string; status: number | string; body?: unknown }[] = [];
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input).replace(/^http:\/\/127\.0\.0\.1:\d+/, "");
  try { const r = await realFetch(input as any, init); netlog.push({ method: init?.method ?? "GET", url, status: r.status, ...(init?.body && !url.includes("/llm/keys") ? { body: String(init.body).slice(0, 300) } : {}) }); return r; }
  catch (e) { netlog.push({ method: init?.method ?? "GET", url, status: String(e) }); throw e; }
}) as typeof fetch;
const fakeDock = { panels: [] as any[], added: [] as string[], getPanel: () => undefined, addPanel(o: any) { this.added.push(o.id ?? o.component); return { api: { setSize() {}, setActive() {} } }; }, groups: [], activePanel: undefined, onDidLayoutChange: () => ({ dispose() {} }) };

test("S0 module registry + full settings render", async () => {
  try { useModulesStore.getState().registerModules(ALL_MODULES); } catch (e) { save("S0-registry-error", String(e)); }
  const { container } = render(<SettingsPanel />);
  await wait(4000);
  const sections = Array.from(container.querySelectorAll("section[aria-labelledby]")).map((s) => s.getAttribute("aria-labelledby"));
  const byId = (id: string) => text(container.querySelector(`section[aria-labelledby="${id}"]`)).slice(0, 1500);
  save("S0-render", { sections, nav: text(container.querySelector("nav")), providers: byId("settings-providers"), research: byId("settings-research"), region: byId("settings-region"), keybindings: byId("settings-keybindings").slice(0, 600), integrations: byId("settings-integrations"), layouts: byId("settings-layouts"), modules: byId("settings-modules"), exportImport: byId("settings-export"), about: byId("settings-about"), net: netlog.slice() });
  cleanup();
});

test("S1 key entry dialog: bogus keys (openai invalid, openrouter accepted), remove", async () => {
  const { container } = render(<SettingsPanel />);
  await wait(1500);
  const out: Record<string, unknown> = {};
  for (const [label, pid] of [["OpenAI", "openai"], ["OpenRouter", "openrouter"]] as const) {
    const rows = Array.from(container.querySelectorAll('section[aria-labelledby="settings-providers"] div.flex-wrap')) as HTMLElement[];
    const row = rows.find((r) => text(r).startsWith(label));
    const addBtn = row ? within(row).queryByText(/Add key|Update key/) : null;
    if (!addBtn) { out[pid] = "no add-key button"; continue; }
    await act(async () => { fireEvent.click(addBtn); });
    await wait(100);
    const input = document.querySelector('input[type="password"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: `SENTINEL-KEY-R15-${pid}` } });
    await act(async () => { fireEvent.submit(input.closest("form")!); });
    await wait(4000);
    const dialogText = text(document.querySelector('[role="dialog"]'));
    await wait(700);
    const rowAfter = (Array.from(container.querySelectorAll('section[aria-labelledby="settings-providers"] div.flex-wrap')) as HTMLElement[]).find((r) => text(r).startsWith(label));
    out[pid] = { dialogText, keychainHas: keychain.has(`llm-provider:${pid}`) || [...keychain.keys()].some((k) => k.includes(pid)), rowAfter: text(rowAfter ?? null) };
    const esc = document.querySelector('[role="dialog"]'); if (esc) { fireEvent.keyDown(esc, { key: "Escape" }); await wait(100); }
  }
  // remove the openrouter key via the trash button
  const rem = screen.queryByLabelText("Remove OpenRouter key");
  if (rem) { await act(async () => { fireEvent.click(rem); }); await wait(300); }
  out.afterRemove = { keychainKeys: [...keychain.keys()], row: text((Array.from(container.querySelectorAll('section[aria-labelledby="settings-providers"] div.flex-wrap')) as HTMLElement[]).find((r) => text(r).startsWith("OpenRouter")) ?? null) };
  out.validateCalls = netlog.filter((n) => n.url.includes("/llm/keys/validate"));
  out.invokes = invokes.filter((i) => i.cmd.startsWith("keychain_set") || i.cmd.startsWith("keychain_delete"));
  save("S1-keys", out);
  cleanup();
});

test("S2 keybindings: record, conflict, reset; export/import", async () => {
  const { container } = render(<SettingsPanel />);
  await wait(800);
  const out: Record<string, unknown> = {};
  const recBtns = Array.from(container.querySelectorAll('button[aria-label^="Record binding for"]')) as HTMLButtonElement[];
  out.actions = recBtns.map((b) => b.getAttribute("aria-label")!.replace("Record binding for ", ""));
  const first = recBtns[0], second = recBtns[1];
  const secondCombo = text(container.querySelector(`[aria-label="${out.actions && (out.actions as string[])[1]} binding"]`));
  await act(async () => { fireEvent.click(first); });
  const def2 = useKeybindingsStore.getState().defFor(Object.keys(useKeybindingsStore.getState().defaults)[1]);
  const keys = def2?.keys ?? "mod+k";
  const parts = keys.split("+"); const key = parts.at(-1)!;
  await act(async () => { fireEvent.keyDown(first, { key: key.length === 1 ? key : key, metaKey: parts.includes("mod"), ctrlKey: false, shiftKey: parts.includes("shift"), altKey: parts.includes("alt") }); });
  await wait(100);
  out.recordedTarget = { secondCombo, overrides: { ...useKeybindingsStore.getState().overrides }, conflicts: useKeybindingsStore.getState().conflicts(), banner: text(container.querySelector('section[aria-labelledby="settings-keybindings"]')).slice(0, 400) };
  // export
  anchorClicks.length = 0;
  await act(async () => { fireEvent.click(screen.getByText("Export settings")); });
  const blob: Blob | undefined = (globalThis as any).__lastBlob;
  const exported = blob ? await blob.text() : null;
  out.export = { anchorClicks: anchorClicks.slice(), exported, status: text(container.querySelector('section[aria-labelledby="settings-export"] p.text-positive, section[aria-labelledby="settings-export"] p.text-negative')) };
  // imports
  const fileInput = screen.getByLabelText("Import settings file") as HTMLInputElement;
  const imports: Record<string, unknown> = {};
  useSettingsStore.getState().setRegion("IN" as any);
  for (const [label, body] of [["empty-object", "{}"], ["package-json", JSON.stringify({ name: "x", version: "1.0.0", dependencies: {} })], ["region-bogus", JSON.stringify({ version: 1, settings: { region: "XX" } })], ["partial-older-export", JSON.stringify({ version: 1, keybindingOverrides: {}, settings: { defaultAgentId: "copilot" } })], ["malformed", "{not json"], ["garbage-bindings", JSON.stringify({ keybindingOverrides: { "no.such.action": "mod+q", "palette.open": 42 } })]] as const) {
    useSettingsStore.getState().setRegion("IN" as any);
    const file = new File([body], `${label}.json`, { type: "application/json" });
    await act(async () => { fireEvent.change(fileInput, { target: { files: [file] } }); });
    await wait(150);
    imports[label] = { status: text(container.querySelector('section[aria-labelledby="settings-export"] p.text-positive, section[aria-labelledby="settings-export"] p.text-negative')), regionAfter: useSettingsStore.getState().region, overrides: { ...useKeybindingsStore.getState().overrides } };
  }
  out.imports = imports;
  save("S2-keybindings-export-import", out);
  cleanup();
});

test("S3 layouts subsection + integrations/plugin CTAs with a fake dockview", async () => {
  useWorkspaceStore.setState({ dockviewApi: fakeDock as any } as any);
  const { container } = render(<SettingsPanel />);
  await wait(1500);
  const out: Record<string, unknown> = {};
  out.layoutsText = text(container.querySelector('section[aria-labelledby="settings-layouts"]'));
  const input = screen.getByLabelText("New layout name") as HTMLInputElement;
  fireEvent.change(input, { target: { value: "R15 S2C layout" } });
  await act(async () => { fireEvent.submit(input.closest("form")!); });
  await wait(1500);
  out.afterSave = text(container.querySelector('section[aria-labelledby="settings-layouts"]'));
  fireEvent.change(input, { target: { value: "Research: TCS" } });
  await act(async () => { fireEvent.submit(input.closest("form")!); });
  await wait(1500);
  out.afterReservedishSave = text(container.querySelector('section[aria-labelledby="settings-layouts"]'));
  fakeDock.added.length = 0;
  await act(async () => { fireEvent.click(screen.getByText("Open Marketplace")); });
  out.openMarketplaceAdded = fakeDock.added.slice();
  out.net = netlog.filter((n) => n.url.startsWith("/workspace"));
  save("S3-layouts-integrations", out);
  cleanup();
});

test("S4 modules toggle", async () => {
  const { container } = render(<SettingsPanel />);
  await wait(500);
  const sw = screen.queryByLabelText("Portfolio enabled") as HTMLElement | null;
  const before = { enabled: { ...useModulesStore.getState().enabled }, portfolioPanel: !!useModulesStore.getState().findPanel("portfolio") };
  if (sw) { await act(async () => { fireEvent.click(sw); }); }
  const after = { portfolioEnabled: useModulesStore.getState().enabled.portfolio, findPanel: !!useModulesStore.getState().findPanel("portfolio"), panelsCount: (useModulesStore.getState() as any).enabledModules?.().length };
  if (sw) { await act(async () => { fireEvent.click(sw); }); }
  save("S4-modules", { switchFound: !!sw, before, after, modulesText: text(container.querySelector('section[aria-labelledby="settings-modules"]')).slice(0, 900) });
  cleanup();
});

test("P1 plugins: bootstrap, manager, marketplace, toggle, remove/install", async () => {
  useWorkspaceStore.setState({ dockviewApi: fakeDock as any } as any);
  const teardown = await bootstrapPlugins();
  await wait(3000);
  const out: Record<string, unknown> = { hostVersion: HOST_VERSION };
  const pm = render(<PluginManagerPanel />);
  await wait(500);
  out.managerText = text(pm.container).slice(0, 2500);
  out.storePlugins = usePluginsStore.getState().plugins.map((p) => ({ id: p.manifest.id, state: p.state, err: p.errorMessage ?? null, health: (p as any).healthHistory?.slice(-1) }));
  pm.unmount();
  const mk = render(<MarketplacePanel />);
  await wait(2500);
  out.marketText = text(mk.container).slice(0, 3000);
  const n0 = netlog.length;
  await act(async () => { await useMarketplaceStore.getState().disable("vysted-example"); });
  await wait(300);
  out.afterDisable = { store: usePluginsStore.getState().plugins.find((p) => p.manifest.id === "vysted-example")?.state, sidecar: await (await realFetch(`http://127.0.0.1:${PORT}/plugins/vysted-example/config`)).json() };
  await act(async () => { await useMarketplaceStore.getState().remove("vysted-example"); });
  await wait(300);
  out.afterRemove = { store: usePluginsStore.getState().plugins.find((p) => p.manifest.id === "vysted-example")?.state ?? "absent", sidecar: (await realFetch(`http://127.0.0.1:${PORT}/plugins/vysted-example/config`)).status, card: text(Array.from(mk.container.querySelectorAll("li")).find((l) => text(l).startsWith("Example")) ?? null) };
  await act(async () => { await useMarketplaceStore.getState().install("vysted-example"); });
  await wait(300);
  out.afterInstall = { store: usePluginsStore.getState().plugins.find((p) => p.manifest.id === "vysted-example")?.state, sidecar: await (await realFetch(`http://127.0.0.1:${PORT}/plugins/vysted-example/config`)).json(), card: text(Array.from(mk.container.querySelectorAll("li")).find((l) => text(l).startsWith("Example")) ?? null) };
  // configure news with a fake NewsAPI key
  try { await act(async () => { await useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "SENTINEL-NEWSAPI-R15" } as any); }); out.configureNews = { configured: useMarketplaceStore.getState().configured["vysted-news"], sidecar: await (await realFetch(`http://127.0.0.1:${PORT}/plugins/vysted-news/config`)).json() }; }
  catch (e) { out.configureNews = String(e); }
  out.net = netlog.slice(n0).filter((n) => n.url.startsWith("/plugins"));
  // empty-state CTA
  const saved = usePluginsStore.getState().plugins;
  usePluginsStore.setState({ plugins: [] } as any);
  fakeDock.added.length = 0;
  const pm2 = render(<PluginManagerPanel />);
  await wait(100);
  const cta = pm2.queryByText("Open Marketplace");
  if (cta) await act(async () => { fireEvent.click(cta); });
  out.emptyState = { text: text(pm2.container), ctaAdded: fakeDock.added.slice() };
  usePluginsStore.setState({ plugins: saved } as any);
  save("P1-plugins", out);
  teardown();
  cleanup();
});
