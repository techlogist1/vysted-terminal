/**
 * Typed client over the sidecar's `/local-models` router (R16 contract,
 * "Frontend ↔ Python sidecar: local models").
 */

import {
  SidecarError,
  extractSidecarDetail,
  getSidecarBaseUrl,
  sidecarFetch,
  sidecarGet,
  sidecarRequest,
  sidecarRequestInit,
  SIDECAR_REQUEST_TIMEOUT_MS,
} from "@/lib/sidecar-client";
import type {
  DownloadState,
  DownloadsResponse,
  InstalledModelsResponse,
  LocalHardwareInfo,
  LocalModelCatalog,
} from "../../types/data";

/** A plain-language failure the UI can act on; `disk` carries the numbers. */
export class LocalModelsError extends Error {
  constructor(
    public readonly kind: "disk" | "other",
    message: string,
    public readonly neededBytes: number | null = null,
    public readonly freeBytes: number | null = null,
  ) {
    super(message);
    this.name = "LocalModelsError";
  }
}

const path = (id: string, verb = "") => `/local-models/${encodeURIComponent(id)}${verb}`;

export const localModelsApi = {
  hardware: () => sidecarGet<LocalHardwareInfo>("/local-models/hardware"),
  catalog: () => sidecarGet<LocalModelCatalog>("/local-models/catalog"),
  installed: () => sidecarGet<InstalledModelsResponse>("/local-models/installed"),
  downloads: () => sidecarGet<DownloadsResponse>("/local-models/downloads"),
  cancel: (id: string, discard = false) =>
    sidecarRequest<DownloadState>("POST", path(id, "/cancel"), {
      params: { discard: discard ? "true" : undefined },
    }),
  remove: (id: string) => sidecarRequest<void>("DELETE", path(id)),
  /** Start or resume. A 409 (not enough disk) rejects with `LocalModelsError{kind:"disk"}`;
   *  read raw here because the shared client drops the body's byte counts. */
  download: async (id: string): Promise<DownloadState> => {
    const url = new URL(path(id, "/download"), await getSidecarBaseUrl()).toString();
    const init = await sidecarRequestInit("POST", { timeoutMs: SIDECAR_REQUEST_TIMEOUT_MS });
    const response = await sidecarFetch(url, init);
    const body: unknown = await response.json().catch(() => null);
    if (response.ok) {
      return body as DownloadState;
    }
    const detail = extractSidecarDetail(body, `HTTP ${response.status}`);
    if (response.status === 409) {
      const b = (body ?? {}) as { neededBytes?: unknown; freeBytes?: unknown };
      throw new LocalModelsError(
        "disk",
        detail,
        typeof b.neededBytes === "number" ? b.neededBytes : null,
        typeof b.freeBytes === "number" ? b.freeBytes : null,
      );
    }
    throw new SidecarError(response.status, detail);
  },
};

/** "4.7 GB" / "820 MB". */
export function formatBytes(n: number): string {
  const gb = n / 1024 ** 3;
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${Math.max(0, Math.round(n / 1024 ** 2))} MB`;
}

/** Whole percent received, 0–100. */
export function downloadPercent(d: DownloadState): number {
  return d.totalBytes > 0 ? Math.min(100, Math.floor((d.receivedBytes / d.totalBytes) * 100)) : 0;
}

/** "about 3 min left" from the current speed, or null when unknown. */
export function timeLeft(d: DownloadState): string | null {
  if (!d.bytesPerSec || d.bytesPerSec <= 0) return null;
  const secs = (d.totalBytes - d.receivedBytes) / d.bytesPerSec;
  if (secs < 60) return "less than a minute left";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `about ${mins} min left`;
  return `about ${Math.round(mins / 60)} h left`;
}

/** True while bytes are (or are about to be) moving. */
export function isActiveDownload(d: DownloadState): boolean {
  return d.state === "queued" || d.state === "downloading" || d.state === "verifying";
}
