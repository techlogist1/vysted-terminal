import { create } from "zustand";

import { getSidecarBaseUrl, sidecarApi } from "@/lib/sidecar-client";

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

/** Global app state — currently the sidecar connection lifecycle. */
export const useAppStore = create<AppState>((set) => ({
  sidecarBaseUrl: null,
  sidecarStatus: "connecting",
  sidecarError: null,
  connectSidecar: async () => {
    set({ sidecarStatus: "connecting", sidecarError: null });
    try {
      const baseUrl = await getSidecarBaseUrl();
      await sidecarApi.health();
      set({ sidecarBaseUrl: baseUrl, sidecarStatus: "connected", sidecarError: null });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      set({ sidecarStatus: "error", sidecarError: message });
    }
  },
}));
