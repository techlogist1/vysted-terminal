import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatSidebar, describeContext } from "@/modules/chat/ChatSidebar";
import {
  resetMessageNoticesForTests,
  useMessageNoticesStore,
} from "@/modules/chat/message-notices";
import { LENGTH_NOTICE } from "@/modules/chat/streaming";
import { parseHostAction } from "@/lib/host-actions";
import { resetAgentAutonomyStoreForTests, useAgentAutonomyStore } from "@/store/agent-autonomy";
import { resetAgentCommandStoreForTests, useAgentCommandStore } from "@/store/agent-command";
import { useAgentModeStore } from "@/store/agent-mode";
import { useAgentSpacesStore } from "@/store/agent-spaces";
import { useAgentsStore, type AgentSummary } from "@/store/agents";
import { resetBriefStoreForTests } from "@/store/brief";
import { useChartSyncBus } from "@/store/chart-sync";
import { useChatHistoryStore } from "@/store/chat-history";
import { useChatPendingStore } from "@/store/chat-pending";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useOnboardingStore } from "@/store/onboarding";
import { usePanelContextBus } from "@/store/panel-context";
import { useNotesStore } from "@/store/notes";
import { useProposedChangesStore } from "@/store/proposed-changes";
import { resetResearchDepthStoreForTests, useResearchDepthStore } from "@/store/research-depth";
import type { ProposedChange } from "../../../types/proposed-change";

// ---- Mocks ----

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => null),
}));

const streamChatMock = vi.hoisted(() => vi.fn(async () => undefined));
const streamAgentInvocationMock = vi.hoisted(() =>
  vi.fn<
    (
      agentId: string,
      payload: unknown,
      handlers: {
        onEvent: (event: unknown) => void;
        onError?: (err: Error) => void;
        signal?: AbortSignal;
      },
    ) => Promise<void>
  >(async () => undefined),
);

vi.mock("@/modules/chat/streaming", async () => {
  const actual = await vi.importActual<typeof import("@/modules/chat/streaming")>(
    "@/modules/chat/streaming",
  );
  return {
    ...actual,
    streamChat: streamChatMock,
    streamAgentInvocation: streamAgentInvocationMock,
  };
});

const getSecretMock = vi.hoisted(() => vi.fn(async () => "sk-cached"));

vi.mock("@/lib/keychain", async () => {
  const actual = await vi.importActual<typeof import("@/lib/keychain")>("@/lib/keychain");
  return {
    ...actual,
    getSecret: getSecretMock,
    setSecret: vi.fn(async () => undefined),
  };
});

// The provider-readiness probe (`@/lib/provider-validation`) runs for real; the
// tests that exercise the keyless gate answer its `fetch` themselves. Tests that
// need a reachable provider use a key-requiring provider (which skips the probe).
vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9000"),
  };
});

