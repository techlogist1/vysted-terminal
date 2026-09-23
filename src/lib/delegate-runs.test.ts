import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  answerDelegateRun,
  cancelDelegateRun,
  launchDelegateRun,
  pollDelegateRuns,
  stopDelegatePolling,
} from "@/lib/delegate-runs";
import { resetAgentRunsStoreForTests, useAgentRunsStore } from "@/store/agent-runs";

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    statusText: ok ? "OK" : "Bad Request",
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

const BUDGET = { maxTokens: 100_000, maxSpendUsd: 1, maxWallSeconds: 600, maxSteps: 12 };

describe("delegate-runs", () => {
  beforeEach(() => {
    resetAgentRunsStoreForTests();
  });

  afterEach(() => {
    stopDelegatePolling();
    vi.restoreAllMocks();
  });

  it("launches a run, sends the budget, and records the sidecar run id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ runId: "run-1" }));
    vi.stubGlobal("fetch", fetchMock);

    await launchDelegateRun({
      agentId: "copilot",
      agentName: "Copilot",
      prompt: "summarize my watchlist",
      budget: BUDGET,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/agents/copilot/runs");
    expect(init.method).toBe("POST");
    const sentBody = JSON.parse(init.body as string);
    expect(sentBody.prompt).toBe("summarize my watchlist");
    expect(sentBody.budget).toEqual({
      max_tokens: 100_000,
      max_spend_usd: 1,
      max_wall_seconds: 600,
      max_steps: 12,
    });

    const run = useAgentRunsStore.getState().runs[0];
    expect(run.sidecarRunId).toBe("run-1");
    expect(run.status).toBe("running");
    expect(run.mode).toBe("delegate");
  });

  it("marks the run errored when the launch is rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "no provider key" }, false)),
    );

    await launchDelegateRun({
      agentId: "copilot",
      agentName: "Copilot",
      prompt: "go",
      budget: BUDGET,
    });

    const run = useAgentRunsStore.getState().runs[0];
    expect(run.status).toBe("error");
    expect(run.detail).toContain("no provider key");
  });

  it("syncs live cost/status from the poll and ends a budget-breached run", async () => {
    // Seed a launched run with a sidecar id.
    const id = useAgentRunsStore.getState().startRun({
      agentId: "copilot",
      agentName: "Copilot",
      mode: "delegate",
      budget: BUDGET,
      cost: { tokens: 0, spendUsd: 0, steps: 0 },
    });
    useAgentRunsStore.getState().updateRun(id, { sidecarRunId: "run-9" });

    // First poll: still running, cost accrued.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          runs: [
            {
              id: "run-9",
              agent_id: "copilot",
              status: "running",
              cost: { tokens: 25_000, spend_usd: 0.12, steps: 3 },
            },
          ],
        }),
      ),
    );
    await pollDelegateRuns();
    let run = useAgentRunsStore.getState().bySidecarId("run-9");
    expect(run?.status).toBe("running");
    expect(run?.cost?.tokens).toBe(25_000);
    expect(run?.cost?.spendUsd).toBe(0.12);

    // Second poll: budget breach → terminal error with the breach reason.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          runs: [
            {
              id: "run-9",
              agent_id: "copilot",
              status: "error",
              cost: { tokens: 100_001, spend_usd: 0.5, steps: 9 },
              detail: "token budget exceeded (100001 > 100000)",
            },
          ],
        }),
      ),
    );
    await pollDelegateRuns();
    run = useAgentRunsStore.getState().bySidecarId("run-9");
    expect(run?.status).toBe("error");
    expect(run?.detail).toContain("token budget exceeded");
  });

  it("routes cancel + answer to the run routes", async () => {
    const cancelFetch = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", cancelFetch);
    await cancelDelegateRun("run-3");
    expect(String(cancelFetch.mock.calls[0][0])).toContain("/runs/run-3/cancel");
    expect(cancelFetch.mock.calls[0][1].method).toBe("POST");

    const answerFetch = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", answerFetch);
    await answerDelegateRun("run-3", "use the live quote");
    expect(String(answerFetch.mock.calls[0][0])).toContain("/runs/run-3/answer");
    expect(JSON.parse(answerFetch.mock.calls[0][1].body as string)).toEqual({
      answer: "use the live quote",
    });
  });
});

