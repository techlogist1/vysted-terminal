import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { formatModelLabel, StatusChrome } from "@/components/StatusChrome";
import { useAgentRunsStore } from "@/store/agent-runs";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { resetModelSelectionStoreForTests, useModelSelectionStore } from "@/store/model-selection";

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
