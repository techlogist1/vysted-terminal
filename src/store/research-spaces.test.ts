import { beforeEach, describe, expect, it } from "vitest";

import { type ChatMessage, useChatHistoryStore } from "./chat-history";
import { summarizeTranscript, useResearchSpacesStore } from "./research-spaces";

function msg(role: "user" | "assistant", content: string, createdAt = 0): ChatMessage {
  return { id: `${content}-${Math.random()}`, role, content, createdAt };
}

describe("research-spaces store — per-space agent memory", () => {
  beforeEach(() => {
    useResearchSpacesStore.setState({ byName: {} });
    useChatHistoryStore.getState().clear();
  });

  it("saveSpace captures the live transcript (filtering empties) with a derived summary", () => {
    useChatHistoryStore.getState().loadMessages([
      msg("user", "is NVDA cheap?", 1),
      msg("assistant", "", 2), // a still-streaming empty turn is dropped
      msg("assistant", "It trades at a premium to peers.", 3),
    ]);

    const memory = useResearchSpacesStore.getState().saveSpace("Research: NVDA", "NVDA");
    expect(memory).not.toBeNull();
    expect(memory!.symbol).toBe("NVDA");
    expect(memory!.transcript.map((t) => t.content)).toEqual([
      "is NVDA cheap?",
      "It trades at a premium to peers.",
    ]);
    expect(memory!.summary).toContain("NVDA");
    // Stored in the keyed archive.
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")?.transcript).toHaveLength(
      2,
    );
  });

  it("restoreSpace replays a saved transcript into the live chat history", () => {
    useResearchSpacesStore.setState({
      byName: {
        "Research: AMD": {
          symbol: "AMD",
          transcript: [
            { role: "user", content: "MI300 ramp?", createdAt: 1 },
            { role: "assistant", content: "Accelerating into next year.", createdAt: 2 },
          ],
          updatedAt: 0,
        },
      },
    });

    useResearchSpacesStore.getState().restoreSpace("Research: AMD");
    expect(useChatHistoryStore.getState().messages.map((m) => m.content)).toEqual([
      "MI300 ramp?",
      "Accelerating into next year.",
    ]);
    // None left pending/streaming.
    expect(useChatHistoryStore.getState().streamingMessageId).toBeNull();
    expect(useChatHistoryStore.getState().messages.some((m) => m.pending)).toBe(false);
  });

  it("restoreSpace clears the live history when the space has no saved memory", () => {
    useChatHistoryStore.getState().loadMessages([msg("user", "leftover", 1)]);
    useResearchSpacesStore.getState().restoreSpace("Research: UNKNOWN");
    expect(useChatHistoryStore.getState().messages).toHaveLength(0);
  });

  it("switchSpace archives the space being left and restores the one being entered", () => {
    // In the NVDA space with a live conversation.
    useChatHistoryStore.getState().loadMessages([msg("user", "nvda q", 1)]);

    // Switch from NVDA → MSFT (a fresh space).
    useResearchSpacesStore
      .getState()
      .switchSpace(
        { name: "Research: NVDA", symbol: "NVDA" },
        { name: "Research: MSFT", symbol: "MSFT" },
      );
    // NVDA's transcript is archived; MSFT starts empty.
    expect(
      useResearchSpacesStore.getState().getMemory("Research: NVDA")?.transcript[0]?.content,
    ).toBe("nvda q");
    expect(useChatHistoryStore.getState().messages).toHaveLength(0);

    // Talk in MSFT, then switch back to NVDA.
    useChatHistoryStore.getState().loadMessages([msg("user", "msft q", 2)]);
    useResearchSpacesStore
      .getState()
      .switchSpace(
        { name: "Research: MSFT", symbol: "MSFT" },
        { name: "Research: NVDA", symbol: "NVDA" },
      );
    expect(useChatHistoryStore.getState().messages.map((m) => m.content)).toEqual(["nvda q"]);
    expect(
      useResearchSpacesStore.getState().getMemory("Research: MSFT")?.transcript[0]?.content,
    ).toBe("msft q");
  });

  it("switchSpace into a non-research space (null next) archives + clears the live thread", () => {
    useChatHistoryStore.getState().loadMessages([msg("user", "nvda q", 1)]);
    useResearchSpacesStore.getState().switchSpace({ name: "Research: NVDA", symbol: "NVDA" }, null);
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")?.transcript).toHaveLength(
      1,
    );
    expect(useChatHistoryStore.getState().messages).toHaveLength(0);
  });

  it("snapshot / replaceAll round-trip the archive in the workspace-blob shape", () => {
    useResearchSpacesStore.getState().saveSpace("Research: NVDA", "NVDA");
    const snap = useResearchSpacesStore.getState().snapshot();
    expect(snap.byName["Research: NVDA"]).toBeDefined();

    useResearchSpacesStore.setState({ byName: {} });
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")).toBeNull();

    useResearchSpacesStore.getState().replaceAll(snap);
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")?.symbol).toBe("NVDA");
  });

  // --- R13 JARVIS 3a: stated-value claims ledger -----------------------------

  it("recordClaims appends bounded claims and seeds a memory entry when absent", () => {
    useResearchSpacesStore.getState().recordClaims("Research: NVDA", [
      { symbol: "NVDA", metric: "P/E", value: 55, statedAt: 1 },
      { symbol: "NVDA", metric: "Price", value: 900, statedAt: 1 },
    ]);
    const mem = useResearchSpacesStore.getState().getMemory("Research: NVDA");
    expect(mem?.symbol).toBe("NVDA");
    expect(mem?.claims).toHaveLength(2);
    // A second record appends (a later turn adds to the ledger).
    useResearchSpacesStore
      .getState()
      .recordClaims("Research: NVDA", [{ symbol: "NVDA", metric: "P/E", value: 52, statedAt: 2 }]);
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")?.claims).toHaveLength(3);
  });

  it("recordClaims caps the ledger at 50 (keeps the most recent)", () => {
    const many = Array.from({ length: 60 }, (_, i) => ({
      symbol: "NVDA",
      metric: `M${i}`,
      value: i,
      statedAt: i,
    }));
    useResearchSpacesStore.getState().recordClaims("Research: NVDA", many);
    const claims = useResearchSpacesStore.getState().getMemory("Research: NVDA")?.claims ?? [];
    expect(claims).toHaveLength(50);
    expect(claims[claims.length - 1].metric).toBe("M59");
  });

  it("recordClaims is a no-op for an empty name or empty list", () => {
    useResearchSpacesStore
      .getState()
      .recordClaims("", [{ symbol: "NVDA", metric: "P/E", value: 55, statedAt: 1 }]);
    useResearchSpacesStore.getState().recordClaims("Research: NVDA", []);
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")).toBeNull();
  });

  it("saveSpace preserves the claims ledger; snapshot/replaceAll round-trip it", () => {
    useResearchSpacesStore
      .getState()
      .recordClaims("Research: NVDA", [{ symbol: "NVDA", metric: "P/E", value: 55, statedAt: 1 }]);
    // A save rebuilds the transcript but must NOT wipe the claims.
    useResearchSpacesStore.getState().saveSpace("Research: NVDA", "NVDA");
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")?.claims).toHaveLength(1);
    // Round-trip through the workspace-blob shape.
    const snap = useResearchSpacesStore.getState().snapshot();
    expect(snap.byName["Research: NVDA"].claims).toHaveLength(1);
    useResearchSpacesStore.setState({ byName: {} });
    useResearchSpacesStore.getState().replaceAll(snap);
    expect(useResearchSpacesStore.getState().getMemory("Research: NVDA")?.claims).toEqual([
      { symbol: "NVDA", metric: "P/E", value: 55, statedAt: 1 },
    ]);
  });

  it("summarizeTranscript handles an empty transcript and trims/condenses recent questions", () => {
    expect(summarizeTranscript([], "NVDA")).toMatch(/New research space for NVDA/);
    const summary = summarizeTranscript(
      [
        { role: "user", content: "first  question\nwith   whitespace", createdAt: 1 },
        { role: "assistant", content: "answer", createdAt: 2 },
        { role: "user", content: "second question", createdAt: 3 },
      ],
      "NVDA",
    );
    expect(summary).toContain("NVDA");
    expect(summary).toContain("2 questions");
    expect(summary).toContain("first question with whitespace");
  });
});
