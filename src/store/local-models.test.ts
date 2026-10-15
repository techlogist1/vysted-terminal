import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DownloadState, InstalledModel } from "../../types/data";

const api = vi.hoisted(() => ({
  hardware: vi.fn(),
  catalog: vi.fn(),
  installed: vi.fn(),
  downloads: vi.fn(),
  download: vi.fn(),
  cancel: vi.fn(),
  remove: vi.fn(),
}));
const meta = vi.hoisted(() => new Map<string, string>());
const engine = vi.hoisted(() => ({ start: vi.fn(), stop: vi.fn(), refresh: vi.fn() }));

vi.mock("@/lib/local-models", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/local-models")>()),
  localModelsApi: api,
}));
vi.mock("@/lib/keychain", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/keychain")>()),
  getAppMeta: vi.fn(async (k: string) => meta.get(k) ?? null),
  setAppMeta: vi.fn(async (k: string, v: string) => void meta.set(k, v)),
}));
vi.mock("@/store/local-engine", () => ({
  useLocalEngineStore: { getState: () => engine },
}));

import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import {
  initLocalModels,
  LOCAL_MODEL_ACTIVE_KEY,
  resetLocalModelsForTests,
  useLocalModelsStore,
} from "@/store/local-models";
import { useModelSelectionStore } from "@/store/model-selection";

const qwen: InstalledModel = {
  id: "qwen",
  name: "Qwen",
  path: "/data/models/qwen.gguf",
  sizeBytes: 5,
  verified: true,
  active: false,
};
const dl = (state: DownloadState["state"], receivedBytes = 50): DownloadState => ({
  id: "qwen",
  state,
  receivedBytes,
  totalBytes: 100,
  bytesPerSec: state === "downloading" ? 10 : null,
  error: null,
  retryable: true,
});
const ready = {
  state: "ready",
  port: 4000,
  modelId: "qwen",
  restarts: 0,
  error: null,
  detail: null,
};

let installed: InstalledModel[] = [];
let downloads: DownloadState[] = [];

beforeEach(() => {
  vi.useFakeTimers();
  resetLocalModelsForTests();
  meta.clear();
  installed = [];
  downloads = [];
  for (const fn of [...Object.values(api), ...Object.values(engine)]) fn.mockReset();
  api.hardware.mockResolvedValue({ totalRamBytes: 16e9 });
  api.catalog.mockResolvedValue({ models: [], recommendedId: null, tier: "16gb", reason: "" });
  api.installed.mockImplementation(async () => ({
    models: installed,
    ollama: { running: false, models: [] },
  }));
  api.downloads.mockImplementation(async () => ({ downloads }));
  api.download.mockImplementation(async () => dl("downloading", 0));
  api.cancel.mockImplementation(async () => dl("cancelled"));
  api.remove.mockResolvedValue(undefined);
  engine.start.mockResolvedValue(ready);
  engine.stop.mockResolvedValue({ ...ready, state: "stopped", port: null });
  engine.refresh.mockResolvedValue(ready);
  useLocalModelsStore.setState({
    downloads: {},
    installed: [],
    activeModelId: null,
    catalog: null,
  });
  useAppStore.setState({ sidecarStatus: "connecting" });
  useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
  useModelSelectionStore.setState({ overrides: {} });
});

afterEach(() => {
  resetLocalModelsForTests();
  vi.useRealTimers();
});

