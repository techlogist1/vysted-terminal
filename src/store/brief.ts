/**
 * Brief store — the research brief LIFECYCLE state machine (R10, D39/E3).
 *
 * The panel state is explicit: `empty` → `in_flight` (a research run began) →
 * `published` (the run's publish landed) | `archived` (with a stated reason).
 * A workspace-restored brief ALWAYS lands archived("restored") — a reboot can
 * never serve yesterday's artifact as current. A publish whose execution
 * run_id does not match the in-flight run is ignored as stale; a failed/
 * abandoned run restores the prior brief as archived("run_failed").
 *
 * `brief` is kept as a legacy MIRROR (published/archived brief, or the
 * in-flight run's prior) so unrelated consumers — workspace serialisation,
 * the arrange planner's content signals, the depth carry — keep reading one
 * field; only the PANEL distinguishes phases.
 *
 * Persistence is unchanged: the brief is non-secret research output and rides
 * the workspace blob (`SerializedWorkspace.brief`) as a plain
 * `ResearchBriefData` — no persisted `archived` marker is needed because the
 * restore path archives by rule. Self-persists via `autosaveLayout` (no-ops
 * before the dockview layout mounts, so unit-test setters are silent no-ops).
 */

import { create } from "zustand";

import { isAcceptableBriefMode, normalizeBriefMode } from "@/lib/brief-ingest";
import { autosaveLayout } from "@/lib/workspace";
import type { BriefDepth, BriefStep, ResearchBriefData } from "../../types/brief";

/**
 * The serialisable brief bundle — exactly what rides the workspace blob's
 * `brief` field. `null` when no brief has been produced this session/workspace.
 */
export type BriefBundle = ResearchBriefData | null;

/** Why an archived brief is archived — always stated, never silent (D39). */
export type BriefArchiveReason = "restored" | "superseded" | "run_failed";

/** The explicit lifecycle the panel renders (R10 brief state machine). */
export type BriefPanelState =
  | { phase: "empty" }
  | {
      phase: "in_flight";
      runId: string;
      query: string;
      symbol?: string;
      depth: BriefDepth;
      startedAt: number;
      steps: BriefStep[];
      /** The previously published/archived brief, restored on a failed run. */
      prior?: ResearchBriefData;
    }
  | { phase: "published"; brief: ResearchBriefData }
  | { phase: "archived"; brief: ResearchBriefData; archivedAt: number; reason: BriefArchiveReason };

/** How a publish resolved against the in-flight run. */
export type BriefPublishResult = "published" | "stale_run";

/**
 * Watchdog budget per depth tier: the engine's wall (`depth.py` PROFILES —
 * iter 120s, heavy 360s; the fast loop has no wall, so it inherits the
 * runtime's ~90s outer dispatch guard) + 60s of slack. An in-flight run older
 * than this can no longer publish a live result — the panel archives the prior
 * instead of spinning forever (E3: a broken run leaves a trail, not a lie).
 */
const RUN_WATCHDOG_MS: Record<BriefDepth, number> = {
  quick: 150_000,
  deep: 180_000,
  heavy: 420_000,
};

