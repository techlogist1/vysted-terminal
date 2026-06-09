import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatSidebar } from "@/modules/chat/ChatSidebar";
import { useAgentModeStore } from "@/store/agent-mode";
import { useAgentsStore, type AgentSummary } from "@/store/agents";
import { useChartSyncBus } from "@/store/chart-sync";
import { useChatHistoryStore } from "@/store/chat-history";
import { useChatPendingStore } from "@/store/chat-pending";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useOnboardingStore } from "@/store/onboarding";
import { usePanelContextBus } from "@/store/panel-context";
import { useProposedChangesStore } from "@/store/proposed-changes";
import { resetResearchDepthStoreForTests, useResearchDepthStore } from "@/store/research-depth";

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

vi.mock("@/modules/chat/streaming", () => ({
  streamChat: streamChatMock,
  streamAgentInvocation: streamAgentInvocationMock,
}));

const getSecretMock = vi.hoisted(() => vi.fn(async () => "sk-cached"));

vi.mock("@/lib/keychain", async () => {
  const actual = await vi.importActual<typeof import("@/lib/keychain")>("@/lib/keychain");
  return {
    ...actual,
    getSecret: getSecretMock,
    setSecret: vi.fn(async () => undefined),
  };
});

// Deterministic provider-readiness probe (no real network in jsdom). Defaults to
// "not reachable" so the Ollama-readiness gate is exercised; tests that need a
// reachable provider use a key-requiring provider (which skips this probe).
const validateProviderMock = vi.hoisted(() => vi.fn(async () => false));

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    validateProvider: validateProviderMock,
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
  });

  it("offers every first-party agent (by display name) in the lens chip's popover", () => {
    render(<ChatSidebar />);
    // R7: the standing persona select row is gone — the lens chip in the 24px
    // meta row opens ONE anchored popover holding the full roster.
    fireEvent.click(screen.getByRole("button", { name: /active lens/i }));
    for (const agent of FIRST_PARTY_AGENTS) {
      expect(screen.getByRole("option", { name: agent.name })).toBeInTheDocument();
    }
  });

  it("the lens chip always shows the display name, never a raw agent id", () => {
    render(<ChatSidebar />);
    fireEvent.click(screen.getByRole("button", { name: /active lens/i }));
    fireEvent.click(screen.getByRole("option", { name: "Warren Buffett" }));
    const chip = screen.getByRole("button", { name: /active lens/i });
    expect(chip.textContent).toContain("Warren Buffett");
    expect(chip.textContent).not.toBe("buffett");
  });

  it("replaces the old depth escalation with the three-stop slider (no toggle button)", () => {
    render(<ChatSidebar />);
    // The "+DEEP · GO ALL OUT" control and any Deep-Research toggle are gone…
    expect(
      screen.queryByRole("button", { name: /deep research|go deeper|go all out/i }),
    ).toBeNull();
    // …replaced by the segmented three-stop slider in the meta row.
    expect(screen.getByRole("radiogroup", { name: "Research depth" })).toBeInTheDocument();
    for (const label of ["Normal", "Deep", "Ultra"]) {
      expect(screen.getByRole("radio", { name: `${label} research depth` })).toBeInTheDocument();
    }
  });

  it("the depth slider sets the store and the depth rides the invocation options", async () => {
    render(<ChatSidebar />);
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

  it("the mode chip switches Agent ↔ Delegate through its popover", () => {
    render(<ChatSidebar />);
    fireEvent.click(screen.getByRole("button", { name: /agent mode/i }));
    fireEvent.click(screen.getByRole("option", { name: /delegate/i }));
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

  it("gates a keyless provider (Ollama) that isn't reachable by opening guided setup", async () => {
    // The ratified onboarding rule: a keyless local provider must be reachable
    // before the call fires. When it isn't (validateProvider false — no daemon in
    // jsdom), the send surfaces an honest status AND opens the first-run setup
    // flow (Track 2) rather than dead-ending; the data tools still work meanwhile.
    useOnboardingStore.setState({ forceOpen: false });
    useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/ask hi" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(screen.getByText(/set up yet/i)).toBeInTheDocument());
    expect(useOnboardingStore.getState().forceOpen).toBe(true);
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
});
