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
