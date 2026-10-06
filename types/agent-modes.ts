/**
 * Agent modes — the inferred-intent spine (FR-003, US3; JARVIS sprint Track B).
 *
 * The old four explicit modes (Ask / Edit / Build / Delegate) forced the user to
 * pick the intent AND created a live contradiction — "Build: you review before
 * anything opens" fought the AUTO autonomy that auto-applies UI changes. The
 * sprint collapses the three hands-on modes into ONE inferred surface:
 *
 *  - Agent    — describe what you want; JARVIS infers read vs edit vs build from
 *               your words (no mode-picking). Read-only intents are gated to
 *               read-only tools SERVER-SIDE (`classify_intent` in the sidecar),
 *               exactly as the old "Ask" was — the safety line is preserved, the
 *               picking is gone.
 *  - Delegate — KEPT distinct: an autonomous, BudgetGuard-bounded background task
 *               (the budget is a §6.5-adjacent safety surface; merging it would
 *               lose that). Hands off to the manipulable cockpit when done.
 *
 * Mode is the "what intent" axis; the persona (copilot/Buffett/…) is the
 * orthogonal "what lens" axis; autonomy (ask/auto) is the orthogonal
 * "how much confirmation" axis. AUTO auto-applies UI/layout/chart/watchlist only —
 * never an order, in any mode (enforced in `proposed-changes`).
 */

export type AgentMode = "agent" | "delegate";

export interface AgentModeMeta {
  id: AgentMode;
  label: string;
  /** Single-digit mnemonic; the global hotkey is Alt/Option + this digit. */
  hotkeyDigit: "1" | "2";
  /** Human hotkey label shown in the UI (⌥ reads as Option on macOS, Alt elsewhere). */
  hotkeyLabel: string;
  /** One-line description of the intent. */
  hint: string;
  /** Consequence label surfaced at the point of use (US3 — consequence-labeled). */
  consequence: string;
  /** Whether this mode may propose mutations (both can; the read-only gate for a
   *  read intent is applied server-side from the inferred intent, not the mode). */
  mutates: boolean;
}

export const AGENT_MODES: readonly AgentModeMeta[] = [
  {
    id: "agent",
    label: "Agent",
    hotkeyDigit: "1",
    hotkeyLabel: "⌥1",
    hint: "Describe what you want — JARVIS infers whether to read, edit, or build.",
    consequence:
      "Reads, edits, or builds from your words. UI changes apply on review (or instantly in AUTO); orders always need review.",
    mutates: true,
  },
  {
    id: "delegate",
    label: "Delegate",
    hotkeyDigit: "2",
    hotkeyLabel: "⌥2",
    hint: "An autonomous, budget-bounded background task that hands off to the cockpit.",
    consequence:
      "Works in the background within a budget and reports back — proposed changes still need your review.",
    mutates: true,
  },
] as const;

export const DEFAULT_AGENT_MODE: AgentMode = "agent";

const MODE_BY_ID: Record<AgentMode, AgentModeMeta> = AGENT_MODES.reduce(
  (acc, m) => {
    acc[m.id] = m;
    return acc;
  },
  {} as Record<AgentMode, AgentModeMeta>,
);

export function agentModeMeta(mode: AgentMode): AgentModeMeta {
  return MODE_BY_ID[mode];
}

export function isAgentMode(value: unknown): value is AgentMode {
  return value === "agent" || value === "delegate";
}

/**
 * Coerce any value (incl. a legacy persisted mode) to a valid {@link AgentMode}.
 * Older workspace blobs stored "ask" / "edit" / "build" — those all fold into the
 * single inferred "agent" surface; "delegate" is preserved; anything else falls
 * to the default. Used on workspace restore so an old blob never drops the mode.
 */
export function coerceAgentMode(value: unknown): AgentMode {
  if (value === "delegate") {
    return "delegate";
  }
  if (value === "agent" || value === "ask" || value === "edit" || value === "build") {
    return "agent";
  }
  return DEFAULT_AGENT_MODE;
}
