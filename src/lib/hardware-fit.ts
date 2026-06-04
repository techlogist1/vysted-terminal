/**
 * Hardware fit client (Track D) — reads `GET /system/hardware`.
 *
 * Surfaces the sidecar's device detection + local-model fit verdicts so the UI
 * can show what this machine can run locally and why a heavy path (e.g. a large
 * local model) is gated to the keyless-remote path. Read-only, no secrets.
 */

import { getSidecarBaseUrl } from "@/lib/sidecar-client";

export type FitVerdict = "green" | "marginal" | "red";

export interface DeviceProfile {
  ramGib: number;
  gpuBudgetGib: number;
  totalCores: number;
  perfCores: number;
  isAppleSilicon: boolean;
  arch: string;
  chip: string;
  osName: string;
  osVersion: string;
}

export interface ScoredModel {
  name: string;
  verdict: FitVerdict;
  gpuFitRatio: number;
  ramFitRatio: number;
  demandGib: number;
  ctxMax: number;
  reason: string;
  throughputNote: string;
  signals: string[];
}

export interface HardwareReport {
  device: DeviceProfile;
  ollama: { endpoint: string; models: ScoredModel[] };
  referenceCandidates: ScoredModel[];
}

/** Fetch the hardware report from the sidecar, or `null` if it's unreachable. */
export async function fetchHardwareReport(): Promise<HardwareReport | null> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL("/system/hardware", base).toString());
    if (!resp.ok) {
      return null;
    }
    return (await resp.json()) as HardwareReport;
  } catch {
    return null;
  }
}

// --- First-run onboarding: local-model recommendation + Ollama setup --------

/** The best-fit local model for this device + every scored candidate (Path B). */
export interface LocalModelRecommendation {
  device: DeviceProfile;
  candidates: ScoredModel[];
  /** First green (best tool-caller), else first marginal, else null (use cloud). */
  recommended: ScoredModel | null;
}

/** Fetch the first-run local-model recommendation, or `null` if unreachable. */
export async function fetchLocalModelRecommendation(): Promise<LocalModelRecommendation | null> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL("/system/local-model-recommendation", base).toString());
    if (!resp.ok) {
      return null;
    }
    return (await resp.json()) as LocalModelRecommendation;
  } catch {
    return null;
  }
}

/** Whether the local Ollama daemon is reachable + what models are pulled. */
export interface OllamaStatus {
  running: boolean;
  endpoint: string;
  models: string[];
}

/** Probe the local Ollama daemon. `running:false` means not installed/started. */
export async function fetchOllamaStatus(): Promise<OllamaStatus> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL("/system/ollama/status", base).toString());
    if (!resp.ok) {
      return { running: false, endpoint: "", models: [] };
    }
    return (await resp.json()) as OllamaStatus;
  } catch {
    return { running: false, endpoint: "", models: [] };
  }
}

/** One progress frame from the streaming Ollama model pull. */
export interface PullProgress {
  status: string;
  total?: number | null;
  completed?: number | null;
  done?: boolean;
  error?: string;
}

/**
 * Pull an Ollama model, streaming progress to `onProgress` (Path B setup).
 * Consumes the sidecar's SSE `POST /system/ollama/pull` via a ReadableStream
 * reader. Resolves `{ok:false, error}` on any failure (daemon down, unknown
 * model) — the caller renders the error rather than throwing. Honors an
 * `AbortSignal` so the user can cancel a download.
 */
export async function pullOllamaModel(
  model: string,
  opts: { onProgress?: (p: PullProgress) => void; signal?: AbortSignal } = {},
): Promise<{ ok: boolean; error?: string }> {
  let lastError: string | undefined;
  try {
    const base = await getSidecarBaseUrl();
    const url = new URL("/system/ollama/pull", base);
    url.searchParams.set("model", model);
    const resp = await fetch(url.toString(), { method: "POST", signal: opts.signal });
    if (!resp.ok || !resp.body) {
      return { ok: false, error: `sidecar returned ${resp.status}` };
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const dataLine = frame.split("\n").find((line) => line.startsWith("data:"));
        if (!dataLine) {
          continue;
        }
        try {
          const payload = JSON.parse(dataLine.slice(5).trim()) as PullProgress;
          if (payload.error) {
            lastError = payload.error;
          }
          opts.onProgress?.(payload);
        } catch {
          // Ignore a partial/garbled frame — the next read completes it.
        }
      }
    }
    return lastError ? { ok: false, error: lastError } : { ok: true };
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return { ok: false, error: "cancelled" };
    }
    return { ok: false, error: err instanceof Error ? err.message : "pull failed" };
  }
}

/** Human label + tailwind text colour for a verdict chip. */
export function verdictMeta(verdict: FitVerdict): { label: string; className: string } {
  switch (verdict) {
    case "green":
      return { label: "runs locally", className: "text-positive" };
    case "marginal":
      return { label: "tight", className: "text-amber-400" };
    default:
      return { label: "too large — remote", className: "text-negative" };
  }
}
