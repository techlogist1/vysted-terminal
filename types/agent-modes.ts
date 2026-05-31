/**
 * Agent modes — the four-intent spine (FR-003, US3).
 *
 * The agent is not one chat box but four explicit intents on stable global
 * hotkeys, mapped to finance verbs:
 *  - Ask      — read-only Q&A over the workspace (never mutates).
 *  - Edit     — a surgical change to the panel in focus.
 *  - Build    — compose multiple panels / a workflow.
 *  - Delegate — an autonomous background task that does the upfront work, then
 *               hands off to the manipulable cockpit.
 *
 * The current mode is always visible and switchable by keyboard. The read-only
 * vs mutating semantics are ENFORCED server-side (the sidecar filters Ask to
 * read-only capabilities — see `AgentInvocationRequest.mode`); this table is the
 * frontend's display + dispatch map. Mode is the "what intent" axis; the persona
 * (copilot/Buffett/…) is the orthogonal "what lens" axis.
 */

export type AgentMode = "ask" | "edit" | "build" | "delegate";

export interface AgentModeMeta {
  id: AgentMode;
  label: string;
  /** Single-digit mnemonic; the global hotkey is Alt/Option + this digit. */
  hotkeyDigit: "1" | "2" | "3" | "4";
  /** Human hotkey label shown in the UI (⌥ reads as Option on macOS, Alt elsewhere). */
  hotkeyLabel: string;
  /** One-line description of the intent. */
  hint: string;
  /** Consequence label surfaced at the point of use (US3 — consequence-labeled). */
  consequence: string;
  /** Whether this mode may propose mutations (false only for Ask). */
  mutates: boolean;
}

export const AGENT_MODES: readonly AgentModeMeta[] = [
  {
    id: "ask",
    label: "Ask",
    hotkeyDigit: "1",
    hotkeyLabel: "⌥1",
    hint: "Read-only Q&A over your workspace.",
    consequence: "Reads only — never changes the cockpit.",
    mutates: false,
  },
  {
    id: "edit",
    label: "Edit panel",
    hotkeyDigit: "2",
    hotkeyLabel: "⌥2",
    hint: "A surgical change to the focused panel.",
    consequence: "Proposes a change to the focused panel — you review before it applies.",
    mutates: true,
  },
  {
    id: "build",
    label: "Build",
    hotkeyDigit: "3",
    hotkeyLabel: "⌥3",
    hint: "Compose multiple panels into a cockpit.",
    consequence: "Stages a multi-panel build — you review before anything opens.",
    mutates: true,
  },
  {
    id: "delegate",
    label: "Delegate",
    hotkeyDigit: "4",
    hotkeyLabel: "⌥4",
    hint: "An autonomous background task that does the upfront work, then hands off.",
    consequence:
      "Works in the background and reports back — proposed changes still need your review.",
    mutates: true,
  },
] as const;

export const DEFAULT_AGENT_MODE: AgentMode = "ask";

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
  return value === "ask" || value === "edit" || value === "build" || value === "delegate";
}
