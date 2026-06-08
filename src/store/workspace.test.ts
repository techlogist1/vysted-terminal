import { describe, expect, it, vi } from "vitest";

import { chartModule } from "@/modules/chart";
import { useModulesStore } from "@/store/modules";
import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";

describe("layout name helpers", () => {
  it("the autosave slot is a reserved name", () => {
    expect(isReservedLayoutName(AUTOSAVE_LAYOUT_NAME)).toBe(true);
  });

  it("user layout names are not reserved", () => {
    expect(isReservedLayoutName("My Cockpit")).toBe(false);
    expect(isReservedLayoutName("default")).toBe(false);
    expect(isReservedLayoutName("trading-2026")).toBe(false);
  });

  it("treats any double-underscore-prefixed name as reserved/internal", () => {
    expect(isReservedLayoutName("__last_session__")).toBe(true);
    expect(isReservedLayoutName("__anything")).toBe(true);
  });
});

/**
 * A minimal dockview api stand-in for the singleton-reuse test: tracks added
 * panels by id and serves `getPanel`/`panels` from that record, so a second
 * `openPanel('chart')` can be observed to REUSE rather than mint (fixes #7).
 */
function fakeDockviewApi() {
  const byId = new Map<
    string,
    { id: string; api: { setSize: () => void; setActive: () => void } }
  >();
  const addPanel = vi.fn(({ id }: { id: string }) => {
    const panel = { id, api: { setSize: vi.fn(), setActive: vi.fn() } };
    byId.set(id, panel);
    return panel;
  });
  return {
    addPanel,
    getPanel: (id: string) => byId.get(id),
    get panels() {
      return [...byId.values()];
    },
  };
}

describe("openPanel chart dedup (singleton)", () => {
  it("a second openPanel('chart') reuses the SAME literal-id panel, never mints a duplicate", () => {
    // Register the real chart module so `findPanel('chart')` resolves its spec
    // (singleton:true) the same way the app does.
    useModulesStore.getState().registerModules([chartModule]);
    const api = fakeDockviewApi();
    useWorkspaceStore.setState({ dockviewApi: api as never });

    useWorkspaceStore.getState().openPanel("chart");
    useWorkspaceStore.getState().openPanel("chart");

    // Exactly one panel was minted, with the literal `chart` id — the second call
    // focused the existing one (no `chart-<ts>-<rand>` duplicate tab).
    expect(api.addPanel).toHaveBeenCalledTimes(1);
    expect(api.addPanel.mock.calls[0][0].id).toBe("chart");
    expect(api.panels).toHaveLength(1);
    expect(api.panels[0].id).toBe("chart");
  });
});
