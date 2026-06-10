import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import { useWorkspaceStore } from "@/store/workspace";
import type { ResearchBriefData } from "../../../types/brief";

import { BriefPanel } from "./BriefPanel";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => null),
}));

/** A minimal sourced brief fixture — `backend` varies per test (gate 2: Team A
 *  guarantees the id on the published brief; the panel renders off it). */
function fixtureBrief(overrides: Partial<ResearchBriefData> = {}): ResearchBriefData {
  return {
    query: "What changed for SAKSOFT this quarter?",
    symbol: "SAKSOFT.NS",
    mode: "DEEP",
    depth: "deep",
    markdown: "Revenue grew on services momentum. [1]",
    sources: [
      {
        url: "https://example.com/report",
        title: "Quarterly results",
        excerpt: "Revenue grew.",
      },
    ],
    sourceCount: 1,
    webAvailable: true,
    createdAt: 1_700_000_000_000,
    ...overrides,
  };
}

const NUDGE_TEXT = /limited keyless search/i;

describe("BriefPanel keyless-fallback nudge (R9 gate 2)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders ONE quiet nudge when the brief's backend id is keyless-fallback", () => {
    useBriefStore.setState({ brief: fixtureBrief({ backend: "keyless-fallback" }) });
    render(<BriefPanel />);
    expect(screen.getAllByText(NUDGE_TEXT)).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: /set up unlimited local research/i }),
    ).toBeInTheDocument();
  });

  it("never renders for the searxng / research-model backends or an absent id", () => {
    for (const backend of ["searxng", "research-model:perplexity/sonar", undefined]) {
      useBriefStore.setState({ brief: fixtureBrief({ backend }) });
      render(<BriefPanel />);
      expect(screen.queryByText(NUDGE_TEXT)).toBeNull();
      cleanup();
    }
  });

  it("is dismissible per-brief: dismissed stays gone for THIS brief, a new brief re-shows it", () => {
    useBriefStore.setState({
      brief: fixtureBrief({ backend: "keyless-fallback", createdAt: 1_000 }),
    });
    render(<BriefPanel />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss the keyless search notice/i }));
    expect(screen.queryByText(NUDGE_TEXT)).toBeNull();
    // The NEXT published fallback brief shows the honest notice again.
    act(() => {
      useBriefStore.setState({
        brief: fixtureBrief({ backend: "keyless-fallback", createdAt: 2_000 }),
      });
    });
    expect(screen.getByText(NUDGE_TEXT)).toBeInTheDocument();
  });

  it("the setup link opens the Settings panel (Settings → Research)", () => {
    const openPanel = vi.fn();
    const original = useWorkspaceStore.getState().openPanel;
    useWorkspaceStore.setState({ openPanel });
    try {
      useBriefStore.setState({ brief: fixtureBrief({ backend: "keyless-fallback" }) });
      render(<BriefPanel />);
      fireEvent.click(screen.getByRole("button", { name: /set up unlimited local research/i }));
      expect(openPanel).toHaveBeenCalledWith("settings");
    } finally {
      useWorkspaceStore.setState({ openPanel: original });
    }
  });
});
