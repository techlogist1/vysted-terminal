"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";
import { useAgentRunsStore } from "@/store/agent-runs";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { DEFAULT_MODEL_BY_PROVIDER, useModelSelectionStore } from "@/store/model-selection";

/**
 * Status chrome (FR-033) — surfaces the three live signals that were computed
 * but unrendered: sidecar connection state, the active provider/model, and the
 * count of running background agents. P1 wires the existing store signals into
 * the header; P2 polishes this into the minimal-dark status surface.
 */
export function StatusChrome() {
  const status = useAppStore((state) => state.sidecarStatus);
  const provider = useLLMProvidersStore((state) => state.defaultProviderId);
  const overrides = useModelSelectionStore((state) => state.overrides);
  const runs = useAgentRunsStore((state) => state.runs);

  const activeRunCount = useMemo(
    () => runs.filter((r) => r.status === "running" || r.status === "paused").length,
    [runs],
  );
  const model = overrides[provider] ?? DEFAULT_MODEL_BY_PROVIDER[provider];

  const dotClass =
    status === "connected"
      ? "bg-positive"
      : status === "error"
        ? "bg-negative"
        : "bg-warning animate-pulse";
  const connLabel =
    status === "connected" ? "Connected" : status === "error" ? "Sidecar error" : "Connecting…";

  return (
    <div
      aria-label="Status"
      className="text-charcoal-400 flex items-center gap-3 font-mono text-[0.6rem]"
    >
      <span className="flex items-center gap-1" title={`Sidecar: ${connLabel}`}>
        <span className={cn("size-1.5 rounded-full", dotClass)} aria-hidden />
        {connLabel}
      </span>
      <span
        className="text-charcoal-500 max-w-[12rem] truncate"
        title="Default provider / model (the agent panel shows the per-send effective provider)"
      >
        {provider} · {model}
      </span>
      {activeRunCount > 0 && (
        <span className="flex items-center gap-1 text-amber-400" title="Running agents">
          <span className="animate-pulse" aria-hidden>
            ●
          </span>
          {activeRunCount}
        </span>
      )}
    </div>
  );
}
