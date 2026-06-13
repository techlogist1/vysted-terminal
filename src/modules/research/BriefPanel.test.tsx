import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAgentCommandStoreForTests, useAgentCommandStore } from "@/store/agent-command";
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

// ── lifecycle surfaces (R10 D39/D37) ─────────────────────────────────────────

describe("BriefPanel lifecycle surfaces (R10)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    resetAgentCommandStoreForTests();
  });

  afterEach(() => {
    cleanup();
  });

  it("IN-FLIGHT renders the working skeleton — never a broken empty panel", () => {
    useBriefStore.setState({
      panel: {
        phase: "in_flight",
        runId: "run-1",
        query: "reliance Q4 results",
        depth: "deep",
        startedAt: Date.now() - 42_000,
        steps: [],
      },
      brief: null,
    });
    render(<BriefPanel />);
    expect(screen.getByText(/Researching — DEEP/)).toBeInTheDocument();
    expect(screen.getByText("reliance Q4 results")).toBeInTheDocument();
    // No empty-state copy mid-run.
    expect(screen.queryByText(/Ask JARVIS to research/)).toBeNull();
  });

  it("IN-FLIGHT shows the live research steps", () => {
    useBriefStore.setState({
      panel: {
        phase: "in_flight",
        runId: "run-1",
        query: "q",
        depth: "heavy",
        startedAt: Date.now(),
        steps: [{ kind: "search", detail: "scanning filings", status: "ok" }],
      },
      brief: null,
    });
    render(<BriefPanel />);
    expect(screen.getByLabelText("Research activity")).toBeInTheDocument();
    expect(screen.getByText("scanning filings")).toBeInTheDocument();
  });

  it("ARCHIVED renders the provenance strip and Refresh re-runs at the brief's depth", () => {
    const brief = fixtureBrief();
    useBriefStore.setState({
      panel: { phase: "archived", brief, archivedAt: Date.now(), reason: "restored" },
      brief,
    });
    render(<BriefPanel />);
    expect(screen.getByText(/Archived · produced/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    const command = useAgentCommandStore.getState().command;
    expect(command?.prompt).toBe("research SAKSOFT.NS at depth=deep");
    expect(command?.depth).toBe("deep");
  });

  it("a brief WITHOUT an execution record renders ARCHIVED by definition (D38)", () => {
    useBriefStore.setState({ brief: fixtureBrief() }); // legacy direct set, no panel phase
    render(<BriefPanel />);
    expect(screen.getByText(/Archived · produced/)).toBeInTheDocument();
  });

  it("a published brief WITH an execution record renders live (no archived strip)", () => {
    const brief = fixtureBrief({
      execution: { runId: "run-9", requestedDepth: "deep", loop: "iter" },
    });
    useBriefStore.setState({ panel: { phase: "published", brief }, brief });
    render(<BriefPanel />);
    expect(screen.queryByText(/Archived · produced/)).toBeNull();
  });

  it("DISAMBIGUATION renders the chooser instead of a body; a chip re-runs the research", () => {
    const brief = fixtureBrief({
      markdown: "",
      sources: [],
      sourceCount: 0,
      disambiguation: {
        query: "reliance",
        candidates: [
          {
            symbol: "RELIANCE",
            name: "Reliance Industries",
            exchange: "NSE",
            yahooSymbol: "RELIANCE.NS",
          },
          { symbol: "RPOWER", name: "Reliance Power", exchange: "NSE", yahooSymbol: "RPOWER.NS" },
        ],
      },
      execution: { runId: "run-d", requestedDepth: "deep", loop: "iter" },
    });
    useBriefStore.setState({ panel: { phase: "published", brief }, brief });
    render(<BriefPanel />);
    expect(screen.getByText("Which did you mean?")).toBeInTheDocument();
    expect(screen.queryByText(/Copy markdown/)).toBeNull(); // no body chrome
    fireEvent.click(screen.getByRole("button", { name: /^RELIANCE.*Industries/ }));
    const command = useAgentCommandStore.getState().command;
    expect(command?.prompt).toBe("research RELIANCE.NS at depth=deep");
    expect(command?.depth).toBe("deep");
  });
});
