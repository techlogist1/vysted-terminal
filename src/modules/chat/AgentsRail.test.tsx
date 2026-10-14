import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Start/resume go through the real `sidecarRequest`; the core reports a bound engine.
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => ({ port: 51763, state: "ready", reason: null })),
}));
vi.mock("@/lib/keychain", () => ({
  KEYCHAIN_NAMESPACES: { llmProvider: (id: string) => `llm-provider:${id}` },
  getSecret: (account: string) =>
    Promise.resolve(account === "llm-provider:openrouter" ? "sk-or-test" : null),
}));

import { stopDelegatePolling } from "@/lib/delegate-runs";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { AgentsRail } from "@/modules/chat/AgentsRail";
import { resetAgentRunsStoreForTests, useAgentRunsStore } from "@/store/agent-runs";

/** The region and research-tier headers every sidecar request carries. */
const SIDECAR_HEADERS = { "X-Vysted-Region": "IN", "X-Vysted-Research-Tier": "tier_a" };

function seedErroredRun(): string {
  const store = useAgentRunsStore.getState();
  const id = store.startRun({
    agentId: "copilot",
    agentName: "Copilot",
    mode: "delegate",
    provider: "openrouter",
    sidecarRunId: "run-5",
  });
  store.endRun(id, "error", "token ceiling 1000 reached (100000 used)");
  return id;
}

describe("AgentsRail", () => {
  beforeEach(async () => {
    resetAgentRunsStoreForTests();
    // Resolve (and cache) the base URL so each test's fetch stub sees only the
    // run requests, never the one-off `/health` readiness probe.
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
    await getSidecarBaseUrl();
  });
  afterEach(() => {
    cleanup();
    stopDelegatePolling();
    vi.unstubAllGlobals();
  });

  it("resumes an errored delegate run with its provider key in a header (R15-AGENT-035)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    vi.stubGlobal("fetch", fetchMock);
    const id = seedErroredRun();
    render(<AgentsRail />);

    expect(screen.getByRole("alert").textContent).toContain("token ceiling 1000");
    fireEvent.click(screen.getByRole("button", { name: "Resume Copilot" }));

    await waitFor(() =>
      expect(useAgentRunsStore.getState().runs.find((r) => r.id === id)?.status).toBe("running"),
    );
    const [url, init] = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/resume"))!;
    expect(String(url)).toBe("http://127.0.0.1:51763/runs/run-5/resume");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ ...SIDECAR_HEADERS, "X-LLM-Api-Key": "sk-or-test" });
    expect(init.body).toBeUndefined();
  });

  it("shows a planned run's plan and its latest steps, and Start runs it (R15-AGENT-039)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    vi.stubGlobal("fetch", fetchMock);
    const store = useAgentRunsStore.getState();
    const id = store.startRun({
      agentId: "copilot",
      agentName: "Copilot",
      mode: "delegate",
      provider: "openrouter",
      sidecarRunId: "run-6",
    });
    store.updateRun(id, {
      status: "planned",
      plan: {
        goal: "Set up the cockpit and research NVDA",
        steps: [
          { action: "open_panel", rationale: "Open the chart" },
          { action: "research", rationale: "Research NVDA" },
        ],
      },
      activity: [{ tool: "web_search", status: "error", summary: "search rate-limited" }],
    });
    render(<AgentsRail />);

    const plan = screen.getByLabelText("Plan for Copilot");
    expect(plan.textContent).toContain("Set up the cockpit and research NVDA");
    expect(Array.from(plan.querySelectorAll("li")).map((li) => li.textContent)).toEqual([
      "Open the chart",
      "Research NVDA",
    ]);
    expect(screen.getByLabelText("Recent steps of Copilot").textContent).toContain(
      "search rate-limited",
    );
    expect(screen.getByRole("button", { name: "Discard Copilot" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Start Copilot" }));
    await waitFor(() =>
      expect(useAgentRunsStore.getState().runs.find((r) => r.id === id)?.status).toBe("running"),
    );
    const [url, init] = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/start"))!;
    expect(String(url)).toBe("http://127.0.0.1:51763/runs/run-6/start");
    expect(init.headers).toEqual({ ...SIDECAR_HEADERS, "X-LLM-Api-Key": "sk-or-test" });
  });
});
