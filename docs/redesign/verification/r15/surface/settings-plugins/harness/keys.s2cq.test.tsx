import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, act } from "@testing-library/react";
import { invokeShim, sleep, text } from "./mocks";
vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));
import { SettingsPanel } from "@/components/SettingsPanel";
import { useKeybindingsStore, matchesEvent } from "@/store/keybindings";
const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c-q/keys-replay.json";
test("S10 Keybindings: record Cmd+K onto 'Toggle agent panel', then Ctrl+K", async () => {
  const { container } = render(<SettingsPanel />);
  await act(async () => { await sleep(1500); });
  const out: Record<string, unknown> = {};
  for (const [label, ev] of [["meta+k", { key: "k", metaKey: true }], ["ctrl+k", { key: "k", ctrlKey: true }]] as const) {
    const rec = container.querySelector('button[aria-label="Record binding for Toggle agent panel"]') as HTMLButtonElement;
    fireEvent.click(rec);
    await act(async () => { await sleep(50); });
    const kbdWhileRecording = text(container.querySelector('kbd[aria-label="Toggle agent panel binding"]'));
    fireEvent.keyDown(rec, ev);
    await act(async () => { await sleep(100); });
    const alert = container.querySelector('#settings-keybindings')?.closest("section")?.querySelector('[role="alert"]');
    out[label] = {
      kbdWhileRecording,
      stored: useKeybindingsStore.getState().overrides["agent.toggle"],
      conflicts: useKeybindingsStore.getState().conflicts(),
      conflictBanner: text(alert),
      paletteAlsoMatches: typeof matchesEvent === "function" ? matchesEvent(useKeybindingsStore.getState().bindingFor("palette.open"), new KeyboardEvent("keydown", ev)) : "n/a",
      agentMatches: typeof matchesEvent === "function" ? matchesEvent(useKeybindingsStore.getState().bindingFor("agent.toggle"), new KeyboardEvent("keydown", ev)) : "n/a",
    };
  }
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
});
