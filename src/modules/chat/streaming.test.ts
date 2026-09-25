import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
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
import { doneFrameOf, errorFrameOf } from "./streaming";

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

describe("streaming — spend_usd on the done frame (R15-AGENT-082, C11)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("parses a priced model's spend_usd into doneFrameOf", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([
        { kind: "done", usage: { input_tokens: 500, output_tokens: 20 }, spend_usd: 0.0042 },
      ]),
    );
    const events: unknown[] = [];
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: (e) => events.push(e) });
    expect(events).toHaveLength(1);
    expect(doneFrameOf(events[0] as never)).toBe(0.0042);
  });

  it("a free model's spend_usd of 0 is a real zero, not dropped", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([{ kind: "done", usage: { input_tokens: 10, output_tokens: 2 }, spend_usd: 0 }]),
    );
    const events: unknown[] = [];
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: (e) => events.push(e) });
    expect(doneFrameOf(events[0] as never)).toBe(0);
  });

  it("an unpriced model's done frame (no spend_usd) yields undefined, not 0", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([{ kind: "done", usage: { input_tokens: 10, output_tokens: 2 } }]),
    );
    const events: unknown[] = [];
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: (e) => events.push(e) });
    expect(doneFrameOf(events[0] as never)).toBeUndefined();
  });

  it("doneFrameOf returns undefined for a non-done event", () => {
    expect(doneFrameOf({ kind: "delta", text: "x" } as never)).toBeUndefined();
  });
});

describe("streaming — tool_result frames and unknown kinds (R15-CODE-AGENT-033)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("drops a frame of an unknown kind; the delta and done around it still arrive", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([{ kind: "delta", text: "hi" }, { kind: "future_kind", x: 1 }, { kind: "done" }]),
    );
    const events: unknown[] = [];
    const onError = vi.fn();
    await streamAgentInvocation(
      "copilot",
      { prompt: "hi" },
      { onEvent: (e) => events.push(e), onError },
    );
    expect(events.map((e) => (e as { kind: string }).kind)).toEqual(["delta", "done"]);
    expect(onError).not.toHaveBeenCalled();
  });

  it("normalises a tool_result frame to the camelCase shape", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([
        {
          kind: "tool_result",
          tool_call_id: "call_1",
          name: "option_chain",
          ok: false,
          error: "422 nearest",
        },
        { kind: "done" },
      ]),
    );
    const events: unknown[] = [];
    await streamAgentInvocation("copilot", { prompt: "hi" }, { onEvent: (e) => events.push(e) });
    expect(events[0]).toEqual({
      kind: "tool_result",
      toolCallId: "call_1",
      name: "option_chain",
      ok: false,
      error: "422 nearest",
    });
  });
});

// ── One terminal callback per stream call (R15-AGENT-029 / CODE-PLATFORM-037 / LIFECYCLE-005) ──

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { STREAM_ENDED_EARLY } from "./streaming";

describe("streaming — exactly one terminal callback", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  function recorder() {
    const events: unknown[] = [];
    const errors: string[] = [];
    return {
      events,
      errors,
      handlers: {
        onEvent: (e: unknown) => events.push(e),
        onError: (err: Error) => errors.push(err.message),
      },
    };
  }

  it("a sidecar that is not ready reaches onError once; the call does not reject", async () => {
    vi.mocked(getSidecarBaseUrl).mockRejectedValueOnce(
      new Error("The data engine did not become ready in time."),
    );
    const rec = recorder();
    await expect(
      streamChat({ provider: "openai", model: "gpt", messages: [] }, rec.handlers),
    ).resolves.toBeUndefined();
    expect(rec.errors).toEqual(["The data engine did not become ready in time."]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("a consumer throw surfaces its own message once, not 'unparseable SSE frame'", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([{ kind: "delta", text: "a" }, { kind: "delta", text: "b" }, { kind: "done" }]),
    );
    const errors: string[] = [];
    await streamChat(
      { provider: "openai", model: "gpt", messages: [] },
      {
        onEvent: (e) => {
          if (e.kind === "delta") {
            throw new Error("enqueueChange blew up");
          }
        },
        onError: (err) => errors.push(err.message),
      },
    );
    expect(errors).toEqual(["enqueueChange blew up"]);
  });

  it("a raw-chat stream that closes without done calls onError once", async () => {
    fetchMock.mockImplementationOnce(async () => sseFrames([{ kind: "delta", text: "partial" }]));
    const rec = recorder();
    await streamChat({ provider: "openai", model: "gpt", messages: [] }, rec.handlers);
    expect(rec.events).toEqual([{ kind: "delta", text: "partial" }]);
    expect(rec.errors).toEqual([STREAM_ENDED_EARLY]);
  });

  it("an agent-invocation stream that closes without done calls onError once", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([{ kind: "tool_use", tool_call_id: "t1", name: "research", input: {} }]),
    );
    const rec = recorder();
    await streamAgentInvocation("copilot", { prompt: "hi" }, rec.handlers);
    expect(rec.errors).toEqual([STREAM_ENDED_EARLY]);
  });

  it("an error frame is the terminal; the server's trailing done is not a second one", async () => {
    fetchMock.mockImplementationOnce(async () =>
      sseFrames([{ kind: "error", message: "declined" }, { kind: "done" }]),
    );
    const rec = recorder();
    await streamAgentInvocation("copilot", { prompt: "hi" }, rec.handlers);
    expect(rec.events).toEqual([{ kind: "error", message: "declined" }]);
    expect(rec.errors).toEqual([]);
  });
});

