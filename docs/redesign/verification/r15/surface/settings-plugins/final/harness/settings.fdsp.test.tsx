import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, cleanup, within, act } from "@testing-library/react";
import { invokeShim, KEYCHAIN, INVOKES, FETCHES, sleep, text } from "./mocks";

vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));

import { SettingsPanel, buildSettingsExport } from "@/components/SettingsPanel";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useSearchSettingsStore } from "@/store/search-settings";
import { useSettingsStore } from "@/store/settings";
import { useKeybindingsStore, matchesEvent } from "@/store/keybindings";
import { useWorkspaceStore } from "@/store/workspace";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModulesStore } from "@/store/modules";

const OUT = process.env.FDSP_OUT + "/settings-replay.json";
const log: Record<string, unknown> = {};
const save = () => fs.writeFileSync(OUT, JSON.stringify(log, null, 1));
const sectionText = (c: HTMLElement, id: string) => text(c.querySelector(`#${id}`)?.closest("section")).slice(0, 1800);
async function mount(ms = 6000) {
  cleanup();
  const r = render(<SettingsPanel />);
  await act(async () => { await sleep(ms); });
  return r;
}
function providerRow(c: HTMLElement, label: string) {
  return Array.from(c.querySelectorAll("section[aria-labelledby=settings-providers] div")).find(
    (d) => d.textContent?.startsWith(label) && d.querySelector("button"),
  ) as HTMLElement | undefined;
}
async function addKey(c: HTMLElement, label: string, key: string) {
  const row = providerRow(c, label);
  const btn = row ? within(row).getAllByRole("button").find((b) => /Add key|Update key|Replace/.test(b.textContent ?? "")) : undefined;
  if (!btn) return { error: `no ${label} key button`, row: text(row).slice(0, 200) };
  const before = FETCHES.length;
  fireEvent.click(btn);
  await act(async () => { await sleep(300); });
  const input = document.body.querySelector('input[aria-label="API key"]') as HTMLInputElement;
  fireEvent.change(input, { target: { value: key } });
  fireEvent.submit(input.closest("form")!);
  await act(async () => { await sleep(4500); });
  return {
    dialogText: text(document.body.querySelector('[role="dialog"]')),
    keychainAccounts: [...KEYCHAIN.keys()],
    rowAfter: text(providerRow(c, label)).slice(0, 200),
    requests: FETCHES.slice(before).map((f) => `${f.m} ${f.url} -> ${f.status} ${f.body ? JSON.stringify(f.body) : ""}`),
  };
}

test("S1 mount: every section populated", async () => {
  await act(async () => { await useLLMProvidersStore.getState().refresh?.(); });
  const { container } = await mount(8000);
  log.S1 = {
    nav: text(container.querySelector('nav[aria-label="Settings sections"]')),
    sections: Object.fromEntries(["settings-providers","settings-research","settings-region","settings-keybindings","settings-integrations","settings-layouts","settings-palette","settings-modules","settings-export","settings-about"].map((id) => [id, sectionText(container, id)])),
    keyStatus: useProviderKeysStore.getState().status,
    fetches: FETCHES.map((f) => `${f.m} ${f.url} -> ${f.status}`),
    invokes: INVOKES.map((i) => `${i.cmd}:${i.ok}`),
  };
  save();
});

test("S2 fake OpenRouter key through KeyEntryDialog (RESEARCH-010)", async () => {
  const { container } = await mount();
  log.S2 = { ...(await addKey(container, "OpenRouter", "sk-or-v1-R15CANARYfinal-not-a-real-key")),
    keyStatusOpenrouter: useProviderKeysStore.getState().status.openrouter,
    researchTierB: sectionText(container, "settings-research").match(/OpenRouter key[^.]*\./g) };
  save();
});

test("S3 whitespace-padded keys (UI-057)", async () => {
  const out: Record<string, unknown> = {};
  for (const [label, key] of [["OpenAI", "sk-R15CANARYfinal-0000000000 "], ["Anthropic", "sk-ant-R15CANARYfinal\n"], ["Groq", "  gsk_R15CANARYfinal\t"]] as const) {
    const { container } = await mount();
    out[label] = await addKey(container, label, key);
  }
  log.S3 = out;
  save();
});

