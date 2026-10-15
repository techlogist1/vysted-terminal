import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EngineStatus } from "@/lib/local-engine";

const invokeMock = vi.hoisted(() => vi.fn());
const listenMock = vi.hoisted(() => vi.fn());
const requestMock = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));
vi.mock("@tauri-apps/api/event", () => ({ listen: listenMock }));
vi.mock("@/lib/sidecar-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
  sidecarRequest: requestMock,
}));

const stopped: EngineStatus = {
  state: "stopped",
  port: null,
  modelId: null,
  restarts: 0,
  error: null,
  detail: null,
};
const ready: EngineStatus = { ...stopped, state: "ready", port: 41234, modelId: "qwen" };

let emit: (status: EngineStatus) => void = () => undefined;

async function load() {
  vi.resetModules();
  const store = await import("@/store/local-engine");
  const app = await import("@/store/app");
  return { ...store, app: app.useAppStore };
}

function puts(): unknown[] {
  return requestMock.mock.calls.map(([method, path, opts]) => {
    expect([method, path]).toEqual(["PUT", "/local-models/engine"]);
    return (opts as { body: unknown }).body;
  });
}

beforeEach(() => {
  invokeMock.mockReset();
  listenMock.mockReset();
  requestMock.mockReset();
  requestMock.mockResolvedValue({ baseUrl: null, modelId: null });
  listenMock.mockImplementation(
    async (event: string, handler: (e: { payload: EngineStatus }) => void) => {
      expect(event).toBe("local-engine://status");
      emit = (status) => handler({ payload: status });
      return () => undefined;
    },
  );
  invokeMock.mockImplementation(async (cmd: string) => {
    if (cmd === "local_engine_status") return stopped;
    if (cmd === "local_engine_stop") return stopped;
    if (cmd === "local_engine_start") return ready;
    throw new Error(`unexpected ${cmd}`);
  });
});

describe("local engine store", () => {
  it("starts through the core command and PUTs the ready port + model", async () => {
    const { useLocalEngineStore, flushLocalEngineSync } = await load();
    const status = await useLocalEngineStore
      .getState()
      .start({ modelPath: "/m/q.gguf", modelId: "qwen" });
    expect(status).toEqual(ready);
    expect(invokeMock).toHaveBeenCalledWith("local_engine_start", {
      modelPath: "/m/q.gguf",
      modelId: "qwen",
    });
    await flushLocalEngineSync();
    expect(useLocalEngineStore.getState().status).toEqual(ready);
    expect(puts()).toEqual([
      { port: null, modelId: null },
      { port: 41234, modelId: "qwen" },
    ]);
  });

  it("PUTs nulls on every non-ready transition and skips duplicates", async () => {
    const { useLocalEngineStore, initLocalEngine, flushLocalEngineSync } = await load();
    await initLocalEngine();
    emit({ ...stopped, state: "starting", modelId: "qwen" });
    emit(ready);
    emit({ ...stopped, state: "crashed", modelId: "qwen", restarts: 1, error: "stopped" });
    emit({ ...stopped, state: "starting", modelId: "qwen", restarts: 1 });
    emit({ ...ready, port: 5000, restarts: 1 });
    await flushLocalEngineSync();
    expect(useLocalEngineStore.getState().status.port).toBe(5000);
    expect(puts()).toEqual([
      { port: null, modelId: null },
      { port: 41234, modelId: "qwen" },
      { port: null, modelId: null },
      { port: 5000, modelId: "qwen" },
    ]);
  });

  it("re-PUTs the current state when the sidecar reconnects", async () => {
    const { initLocalEngine, flushLocalEngineSync, app } = await load();
    app.setState({ sidecarStatus: "connected" });
    await initLocalEngine();
    emit(ready);
    await flushLocalEngineSync();
    requestMock.mockClear();
    app.setState({ sidecarStatus: "error" });
    app.setState({ sidecarStatus: "connected" });
    await flushLocalEngineSync();
    expect(puts()).toEqual([{ port: 41234, modelId: "qwen" }]);
  });

  it("logs a missing models router once and never throws", async () => {
    const { SidecarError } = await import("@/lib/sidecar-client");
    requestMock.mockRejectedValue(new SidecarError(404, "Not Found"));
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { useLocalEngineStore, initLocalEngine, flushLocalEngineSync } = await load();
    await initLocalEngine();
    emit(ready);
    emit(stopped);
    await expect(useLocalEngineStore.getState().stop()).resolves.toEqual(stopped);
    await flushLocalEngineSync();
    expect(requestMock.mock.calls.length).toBeGreaterThan(1);
    expect(warn).toHaveBeenCalledTimes(1);
    warn.mockRestore();
  });

  it("retries a PUT that failed once the sidecar is back", async () => {
    requestMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { initLocalEngine, flushLocalEngineSync } = await load();
    await initLocalEngine();
    emit(stopped);
    await flushLocalEngineSync();
    expect(puts()).toEqual([
      { port: null, modelId: null },
      { port: null, modelId: null },
    ]);
    warn.mockRestore();
  });

  it("surfaces a rejected start to the caller", async () => {
    invokeMock.mockImplementation(async (cmd: string) => {
      if (cmd === "local_engine_status") return stopped;
      throw "That model file isn't in the app's models folder or Ollama's model store.";
    });
    const { useLocalEngineStore } = await load();
    await expect(
      useLocalEngineStore.getState().start({ modelPath: "/etc/passwd", modelId: "x" }),
    ).rejects.toMatch("models folder");
    expect(useLocalEngineStore.getState().status).toEqual(stopped);
  });
});
