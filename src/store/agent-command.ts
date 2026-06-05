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

interface AgentCommandState {
  /** Most recent "send this prompt to the agent" command from a non-chat module.
   *  `seq` bumps on every issue so an identical prompt still re-triggers the
   *  subscriber (e.g. clicking "Go deeper" twice). `null` until first issued. */
  command: { prompt: string; seq: number } | null;
  /** Push a prompt onto the channel for the chat sidebar to send. */
  send: (prompt: string) => void;
}

export const useAgentCommandStore = create<AgentCommandState>((set) => ({
  command: null,
  send: (prompt) => set((state) => ({ command: { prompt, seq: (state.command?.seq ?? 0) + 1 } })),
}));

/** Non-reactive helper: push a prompt to the agent from anywhere (event handlers). */
export function sendToAgent(prompt: string): void {
  useAgentCommandStore.getState().send(prompt);
}

/** Test helper: reset the agent-command store. */
export function resetAgentCommandStoreForTests(): void {
  useAgentCommandStore.setState({ command: null });
}
