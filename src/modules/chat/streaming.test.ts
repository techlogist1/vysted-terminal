import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:8787"),
}));
vi.mock("@/lib/search-headers", () => ({
  buildSearchHeaders: vi.fn(async () => ({})),
}));

import { streamAgentInvocation, streamChat } from "./streaming";

/** One terminated SSE frame so the consumer drains cleanly. */
function sseResponse(): Response {
  return new Response('data: {"kind":"done"}\n\n', {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

const fetchMock = vi.fn(async () => sseResponse());

function sentBody(): Record<string, unknown> {
  const init = (fetchMock.mock.calls[0] as unknown[])[1] as { body: string };
  return JSON.parse(init.body) as Record<string, unknown>;
}

describe("streaming — options wire mapping (research_depth)", () => {
  beforeEach(() => {
    fetchMock.mockClear();
    fetchMock.mockImplementation(async () => sseResponse());
    vi.stubGlobal("fetch", fetchMock);
  });

  it("maps options.researchDepth to snake_case research_depth on the agent wire", async () => {
    const events: unknown[] = [];
    await streamAgentInvocation(
      "copilot",
      { prompt: "hi", options: { researchDepth: "ultra", deepResearchBackend: "auto" } },
      { onEvent: (e) => events.push(e) },
    );
    const options = sentBody().options as Record<string, unknown>;
    expect(options.research_depth).toBe("ultra");
    expect(options.researchDepth).toBeUndefined();
    // Other option keys pass through UNCHANGED (existing sidecar contracts).
    expect(options.deepResearchBackend).toBe("auto");
    expect(events).toEqual([{ kind: "done", usage: undefined, finishReason: undefined }]);
  });

  it("maps options.researchDepth on the raw-chat wire too", async () => {
    await streamChat(
      {
        provider: "deepseek",
        model: "deepseek-chat",
        messages: [{ role: "user", content: "hi" }],
        options: { researchDepth: "deep" },
      },
      { onEvent: () => undefined },
    );
    const options = sentBody().options as Record<string, unknown>;
    expect(options.research_depth).toBe("deep");
    expect(options.researchDepth).toBeUndefined();
  });

  it("sends empty options untouched when none are provided", async () => {
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: () => undefined });
    expect(sentBody().options).toEqual({});
  });
});

// ── R10: research:begin lifecycle feed + structured error frames ────────────

import { resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import { errorFrameOf } from "./streaming";

function sseFrames(payloads: Record<string, unknown>[]): Response {
  const body = payloads.map((p) => `data: ${JSON.stringify(p)}\n\n`).join("");
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("streaming — brief lifecycle feed (R10 D39)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("the research:begin engine step keys the in-flight brief state", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([
        {
          kind: "research_step",
          step_kind: "engine",
          detail: "research:begin abc123 depth=deep query=reliance industries",
          status: "ok",
          index: 1,
        },
        {
          kind: "research_step",
          step_kind: "search",
          detail: "web round",
          latency_ms: 1200,
          status: "ok",
          index: 2,
        },
        { kind: "done" },
      ]),
    );
    await streamAgentInvocation(
      "copilot",
      { prompt: "research reliance" },
      {
        onEvent: () => undefined,
      },
    );
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("in_flight");
    if (panel.phase === "in_flight") {
      expect(panel.runId).toBe("abc123");
      expect(panel.depth).toBe("deep");
      expect(panel.query).toBe("reliance industries");
      // The follow-up step rode into the live trace.
      expect(panel.steps).toEqual([
        { kind: "search", detail: "web round", latencyMs: 1200, status: "ok" },
      ]);
    }
  });

  it("an ultra begin maps onto the heavy tier; steps outside a run are ignored", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([
        {
          kind: "research_step",
          step_kind: "search",
          detail: "no run yet — ignored",
          status: "ok",
          index: 1,
        },
        {
          kind: "research_step",
          step_kind: "engine",
          detail: "research:begin r9 depth=ultra",
          status: "ok",
          index: 2,
        },
        { kind: "done" },
      ]),
    );
    await streamAgentInvocation(
      "copilot",
      { prompt: "go all out" },
      {
        onEvent: () => undefined,
      },
    );
    const panel = useBriefStore.getState().panel;
    expect(panel.phase === "in_flight" && panel.depth).toBe("heavy");
    expect(panel.phase === "in_flight" && panel.steps).toEqual([]);
  });
});

describe("streaming — structured error frames (R10 D43)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("forwards action/detail/code on the error event; errorFrameOf reads them", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([
        {
          kind: "error",
          message: "Your DeepSeek balance is empty — top up or switch provider.",
          action: "Top up or switch provider in Settings.",
          detail: 'Error code: 402 - {"error":"Insufficient Balance"}',
          code: "provider_402",
        },
      ]),
    );
    const events: unknown[] = [];
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: (e) => events.push(e) });
    expect(events).toHaveLength(1);
    const frame = errorFrameOf(events[0] as never);
    expect(frame).toEqual({
      action: "Top up or switch provider in Settings.",
      detail: 'Error code: 402 - {"error":"Insufficient Balance"}',
      code: "provider_402",
    });
  });

  it("a legacy bare error stays a plain frame (errorFrameOf → null)", async () => {
    fetchMock.mockImplementationOnce(async () => sseFrames([{ kind: "error", message: "boom" }]));
    const events: unknown[] = [];
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: (e) => events.push(e) });
    expect(events).toEqual([{ kind: "error", message: "boom" }]);
    expect(errorFrameOf(events[0] as never)).toBeNull();
  });
});
