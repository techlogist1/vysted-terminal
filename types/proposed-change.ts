/**
 * Proposed mutation — the diff/accept trust gate (FR-010, US4).
 *
 * Every change an agent proposes (panel re-config, chart symbol, watchlist
 * edit, multi-panel build, or order) is staged as a ProposedChange and shown
 * as a reviewable old→new diff. Nothing lands until the user accepts; rejecting
 * leaves state unchanged. Copying Cursor's diff/accept correctly — and refusing
 * its auto-apply regression — is the trust spine (Constitution / spec US4).
 *
 * For orders the "accept" terminates in the §6.5 confirm_and_place dialog (the
 * mandatory "I reviewed" checkbox + Confirm), NEVER a generic apply — the AI has
 * no path to placement (FR-011).
 */

/**
 * The host-action families the gate governs (all `read_only=false` in the
 * catalog). R10 (D41/D45) adds `data-write` (paper-portfolio positions, notes,
 * saved screens — auto-applicable under AUTO autonomy) and `settings` (the two
 * agent-drivable settings: region + default research depth). `order` remains
 * the ONE kind that never auto-applies in any mode (§6.5).
 */
export type ProposedChangeKind =
  | "panel"
  | "chart"
  | "watchlist"
  | "order"
  | "data-write"
  | "settings";

export type ProposedChangeStatus = "pending" | "accepted" | "rejected";

export interface ProposedChange {
  /** Stable id for this proposed change. */
  id: string;
  /** Tool-call id from the streamed `tool_use` event that produced it. */
  toolCallId: string;
  /** The host-action the agent proposed (catalog tool name + its arguments). */
  action: { name: string; input: Record<string, unknown> };
  kind: ProposedChangeKind;
  /** One-line title, e.g. "Open the News panel". */
  title: string;
  /** Old-state summary (what the cockpit shows now). */
  before: string;
  /** New-state summary (what the change would make it). */
  after: string;
  status: ProposedChangeStatus;
  /** Failure detail when an accepted change could not apply (re-pended for retry). */
  detail?: string;
  /** Groups changes from a single agent turn for bulk accept/reject. */
  batchId: string;
  /** Agent that proposed it (order provenance + the diff header). */
  agentId?: string;
  agentName?: string;
  /** Epoch milliseconds when staged. */
  createdAt: number;
}