describe("local-models store", () => {
  it("polls only while a download is active", async () => {
    downloads = [dl("downloading")];
    await useLocalModelsStore.getState().refresh();
    expect(api.downloads).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1_000);
    expect(api.downloads).toHaveBeenCalledTimes(2);
    downloads = [dl("paused")];
    await vi.advanceTimersByTimeAsync(1_000);
    expect(api.downloads).toHaveBeenCalledTimes(3);
    await vi.advanceTimersByTimeAsync(5_000);
    expect(api.downloads).toHaveBeenCalledTimes(3);
  });

  it("does not poll when nothing is downloading", async () => {
    await useLocalModelsStore.getState().refresh();
    await vi.advanceTimersByTimeAsync(5_000);
    expect(api.downloads).toHaveBeenCalledTimes(1);
  });

  it("auto-activates a finished download when nothing is active", async () => {
    await useLocalModelsStore.getState().download("qwen");
    installed = [qwen];
    downloads = [dl("done", 100)];
    await vi.advanceTimersByTimeAsync(1_000);
    await vi.waitFor(() => expect(engine.start).toHaveBeenCalled());
    expect(engine.start).toHaveBeenCalledWith({ modelPath: qwen.path, modelId: "qwen" });
    expect(useLocalModelsStore.getState().activeModelId).toBe("qwen");
  });

  it("leaves the active model alone when another download finishes", async () => {
    useLocalModelsStore.setState({ activeModelId: "other" });
    await useLocalModelsStore.getState().download("qwen");
    installed = [qwen];
    downloads = [dl("done", 100)];
    await vi.advanceTimersByTimeAsync(1_000);
    await vi.advanceTimersByTimeAsync(10);
    expect(engine.start).not.toHaveBeenCalled();
  });

  it("activate starts the engine, persists the id and makes local the default", async () => {
    useLocalModelsStore.setState({ installed: [qwen] });
    const status = await useLocalModelsStore.getState().activate("qwen");
    expect(status).toEqual(ready);
    expect(engine.start).toHaveBeenCalledWith({ modelPath: qwen.path, modelId: "qwen" });
    expect(meta.get(LOCAL_MODEL_ACTIVE_KEY)).toBe("qwen");
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("local");
    expect(useModelSelectionStore.getState().modelFor("local")).toBe("qwen");
  });

  it.each([
    ["under-8gb", 16384],
    ["8gb", 24576],
    ["16gb", 32768],
    ["32gb", 65536],
  ] as const)("a %s machine starts the engine with -c %i", async (tier, ctxSize) => {
    api.catalog.mockResolvedValue({ models: [], recommendedId: null, tier, reason: "" });
    await useLocalModelsStore.getState().refresh();
    useLocalModelsStore.setState({ installed: [qwen] });
    await useLocalModelsStore.getState().activate("qwen");
    expect(engine.start).toHaveBeenCalledWith({ modelPath: qwen.path, modelId: "qwen", ctxSize });
  });

  it("an unknown tier leaves the context size to the engine's default", async () => {
    useLocalModelsStore.setState({ installed: [qwen] });
    await useLocalModelsStore.getState().activate("qwen");
    expect(engine.start.mock.calls[0][0].ctxSize).toBeUndefined();
  });

  it("activate leaves the choice unsaved when the engine start fails", async () => {
    useLocalModelsStore.setState({ installed: [qwen] });
    const failed = { ...ready, state: "failed", port: null, error: "out of memory" };
    engine.start.mockResolvedValue(failed);
    const status = await useLocalModelsStore.getState().activate("qwen");
    expect(status).toEqual(failed);
    expect(useLocalModelsStore.getState().activeModelId).toBeNull();
    expect(meta.has(LOCAL_MODEL_ACTIVE_KEY)).toBe(false);
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("ollama");
    expect(useModelSelectionStore.getState().modelFor("local")).not.toBe("qwen");
  });

  it("remove stops the engine first when the model is active", async () => {
    useLocalModelsStore.setState({ installed: [qwen], activeModelId: "qwen" });
    const order: string[] = [];
    engine.stop.mockImplementation(async () => void order.push("stop"));
    api.remove.mockImplementation(async () => void order.push("delete"));
    await useLocalModelsStore.getState().remove("qwen");
    expect(order).toEqual(["stop", "delete"]);
    expect(useLocalModelsStore.getState().activeModelId).toBeNull();
    expect(meta.get(LOCAL_MODEL_ACTIVE_KEY)).toBe("");
  });

  it("remove of an inactive model never touches the engine", async () => {
    useLocalModelsStore.setState({ installed: [qwen], activeModelId: "other" });
    await useLocalModelsStore.getState().remove("qwen");
    expect(engine.stop).not.toHaveBeenCalled();
    expect(api.remove).toHaveBeenCalledWith("qwen");
  });

  it("a sidecar that is still starting reads as warming up, not an error", async () => {
    const { SidecarError } = await import("@/lib/sidecar-client");
    api.hardware.mockRejectedValue(new SidecarError(0, "not responding"));
    await useLocalModelsStore.getState().refresh();
    expect(useLocalModelsStore.getState().loadError).toMatch(/Getting things ready/);
  });

  it("on launch restarts the persisted active model and resumes a paused download once", async () => {
    meta.set(LOCAL_MODEL_ACTIVE_KEY, "qwen");
    installed = [qwen];
    downloads = [{ ...dl("paused"), id: "big" }];
    await initLocalModels();
    expect(engine.start).not.toHaveBeenCalled();
    useAppStore.setState({ sidecarStatus: "connected" });
    await vi.waitFor(() => expect(engine.start).toHaveBeenCalledTimes(1));
    expect(engine.start).toHaveBeenCalledWith({
      modelPath: qwen.path,
      modelId: "qwen",
      ctxSize: 32768,
    });
    expect(api.download).toHaveBeenCalledTimes(1);
    expect(api.download).toHaveBeenCalledWith("big");
    // A later reconnect re-loads but does not start or resume again.
    useAppStore.setState({ sidecarStatus: "error" });
    useAppStore.setState({ sidecarStatus: "connected" });
    await vi.advanceTimersByTimeAsync(10);
    expect(engine.start).toHaveBeenCalledTimes(1);
    expect(api.download).toHaveBeenCalledTimes(1);
  });

  it("on launch does not start a persisted model that is no longer installed", async () => {
    meta.set(LOCAL_MODEL_ACTIVE_KEY, "gone");
    useAppStore.setState({ sidecarStatus: "connected" });
    await initLocalModels();
    expect(engine.start).not.toHaveBeenCalled();
    expect(useLocalModelsStore.getState().activeModelId).toBe("gone");
  });
});

describe("local-models client", () => {
  it("turns a 409 into a disk error with the numbers", async () => {
    vi.useRealTimers();
    vi.resetModules();
    vi.doUnmock("@/lib/local-models");
    vi.doMock("@/lib/sidecar-client", async (importOriginal) => ({
      ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
      getSidecarBaseUrl: async () => "http://127.0.0.1:9",
      sidecarRequestInit: async () => ({ method: "POST" }),
      sidecarFetch: async () =>
        new Response(
          JSON.stringify({
            detail: "Not enough disk space (needs 5.1 GB, 2.0 GB free)",
            neededBytes: 5_100,
            freeBytes: 2_000,
          }),
          { status: 409 },
        ),
    }));
    const { localModelsApi, LocalModelsError } = await import("@/lib/local-models");
    const err = await localModelsApi.download("qwen").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(LocalModelsError);
    expect(err).toMatchObject({
      kind: "disk",
      neededBytes: 5_100,
      freeBytes: 2_000,
      message: "Not enough disk space (needs 5.1 GB, 2.0 GB free)",
    });
    vi.doUnmock("@/lib/sidecar-client");
  });
});
