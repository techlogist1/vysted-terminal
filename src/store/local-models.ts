/**
 * Local-models store (R16 contract, Wave 2) — the one owner of the on-computer
 * model state: hardware, catalog, installed models, downloads (polled each
 * second while one is moving) and the active model (app-meta
 * `local-model-active`). Everyone imports this; nobody re-implements it.
 */

import { create } from "zustand";

import { getAppMeta, setAppMeta } from "@/lib/keychain";
import type { EngineStatus } from "@/lib/local-engine";
import { isActiveDownload, localModelsApi } from "@/lib/local-models";
import { SidecarError } from "@/lib/sidecar-client";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useLocalEngineStore } from "@/store/local-engine";
import { useModelSelectionStore } from "@/store/model-selection";
import type {
  DownloadState,
  InstalledModel,
  LocalHardwareInfo,
  LocalModelCatalog,
} from "../../types/data";

export { LocalModelsError } from "@/lib/local-models";

export const LOCAL_MODEL_ACTIVE_KEY = "local-model-active";
export const POLL_MS = 1_000;
/** What a not-yet-answering data engine looks like to a layperson. */
export const WARMING_UP = "Getting things ready — the first launch takes about a minute.";

interface LocalModelsState {
  hardware: LocalHardwareInfo | null;
  catalog: LocalModelCatalog | null;
  installed: InstalledModel[];
  ollama: { running: boolean; models: string[] };
  downloads: Record<string, DownloadState>;
  activeModelId: string | null;
  loadError: string | null;
  refresh(): Promise<void>;
  download(id: string): Promise<DownloadState>;
  cancel(id: string, discard?: boolean): Promise<void>;
  remove(id: string): Promise<void>;
  activate(id: string): Promise<EngineStatus>;
  deactivate(): Promise<void>;
}

/** Downloads the user asked for this session: these auto-activate on `done`. */
const userStarted = new Set<string>();
let pollTimer: ReturnType<typeof setTimeout> | null = null;

function engineStart(id: string): Promise<EngineStatus> {
  const model = useLocalModelsStore.getState().installed.find((m) => m.id === id);
  if (!model) {
    return Promise.reject(new Error("That model isn't on this computer yet."));
  }
  return useLocalEngineStore.getState().start({ modelPath: model.path, modelId: id });
}

function persistActive(id: string | null): Promise<void> {
  return setAppMeta(LOCAL_MODEL_ACTIVE_KEY, id ?? "").catch(() => undefined);
}

function mergeDownloads(list: DownloadState[]): void {
  const prev = useLocalModelsStore.getState().downloads;
  const next = Object.fromEntries(list.map((d) => [d.id, d]));
  useLocalModelsStore.setState({ downloads: next });
  for (const d of list) {
    if (d.state === "done" && prev[d.id]?.state !== "done") {
      void onFinished(d.id);
    }
  }
}

async function onFinished(id: string): Promise<void> {
  await loadInstalled();
  const { activeModelId, activate } = useLocalModelsStore.getState();
  if (userStarted.delete(id) && activeModelId === null) {
    await activate(id).catch(() => undefined);
  }
}

async function loadInstalled(): Promise<void> {
  const res = await localModelsApi.installed();
  useLocalModelsStore.setState({ installed: res.models, ollama: res.ollama });
}

function schedulePoll(): void {
  const busy = Object.values(useLocalModelsStore.getState().downloads).some(isActiveDownload);
  if (!busy || pollTimer !== null) return;
  pollTimer = setTimeout(async () => {
    pollTimer = null;
    try {
      mergeDownloads((await localModelsApi.downloads()).downloads);
    } catch {
      // A missed tick; the next one tries again.
    }
    schedulePoll();
  }, POLL_MS);
}

