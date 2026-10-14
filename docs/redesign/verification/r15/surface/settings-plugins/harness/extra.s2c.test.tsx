import { test } from "vitest";
import fs from "fs";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";
import { vystedModules } from "@/modules";
import { applyHostAction } from "@/lib/host-actions";
import { collectPanelComponents } from "@/lib/module-registry";
const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c/out/extra-replay.json";
test("X1 openPanel ids + disabled module", () => {
  useModulesStore.getState().registerModules(vystedModules);
  const added: string[] = [];
  const fakeDock: any = { panels: [], groups: [], getPanel: () => undefined, addPanel(o: any) { added.push(`${o.id}|${o.component}`); return { api: { setSize() {}, setActive() {} } }; } };
  useWorkspaceStore.setState({ dockviewApi: fakeDock } as any);
  const r: Record<string, unknown> = {};
  const ws = useWorkspaceStore.getState();
  for (const id of ["marketplace-panel", "marketplace", "screener-panel", "screener", "portfolio", "notes"]) { added.length = 0; try { ws.openPanel(id); } catch (e) { added.push("THROW " + String(e)); } r[`open:${id}`] = added.slice(); }
  useModulesStore.getState().setModuleEnabled("portfolio", false);
  const enabledComponents = Object.keys(collectPanelComponents(useModulesStore.getState().enabledModules()));
  added.length = 0; ws.openPanel("portfolio"); r["open:portfolio(disabled)"] = added.slice();
  r.portfolioComponentMounted = enabledComponents.includes("portfolio-panel");
  added.length = 0; r.agentOpenPanelLabel = applyHostAction("open_panel", { panel: "portfolio" }); r.agentAdded = added.slice();
  added.length = 0; r.agentAddPosition = "n/a";
  useModulesStore.getState().setModuleEnabled("portfolio", true);
  fs.writeFileSync(OUT, JSON.stringify(r, null, 1));
});
