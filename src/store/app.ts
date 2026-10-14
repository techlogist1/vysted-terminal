import { create } from "zustand";

import { getSidecarBaseUrl, onSidecarReachability, sidecarApi } from "@/lib/sidecar-client";

/** Connection status to the Python sidecar. */
export type SidecarStatus = "connecting" | "connected" | "error";

interface AppState {
  /** Resolved sidecar base URL, or null until the Tauri core reports the port. */
  sidecarBaseUrl: string | null;
  /** Current connection status to the Python sidecar. */
  sidecarStatus: SidecarStatus;
  /** Last connection error message, if any. */
  sidecarError: string | null;
  /** Resolve the sidecar URL and verify it is healthy. Safe to call repeatedly. */
  connectSidecar: () => Promise<void>;
}

/** While the sidecar is in `error`, `/health` is re-probed this often. */
export const SIDECAR_REPROBE_MS = 20_000;

/** Global app state — currently the sidecar connection lifecycle. */
export const useAppStore = create<AppState>((set) => ({
  sidecarBaseUrl: null,
  sidecarStatus: "connecting",
  sidecarError: null,
  connectSidecar: async () => {
    wireLifecycle();
    set({ sidecarStatus: "connecting", sidecarError: null });
    try {
      const baseUrl = await getSidecarBaseUrl();
      await sidecarApi.health();
      set({ sidecarBaseUrl: baseUrl });
      markReachable(true);
    } catch (error) {
      markReachable(false, error instanceof Error ? error.message : String(error));
    }
  },
}));

let reprobeTimer: ReturnType<typeof setInterval> | null = null;
let reprobing = false;

/**
 * The status moves both ways (R15-LIFECYCLE-011): any sidecar answer is
 * `connected`, a connection-level failure is `error` with its reason. While in
 * `error` a slow `/health` re-probe runs, so a recovered engine turns the
 * status back (and re-arms every `useRetryOnSidecarReady` panel).
 */
function markReachable(reachable: boolean, reason?: string): void {
  const { sidecarStatus, sidecarError } = useAppStore.getState();
  if (reachable) {
    if (reprobeTimer !== null) {
      clearInterval(reprobeTimer);
      reprobeTimer = null;
    }
    if (sidecarStatus !== "connected") {
      useAppStore.setState({ sidecarStatus: "connected", sidecarError: null });
    }
    return;
  }
  const message = reason ?? "The data engine is unreachable.";
  if (sidecarStatus !== "error" || sidecarError !== message) {
    useAppStore.setState({ sidecarStatus: "error", sidecarError: message });
  }
  reprobeTimer ??= setInterval(() => {
    if (reprobing) {
      return; // a probe waiting on a starting engine is still in flight
    }
    reprobing = true;
    void sidecarApi
      .health()
      .catch(() => undefined) // the failure already reported itself
      .finally(() => {
        reprobing = false;
      });
  }, SIDECAR_REPROBE_MS);
}

let lifecycleWired = false;

/** Follow every sidecar answer/failure, and the Rust core's
 *  `vysted://sidecar-terminated` (emitted with the reason when the engine
 *  process exits). Outside a Tauri webview the event listen fails: no-op. */
function wireLifecycle(): void {
  if (lifecycleWired) {
    return;
  }
  lifecycleWired = true;
  onSidecarReachability(markReachable);
  void import("@tauri-apps/api/event")
    .then(({ listen }) =>
      listen<string>("vysted://sidecar-terminated", (event) => markReachable(false, event.payload)),
    )
    .catch(() => undefined);
}
