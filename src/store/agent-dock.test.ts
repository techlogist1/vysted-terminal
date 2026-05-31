import { beforeEach, describe, expect, it } from "vitest";

import {
  AGENT_DOCK_DEFAULT_WIDTH,
  AGENT_DOCK_MAX_WIDTH,
  AGENT_DOCK_MIN_WIDTH,
  resetAgentDockStoreForTests,
  useAgentDockStore,
} from "@/store/agent-dock";

describe("agent-dock store (FR-001)", () => {
  beforeEach(() => resetAgentDockStoreForTests());

  it("defaults to expanded at the default width", () => {
    expect(useAgentDockStore.getState().collapsed).toBe(false);
    expect(useAgentDockStore.getState().width).toBe(AGENT_DOCK_DEFAULT_WIDTH);
  });

  it("toggles collapsed (full-cockpit handoff)", () => {
    useAgentDockStore.getState().toggleCollapsed();
    expect(useAgentDockStore.getState().collapsed).toBe(true);
    useAgentDockStore.getState().toggleCollapsed();
    expect(useAgentDockStore.getState().collapsed).toBe(false);
  });

  it("clamps width to [MIN, MAX] so the column can't be dragged off-screen", () => {
    useAgentDockStore.getState().setWidth(10);
    expect(useAgentDockStore.getState().width).toBe(AGENT_DOCK_MIN_WIDTH);
    useAgentDockStore.getState().setWidth(99999);
    expect(useAgentDockStore.getState().width).toBe(AGENT_DOCK_MAX_WIDTH);
    useAgentDockStore.getState().setWidth(600);
    expect(useAgentDockStore.getState().width).toBe(600);
  });
});