// ── Stall watchdog (R15-AGENT-025) ──

import { AGENT_STREAM_IDLE_MS, STREAM_STALLED } from "./streaming";

describe("streaming — stall watchdog", () => {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array>;

  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    fetchMock.mockImplementationOnce(
      async () =>
        new Response(
          new ReadableStream<Uint8Array>({
            start: (c) => {
              controller = c;
            },
          }),
          { status: 200, headers: { "Content-Type": "text/event-stream" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.useFakeTimers();
    return () => vi.useRealTimers();
  });

  function frame(payload: Record<string, unknown>): void {
    controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
  }

  it("ends a silent agent stream with the stalled error, once", async () => {
    const errors: string[] = [];
    const run = streamAgentInvocation(
      "copilot",
      { prompt: "price of RELIANCE?" },
      { onEvent: () => undefined, onError: (err) => errors.push(err.message) },
    );
    await vi.advanceTimersByTimeAsync(AGENT_STREAM_IDLE_MS + 1);
    await run;
    expect(errors).toEqual([STREAM_STALLED]);
  });

  it("does not fire while heartbeats keep arriving past the budget", async () => {
    const events: unknown[] = [];
    const errors: string[] = [];
    const run = streamAgentInvocation(
      "copilot",
      { prompt: "deep research BDL" },
      { onEvent: (e) => events.push(e), onError: (err) => errors.push(err.message) },
    );
    for (let elapsed = 0; elapsed < AGENT_STREAM_IDLE_MS * 2; elapsed += 10_000) {
      await vi.advanceTimersByTimeAsync(10_000);
      frame({ kind: "heartbeat" });
    }
    frame({ kind: "delta", text: "BDL order book is Rs 23,000 cr." });
    frame({ kind: "done" });
    controller.close();
    await run;
    expect(errors).toEqual([]);
    expect(events.at(-1)).toMatchObject({ kind: "done" });
    expect(events.filter((e) => (e as { kind: string }).kind === "heartbeat").length).toBe(9);
  });
});

// ── Non-2xx and transport failures read as sentences (R15-UI-012 / R15-UI-014) ──

import { SIDECAR_UNREACHABLE } from "@/lib/sidecar-client";

describe("streaming — error layer", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  async function agentErrors(): Promise<string[]> {
    const errors: string[] = [];
    await streamAgentInvocation(
      "nope",
      { prompt: "hi" },
      { onEvent: () => undefined, onError: (err) => errors.push(err.message) },
    );
    return errors;
  }

  it("a non-2xx string detail reaches onError as the sentence, not the JSON body", async () => {
    fetchMock.mockImplementationOnce(
      async () =>
        new Response(JSON.stringify({ detail: "unknown agent: 'nope'" }), { status: 404 }),
    );
    expect(await agentErrors()).toEqual(["unknown agent: 'nope'"]);
  });

  it("a 422 field-error array reaches onError as 'field: msg'", async () => {
    const detail = [{ loc: ["body", "prompt"], msg: "Field required", type: "missing" }];
    fetchMock.mockImplementationOnce(
      async () => new Response(JSON.stringify({ detail }), { status: 422 }),
    );
    expect(await agentErrors()).toEqual(["prompt: Field required"]);
  });

  it("a refused connection reaches onError as the unreachable sentence", async () => {
    fetchMock.mockImplementationOnce(async () => {
      throw new TypeError("Load failed");
    });
    expect(await agentErrors()).toEqual([SIDECAR_UNREACHABLE]);
  });
});
