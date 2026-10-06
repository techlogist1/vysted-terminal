import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, cleanup, within, act } from "@testing-library/react";
import { invokeShim, KEYCHAIN, INVOKES, FETCHES, sleep, text } from "./mocks";

vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));

import { SettingsPanel, buildSettingsExport } from "@/components/SettingsPanel";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useSearchSettingsStore } from "@/store/search-settings";
import { useSettingsStore } from "@/store/settings";
import { useKeybindingsStore } from "@/store/keybindings";
import { useWorkspaceStore } from "@/store/workspace";
import { useLLMProvidersStore } from "@/store/llm-providers";

const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c-q/settings-replay.json";
const log: Record<string, unknown> = {};
const save = () => fs.writeFileSync(OUT, JSON.stringify(log, null, 1));
function sectionText(container: HTMLElement, id: string): string {
  const h = container.querySelector(`#${id}`);
  const sec = h?.closest("section");
  return text(sec).slice(0, 1600);
}
async function mount() {
  cleanup();
  const r = render(<SettingsPanel />);
  await act(async () => { await sleep(7000); });
  return r;
}

test("S1 mount: every section populated against :52222", async () => {
  await act(async () => { await useLLMProvidersStore.getState().refresh?.(); });
  const { container } = await mount();
  log.S1 = {
    nav: text(container.querySelector('nav[aria-label="Settings sections"]')),
    providers: sectionText(container, "settings-providers"),
    research: sectionText(container, "settings-research"),
    region: sectionText(container, "settings-region"),
    keybindings: sectionText(container, "settings-keybindings").slice(0, 700),
    integrations: sectionText(container, "settings-integrations"),
    layouts: sectionText(container, "settings-layouts"),
    modules: sectionText(container, "settings-modules"),
    exportImport: sectionText(container, "settings-export"),
    about: sectionText(container, "settings-about"),
    keyStatus: useProviderKeysStore.getState().status,
    fetches: FETCHES.map((f) => `${f.m} ${f.url} -> ${f.status}`),
    invokes: INVOKES.map((i) => `${i.cmd}:${i.ok}`),
  };
  save();
});

test("S2 Add key: a FAKE OpenRouter key through the real KeyEntryDialog", async () => {
  const { container } = await mount();
  const rows = Array.from(container.querySelectorAll("#settings-providers ~ div div.flex.min-h-8"));
  const orRow = Array.from(container.querySelectorAll("section[aria-labelledby=settings-providers] div")).find(
    (d) => d.textContent?.startsWith("OpenRouter") && d.querySelector("button"),
  ) as HTMLElement | undefined;
  const btn = orRow ? within(orRow).getAllByRole("button").find((b) => /Add key|Update key/.test(b.textContent ?? "")) : undefined;
  const before = FETCHES.length;
  if (!btn) { log.S2 = { error: "no OpenRouter Add key button", rows: rows.length }; save(); return; }
  fireEvent.click(btn);
  await act(async () => { await sleep(300); });
  const input = document.body.querySelector('input[aria-label="API key"]') as HTMLInputElement;
  fireEvent.change(input, { target: { value: "sk-or-v1-R15CANARY-this-is-not-a-real-key" } });
  const form = input.closest("form")!;
  fireEvent.submit(form);
  await act(async () => { await sleep(3000); });
  const dialogText = text(document.body.querySelector('[role="dialog"]'));
  await act(async () => { await sleep(1500); });
  log.S2 = {
    dialogTextAfterSave: dialogText,
    keychainAccountsWritten: [...KEYCHAIN.keys()],
    keyStatusOpenrouter: useProviderKeysStore.getState().status.openrouter,
    providersRowAfter: text(orRow).slice(0, 200),
    researchTierBText: sectionText(container, "settings-research").match(/OpenRouter key[^.]*\./g),
    requests: FETCHES.slice(before).map((f) => `${f.m} ${f.url} -> ${f.status} ${f.body ? JSON.stringify(f.body) : ""}`),
  };
  save();
});

