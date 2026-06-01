/**
 * Hardware fit client (Track D) — reads `GET /system/hardware`.
 *
 * Surfaces the sidecar's device detection + local-model fit verdicts so the UI
 * can show what this machine can run locally and why a heavy path (e.g. local
 * deep-research) is gated to the keyless-remote fallback. Read-only, no secrets.
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
