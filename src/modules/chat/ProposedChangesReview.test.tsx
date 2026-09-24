import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ProposedChangesReview } from "@/modules/chat/ProposedChangesReview";
import { parseHostAction } from "@/lib/host-actions";
import {
  resetProposedChangesStoreForTests,
  useProposedChangesStore,
} from "@/store/proposed-changes";
import { useSymbolsStore } from "@/store/symbols";

describe("ProposedChangesReview", () => {
  afterEach(() => {
    cleanup();
    resetProposedChangesStoreForTests();
  });

  it("keeps an applied data write listed with Undo, which restores it (R15-AGENT-041)", () => {
    useSymbolsStore.setState({ entries: [{ symbol: "TSLA", assetClass: "equity" }] });
    useProposedChangesStore.setState({
      changes: [
        {
          id: "change-1",
          toolCallId: "tc-1",
          action: { name: "add_to_watchlist", input: { symbol: "TSLA" } },
          intent: parseHostAction("add_to_watchlist", { symbol: "TSLA" }),
          kind: "watchlist",
          title: "Add TSLA to your watchlist",
          before: "Watchlist: 0 symbols",
          after: "Watchlist: +TSLA (1 total)",
          status: "accepted",
          preImage: { kind: "watchlist-added", symbol: "TSLA" },
          batchId: "b",
          createdAt: 0,
        },
      ],
    });
    render(<ProposedChangesReview />);
    expect(screen.getByText("Applied: Add TSLA to your watchlist")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo: Add TSLA to your watchlist" }));
    expect(useSymbolsStore.getState().entries).toEqual([]);
    expect(useProposedChangesStore.getState().changes[0].status).toBe("undone");
  });
});
