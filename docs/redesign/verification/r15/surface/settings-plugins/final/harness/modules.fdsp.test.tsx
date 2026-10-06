import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, act } from "@testing-library/react";
import { invokeShim, sleep, text } from "./mocks";
vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));
import { vystedModules } from "@/modules";
import { useModulesStore } from "@/store/modules";
import { useSettingsStore } from "@/store/settings";
import { useWorkspaceStore } from "@/store/workspace";
import { SettingsPanel } from "@/components/SettingsPanel";
const OUT = process.env.FDSP_OUT + "/modules-replay.json";

test("S8 Modules toggles + disabled-module openPanel + Region select", async () => {
  useModulesStore.getState().registerModules(vystedModules);
  const { container } = render(<SettingsPanel />);
  await act(async () => { await sleep(4000); });
  const sec = container.querySelector("#settings-modules")!.closest("section")!;
  const switches = Array.from(sec.querySelectorAll('input[role="switch"], button[role="switch"]')) as HTMLElement[];
  const labels = switches.map((s) => `${s.getAttribute("aria-label")}${(s as HTMLInputElement).disabled || s.hasAttribute("disabled") ? " [disabled]" : ""}`);
  const cmdsBefore = useModulesStore.getState().enabledCommands().map((c) => c.id);
  const notes = switches.find((s) => /^Notes/.test(s.getAttribute("aria-label") ?? ""));
  const portfolio = switches.find((s) => /^Portfolio/.test(s.getAttribute("aria-label") ?? ""));
  if (notes) fireEvent.click(notes);
  if (portfolio) fireEvent.click(portfolio);
  await act(async () => { await sleep(200); });
  const cmdsAfter = useModulesStore.getState().enabledCommands().map((c) => c.id);
  // fake dockview api to observe addPanel calls (jsdom has no dockview)
  const added: unknown[] = [];
  const fakeApi = { getPanel: () => undefined, addPanel: (o: unknown) => { added.push(o); return { api: { setSize() {}, setActive() {}, setConstraints() {} } }; }, panels: [], activePanel: undefined } as never;
  useWorkspaceStore.setState({ dockviewApi: fakeApi } as never);
  let openErr: string | null = null;
  try { useWorkspaceStore.getState().openPanel("portfolio"); } catch (e) { openErr = (e as Error).message; }
  const addedWhilePortfolioOff = added.length;
  if (portfolio) fireEvent.click(portfolio);
  await act(async () => { await sleep(100); });
  try { useWorkspaceStore.getState().openPanel("portfolio"); } catch (e) { openErr = (e as Error).message; }
  const addedAfterReenable = added.length - addedWhilePortfolioOff;
  const beforeMk = added.length;
  useWorkspaceStore.getState().openPanel("marketplace");
  const marketplaceAdds = added.length - beforeMk;
  const beforeMk2 = added.length;
  useWorkspaceStore.getState().openPanel("marketplace-panel");
  const marketplacePanelIdAdds = added.length - beforeMk2;
  const regionSel = container.querySelector('select[aria-label="Region"]') as HTMLSelectElement;
  const regionBefore = { value: regionSel.value, store: useSettingsStore.getState().region, rowText: text(regionSel.closest("section")).slice(0, 300) };
  fireEvent.change(regionSel, { target: { value: regionSel.value === "US" ? "IN" : "US" } });
  await act(async () => { await sleep(100); });
  const out = {
    moduleRows: labels,
    enabledMapAfterToggles: useModulesStore.getState().enabled,
    notesCmdsBefore: cmdsBefore.filter((c) => c.startsWith("notes")), notesCmdsAfter: cmdsAfter.filter((c) => c.startsWith("notes")),
    openPanelPortfolioWhileDisabled_addPanelCalls: addedWhilePortfolioOff, openPanelAfterReenable_addPanelCalls: addedAfterReenable, openErr,
    marketplaceAdds, marketplacePanelIdAdds, marketplaceSpec: useModulesStore.getState().findPanel("marketplace") ? "registered" : "missing",
    region: { before: regionBefore, afterStore: useSettingsStore.getState().region, rowAfter: text(regionSel.closest("section")).slice(0, 300) },
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
});