const FIRST_PARTY_AGENTS: AgentSummary[] = [
  {
    id: "buffett",
    name: "Warren Buffett",
    philosophy: "value",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "graham",
    name: "Benjamin Graham",
    philosophy: "deep value",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "lynch",
    name: "Peter Lynch",
    philosophy: "garp",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "munger",
    name: "Charlie Munger",
    philosophy: "lattice",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "marks",
    name: "Howard Marks",
    philosophy: "cycles",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "klarman",
    name: "Seth Klarman",
    philosophy: "contrarian",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "dalio",
    name: "Ray Dalio",
    philosophy: "macro",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "druckenmiller",
    name: "Stanley Druckenmiller",
    philosophy: "macro",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "soros",
    name: "George Soros",
    philosophy: "reflexivity",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "researcher",
    name: "AI Researcher",
    philosophy: "fundamental",
    tools: ["price_data"],
    defaultProvider: "openai",
    origin: "first-party",
  },
  {
    id: "portfolio_advisor",
    name: "AI Portfolio Advisor",
    philosophy: "rebalancing",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
  {
    id: "strategy_critic",
    name: "AI Strategy Critic",
    philosophy: "critique",
    tools: ["price_data"],
    defaultProvider: "anthropic",
    origin: "first-party",
  },
];

/** A staged (ASK-mode) write_note the user has not resolved yet. */
function pendingNoteChange(): ProposedChange {
  const input = { scope: "global", text: "Cochin looks stretched", mode: "replace" };
  return {
    id: "change-note",
    toolCallId: "tc-note",
    action: { name: "write_note", input },
    intent: parseHostAction("write_note", input),
    kind: "data-write",
    title: "Replace the note",
    before: "",
    after: "Cochin looks stretched",
    status: "pending",
    batchId: "b-note",
    createdAt: 0,
  };
}

function seedStores() {
  useAgentsStore.setState({
    firstPartyAgents: FIRST_PARTY_AGENTS,
    customAgents: [],
    customSummaries: [],
    loading: false,
    error: null,
    refresh: async () => undefined,
  });
  useChatHistoryStore.setState({
    messages: [],
    streamingMessageId: null,
  });
  useLLMProvidersStore.setState({
    providers: [
      { id: "anthropic", label: "Anthropic", requiresKey: true },
      { id: "openai", label: "OpenAI", requiresKey: true },
      { id: "ollama", label: "Ollama (local)", requiresKey: false },
    ],
    defaultProviderId: "anthropic",
  });
  usePanelContextBus.setState({
    lastEventBySource: {},
    focusedSource: null,
    updatedAt: 0,
  });
  useAgentModeStore.setState({ mode: "agent" });
  useProposedChangesStore.setState({ changes: [] });
  useChartSyncBus.setState({ symbol: null });
  useChatPendingStore.setState({ queue: [] });
  resetResearchDepthStoreForTests();
  resetAgentCommandStoreForTests();
  resetMessageNoticesForTests();
  resetBriefStoreForTests();
}

describe("ChatSidebar", () => {
  beforeEach(() => {
    seedStores();
    streamChatMock.mockClear();
    streamAgentInvocationMock.mockClear();
    getSecretMock.mockClear();
    getSecretMock.mockResolvedValue("sk-cached");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("offers every first-party agent (by display name) in the plus menu's persona drill", () => {
    render(<ChatSidebar />);
    // R9: the meta-row lens chip is dead — the + menu absorbs the persona
    // picker as a drill-in roster.
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /persona/i }));
    for (const agent of FIRST_PARTY_AGENTS) {
      expect(screen.getByRole("menuitemradio", { name: agent.name })).toBeInTheDocument();
    }
  });

  it("the persona row always shows the display name, never a raw agent id", () => {
    render(<ChatSidebar />);
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /persona/i }));
    fireEvent.mouseDown(screen.getByRole("menuitemradio", { name: "Warren Buffett" }));
    // The pick closed the menu; reopening shows the DISPLAY name on the row.
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    const row = screen.getByRole("menuitem", { name: /persona/i });
    expect(row.textContent).toContain("Warren Buffett");
    expect(row.textContent).not.toContain("buffett");
  });

  it("replaces the old depth escalation with the segmented three-stop pill (no toggle button)", () => {
    render(<ChatSidebar />);
    // The "+DEEP · GO ALL OUT" control and any Deep-Research toggle are gone…
    expect(
      screen.queryByRole("button", { name: /deep research|go deeper|go all out/i }),
    ).toBeNull();
    // …replaced by the segmented depth pill inside the composer's controls
    // row: the active stop shows at rest, all three on hover/focus.
    const pill = screen.getByRole("radiogroup", { name: "Research depth" });
    fireEvent.mouseEnter(pill);
    for (const label of ["Normal", "Deep", "Ultra"]) {
      expect(screen.getByRole("radio", { name: `${label} research depth` })).toBeInTheDocument();
    }
  });

  it("the depth pill sets the store and the depth rides the invocation options", async () => {
    render(<ChatSidebar />);
    fireEvent.mouseEnter(screen.getByRole("radiogroup", { name: "Research depth" }));
    fireEvent.click(screen.getByRole("radio", { name: "Deep research depth" }));
    expect(useResearchDepthStore.getState().depth).toBe("deep");
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "look at SPY" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    const payload = (streamAgentInvocationMock.mock.calls[0] as unknown[])[1] as {
      options?: Record<string, unknown>;
    };
    expect(payload.options?.researchDepth).toBe("deep");
  });

  it("the plus menu's Mode rows switch Agent ↔ Delegate", () => {
    render(<ChatSidebar />);
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    fireEvent.mouseDown(screen.getByRole("menuitemradio", { name: /delegate/i }));
    expect(useAgentModeStore.getState().mode).toBe("delegate");
  });

  it("the model chip opens the provider/model popover with the refresh affordance", () => {
    render(<ChatSidebar />);
    fireEvent.click(screen.getByRole("button", { name: /^model — /i }));
    expect(screen.getByRole("option", { name: "OpenAI" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh model list" })).toBeInTheDocument();
  });

  it("queues a prompt typed while streaming and drains it in order when the stream ends", async () => {
    let release!: () => void;
    streamAgentInvocationMock.mockImplementationOnce(
      (_id, _payload, handlers) =>
        new Promise<void>((resolve) => {
          release = () => {
            handlers.onEvent({ kind: "done" });
            resolve();
          };
        }),
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "first question" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    // The stream is live — typing stays enabled and Enter queues a visible chip.
    fireEvent.change(input, { target: { value: "second question" } });
    fireEvent.submit(input.closest("form")!);
    expect(useChatPendingStore.getState().queue).toEqual(["second question"]);
    expect(screen.getByText("second question")).toBeInTheDocument();
    release();
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(2));
    const second = (streamAgentInvocationMock.mock.calls[1] as unknown[])[1] as {
      prompt: string;
    };
    expect(second.prompt).toBe("second question");
    await waitFor(() => expect(useChatPendingStore.getState().queue).toEqual([]));
  });

  it("a queued chip's [x] removes it before it sends", async () => {
    let release!: () => void;
    streamAgentInvocationMock.mockImplementationOnce(
      (_id, _payload, handlers) =>
        new Promise<void>((resolve) => {
          release = () => {
            handlers.onEvent({ kind: "done" });
            resolve();
          };
        }),
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "keep streaming" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    fireEvent.change(input, { target: { value: "never send this" } });
    fireEvent.submit(input.closest("form")!);
    fireEvent.click(screen.getByRole("button", { name: "Remove queued prompt: never send this" }));
    expect(useChatPendingStore.getState().queue).toEqual([]);
    release();
    // The stream ends with an empty queue — nothing else fires.
    await waitFor(() => expect(useChatHistoryStore.getState().streamingMessageId).toBeNull());
    expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1);
  });

  it("the stop square aborts the in-flight stream and marks the message stopped", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      (_id, _payload, handlers) =>
        new Promise<void>((resolve) => {
          handlers.signal?.addEventListener("abort", () => {
            handlers.onError?.(new Error("aborted"));
            resolve();
          });
        }),
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "a long research question" } });
    fireEvent.submit(input.closest("form")!);
    const stop = await screen.findByRole("button", { name: /stop/i });
    fireEvent.click(stop);
    await waitFor(() => expect(useChatHistoryStore.getState().streamingMessageId).toBeNull());
    const assistant = useChatHistoryStore.getState().messages.find((m) => m.role === "assistant");
    expect(assistant?.stopped).toBe(true);
    expect(assistant?.error).toBeFalsy();
    // The transcript marks it quietly — a tertiary caption, not an error row.
    expect(screen.getByText("stopped")).toBeInTheDocument();
  });

  it("a stream call that rejects still settles the message and frees the composer", async () => {
    streamAgentInvocationMock.mockRejectedValueOnce(new Error("handler blew up"));
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "question" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(useChatHistoryStore.getState().streamingMessageId).toBeNull());
    const assistant = useChatHistoryStore.getState().messages.find((m) => m.role === "assistant");
    expect(assistant?.pending).toBe(false);
    expect(assistant?.error).toBe("handler blew up");
  });

  it("collapses a finished run's step trace into one disclosure line, expandable on demand", () => {
    useChatHistoryStore.setState({
      messages: [
        {
          id: "a1",
          role: "assistant",
          content: "Momentum looks stretched here.",
          pending: false,
          toolSteps: ["Reading your portfolio"],
          researchSteps: [
            { stepKind: "plan", detail: "decomposed the question", status: "ok", index: 1 },
            {
              stepKind: "search",
              detail: "searched filings",
              status: "ok",
              index: 2,
              latencyMs: 8000,
            },
            {
              stepKind: "synthesize",
              detail: "wrote the brief",
              status: "ok",
              index: 3,
              latencyMs: 4000,
            },
          ],
          createdAt: 0,
        },
      ],
      streamingMessageId: null,
    });
    render(<ChatSidebar />);
    // Prose first; the telemetry collapses to ONE quiet line — `▸ Worked for 12s · 4 steps`.
    expect(screen.getByText("Momentum looks stretched here.")).toBeInTheDocument();
    const disclosure = screen.getByRole("button", { name: /expand step trace/i });
    expect(disclosure.textContent).toContain("Worked for 12s · 4 steps");
    expect(screen.queryByText("Reading your portfolio")).toBeNull();
    expect(screen.queryByText("searched filings")).toBeNull();
    // Expanding reveals the ResearchActivity-style detail + humanized tool steps.
    fireEvent.click(disclosure);
    expect(screen.getByText("Reading your portfolio")).toBeInTheDocument();
    expect(screen.getByText("searched filings")).toBeInTheDocument();
    expect(screen.getByLabelText("Research activity")).toBeInTheDocument();
    // …and collapses back.
    fireEvent.click(screen.getByRole("button", { name: /collapse step trace/i }));
    expect(screen.queryByText("searched filings")).toBeNull();
  });

  it("keeps the live activity visible (no disclosure) while the run streams", () => {
    useChatHistoryStore.setState({
      messages: [
        {
          id: "a2",
          role: "assistant",
          content: "Digging in",
          pending: true,
          researchSteps: [
            { stepKind: "search", detail: "scanning the wire", status: "ok", index: 1 },
          ],
          researchStartedAt: Date.now(),
          createdAt: 0,
        },
      ],
      streamingMessageId: "a2",
    });
    render(<ChatSidebar />);
    // The animated trace renders as today — visible, never behind a disclosure.
    expect(screen.getByText("Researching")).toBeInTheDocument();
    expect(screen.getByText("scanning the wire")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /step trace/i })).toBeNull();
  });

  it("renders an empty-state hint until a message is sent", () => {
    render(<ChatSidebar />);
    expect(screen.getByText(/Ask anything about what you/)).toBeInTheDocument();
  });

  it("/ask <prompt> appends a user message and invokes streamChat with the keychain key", async () => {
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/ask is AAPL cheap?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamChatMock).toHaveBeenCalledTimes(1));
    const callArgs = (streamChatMock.mock.calls[0] as unknown as unknown[])[0] as {
      provider: string;
      messages: { content: string }[];
      apiKey?: string;
    };
    expect(callArgs.provider).toBe("anthropic");
    expect(callArgs.messages[0].content).toBe("is AAPL cheap?");
    expect(callArgs.apiKey).toBe("sk-cached");
    expect(getSecretMock).toHaveBeenCalledWith("llm-provider:anthropic");
    expect(useChatHistoryStore.getState().messages).toHaveLength(2);
    expect(useChatHistoryStore.getState().messages[0].role).toBe("user");
  });

  it("a raw chat cut at the output limit says so under the answer (R15-AGENT-026)", async () => {
    streamChatMock.mockImplementationOnce((async (
      _payload: unknown,
      handlers: { onEvent: (event: unknown) => void },
    ) => {
      handlers.onEvent({ kind: "delta", text: "RELIANCE closed at Rs 1,4" });
      handlers.onEvent({ kind: "done", finishReason: "length" });
    }) as unknown as () => Promise<undefined>);
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "/ask price of RELIANCE?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText(LENGTH_NOTICE)).toBeInTheDocument());
  });

  it("/agent buffett invokes the agent endpoint with the context snapshot", async () => {
    // Seed a chart panel context so the snapshot has content.
    usePanelContextBus.setState({
      lastEventBySource: {
        "chart-1": {
          source: "chart-1",
          kind: "snapshot",
          payload: { symbol: "SPY", timeframe: "1D" },
          emittedAt: 1,
        },
      },
      focusedSource: "chart-1",
      updatedAt: 1,
    });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/agent buffett is SPY a moat business?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    const [agentId, payload] = streamAgentInvocationMock.mock.calls[0] as unknown as unknown[] as [
      string,
      {
        prompt: string;
        contextSnapshot: { focusedSource: string; bySource: Record<string, unknown> };
      },
    ];
    expect(agentId).toBe("buffett");
    expect(payload.prompt).toBe("is SPY a moat business?");
    expect(payload.contextSnapshot.focusedSource).toBe("chart-1");
    // Phase 10: context is sent as the structured `__terminal__` snapshot, not
    // raw per-source payloads — the focused chart symbol is resolvable.
    const terminal = payload.contextSnapshot.bySource["__terminal__"] as {
      focusedSymbol: string;
      charts: { symbol: string }[];
    };
    expect(terminal.focusedSymbol).toBe("SPY");
    expect(terminal.charts[0].symbol).toBe("SPY");
  });

  it("ContextBadge hidden with no bus events, shown with one panel event (asserted on kind) (R15-CODE-FRONTEND-021)", () => {
    const bus = usePanelContextBus.getState();
    expect(describeContext(bus).kind).toBe("none");
    const { unmount } = render(<ChatSidebar />);
    expect(screen.queryByLabelText("Panel context")).toBeNull();
    unmount();
    bus.publish({
      source: "chart",
      kind: "snapshot",
      payload: { symbol: "SPY", timeframe: "1d" },
      emittedAt: 1,
    });
    const described = describeContext(usePanelContextBus.getState());
    expect(described.kind).toBe("panels");
    render(<ChatSidebar />);
    expect(screen.getByLabelText("Panel context")).toHaveTextContent(
      described.kind === "panels" ? described.text : "unreachable",
    );
  });

  it("a focused Equity Overview's ticker drives the badge, the chips and the snapshot (R15-CODE-FRONTEND-015)", async () => {
    // The real dockview ids: PanelHost focuses "equity-overview" while the
    // chart ("chart") still shows SPY.
    const bus = usePanelContextBus.getState();
    bus.publish({
      source: "chart",
      kind: "snapshot",
      payload: { symbol: "SPY", timeframe: "1d" },
      emittedAt: 1,
    });
    bus.publish({
      source: "equity-overview",
      kind: "symbol",
      payload: { ticker: "INFY", loadedSections: ["quote"] },
      emittedAt: 2,
    });
    bus.setFocusedSource("equity-overview");
    render(<ChatSidebar />);
    expect(screen.getByLabelText("Panel context")).toHaveTextContent(
      "Context: equity-overview (INFY)",
    );
    expect(screen.getByRole("button", { name: /Research \$INFY/ })).toBeInTheDocument();
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "/agent buffett is this a moat business?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    const payload = streamAgentInvocationMock.mock.calls[0]![1] as unknown as {
      contextSnapshot: { bySource: Record<string, { focusedSymbol: string }> };
    };
    expect(payload.contextSnapshot.bySource["__terminal__"].focusedSymbol).toBe("INFY");
  });

  it("an agent send carries the user's notes as __notes__ (R15-AGENT-020)", async () => {
    useNotesStore.setState({ general: "", bySymbol: { BDL: "exit if promoter pledge > 20%" } });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "/agent buffett does BDL still fit my thesis?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    const payload = streamAgentInvocationMock.mock.calls[0]![1] as unknown as {
      contextSnapshot: { bySource: Record<string, unknown> };
    };
    expect(payload.contextSnapshot.bySource["__notes__"]).toEqual({
      general: "",
      bySymbol: { BDL: "exit if promoter pledge > 20%" },
    });
    useNotesStore.setState({ general: "", bySymbol: {} });
  });

  it("/help shows the cheat-sheet without sending a message", () => {
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/help" } });
    fireEvent.submit(input.closest("form")!);
    expect(streamChatMock).not.toHaveBeenCalled();
    expect(streamAgentInvocationMock).not.toHaveBeenCalled();
    expect(screen.getByText(/\/ask <prompt>/)).toBeInTheDocument();
  });

  it("surfaces an error when no API key is set for the default provider", async () => {
    // Persistent null: the mount-time key-probe (provider-keys refresh) AND the
    // per-send getSecret both resolve to "no key", so the no-key path fires.
    getSecretMock.mockResolvedValue(null as unknown as string);
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/ask hi" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText(/No API key for anthropic/i)).toBeInTheDocument());
    expect(streamChatMock).not.toHaveBeenCalled();
  });

  it("a send with no key leaves no orphaned user turn and keeps the prompt (R15-UI-017)", async () => {
    getSecretMock.mockResolvedValue(null as unknown as string);
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "how is NVDA doing?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText(/No API key for anthropic/i)).toBeInTheDocument());
    expect(useChatHistoryStore.getState().messages).toEqual([]);
    expect(input.value).toBe("how is NVDA doing?");
  });

  it("a keyless provider whose model is not pulled opens setup at the download step (R15-AGENT-028)", async () => {
    // The ratified onboarding rule: a keyless local provider must be usable
    // before the call fires. Ollama is up but the model is not downloaded, so the
    // send opens the guided setup at its local-model download step.
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              ok: false,
              reason: "model_not_pulled",
              detail: "qwen2.5:7b is not downloaded in Ollama (local) yet.",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
      ),
    );
    useOnboardingStore.setState({ forceOpen: false, forceStep: null });
    useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/ask hi" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText(/not downloaded yet/i)).toBeInTheDocument());
    expect(useOnboardingStore.getState()).toMatchObject({ forceOpen: true, forceStep: "local" });
    expect(streamChatMock).not.toHaveBeenCalled();
  });

  it("a data engine that does not answer the probe is not 'no model set up' (R15-UI-013)", async () => {
    // The validate request itself fails (sidecar down): that is not a missing
    // model, so setup must NOT open; the status says the engine is not responding
    // and the prompt stays in the composer.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Load failed");
      }),
    );
    useOnboardingStore.setState({ forceOpen: false, forceStep: null });
    useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/ask hello there" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(screen.getByText(/data engine is not responding/i)).toBeInTheDocument(),
    );
    expect(useOnboardingStore.getState().forceOpen).toBe(false);
    expect(input.value).toBe("/ask hello there");
    expect(streamChatMock).not.toHaveBeenCalled();
  });

  it("/clear empties the conversation", () => {
    useChatHistoryStore.setState({
      messages: [{ id: "1", role: "user", content: "hi", createdAt: 0 }],
      streamingMessageId: null,
    });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/clear" } });
    fireEvent.submit(input.closest("form")!);
    expect(useChatHistoryStore.getState().messages).toEqual([]);
  });

  it("/clear rejects a pending write_note and acks it failed (R15-CODE-FRONTEND-032)", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    useProposedChangesStore.setState({ changes: [pendingNoteChange()] });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/clear" } });
    fireEvent.submit(input.closest("form")!);
    expect(useProposedChangesStore.getState().pending()).toEqual([]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, { body: string }];
    expect(url).toContain("/agents/actions/ack");
    expect(JSON.parse(init.body)).toMatchObject({ tool_call_id: "tc-note", status: "failed" });
  });

  it("switching to a new chat space rejects pending proposals (R15-CODE-FRONTEND-032)", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 200 })),
    );
    useProposedChangesStore.setState({ changes: [pendingNoteChange()] });
    render(<ChatSidebar />);
    fireEvent.click(screen.getByRole("button", { name: "New chat space" }));
    expect(useProposedChangesStore.getState().pending()).toEqual([]);
    const spaces = useAgentSpacesStore.getState();
    act(() => spaces.closeSpace(spaces.activeId));
  });

  it("the context badge reports the focused panel's symbol when populated", () => {
    usePanelContextBus.setState({
      lastEventBySource: {
        "chart-1": {
          source: "chart-1",
          kind: "snapshot",
          payload: { symbol: "AAPL", timeframe: "1D" },
          emittedAt: 1,
        },
      },
      focusedSource: "chart-1",
      updatedAt: 1,
    });
    render(<ChatSidebar />);
    expect(screen.getByLabelText("Panel context").textContent).toContain("AAPL");
    expect(screen.getByLabelText("Panel context").textContent).toContain("1D");
  });

  it("passes the active mode to the agent invocation (default Agent — FR-003, Track B)", async () => {
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/agent buffett look at SPY" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    const payload = (streamAgentInvocationMock.mock.calls[0] as unknown[])[1] as { mode?: string };
    // Default is the inferred Agent surface; the sidecar derives read/edit/build.
    expect(payload.mode).toBe("agent");
  });

  it("stages an agent-proposed cockpit mutation as a reviewable diff — never auto-applies (FR-010)", async () => {
    useAgentModeStore.setState({ mode: "agent" });
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({
          kind: "tool_use",
          name: "set_chart_symbol",
          input: { symbol: "NVDA" },
          toolCallId: "tc-1",
        });
        handlers.onEvent({ kind: "done" });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "build me an NVDA view" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(useProposedChangesStore.getState().changes.length).toBe(1));
    const change = useProposedChangesStore.getState().changes[0];
    expect(change.status).toBe("pending");
    expect(change.action).toEqual({ name: "set_chart_symbol", input: { symbol: "NVDA" } });
    // The mutation did NOT apply — the chart bus is untouched until acceptance.
    expect(useChartSyncBus.getState().symbol).toBeNull();
  });

  it("under AUTO a staged data write reads 'Proposed:', never 'Applied:'", async () => {
    useAgentAutonomyStore.setState({ autonomy: "auto" });
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({
          kind: "tool_use",
          name: "portfolio_delete_position",
          input: { symbol: "RELIANCE" },
          toolCallId: "tc-del",
        });
        handlers.onEvent({ kind: "done" });
      },
    );
    try {
      render(<ChatSidebar />);
      const input = screen.getByLabelText("Chat input") as HTMLInputElement;
      fireEvent.change(input, { target: { value: "drop reliance" } });
      fireEvent.submit(input.closest("form")!);
      await waitFor(() => expect(useProposedChangesStore.getState().changes.length).toBe(1));
      expect(useProposedChangesStore.getState().changes[0].status).toBe("pending");
      // The line is written once the gate resolves the change (staged here).
      await waitFor(() =>
        expect(assistantSteps().some((s) => s.startsWith("Proposed: Remove RELIANCE"))).toBe(true),
      );
      expect(assistantSteps().some((s) => s.startsWith("Applied:"))).toBe(false);
    } finally {
      resetAgentAutonomyStoreForTests();
    }
  });

  it("under AUTO a failing auto-apply writes no 'Applied:' line, it says why (R15-AGENT-032)", async () => {
    useAgentAutonomyStore.setState({ autonomy: "auto" });
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({
          kind: "tool_use",
          name: "open_panel",
          input: { panel: "flux-capacitor" },
          toolCallId: "tc-open",
        });
        handlers.onEvent({ kind: "done" });
      },
    );
    try {
      render(<ChatSidebar />);
      const input = screen.getByLabelText("Chat input") as HTMLInputElement;
      fireEvent.change(input, { target: { value: "open the flux capacitor" } });
      fireEvent.submit(input.closest("form")!);
      await waitFor(() =>
        expect(assistantSteps().some((s) => s.startsWith("Couldn't apply: Open Flux"))).toBe(true),
      );
      expect(assistantSteps().some((s) => s.startsWith("Applied:"))).toBe(false);
      expect(useProposedChangesStore.getState().changes[0].status).toBe("pending");
    } finally {
      resetAgentAutonomyStoreForTests();
    }
  });
});

