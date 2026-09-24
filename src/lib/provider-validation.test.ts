import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { validateProvider, VALIDATION_TIMEOUT_MS } from "@/lib/provider-validation";

vi.mock("@/lib/sidecar-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

const fetchMock = vi.fn();

function answer(status: number, body: unknown) {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function hangUntilAborted(_url: string, init: RequestInit): Promise<Response> {
  // Like the real fetch: an already-aborted signal rejects at once.
  return new Promise((_, reject) => {
    const abort = () => reject(new DOMException("", "AbortError"));
    if (init.signal?.aborted) {
      abort();
    }
    init.signal?.addEventListener("abort", abort);
  });
}

describe("validateProvider (C4)", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("passes each sidecar reason through", async () => {
    for (const reason of ["invalid", "not_configured", "unreachable", "model_not_pulled"]) {
      answer(200, { ok: false, reason, detail: `because ${reason}` });
      await expect(validateProvider("ollama", { model: "qwen2.5:7b" })).resolves.toEqual({
        ok: false,
        reason,
        detail: `because ${reason}`,
      });
    }
    answer(200, { ok: true, reason: null, detail: null });
    await expect(validateProvider("openrouter", { apiKey: "sk-x" })).resolves.toEqual({
      ok: true,
      reason: null,
      detail: null,
    });
  });

  it("sends a trimmed key and the model", async () => {
    answer(200, { ok: true, reason: null, detail: null });
    await validateProvider("openai", { apiKey: "  sk-test\n", model: "gpt-4.1" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://127.0.0.1:9000/llm/keys/validate");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      provider: "openai",
      api_key: "sk-test",
      model: "gpt-4.1",
    });
  });

  it("a rejected fetch (data engine down) is unreachable, never a bad key", async () => {
    fetchMock.mockRejectedValue(new TypeError("Load failed"));
    const result = await validateProvider("openrouter", { apiKey: "sk-x" });
    expect(result.ok).toBe(false);
    expect(result.reason).toBe("unreachable");
    expect(result.detail).toMatch(/data engine is not responding/);
  });

  it("a non-2xx from the sidecar is unreachable with its detail", async () => {
    answer(500, { detail: "boom" });
    await expect(validateProvider("openai", { apiKey: "sk-x" })).resolves.toEqual({
      ok: false,
      reason: "unreachable",
      detail: "boom",
    });
  });

  it("gives up after the timeout instead of hanging", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(hangUntilAborted);
    const pending = validateProvider("openai", { apiKey: "sk-x" });
    await vi.advanceTimersByTimeAsync(VALIDATION_TIMEOUT_MS);
    const result = await pending;
    expect(result.reason).toBe("unreachable");
    expect(result.detail).toMatch(/No answer within 15 s/);
  });

  it("a caller abort (Cancel) rejects instead of reporting a reason", async () => {
    fetchMock.mockImplementation(hangUntilAborted);
    const controller = new AbortController();
    const pending = validateProvider("openai", { apiKey: "sk-x", signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toThrow();
  });
});
