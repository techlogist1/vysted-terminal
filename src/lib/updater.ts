import { invoke } from "@tauri-apps/api/core";

import { sidecarGet } from "@/lib/sidecar-client";

/** `update_check` answer (R16 contract). */
export interface UpdateInfo {
  available: boolean;
  version?: string;
  notes?: string;
  date?: string;
}

/** `updater://progress` payload; `total` is null when the server sent no length. */
export interface UpdateProgress {
  downloaded: number;
  total: number | null;
}

function inTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/** Never throws: outside the desktop shell or on any failure there is no update. */
export async function checkForUpdate(): Promise<UpdateInfo> {
  if (!inTauri()) return { available: false };
  try {
    return await invoke<UpdateInfo>("update_check");
  } catch {
    return { available: false };
  }
}

/** Downloads, verifies, installs, then the app relaunches (resolves only on failure paths). */
export async function installUpdate(onProgress: (p: UpdateProgress) => void): Promise<void> {
  const { listen } = await import("@tauri-apps/api/event");
  const unlisten = await listen<UpdateProgress>("updater://progress", (e) => onProgress(e.payload));
  try {
    await invoke("update_download_and_install");
  } finally {
    unlisten();
  }
}

/** True while any local-model download is `downloading` or `verifying`. A missing
 *  models router (404) or an unreachable sidecar counts as no active download. */
export async function hasActiveModelDownload(): Promise<boolean> {
  try {
    const { downloads } = await sidecarGet<{ downloads: { state: string }[] }>(
      "/local-models/downloads",
    );
    return downloads.some((d) => d.state === "downloading" || d.state === "verifying");
  } catch {
    return false;
  }
}