interface BriefState {
  /** The lifecycle state the panel renders. */
  panel: BriefPanelState;
  /** Legacy mirror — published/archived brief, or the in-flight run's prior. */
  brief: ResearchBriefData | null;
  /** A research run began (the runtime's `research:begin` engine step). */
  beginRun: (run: { runId: string; query: string; symbol?: string; depth: BriefDepth }) => void;
  /** Append a live research step to the in-flight run (no-op otherwise). */
  appendRunStep: (step: BriefStep) => void;
  /** A publish_brief applied — published when it belongs to the in-flight run
   *  (or none is in flight); a mismatched run_id is ignored as stale. */
  publish: (brief: ResearchBriefData) => BriefPublishResult;
  /** The run died (stream error / done-without-publish / rejected publish):
   *  restore the prior as archived("run_failed"), or fall back to empty. */
  failRun: () => void;
  /** Archive an in-flight run that outlived its depth wall + 60s slack. */
  watchdogTick: (now?: number) => void;
  /** Legacy setter — publishes through the state machine. */
  setBrief: (brief: ResearchBriefData) => void;
  /** Clear back to the empty state. */
  clearBrief: () => void;
  /** Snapshot the current brief as a plain bundle (for serialize/export). */
  toBundle: () => BriefBundle;
  /** Restore from a persisted bundle — ALWAYS archived("restored") (D39). */
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

/** The legacy `brief` mirror for a panel state — one derivation, every setter. */
function mirrorOf(panel: BriefPanelState): ResearchBriefData | null {
  switch (panel.phase) {
    case "published":
      return panel.brief;
    case "archived":
      return panel.brief;
    case "in_flight":
      return panel.prior ?? null;
    default:
      return null;
  }
}

/** The brief a dying run restores: the in-flight prior, else the current brief. */
function archiveOnFailure(panel: BriefPanelState): BriefPanelState {
  const prior = panel.phase === "in_flight" ? panel.prior : mirrorOf(panel);
  if (!prior) {
    return { phase: "empty" };
  }
  return { phase: "archived", brief: prior, archivedAt: Date.now(), reason: "run_failed" };
}

export const useBriefStore = create<BriefState>((set, get) => {
  const transition = (panel: BriefPanelState, options?: { persist?: boolean }): void => {
    set({ panel, brief: mirrorOf(panel) });
    if (options?.persist !== false) {
      persist();
    }
  };

  return {
    panel: { phase: "empty" },
    brief: null,

    beginRun: ({ runId, query, symbol, depth }) => {
      // The prior published/archived brief rides INTO the run so a failure can
      // restore it (archived, reason run_failed) instead of a dead panel. A
      // re-begin while in flight keeps the ORIGINAL prior — the abandoned
      // run never produced anything worth carrying. Transient state: no
      // autosave churn mid-run (the publish/fail transition persists).
      const current = get().panel;
      const prior = current.phase === "in_flight" ? current.prior : (mirrorOf(current) ?? undefined);
      transition(
        {
          phase: "in_flight",
          runId,
          query,
          symbol,
          depth,
          startedAt: Date.now(),
          steps: [],
          prior,
        },
        { persist: false },
      );
    },

    appendRunStep: (step) => {
      const current = get().panel;
      if (current.phase !== "in_flight") {
        return;
      }
      // Transient (no autosave) — steps feed the live in-flight surface only.
      set({ panel: { ...current, steps: [...current.steps, step] } });
    },

    publish: (brief) => {
      const current = get().panel;
      if (current.phase === "in_flight" && brief.execution?.runId !== current.runId) {
        // A publish that does not belong to the run on screen — an older run
        // racing in, or a record-less legacy artifact — never replaces the
        // live run (E3.2: stale artifacts don't serve as current).
        return "stale_run";
      }
      // The previously published brief (current.prior on a matched run, or the
      // directly replaced one) is superseded by this publish — single-slot
      // panel, the richer-artifact arbitration happened in the apply path.
      transition({ phase: "published", brief });
      return "published";
    },

    failRun: () => {
      transition(archiveOnFailure(get().panel));
    },

    watchdogTick: (now = Date.now()) => {
      const current = get().panel;
      if (current.phase !== "in_flight") {
        return;
      }
      const budget = RUN_WATCHDOG_MS[current.depth] ?? RUN_WATCHDOG_MS.quick;
      if (now - current.startedAt > budget) {
        transition(archiveOnFailure(current));
      }
    },

    setBrief: (brief) => {
      get().publish(brief);
    },

    clearBrief: () => {
      transition({ phase: "empty" });
    },

    toBundle: () => get().brief,

    fromBundle: (bundle) => {
      // Accept only a well-formed brief; a garbled/partial blob restores to
      // empty so the panel never renders a half-populated brief. Coerce the
      // mode to the canonical uppercase FAST|DEEP (S-6). A restored brief is
      // ALWAYS archival (D39) — it was produced in a previous session and must
      // never re-render as current; the panel's Refresh affordance re-runs it.
      if (!isBriefData(bundle)) {
        transition({ phase: "empty" });
        return;
      }
      transition({
        phase: "archived",
        brief: { ...bundle, mode: normalizeBriefMode(bundle.mode) },
        archivedAt: Date.now(),
        reason: "restored",
      });
    },
  };
});

/** Non-reactive snapshot of the brief bundle (for serialize/export). */
export function briefBundle(): BriefBundle {
  return useBriefStore.getState().toBundle();
}

/** Test helper: reset the brief store to its empty state. */
export function resetBriefStoreForTests(): void {
  useBriefStore.setState({ panel: { phase: "empty" }, brief: null });
}
