/**
 * Brief store — the most recent research brief JARVIS produced (FR-074,
 * PASS_B_RESEARCH B.5).
 *
 * Holds at most one brief (the latest run); a new run replaces it. The brief is
 * non-secret research output, so — unlike a credential — it rides the workspace
 * blob (`SerializedWorkspace.brief`) and survives a relaunch. Persistence mirrors
 * the search-settings pattern exactly: because setting a brief does not move the
 * dockview layout, the store self-persists by calling `void autosaveLayout()`
 * from each mutating action.
 *
 * SSR-safe: no `window`/`navigator` at module load; `autosaveLayout` no-ops
 * before the dockview layout mounts (so a setter in a unit test is a silent
 * no-op when the network/dockview is absent).
 */

import { create } from "zustand";

import { isAcceptableBriefMode, normalizeBriefMode } from "@/lib/brief-ingest";
import { autosaveLayout } from "@/lib/workspace";
import type { ResearchBriefData } from "../../types/brief";

/**
 * The serialisable brief bundle — exactly what rides the workspace blob's
 * `brief` field. `null` when no brief has been produced this session/workspace.
 */
export type BriefBundle = ResearchBriefData | null;

interface BriefState {
  /** The most recent research brief, or `null` before any run. */
  brief: ResearchBriefData | null;
  /** Replace the current brief with a fresh run's output. */
  setBrief: (brief: ResearchBriefData) => void;
  /** Clear the current brief back to the empty state. */
  clearBrief: () => void;
  /** Snapshot the current brief as a plain bundle (for serialize/export). */
  toBundle: () => BriefBundle;
  /** Replace the current brief from a persisted bundle (workspace restore). */
  fromBundle: (bundle: BriefBundle) => void;
}

/**
 * Self-persist a brief change into the autosave slot. Fire-and-forget —
 * `autosaveLayout` is best-effort and no-ops before the layout mounts.
 */
function persist(): void {
  void autosaveLayout();
}

/**
 * Validate a candidate bundle on the way in from a persisted blob. A hand-edited
 * or older export could carry a partial/garbled shape; we accept it only when it
 * has the load-bearing fields, otherwise treat it as "no brief" rather than
 * render a half-populated panel. The `mode` check accepts a raw lowercase wire
 * value (`fast`/`deep`/`heavy`) too — a brief persisted straight from the wire
 * before the casing fix still restores (it is normalised to FAST|DEEP below).
 */
function isBriefData(value: unknown): value is ResearchBriefData {
  if (value === null || typeof value !== "object") {
    return false;
  }
  const v = value as Record<string, unknown>;
  return (
    typeof v.query === "string" &&
    isAcceptableBriefMode(v.mode) &&
    typeof v.markdown === "string" &&
    Array.isArray(v.sources) &&
    typeof v.sourceCount === "number" &&
    typeof v.webAvailable === "boolean" &&
    typeof v.createdAt === "number"
  );
}

export const useBriefStore = create<BriefState>((set, get) => ({
  brief: null,

  setBrief: (brief) => {
    set({ brief });
    persist();
  },

  clearBrief: () => {
    set({ brief: null });
    persist();
  },

  toBundle: () => get().brief,

  fromBundle: (bundle) => {
    // Accept only a well-formed brief; a garbled/partial blob restores to empty
    // so the panel never renders a half-populated brief. Coerce the mode to the
    // canonical uppercase FAST|DEEP so a brief persisted with a raw lowercase
    // wire mode renders the badge correctly after restore (S-6).
    set({
      brief: isBriefData(bundle) ? { ...bundle, mode: normalizeBriefMode(bundle.mode) } : null,
    });
    persist();
  },
}));

/** Non-reactive snapshot of the brief bundle (for serialize/export). */
export function briefBundle(): BriefBundle {
  return useBriefStore.getState().toBundle();
}

/** Test helper: reset the brief store to its empty state. */
export function resetBriefStoreForTests(): void {
  useBriefStore.setState({ brief: null });
}