function assistantSteps(): string[] {
  const assistant = useChatHistoryStore.getState().messages.find((m) => m.role === "assistant");
  return assistant?.toolSteps ?? [];
}

// ── R10: refresh depth override, structured errors, divergence chips, E10 ───

describe("ChatSidebar — R10 brief/error honesty", () => {
  beforeEach(() => {
    seedStores();
    streamChatMock.mockClear();
    streamAgentInvocationMock.mockClear();
    getSecretMock.mockClear();
    getSecretMock.mockResolvedValue("sk-cached");
  });

  afterEach(() => {
    cleanup();
  });

  it("a depth-carrying agent command OVERRIDES the slider depth on the wire (E2 UI leg)", async () => {
    // Slider sits at normal; the archived-brief Refresh / go-deeper escalates
    // to heavy — the send must ride research_depth=ultra, not the slider.
    render(<ChatSidebar />);
    useAgentCommandStore.getState().send("research SAKSOFT at depth=heavy", "heavy");
    await waitFor(() => expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1));
    const payload = (streamAgentInvocationMock.mock.calls[0] as unknown[])[1] as {
      prompt: string;
      options?: Record<string, unknown>;
    };
    expect(payload.prompt).toBe("research SAKSOFT at depth=heavy");
    expect(payload.options?.researchDepth).toBe("ultra");
    // The slider itself is untouched — the override was per-send.
    expect(useResearchDepthStore.getState().depth).toBe("normal");
  });

  it("renders a STRUCTURED error frame as message + action + a Details disclosure (E9)", async () => {
    // The only provider — a 402 has no configured provider to fall back to
    // (R15-UI-087), so the error itself renders.
    useLLMProvidersStore.setState({
      providers: [{ id: "anthropic", label: "Anthropic", requiresKey: true }],
    });
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({
          kind: "error",
          message: "Your DeepSeek balance is empty — top up or switch provider.",
          action: "Top up or switch provider in Settings.",
          detail: 'Error code: 402 - {"error":{"message":"Insufficient Balance"}}',
          code: "provider_402",
        });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "research reliance" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(
        screen.getByText("Your DeepSeek balance is empty — top up or switch provider."),
      ).toBeInTheDocument(),
    );
    // The structured frame drops the legacy "Something went wrong —" prefix…
    expect(screen.queryByText(/Something went wrong/)).toBeNull();
    // …surfaces the next step…
    expect(screen.getByText("Top up or switch provider in Settings.")).toBeInTheDocument();
    // …and keeps the raw provider text behind the Details toggle.
    expect(screen.queryByText(/Insufficient Balance/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Details" }));
    expect(screen.getByText(/Insufficient Balance/)).toBeInTheDocument();
    // Retry survives.
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("a legacy plain-string error renders exactly as before (no Details)", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({ kind: "error", message: "boom" });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "hello" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(screen.getByText(/Something went wrong — boom/)).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: "Details" })).toBeNull();
  });

  // R15-UI-087 (FR-038, D-B11-7): a provider failure before any answer text
  // falls back to the next configured provider in the preference order.
  it("a first-provider auth failure is answered by the next configured provider, and the notice names both", async () => {
    streamAgentInvocationMock
      .mockImplementationOnce(async (_id, _payload, handlers) => {
        handlers.onEvent({
          kind: "error",
          message: "The Anthropic API key was rejected — check it in Settings.",
          code: "auth",
        });
      })
      .mockImplementationOnce(async (_id, _payload, handlers) => {
        handlers.onEvent({ kind: "delta", text: "The market is up 0.4% today." });
        handlers.onEvent({ kind: "done" });
      });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "how is SPY doing" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(screen.getByText("The market is up 0.4% today.")).toBeInTheDocument(),
    );
    expect(streamAgentInvocationMock).toHaveBeenCalledTimes(2);
    const calls = streamAgentInvocationMock.mock.calls.map(
      (call) => call[1] as { provider: string; apiKey?: string },
    );
    expect(calls.map((c) => c.provider)).toEqual(["anthropic", "openai"]);
    expect(calls[1].apiKey).toBe("sk-cached");
    const assistant = useChatHistoryStore.getState().messages.find((m) => m.role === "assistant")!;
    expect(assistant.error).toBeFalsy();
    const notices = useMessageNoticesStore.getState().notices[assistant.id] ?? [];
    expect(notices).toHaveLength(1);
    expect(notices[0]).toMatch(/Anthropic could not answer: .*Retried with OpenAI\./);
  });

  it("a provider failure AFTER answer text does not fall back", async () => {
    streamAgentInvocationMock.mockImplementationOnce(async (_id, _payload, handlers) => {
      handlers.onEvent({ kind: "delta", text: "Partial answer" });
      handlers.onEvent({
        kind: "error",
        message: "Could not reach Anthropic — check your network.",
        code: "network",
      });
    });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "how is SPY doing" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(
        screen.getByText("Could not reach Anthropic — check your network."),
      ).toBeInTheDocument(),
    );
    expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1);
  });

  it("a content error (not a provider failure) does not fall back", async () => {
    streamAgentInvocationMock.mockImplementationOnce(async (_id, _payload, handlers) => {
      handlers.onEvent({
        kind: "error",
        message: "The conversation is too long for this Anthropic model.",
        code: "context_overflow",
      });
    });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "how is SPY doing" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(
        screen.getByText("The conversation is too long for this Anthropic model."),
      ).toBeInTheDocument(),
    );
    expect(streamAgentInvocationMock).toHaveBeenCalledTimes(1);
  });

  it("a history compaction notice renders the older-turns marker and the context meter (R15-AGENT-040)", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({
          kind: "research_step",
          toolCallId: "",
          tool: "history",
          stepKind: "notice",
          detail: "Older turns summarised: the 4 earliest messages of this thread were folded.",
          status: "ok",
          index: 1,
        });
        handlers.onEvent({ kind: "delta", text: "BDL delivered 92% of FY26 guidance." });
        handlers.onEvent({
          kind: "done",
          usage: { inputTokens: 6_000, outputTokens: 192 },
          contextWindow: 32_768,
        });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "and the latest quarter?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(screen.getByRole("note", { name: "Older turns summarised" })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/the 4 earliest messages/)).toBeNull();
    expect(screen.getByLabelText("Context meter")).toHaveTextContent(
      "Context 6,192 / 32,768 tokens (19%)",
    );
  });

  // R15-AGENT-082: the done frame's spend_usd (parsed camelCase by streaming.ts
  // as spendUsd) reaches the finished message's own footer, distinct from the
  // composer-wide context meter above.
  it("a finished message's footer shows tokens and estimated spend (R15-AGENT-082)", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({ kind: "delta", text: "AAPL closed at $214." });
        handlers.onEvent({
          kind: "done",
          usage: { inputTokens: 500, outputTokens: 20 },
          spendUsd: 0.0042,
        });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "AAPL?" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText("520 tok · ~$0.00")).toBeInTheDocument());
  });

  it("a free model's finished message shows ~$0.00, not a hidden spend (R15-AGENT-082)", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({ kind: "delta", text: "ok" });
        handlers.onEvent({
          kind: "done",
          usage: { inputTokens: 10, outputTokens: 2 },
          spendUsd: 0,
        });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "hi" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText("12 tok · ~$0.00")).toBeInTheDocument());
  });

  it("a message with no spend_usd (unpriced model) shows tokens with no spend segment", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({ kind: "delta", text: "ok" });
        handlers.onEvent({ kind: "done", usage: { inputTokens: 10, outputTokens: 2 } });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "hi" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText("12 tok")).toBeInTheDocument());
    expect(screen.queryByText(/\$/)).toBeNull();
  });

  // R15-AGENT-031 / R15-UI-054: this used to feed the regex's own stale copy on
  // the engine kind; the chip now keys on the notice kind, so the runtime's
  // current wording (which the old regex never matched) renders as a chip.
  it("renders a runtime notice as a quiet chip by kind, not a step row (C9)", async () => {
    streamAgentInvocationMock.mockImplementationOnce(
      async (_id: unknown, _payload: unknown, handlers: { onEvent: (event: unknown) => void }) => {
        handlers.onEvent({
          kind: "research_step",
          toolCallId: "pub-1",
          tool: "publish_brief",
          stepKind: "notice",
          detail: "The brief panel reported the publish failed (AAPL).",
          status: "error",
          index: 1,
        });
        handlers.onEvent({ kind: "delta", text: "Here is the report." });
        handlers.onEvent({ kind: "done" });
      },
    );
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input");
    fireEvent.change(input, { target: { value: "research reliance" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(
        screen.getByText("The brief panel reported the publish failed (AAPL)."),
      ).toBeInTheDocument(),
    );
    // It is a transcript chip — NOT a collapsed step-trace entry.
    expect(screen.queryByRole("button", { name: /step trace/i })).toBeNull();
  });

  it("E10: the streaming caret never reaches over the message eyebrow on an empty body", () => {
    useChatHistoryStore.setState({
      messages: [{ id: "m1", role: "assistant", content: "", pending: true, createdAt: 0 }],
      streamingMessageId: "m1",
    });
    render(<ChatSidebar />);
    const caret = screen.getByTestId("stream-caret");
    // No preceding body block → the gap-cancelling negative margin must be OFF
    // (it used to pull the caret up over the "VYSTED COPILOT" eyebrow).
    expect(caret.className).not.toContain("-mt-4");
  });

  it("E10: with rendered content the caret keeps its gap-cancelling margin", () => {
    useChatHistoryStore.setState({
      messages: [
        {
          id: "m2",
          role: "assistant",
          content: "Reading the filings now.",
          pending: true,
          createdAt: 0,
        },
      ],
      streamingMessageId: "m2",
    });
    render(<ChatSidebar />);
    expect(screen.getByTestId("stream-caret").className).toContain("-mt-4");
  });
});