test("S4 Import settings files (UI-058 / LEAD-089)", async () => {
  const out: Record<string, unknown> = {};
  const cases: [string, string][] = [
    ["empty-object", "{}"],
    ["other-app-json", JSON.stringify({ theme: "dark", fontSize: 14 })],
    ["settings-fontSize-only", JSON.stringify({ settings: { fontSize: 14 } })],
    ["numbers-as-bindings", JSON.stringify({ version: 1, keybindingOverrides: { "palette.open": 42, "agent.toggle": "mod+j" }, settings: { region: "XX", defaultAgentId: 7 } })],
    ["not-json", "hello, world"],
    ["valid-roundtrip", JSON.stringify(buildSettingsExport())],
  ];
  for (const [label, body] of cases) {
    const { container } = await mount(2500);
    useKeybindingsStore.getState().setOverrides({ "agent.toggle": "mod+shift+y" });
    const before = { overrides: { ...useKeybindingsStore.getState().overrides }, region: useSettingsStore.getState().region };
    const input = container.querySelector('input[aria-label="Import settings file"]') as HTMLInputElement;
    const file = new File([body], `${label}.json`, { type: "application/json" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    fireEvent.change(input);
    await act(async () => { await sleep(500); });
    out[label] = { sectionText: sectionText(container, "settings-export"), before,
      after: { overrides: { ...useKeybindingsStore.getState().overrides }, region: useSettingsStore.getState().region } };
  }
  log.S4 = out;
  save();
});

test("S5 Export bundle carries the visible preferences (UI-058)", async () => {
  useSearchSettingsStore.getState().setResearchTier?.("tier_b");
  useSearchSettingsStore.getState().setResearchModel?.("deep", "openai/o4-mini-deep-research");
  useSearchSettingsStore.getState().setSearxngUrl?.("http://localhost:8080");
  useLLMProvidersStore.getState().setDefaultProviderId?.("openai" as never);
  const bundle = buildSettingsExport() as unknown as Record<string, unknown>;
  log.S5 = { exportBundle: bundle, topKeys: Object.keys(bundle) };
  save();
});

test("S6 Layouts subsection save via UI (UI-082)", async () => {
  const out: Record<string, unknown> = {};
  for (const name of ["R15 Final Harness", "मेरा लेआउट", "म".repeat(200), "L".repeat(230)]) {
    const { container } = await mount(2500);
    const before = FETCHES.length;
    const input = container.querySelector('input[aria-label="New layout name"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: name } });
    fireEvent.submit(input.closest("form")!);
    await act(async () => { await sleep(1500); });
    out[`${name.slice(0, 20)} (len ${name.length})`] = { maxLengthAttr: input.getAttribute("maxlength"), titleAttr: input.getAttribute("title"),
      layoutsText: sectionText(container, "settings-layouts"),
      requests: FETCHES.slice(before).map((f) => `${f.m} ${f.url.slice(0, 80)} -> ${f.status}`) };
  }
  log.S6 = out;
  save();
});

test("S7 Integrations Open Marketplace passes a registered id", async () => {
  const { container } = await mount(2500);
  const spy = vi.spyOn(useWorkspaceStore.getState(), "openPanel");
  const btn = within(container.querySelector("section[aria-labelledby=settings-integrations]") as HTMLElement).getByRole("button", { name: /Open Marketplace/ });
  fireEvent.click(btn);
  log.S7 = { openPanelCalls: spy.mock.calls, registeredModuleIds: useModulesStore.getState().modules.map((m) => m.id) };
  save();
});

test("S8 Modules toggles + Region", async () => {
  const { container } = await mount(3000);
  const sec = container.querySelector("#settings-modules")!.closest("section")!;
  const switches = Array.from(sec.querySelectorAll('input[role="switch"], button[role="switch"]')) as HTMLElement[];
  const labels = switches.map((s) => `${s.getAttribute("aria-label")}${(s as HTMLInputElement).disabled || s.hasAttribute("disabled") ? " [disabled]" : ""}`);
  const cmdsBefore = useModulesStore.getState().enabledCommands().map((c) => c.id);
  const notes = switches.find((s) => /^Notes/.test(s.getAttribute("aria-label") ?? ""));
  if (notes) fireEvent.click(notes);
  await act(async () => { await sleep(200); });
  const cmdsAfter = useModulesStore.getState().enabledCommands().map((c) => c.id);
  const regionSel = container.querySelector('select[aria-label="Region"]') as HTMLSelectElement;
  const regionBefore = { value: regionSel.value, store: useSettingsStore.getState().region, rowText: text(regionSel.closest("section")).slice(0, 400) };
  fireEvent.change(regionSel, { target: { value: regionSel.value === "US" ? "IN" : "US" } });
  await act(async () => { await sleep(100); });
  log.S8 = { moduleRows: labels, enabledMapAfterNotesOff: useModulesStore.getState().enabled,
    notesCmdsBefore: cmdsBefore.filter((c) => c.startsWith("notes")), notesCmdsAfter: cmdsAfter.filter((c) => c.startsWith("notes")),
    region: { before: regionBefore, afterStore: useSettingsStore.getState().region, rowAfter: text(regionSel.closest("section")).slice(0, 400) } };
  if (notes) fireEvent.click(notes);
  save();
});

test("S9 Keybindings: Ctrl+K on agent.toggle vs palette (mod+k) conflict", async () => {
  const st = useKeybindingsStore.getState();
  const out: Record<string, unknown> = {};
  for (const combo of ["meta+k", "ctrl+k", "mod+k"]) {
    useKeybindingsStore.getState().setBinding("agent.toggle", combo);
    const ev = { key: "k", ctrlKey: combo !== "meta+k", metaKey: combo === "meta+k", altKey: false, shiftKey: false };
    const { container } = await mount(1200);
    out[combo] = { stored: useKeybindingsStore.getState().bindingFor("agent.toggle"), conflicts: useKeybindingsStore.getState().conflicts(),
      paletteMatches: matchesEvent(useKeybindingsStore.getState().bindingFor("palette.open"), ev as never),
      agentMatches: matchesEvent(useKeybindingsStore.getState().bindingFor("agent.toggle"), ev as never),
      banner: text(container.querySelector("section[aria-labelledby=settings-keybindings] [role=alert]")) };
  }
  st.resetBinding("agent.toggle");
  log.S9 = { platform: navigator.platform, out };
  save();
});
