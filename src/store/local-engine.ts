import { create } from "zustand";

import {
  STOPPED_ENGINE,
  getLocalEngineStatus,
  onLocalEngineStatus,
  startLocalEngine,
  stopLocalEngine,
  type EngineStartArgs,
  type EngineStatus,
} from "@/lib/local-engine";
import { SidecarError, sidecarRequest } from "@/lib/sidecar-client";
import { useAppStore } from "@/store/app";

interface LocalEngineStore {
  status: EngineStatus;
  /** Rejects with the core's reason (e.g. a model path outside the allowed folders). */
  start: (args: EngineStartArgs) => Promise<EngineStatus>;
  stop: () => Promise<EngineStatus>;
  refresh: () => Promise<EngineStatus>;
}

export const useLocalEngineStore = create<LocalEngineStore>(() => ({
  status: STOPPED_ENGINE,
  start: async (args) => {
    await initLocalEngine();
    return applyStatus(await startLocalEngine(args));
  },
  stop: async () => {
    await initLocalEngine();
    return applyStatus(await stopLocalEngine());
  },
  refresh: async () => {
    await initLocalEngine();
    return applyStatus(await getLocalEngineStatus());
  },
}));

let wiring: Promise<void> | null = null;
let lastSent: string | null = null;
let putQueue: Promise<void> = Promise.resolve();
let warnedMissingRouter = false;

/** Listen for core transitions and re-sync the sidecar on reconnect. Idempotent. */
export function initLocalEngine(): Promise<void> {
  wiring ??= (async () => {
    await onLocalEngineStatus(applyStatus);
    useAppStore.subscribe((state, prev) => {
      if (state.sidecarStatus === "connected" && prev.sidecarStatus !== "connected") {
        syncSidecar(useLocalEngineStore.getState().status, true);
      }
    });
    applyStatus(await getLocalEngineStatus());
  })();
  return wiring;
}

function applyStatus(status: EngineStatus): EngineStatus {
  useLocalEngineStore.setState({ status });
  syncSidecar(status, false);
  return status;
}

/** Point provider `local` at the engine: `{port, modelId}` when ready, nulls otherwise. */
function syncSidecar(status: EngineStatus, force: boolean): void {
  const ready = status.state === "ready" && status.port !== null;
  const body = {
    port: ready ? status.port : null,
    modelId: ready ? status.modelId : null,
  };
  const key = JSON.stringify(body);
  putQueue = putQueue.then(async () => {
    if (!force && key === lastSent) {
      return;
    }
    try {
      await sidecarRequest("PUT", "/local-models/engine", { body });
      lastSent = key;
    } catch (error) {
      if (error instanceof SidecarError && error.status === 404) {
        if (!warnedMissingRouter) {
          warnedMissingRouter = true;
          console.warn("[local-engine] the sidecar has no /local-models router; engine not synced");
        }
        return;
      }
      console.warn("[local-engine] could not sync the engine to the sidecar", error);
    }
  });
}

/** Test seam: settle every queued PUT. */
export function flushLocalEngineSync(): Promise<void> {
  return putQueue;
}
