/**
 * Proposed mutation — the diff/accept trust gate (FR-010, US4).
 *
 * Every change an agent proposes (panel re-config, chart symbol, watchlist
 * edit, multi-panel build, portfolio/notes/screen/layout write, or setting) is
 * staged as a ProposedChange and shown as a reviewable old→new diff. Nothing
 * lands until the user accepts (or has chosen AUTO autonomy); rejecting leaves
 * state unchanged. This is the trust spine (Constitution / spec US4).
 */

/**
 * The host-action families the gate governs (all `read_only=false` in the
 * catalog). R10 (D41/D45) adds `data-write` (portfolio positions, notes,
 * saved screens — auto-applicable under AUTO autonomy) and `settings` (the two
 * agent-drivable settings: region + default research depth).
 */
export type ProposedChangeKind = "panel" | "chart" | "watchlist" | "data-write" | "settings";

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
  /** Agent that proposed it (provenance for the diff header). */
  agentId?: string;
  agentName?: string;
  /** Epoch milliseconds when staged. */
  createdAt: number;
}