// ── R15-AGENT-013: a finished run's output reaches its originating thread once ──

import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useAgentSpacesStore } from "@/store/agent-spaces";
import { useChatHistoryStore } from "@/store/chat-history";
import { useProposedChangesStore } from "@/store/proposed-changes";

describe("delegate-runs — output delivery", () => {
  const LONG_ANSWER = "Round 1 valuation. ".repeat(40);

  function routedFetch(status: "done" | "error", output: Record<string, unknown>) {
    return vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(String(url)).pathname;
      if (init?.method === "POST") {
        return jsonResponse({ runId: "run-7" });
      }
      if (path === "/runs") {
        return jsonResponse({
          runs: [{ id: "run-7", agent_id: "copilot", status, detail: "token ceiling hit" }],
        });
      }
      return jsonResponse({ id: "run-7", status, ...output });
    });
  }

  beforeEach(() => {
    resetAgentRunsStoreForTests();
    useAgentAutonomyStore.setState({ autonomy: "ask" });
    useProposedChangesStore.setState({ changes: [] });
    useChatHistoryStore.getState().clear();
    useAgentSpacesStore.setState({
      spaces: [
        { id: "t1", title: "Chat 1" },
        { id: "t2", title: "Chat 2" },
      ],
      activeId: "t2",
      archived: { t1: [] },
    });
  });

  afterEach(() => {
    stopDelegatePolling();
    vi.restoreAllMocks();
  });

  it("appends the answer to the launching thread and gates the note and the brief", async () => {
    const fetchMock = routedFetch("done", {
      answer: LONG_ANSWER,
      brief: { symbol: "NVDA", markdown: "## Thesis" },
      hostActions: [
        { tool_call_id: "c-note", name: "write_note", input: { scope: "NVDA", text: "margin" } },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);
    await launchDelegateRun({
      agentId: "copilot",
      agentName: "Copilot",
      prompt: "research NVDA",
      budget: BUDGET,
      threadId: "t1",
    });

    await pollDelegateRuns();
    await pollDelegateRuns(); // a later poll never delivers twice

    const thread = useAgentSpacesStore.getState().archived.t1;
    expect(thread).toHaveLength(1);
    expect(thread[0]).toMatchObject({
      role: "assistant",
      content: LONG_ANSWER,
      agentId: "copilot",
    });
    expect(useChatHistoryStore.getState().messages).toEqual([]); // not the live tab
    const changes = useProposedChangesStore.getState().changes;
    expect(changes.map((c) => [c.action.name, c.status])).toEqual([
      ["write_note", "pending"],
      ["publish_brief", "pending"],
    ]);
    expect(changes[1].action.input).toEqual({ symbol: "NVDA", markdown: "## Thesis" });
    const detailFetches = fetchMock.mock.calls.filter(([u]) => String(u).endsWith("/runs/run-7"));
    expect(detailFetches).toHaveLength(1);
  });

  it("a run that ends in error still delivers its partial text with the error", async () => {
    vi.stubGlobal("fetch", routedFetch("error", { answer: "Partial analysis." }));
    await launchDelegateRun({
      agentId: "copilot",
      agentName: "Copilot",
      prompt: "go",
      budget: BUDGET,
      threadId: "t2",
    });

    await pollDelegateRuns();

    const live = useChatHistoryStore.getState().messages;
    expect(live).toHaveLength(1);
    expect(live[0]).toMatchObject({ content: "Partial analysis.", error: "token ceiling hit" });
    expect(useProposedChangesStore.getState().changes).toEqual([]);
  });
});
