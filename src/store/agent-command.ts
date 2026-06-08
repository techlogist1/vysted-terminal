/**
 * Agent command channel — a cross-module "send this to the agent" path.
 *
 * Mirrors the `chart-command` store pattern (host → consumer, with a `seq` so an
 * identical re-issue still re-triggers): a module OUTSIDE the chat sidebar (e.g.
 * the brief panel's "Go deeper" affordance, or a first-run "try this" chip)
 * pushes a natural-language prompt here, and the chat sidebar — the single owner
 * of the send pipeline (provider/model resolution, history, the §6.5 gate) —
 * subscribes and routes it through its normal `handleSend`. This keeps ONE send
 * path: the affordance never re-implements provider/key resolution or the gate.
 *
 * Used by the research collapse (FR-115 / SC-028): "Go deeper" on a rendered
 * brief re-runs the SAME query at the next depth tier in place, so depth is an
 * escalation the user controls without ever seeing a mode/angles/backend knob.
 *
 * SSR-safe: no `window`/`navigator` at module load.
 */

import { create } from "zustand";

import type { BriefDepth } from "../../types/brief";

/** One issued agent command. The load-bearing deterministic signal is `prompt`
 *  itself: for a depth escalation `researchDepthPrompt` composes it as
 *  `research <subject> at depth=<tier>`, naming the exact tier so the agent maps
 *  it straight to `research(subject, depth=<tier>)` — never parsing a fuzzy
 *  "go all out" phrase. `depth` rides alongside as structured provenance for any
 *  subscriber that wants the tier without re-parsing the prompt. */
export interface AgentCommand {
  prompt: string;
  /** The explicit research depth tier this command escalates to, when it is a
   *  depth escalation (`quick`/`deep`/`heavy`); omitted for a plain prompt.
   *  Structured provenance — the prompt already encodes the tier deterministically. */
  depth?: BriefDepth;
  /** Bumps on every issue so an identical command still re-triggers the
   *  subscriber (e.g. clicking "Go deeper" twice). */
  seq: number;
}

interface AgentCommandState {
  /** Most recent "send this prompt to the agent" command from a non-chat module
   *  (the chat surface's depth control, a first-run "try this" chip). `null`
   *  until first issued. */
  command: AgentCommand | null;
  /** Push a prompt onto the channel for the chat sidebar to send. The optional
   *  `depth` rides along as structured data for a research-depth escalation. */
  send: (prompt: string, depth?: BriefDepth) => void;
}

export const useAgentCommandStore = create<AgentCommandState>((set) => ({
  command: null,
  send: (prompt, depth) =>
    set((state) => ({ command: { prompt, depth, seq: (state.command?.seq ?? 0) + 1 } })),
}));

/** The deterministic prompt for escalating the SAME research to an explicit tier.
 *  Built from `{subject, depth}` so the re-run is unambiguous (the agent maps the
 *  named tier straight to `research(subject, depth=<tier>)`) — NOT a fuzzy phrase
 *  the model has to interpret. The tier word is load-bearing data, not prose. */
export function researchDepthPrompt(subject: string, depth: BriefDepth): string {
  return `research ${subject} at depth=${depth}`;
}

/** Non-reactive helper: push a prompt to the agent from anywhere (event handlers). */
export function sendToAgent(prompt: string): void {
  useAgentCommandStore.getState().send(prompt);
}

/** Escalate the SAME research subject to an explicit depth tier through the one
 *  send path (the chat's `handleSend`). Deterministic: the prompt names the exact
 *  tier, so the re-run is never ambiguous and never bypasses the §6.5 gate. */
export function escalateResearchDepth(subject: string, depth: BriefDepth): void {
  useAgentCommandStore.getState().send(researchDepthPrompt(subject, depth), depth);
}

/** Test helper: reset the agent-command store. */
export function resetAgentCommandStoreForTests(): void {
  useAgentCommandStore.setState({ command: null });
}
