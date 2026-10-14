import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentDock } from "@/components/AgentDock";
import { resetAgentDockStoreForTests, useAgentDockStore } from "@/store/agent-dock";

vi.mock("@/modules/chat/ChatSidebar", () => ({ ChatSidebar: () => <div>agent</div> }));

describe("AgentDock maximize (R15-UI-084)", () => {
  beforeEach(() => resetAgentDockStoreForTests());

  it("fills the cockpit while the dockview host stays mounted, hidden at its prior box", () => {
    render(
      <AgentDock>
        <div data-testid="panel-host">cockpit</div>
      </AgentDock>,
    );
    act(() => {
      useAgentDockStore.getState().setWidth(640);
      useAgentDockStore.getState().toggleMaximized();
    });

    const cockpit = screen.getByTestId("agent-dock-cockpit");
    expect(cockpit).toContainElement(screen.getByTestId("panel-host"));
    expect(cockpit).toHaveClass("invisible");
    expect(cockpit).toHaveAttribute("aria-hidden", "true");
    expect(cockpit.style.left).toBe("652px");
    expect(screen.getByTestId("agent-dock-track").style.width).toBe("100%");

    act(() => useAgentDockStore.getState().toggleMaximized());
    expect(cockpit).not.toHaveClass("invisible");
    expect(screen.getByTestId("agent-dock-track").style.width).toBe("640px");
  });
});
