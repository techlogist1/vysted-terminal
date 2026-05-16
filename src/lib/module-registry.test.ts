import { describe, expect, it } from "vitest";

import { collectCommands, collectPanelComponents, collectPanels } from "@/lib/module-registry";
import { vystedModules } from "@/modules";

describe("module registry", () => {
  it("registers the Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 modules plus the Phase 6 Teammate E additions", () => {
    // Phase 6 (Teammate E) adds `earnings` and `analyst-ratings` to the registry.
    // Other Phase 6 teammates add their own ids when integrated; the assertion
    // is a strict equality so a registration drift fails loudly.
    expect([...vystedModules.map((module) => module.id)].sort()).toEqual([
      "agent-builder",
      "analyst-ratings",
      "backtest",
      "broker-connect",
      "chart",
      "chat",
      "earnings",
      "equity-overview",
      "news",
      "node-editor",
      "platform",
      "plugin-manager",
      "portfolio",
      "safety",
      "watchlist",
    ]);
  });

  it("every module declares at least one panel and one command", () => {
    for (const mod of vystedModules) {
      expect(mod.panels.length).toBeGreaterThan(0);
      expect(mod.commands.length).toBeGreaterThan(0);
    }
  });

  it("every panel has a registered component", () => {
    const components = collectPanelComponents(vystedModules);
    for (const panel of collectPanels(vystedModules)) {
      expect(components[panel.component]).toBeDefined();
    }
  });

  it("every command opens a panel or names a control-plane command", () => {
    for (const command of collectCommands(vystedModules)) {
      expect(Boolean(command.opensPanel) || Boolean(command.commandId)).toBe(true);
    }
  });

  it("panel ids are unique across modules", () => {
    const ids = collectPanels(vystedModules).map((panel) => panel.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("collectCommands flattens commands from every module", () => {
    const total = vystedModules.reduce((sum, module) => sum + module.commands.length, 0);
    expect(collectCommands(vystedModules)).toHaveLength(total);
  });
});
