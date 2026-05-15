import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatSidebar } from "@/modules/chat/ChatSidebar";
import { useAgentsStore, type AgentSummary } from "@/store/agents";
import { useChatHistoryStore } from "@/store/chat-history";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { usePanelContextBus } from "@/store/panel-context";

// ---- Mocks ----

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => null),
}));

const streamChatMock = vi.hoisted(() => vi.fn(async () => undefined));
const streamAgentInvocationMock = vi.hoisted(() => vi.fn(async () => undefined));

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

  it("renders the agent picker with all 12 first-party agents", () => {
    render(<ChatSidebar />);
    const picker = screen.getByLabelText("Agent picker") as HTMLSelectElement;
    const optionLabels = Array.from(picker.options).map((option) => option.text);
    // 1 (no-agent) + 12 first-party = 13 options.
    expect(picker.options.length).toBe(13);
    for (const agent of FIRST_PARTY_AGENTS) {
      expect(optionLabels).toContain(agent.name);
    }
  });

  it("renders an empty-state hint until a message is sent", () => {
    render(<ChatSidebar />);
    expect(screen.getByText(/Type/)).toBeInTheDocument();
    expect(screen.getByText("/ask")).toBeInTheDocument();
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
    expect(payload.contextSnapshot.bySource["chart-1"]).toEqual({ symbol: "SPY", timeframe: "1D" });
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
    getSecretMock.mockResolvedValueOnce(null as unknown as string);
    render(<ChatSidebar />);
    const input = screen.getByLabelText("Chat input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/ask hi" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() =>
      expect(screen.getByText(/no API key set for anthropic/)).toBeInTheDocument(),
    );
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
});