function plainLoadError(error: unknown): string {
  if (error instanceof SidecarError && (error.status === 0 || error.status >= 500)) {
    return WARMING_UP;
  }
  if (useAppStore.getState().sidecarStatus !== "connected") return WARMING_UP;
  return error instanceof Error ? error.message : String(error);
}

export const useLocalModelsStore = create<LocalModelsState>((set, get) => ({
  hardware: null,
  catalog: null,
  installed: [],
  ollama: { running: false, models: [] },
  downloads: {},
  activeModelId: null,
  loadError: null,

  refresh: async () => {
    try {
      const [hardware, catalog, installed, downloads] = await Promise.all([
        localModelsApi.hardware(),
        localModelsApi.catalog(),
        localModelsApi.installed(),
        localModelsApi.downloads(),
      ]);
      set({
        hardware,
        catalog,
        installed: installed.models,
        ollama: installed.ollama,
        loadError: null,
      });
      mergeDownloads(downloads.downloads);
      schedulePoll();
    } catch (error) {
      set({ loadError: plainLoadError(error) });
    }
  },

  download: async (id) => {
    userStarted.add(id);
    try {
      const state = await localModelsApi.download(id);
      mergeDownloads([...Object.values(get().downloads).filter((d) => d.id !== id), state]);
      schedulePoll();
      return state;
    } catch (error) {
      userStarted.delete(id);
      throw error;
    }
  },

  cancel: async (id, discard = false) => {
    userStarted.delete(id);
    const state = await localModelsApi.cancel(id, discard);
    const rest = Object.values(get().downloads).filter((d) => d.id !== id);
    mergeDownloads(discard ? rest : [...rest, state]);
  },

  remove: async (id) => {
    if (get().activeModelId === id) {
      await get().deactivate();
    }
    await localModelsApi.remove(id);
    await loadInstalled();
  },

  activate: async (id) => {
    const status = await engineStart(id);
    set({ activeModelId: id });
    await persistActive(id);
    useLLMProvidersStore.getState().setDefaultProviderId("local");
    useModelSelectionStore.getState().setModel("local", id);
    return status;
  },

  deactivate: async () => {
    await useLocalEngineStore.getState().stop();
    set({ activeModelId: null });
    await persistActive(null);
  },
}));

let wiring: Promise<void> | null = null;

/**
 * Boot wiring (call once from the shell; idempotent): read the persisted active
 * model, then on the first sidecar connection load everything, restart the
 * engine for an installed active model and resume each paused download once.
 * Every later reconnect re-loads quietly.
 */
export function initLocalModels(): Promise<void> {
  wiring ??= (async () => {
    void useLocalEngineStore
      .getState()
      .refresh()
      .catch(() => undefined);
    const persisted = await getAppMeta(LOCAL_MODEL_ACTIVE_KEY).catch(() => null);
    useLocalModelsStore.setState({ activeModelId: persisted || null });
    let launched = false;
    const onConnected = async () => {
      const store = useLocalModelsStore.getState();
      await store.refresh();
      if (launched || useLocalModelsStore.getState().loadError !== null) return;
      launched = true;
      const { activeModelId, installed, downloads } = useLocalModelsStore.getState();
      if (activeModelId && installed.some((m) => m.id === activeModelId)) {
        void engineStart(activeModelId).catch(() => undefined);
      }
      for (const d of Object.values(downloads)) {
        if (d.state === "paused") {
          void store.download(d.id).catch(() => undefined);
        }
      }
    };
    useAppStore.subscribe((state, prev) => {
      if (state.sidecarStatus === "connected" && prev.sidecarStatus !== "connected") {
        void onConnected();
      }
    });
    if (useAppStore.getState().sidecarStatus === "connected") {
      await onConnected();
    }
  })();
  return wiring;
}

/** Test seam: stop the poll timer and forget session state. */
export function resetLocalModelsForTests(): void {
  if (pollTimer !== null) clearTimeout(pollTimer);
  pollTimer = null;
  userStarted.clear();
  wiring = null;
}
