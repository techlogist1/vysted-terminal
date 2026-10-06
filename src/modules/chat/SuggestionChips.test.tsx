import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { SuggestionChips } from "@/modules/chat/SuggestionChips";
import { useAgentCommandStore, resetAgentCommandStoreForTests } from "@/store/agent-command";
import { usePanelContextBus } from "@/store/panel-context";

function resetStores() {
  resetAgentCommandStoreForTests();
  usePanelContextBus.setState({
    lastEventBySource: {},
    focusedSource: null,
    updatedAt: 0,
  });
}

describe("SuggestionChips", () => {
  beforeEach(() => {
    resetStores();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the static finance defaults when no symbol is focused", () => {
    render(<SuggestionChips />);
    const region = screen.getByLabelText("Suggested prompts");
    const chips = within(region).getAllByRole("button");
    expect(chips.length).toBeGreaterThanOrEqual(3);
    expect(within(region).getByRole("button", { name: /Research \$NVDA/ })).toBeInTheDocument();
    expect(
      within(region).getByRole("button", { name: /Compare AAPL vs MSFT/ }),
    ).toBeInTheDocument();
    expect(
      within(region).getByRole("button", { name: /Summarize my portfolio P&L/ }),
    ).toBeInTheDocument();
  });

  it("clicking a chip drives the agent-command send path", () => {
    render(<SuggestionChips />);
    expect(useAgentCommandStore.getState().command).toBeNull();
    const chip = screen.getByRole("button", { name: /Research \$NVDA/ });
    fireEvent.click(chip);
    const command = useAgentCommandStore.getState().command;
    expect(command).not.toBeNull();
    expect(command?.prompt).toContain("$NVDA");
    expect(command?.seq).toBe(1);
  });

  it("each chip dispatches a distinct prompt and re-bumps the seq", () => {
    render(<SuggestionChips />);
    fireEvent.click(screen.getByRole("button", { name: /Research \$NVDA/ }));
    fireEvent.click(screen.getByRole("button", { name: /Compare AAPL vs MSFT/ }));
    const command = useAgentCommandStore.getState().command;
    expect(command?.prompt).toContain("$AAPL");
    expect(command?.prompt).toContain("$MSFT");
    expect(command?.seq).toBe(2);
  });

  it("is context-aware: a focused chart symbol leads with symbol-scoped chips", () => {
    usePanelContextBus.setState({
      lastEventBySource: {
        "chart-1": {
          source: "chart-1",
          kind: "snapshot",
          payload: { symbol: "TSLA", timeframe: "1D" },
          emittedAt: 1,
        },
      },
      focusedSource: "chart-1",
      updatedAt: 1,
    });
    render(<SuggestionChips />);
    expect(screen.getByRole("button", { name: /Research \$TSLA/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /What moved \$TSLA today/ })).toBeInTheDocument();
  });
});
