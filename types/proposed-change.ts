/**
 * Proposed mutation — the diff/accept trust gate (FR-010, US4).
 *
 * Every change an agent proposes (panel re-config, chart symbol, watchlist
 * edit, multi-panel build, portfolio/notes/screen/layout write, or setting) is
 * staged as a ProposedChange and shown as a reviewable old→new diff. Nothing
 * lands until the user accepts (or has chosen AUTO autonomy and the kind
 * {@link autoApplies}); rejecting leaves state unchanged. This is the trust
 * spine (Constitution / spec US4).
 */

import type { HostIntent, PreImage } from "../src/lib/host-actions";

/**
 * The host-action families the gate governs (all `read_only=false` in the
 * catalog). R10 (D41/D45) adds `data-write` (portfolio positions, notes, saved
 * screens and layouts) and `settings` (the agent-drivable region).
 */
export const PROPOSED_CHANGE_KINDS = [
  "chart",
  "panel",
  "watchlist",
  "data-write",
  "settings",
] as const;

export type ProposedChangeKind = (typeof PROPOSED_CHANGE_KINDS)[number];

/**
 * The kinds that apply without review under AUTO autonomy (spec SC-025):
 * `panel` (which covers publish_brief, arrange_layout and
 * write_screener_filters), `chart` and `watchlist`. `data-write` and
 * `settings` always wait for the user's review. The one declaration of the
 * auto-applied set — {@link autoApplies} reads it (R15-DOCS-016/017/018;
 * docs/CURRENT_STATE.md quotes this constant by name rather than
 * hand-counting the write set).
 */
export const AUTO_APPLIED_KINDS: readonly ProposedChangeKind[] = [
  "panel",
  "chart",
  "watchlist",
] as const;

export function autoApplies(kind: ProposedChangeKind): boolean {
  return (AUTO_APPLIED_KINDS as readonly ProposedChangeKind[]).includes(kind);
}

/** `undone`: an applied data write the user reverted from the review (session Undo). */
export type ProposedChangeStatus = "pending" | "accepted" | "rejected" | "undone";

export interface ProposedChange {
  /** Stable id for this proposed change. */
  id: string;
  /** Tool-call id from the streamed `tool_use` event that produced it. */
  toolCallId: string;
  /** The host-action the agent proposed (catalog tool name + its arguments). */
  action: { name: string; input: Record<string, unknown> };
  /** The action parsed ONCE at enqueue, targets bound — the diff was built from
   *  it and accept applies exactly it (never re-resolved at accept time). */
  intent: HostIntent;
  kind: ProposedChangeKind;
  /** One-line title, e.g. "Open the News panel". */
  title: string;
  /** Old-state summary (what the cockpit shows now). */
  before: string;
  /** New-state summary (what the change would make it). */
  after: string;
  status: ProposedChangeStatus;
  /** Failure detail when an accepted change could not apply (re-pended for retry),
   *  or why its Undo could not restore the pre-image. */
  detail?: string;
  /** What the applied write replaced — set on apply for an undoable data write. */
  preImage?: PreImage;
  /** Groups changes from a single agent turn for bulk accept/reject. */
  batchId: string;
  /** Agent that proposed it (provenance for the diff header). */
  agentId?: string;
  agentName?: string;
  /** Epoch milliseconds when staged. */
  createdAt: number;
}
