import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, act } from "@testing-library/react";
import { invokeShim, sleep, text } from "./mocks";
vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));
import { vystedModules } from "@/modules";
import { useModulesStore } from "@/store/modules";
import { useSettingsStore } from "@/store/settings";
import { SettingsPanel } from "@/components/SettingsPanel";
const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c-q/modules-replay.json";

test("S8 Modules toggles + S9 Region select", async () => {
  useModulesStore.getState().registerModules(vystedModules);
  const { container } = render(<SettingsPanel />);
  await act(async () => { await sleep(4000); });
  const sec = container.querySelector("#settings-modules")!.closest("section")!;
  const switches = Array.from(sec.querySelectorAll('input[role="switch"], button[role="switch"]')) as HTMLElement[];
  const labels = switches.map((s) => `${s.getAttribute("aria-label")}${(s as HTMLInputElement).disabled || s.hasAttribute("disabled") ? " [disabled]" : ""}`);
  const cmdsBefore = useModulesStore.getState().enabledCommands().map((c) => c.id);
  const notes = switches.find((s) => /^Notes/.test(s.getAttribute("aria-label") ?? ""));
  if (notes) fireEvent.click(notes);
  await act(async () => { await sleep(200); });
  const cmdsAfter = useModulesStore.getState().enabledCommands().map((c) => c.id);
  const regionSel = container.querySelector('select[aria-label="Region"]') as HTMLSelectElement;
  const regionBefore = { value: regionSel.value, store: useSettingsStore.getState().region, hint: text(regionSel.closest("div")?.parentElement).slice(0, 120) };
  fireEvent.change(regionSel, { target: { value: "US" } });
  await act(async () => { await sleep(100); });
  const out = {
    moduleRows: labels, moduleSectionText: text(sec).slice(0, 1500),
    enabledMapAfterNotesOff: useModulesStore.getState().enabled,
    notesCommandsBefore: cmdsBefore.filter((c) => c.startsWith("notes")), notesCommandsAfter: cmdsAfter.filter((c) => c.startsWith("notes")),
    region: { before: regionBefore, afterStore: useSettingsStore.getState().region },
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
});