test("S3 Add key: a key pasted with a trailing space/newline (OpenAI + Anthropic)", async () => {
  const out: Record<string, unknown> = {};
  for (const [label, key] of [["OpenAI", "sk-R15CANARY-fake-0000000000 "], ["Anthropic", "sk-ant-R15CANARY-fake\n"]] as const) {
    const { container } = await mount();
    const row = Array.from(container.querySelectorAll("section[aria-labelledby=settings-providers] div")).find(
      (d) => d.textContent?.startsWith(label) && d.querySelector("button"),
    ) as HTMLElement;
    const btn = within(row).getAllByRole("button").find((b) => /Add key|Update key/.test(b.textContent ?? ""))!;
    fireEvent.click(btn);
    await act(async () => { await sleep(300); });
    const input = document.body.querySelector('input[aria-label="API key"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: key } });
    fireEvent.submit(input.closest("form")!);
    await act(async () => { await sleep(4000); });
    out[label] = { dialogText: text(document.body.querySelector('[role="dialog"]')) };
    cleanup();
  }
  log.S3 = out;
  save();
});

test("S4 Import settings: wrong-shaped / garbage / hostile files", async () => {
  const out: Record<string, unknown> = {};
  const cases: [string, string][] = [
    ["empty-object", "{}"],
    ["other-app-json", JSON.stringify({ theme: "dark", fontSize: 14 })],
    ["numbers-as-bindings", JSON.stringify({ version: 1, keybindingOverrides: { "palette.open": 42, "agent.toggle": "mod+j" }, settings: { region: "XX", defaultAgentId: 7 } })],
    ["not-json", "hello, world"],
    ["valid-roundtrip", JSON.stringify(buildSettingsExport())],
  ];
  for (const [label, body] of cases) {
    const { container } = await mount();
    useKeybindingsStore.getState().setOverrides({ "agent.toggle": "mod+shift+y" });
    const before = { overrides: { ...useKeybindingsStore.getState().overrides }, region: useSettingsStore.getState().region };
    const input = container.querySelector('input[aria-label="Import settings file"]') as HTMLInputElement;
    const file = new File([body], `${label}.json`, { type: "application/json" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    fireEvent.change(input);
    await act(async () => { await sleep(400); });
    out[label] = {
      statusLine: sectionText(container, "settings-export").replace(/.*written to the file\./, ""),
      before,
      after: { overrides: { ...useKeybindingsStore.getState().overrides }, region: useSettingsStore.getState().region },
    };
    cleanup();
  }
  log.S4 = out;
  save();
});

test("S5 Export bundle vs the preferences the panel shows", async () => {
  useSearchSettingsStore.getState().setResearchTier?.("tier_b");
  useSearchSettingsStore.getState().setResearchModel?.("deep", "openai/o4-mini-deep-research");
  useSearchSettingsStore.getState().setSearxngUrl?.("http://localhost:8080");
  useLLMProvidersStore.getState().setDefaultProviderId?.("openai" as never);
  const bundle = buildSettingsExport();
  log.S5 = {
    exportBundle: bundle,
    notExported_visibleInPanel: {
      researchTier: useSearchSettingsStore.getState().researchTier,
      researchModels: useSearchSettingsStore.getState().researchModels,
      searxngUrl: useSearchSettingsStore.getState().searxngUrl,
      defaultProviderId: useLLMProvidersStore.getState().defaultProviderId,
    },
    exportKeys: Object.keys(bundle.settings),
  };
  save();
});

test("S6 Layouts subsection: save / reserved name / Hindi name / long name", async () => {
  const out: Record<string, unknown> = {};
  for (const name of ["R15 Harness", "__hidden", "मेरा लेआउट", "L".repeat(230)]) {
    const { container } = await mount();
    const before = FETCHES.length;
    const input = container.querySelector('input[aria-label="New layout name"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: name } });
    fireEvent.submit(input.closest("form")!);
    await act(async () => { await sleep(1500); });
    out[name.slice(0, 24)] = {
      layoutsText: sectionText(container, "settings-layouts"),
      activeName: useWorkspaceStore.getState().name,
      requests: FETCHES.slice(before).map((f) => `${f.m} ${f.url.slice(0, 60)} -> ${f.status}`),
    };
    cleanup();
  }
  log.S6 = out;
  save();
});

test("S7 Integrations: Open Marketplace", async () => {
  const { container } = await mount();
  const spy = vi.spyOn(useWorkspaceStore.getState(), "openPanel");
  const btn = within(container.querySelector("section[aria-labelledby=settings-integrations]") as HTMLElement).getByRole("button", { name: /Open Marketplace/ });
  fireEvent.click(btn);
  log.S7 = { openPanelCalls: spy.mock.calls, dockviewApi: useWorkspaceStore.getState().dockviewApi ? "mounted" : "null (no dockview in jsdom)" };
  save();
});
