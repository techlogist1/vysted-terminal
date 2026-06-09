/**
 * Research depth store — the composer's three-stop depth slider (R7 Track C).
 *
 * One session-scoped knob: how hard the NEXT research run works. The slider in
 * the composer meta row sets it; `handleSend` reads it at call time and threads
 * it into the invocation `options` as `researchDepth` (crossing the wire as
 * snake_case `research_depth` — see `streaming.ts`). Deliberately session-state
 * zustand, NOT persisted: the lead wires persistence + the sidecar honoring of
 * `options.research_depth` (docs/redesign/INTEGRATION_NOTES_R7_CHAT.md).
 *
 * Distinct from `BriefDepth` (`quick`/`deep`/`heavy`) — that vocabulary belongs
 * to the brief's published tier + the deterministic "go deeper" escalation
 * (agent-command), which stays untouched. This is the forward-looking knob.
 */

import { create } from "zustand";

export type ResearchDepth = "normal" | "deep" | "ultra";

/** Slider stops, shallow → deep (the rail renders them in this order). */
export const RESEARCH_DEPTHS: readonly ResearchDepth[] = ["normal", "deep", "ultra"];

export const RESEARCH_DEPTH_LABEL: Record<ResearchDepth, string> = {
  normal: "Normal",
  deep: "Deep",
  ultra: "Ultra",
};

interface ResearchDepthState {
  /** Depth the next research run should work at. */
  depth: ResearchDepth;
  setDepth: (depth: ResearchDepth) => void;
}

export const useResearchDepthStore = create<ResearchDepthState>((set) => ({
  depth: "normal",
  setDepth: (depth) => set({ depth }),
}));

export function isResearchDepth(value: unknown): value is ResearchDepth {
  return value === "normal" || value === "deep" || value === "ultra";
}

/** Test helper: reset to the default depth. */
export function resetResearchDepthStoreForTests(): void {
  useResearchDepthStore.setState({ depth: "normal" });
}
