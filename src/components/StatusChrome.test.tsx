import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  __resetProviderProbeCacheForTests,
  formatModelLabel,
  StatusChrome,
} from "@/components/StatusChrome";
import { useAgentRunsStore } from "@/store/agent-runs";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { resetModelSelectionStoreForTests, useModelSelectionStore } from "@/store/model-selection";
import { useProviderKeysStore } from "@/store/provider-keys";

vi.mock("@/lib/sidecar-client", () => ({
  validateProvider: vi.fn().mockResolvedValue(true),
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

const sidecarClient = await import("@/lib/sidecar-client");
const mockValidateProvider = vi.mocked(sidecarClient.validateProvider);

describe("formatModelLabel", () => {
  it("brand-cases and spaces a hyphenated id (the operator's defect case)", () => {
    expect(formatModelLabel("deepseek-v4-flash")).toBe("DeepSeek V4 Flash");
  });

  it("drops the org prefix of an OpenRouter-style id", () => {
    expect(formatModelLabel("minimax/minimax-m3")).toBe("MiniMax M3");
  });

  it("uppercases short version tokens and parameter counts", () => {
    expect(formatModelLabel("deepseek-r1")).toBe("DeepSeek R1");
    expect(formatModelLabel("qwen2.5-72b-instruct")).toBe("Qwen2.5 72B Instruct");
  });

  it("keeps lowercase numeric variants intact (gpt-4o)", () => {
    expect(formatModelLabel("gpt-4o")).toBe("GPT 4o");
  });

  it("trims MIDDLE segments on a long id — never a mid-word ellipsis", () => {
    const label = formatModelLabel("llama-3.1-70b-instruct-extended-free");
    expect(label).toBe("Llama 3.1 70B … Free");
    // No word is ever cut in half: every output token is a whole input word or "…".
    for (const word of label.split(" ")) {
      expect(word === "…" || /^[\w.]+$/.test(word)).toBe(true);
    }
  });

  it("leaves a short, already-clean id readable", () => {
    expect(formatModelLabel("kimi-k2")).toBe("Kimi K2");
  });
});

describe("StatusChrome", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockValidateProvider.mockResolvedValue(true);
    __resetProviderProbeCacheForTests();
    useProviderKeysStore.setState({ status: {}, probed: false });
  });

  afterEach(() => {
    cleanup();
    useAgentRunsStore.setState({ runs: [] });
    resetModelSelectionStoreForTests();
  });

  it("renders the designed short model form, with the exact id in the tooltip", () => {
    useLLMProvidersStore.setState({
      providers: [{ id: "deepseek", label: "DeepSeek", requiresKey: true }],
      defaultProviderId: "deepseek",
    });
    useModelSelectionStore.setState({ overrides: { deepseek: "deepseek-v4-flash" } });
    render(<StatusChrome />);
    // The model id names its provider, so only the short model form renders…
    expect(screen.getByText("DeepSeek V4 Flash")).toBeInTheDocument();
    // …and the tooltip carries the exact raw id.
    expect(screen.getByTitle(/deepseek-v4-flash/)).toBeInTheDocument();
  });

  it("an unreachable keyless default renders the honest muted state (D60)", async () => {
    mockValidateProvider.mockResolvedValue(false);
    useLLMProvidersStore.setState({
      providers: [{ id: "ollama", label: "Ollama (local)", requiresKey: false }],
      defaultProviderId: "ollama",
    });
    useModelSelectionStore.setState({ overrides: { ollama: "qwen2.5:7b" } });
    render(<StatusChrome />);

    // The probe is fire-and-forget: the confident chip renders first, then
    // downgrades on the CONFIRMED failure.
    const chip = await screen.findByTestId("provider-not-ready");
    expect(chip).toHaveTextContent("Ollama (local) · not running — set up in Settings");
    expect(chip.title).toContain("isn't ready");
    // The model claim the app cannot back disappears with it.
    expect(screen.queryByText(/Qwen2\.5 7B/)).not.toBeInTheDocument();
    expect(mockValidateProvider).toHaveBeenCalledWith("ollama");
  });

  it("a reachable keyless default keeps exactly today's confident chip (D60)", async () => {
    mockValidateProvider.mockResolvedValue(true);
    useLLMProvidersStore.setState({
      providers: [{ id: "ollama", label: "Ollama (local)", requiresKey: false }],
      defaultProviderId: "ollama",
    });
    useModelSelectionStore.setState({ overrides: { ollama: "qwen2.5:7b" } });
    render(<StatusChrome />);

    await waitFor(() => {
      expect(mockValidateProvider).toHaveBeenCalledWith("ollama");
    });
    expect(screen.getByText("Ollama (local) · Qwen2.5 7B")).toBeInTheDocument();
    expect(screen.queryByTestId("provider-not-ready")).not.toBeInTheDocument();
  });

  it("a BYOK default with a MISSING key renders 'no API key' without probing (D60)", () => {
    useLLMProvidersStore.setState({
      providers: [{ id: "deepseek", label: "DeepSeek", requiresKey: true }],
      defaultProviderId: "deepseek",
    });
    useProviderKeysStore.setState({ status: { deepseek: "missing" }, probed: true });
    render(<StatusChrome />);

    const chip = screen.getByTestId("provider-not-ready");
    expect(chip).toHaveTextContent("DeepSeek · no API key — set up in Settings");
    // BYOK keys live in the OS keychain the probe cannot read — probing would
    // false-negative a configured provider, so it must not fire.
    expect(mockValidateProvider).not.toHaveBeenCalled();
  });

  it("a BYOK default with UNKNOWN key status never raises a false alarm (D60)", () => {
    useLLMProvidersStore.setState({
      providers: [{ id: "deepseek", label: "DeepSeek", requiresKey: true }],
      defaultProviderId: "deepseek",
    });
    // Outside the Tauri shell the keychain probe reports "unknown" — the chip
    // must stay confident rather than accuse a possibly-configured provider.
    useProviderKeysStore.setState({ status: { deepseek: "unknown" }, probed: true });
    useModelSelectionStore.setState({ overrides: { deepseek: "deepseek-v4-flash" } });
    render(<StatusChrome />);

    expect(screen.getByText("DeepSeek V4 Flash")).toBeInTheDocument();
    expect(screen.queryByTestId("provider-not-ready")).not.toBeInTheDocument();
    expect(mockValidateProvider).not.toHaveBeenCalled();
  });

  it("the probe result is cached — a re-mount does not re-probe (D60)", async () => {
    mockValidateProvider.mockResolvedValue(false);
    useLLMProvidersStore.setState({
      providers: [{ id: "ollama", label: "Ollama (local)", requiresKey: false }],
      defaultProviderId: "ollama",
    });
    const first = render(<StatusChrome />);
    await screen.findByTestId("provider-not-ready");
    first.unmount();

    render(<StatusChrome />);
    expect(await screen.findByTestId("provider-not-ready")).toBeInTheDocument();
    // One live probe total — the second mount served from the module cache.
    expect(mockValidateProvider).toHaveBeenCalledTimes(1);
  });

  it("the active-runs chip names the runs it counts (the '+N' tooltip)", () => {
    useLLMProvidersStore.setState({
      providers: [{ id: "deepseek", label: "DeepSeek", requiresKey: true }],
      defaultProviderId: "deepseek",
    });
    useAgentRunsStore.setState({
      runs: [
        {
          id: "r1",
          agentId: "buffett",
          agentName: "Warren Buffett",
          mode: "agent",
          status: "running",
          startedAt: 1,
        },
        {
          id: "r2",
          agentId: "researcher",
          agentName: "AI Researcher",
          mode: "delegate",
          status: "paused",
          startedAt: 2,
        },
        {
          id: "r3",
          agentId: null,
          agentName: "Done run",
          mode: "agent",
          status: "done",
          startedAt: 3,
        },
      ],
    });
    render(<StatusChrome />);
    const chip = screen.getByTitle(/2 agent runs in progress/);
    expect(chip.title).toContain("Warren Buffett");
    expect(chip.title).toContain("AI Researcher");
    expect(chip.title).not.toContain("Done run");
    expect(chip.textContent).toContain("2");
  });
});
