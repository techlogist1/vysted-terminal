/**
 * Agents store — first-party agent registry + Custom Agent Builder records.
 *
 * Phase 3 ships two sources of `AgentSpec` records:
 *
 * 1. **First-party** — 11 BLUEPRINT §3.4 named agents (Buffett, Graham, Lynch,
 *    Munger, Marks, Klarman, Dalio, Druckenmiller, Soros, AI Researcher, AI
 *    Portfolio Advisor) plus AI Strategy Critic, exposed by Teammate A's
 *    `GET /agents` sidecar router (config discovered from
 *    `sidecar/agents/*.json`).
 * 2. **Custom** — user-defined agents from the Custom Agent Builder (Module 36,
 *    Teammate C), exposed by `GET /custom-agents`. Custom-agent ids always
 *    start with `custom:` so they cannot collide with first-party ids and so
 *    the chat sidebar's picker can group them separately.
 *
 * This store is the single source of truth the chat sidebar's agent picker
 * reads. `agents` (the union) is what the picker iterates; `firstPartyAgents`
 * and `customAgents` stay separate so the picker can render a "First-party"
 * section + a "Custom" section without re-filtering on every render.
 *
 * No localStorage — both sources are sidecar-backed, per the CLAUDE.md
 * sidecar-owned-persistence convention.
 */

import { create } from "zustand";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";

import type { AgentSpec } from "../../types/plugin";

/** Required prefix on custom-agent ids — mirrors the sidecar's enforcement. */
export const CUSTOM_AGENT_ID_PREFIX = "custom:";

/** Predicate: `true` if this agent was authored in the Custom Agent Builder. */
export function isCustomAgent(agent: AgentSpec): boolean {
  return agent.id.startsWith(CUSTOM_AGENT_ID_PREFIX);
}

/**
 * Wire shape returned by ``GET /custom-agents`` — Pydantic emits snake_case
 * keys, but `AgentSpec` (the host contract) is camelCase. This local type
 * captures the wire shape; `fromCustomAgentWire` maps it to `AgentSpec`.
 */
interface CustomAgentWire {
  id: string;
  name: string;
  philosophy: string;
  system_prompt: string;
  tools: string[];
  default_provider: string;
  default_model?: string | null;
  icon?: string | null;
  created_at: number;
  updated_at: number;
}

/** Map a custom-agent wire record to the locked `AgentSpec` shape. */
export function fromCustomAgentWire(record: CustomAgentWire): AgentSpec {
  return {
    id: record.id,
    name: record.name,
    philosophy: record.philosophy,
    systemPrompt: record.system_prompt,
    tools: [...record.tools],
    defaultProvider: record.default_provider,
    icon: record.icon ?? undefined,
  };
}

/** Status of an async fetch slice — common to first-party and custom. */
export type AgentsLoadStatus = "idle" | "loading" | "ready" | "error";

interface AgentsState {
  /** First-party agents from `GET /agents` (sidecar config-discovered). */
  firstPartyAgents: AgentSpec[];
  /** Custom-Builder agents from `GET /custom-agents`. */
  customAgents: AgentSpec[];
  /** Convenience union: first-party first, then custom. */
  agents: AgentSpec[];

  firstPartyStatus: AgentsLoadStatus;
  firstPartyError: string | null;
  customStatus: AgentsLoadStatus;
  customError: string | null;

  /** Replace first-party agents (used by `refreshFirstParty` and Teammate A). */
  setFirstPartyAgents: (next: AgentSpec[]) => void;
  /** Replace custom agents (used by `refreshCustom` and the Builder UI). */
  setCustomAgents: (next: AgentSpec[]) => void;

  /** Fetch the first-party list from the sidecar. */
  refreshFirstParty: () => Promise<void>;
  /** Fetch the custom list from the sidecar. */
  refreshCustom: () => Promise<void>;
  /** Convenience: refresh both in parallel. */
  refreshAll: () => Promise<void>;
}

/** Build the flat union: first-party first, then custom (alphabetical inside each group). */
function buildUnion(firstParty: AgentSpec[], custom: AgentSpec[]): AgentSpec[] {
  return [...firstParty, ...custom];
}

/**
 * The agents store. Two sources, one union — the chat sidebar picker reads
 * `agents` for iteration order and uses `isCustomAgent` to group the two
 * sections visually.
 */
export const useAgentsStore = create<AgentsState>((set) => ({
  firstPartyAgents: [],
  customAgents: [],
  agents: [],
  firstPartyStatus: "idle",
  firstPartyError: null,
  customStatus: "idle",
  customError: null,

  setFirstPartyAgents: (next) =>
    set((state) => ({
      firstPartyAgents: next,
      agents: buildUnion(next, state.customAgents),
      firstPartyStatus: "ready",
      firstPartyError: null,
    })),
  setCustomAgents: (next) =>
    set((state) => ({
      customAgents: next,
      agents: buildUnion(state.firstPartyAgents, next),
      customStatus: "ready",
      customError: null,
    })),

  refreshFirstParty: async () => {
    set({ firstPartyStatus: "loading", firstPartyError: null });
    try {
      const base = await getSidecarBaseUrl();
      const response = await fetch(new URL("/agents", base).toString());
      if (!response.ok) {
        throw new Error(`/agents returned ${response.status}`);
      }
      const data = (await response.json()) as AgentSpec[];
      set((state) => ({
        firstPartyAgents: data,
        agents: buildUnion(data, state.customAgents),
        firstPartyStatus: "ready",
        firstPartyError: null,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to load agents";
      set({ firstPartyStatus: "error", firstPartyError: message });
    }
  },

  refreshCustom: async () => {
    set({ customStatus: "loading", customError: null });
    try {
      const base = await getSidecarBaseUrl();
      const response = await fetch(new URL("/custom-agents", base).toString());
      if (!response.ok) {
        throw new Error(`/custom-agents returned ${response.status}`);
      }
      const wire = (await response.json()) as CustomAgentWire[];
      const data = wire.map(fromCustomAgentWire);
      set((state) => ({
        customAgents: data,
        agents: buildUnion(state.firstPartyAgents, data),
        customStatus: "ready",
        customError: null,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to load custom agents";
      set({ customStatus: "error", customError: message });
    }
  },

  refreshAll: async () => {
    // Run both in parallel — neither depends on the other and the union is
    // re-computed inside each `set` call from the latest slice values.
    const { refreshFirstParty, refreshCustom } = useAgentsStore.getState();
    await Promise.all([refreshFirstParty(), refreshCustom()]);
  },
}));

/**
 * Stable empty agents array — re-used so a selector returning `agents` on an
 * idle store does not mint a fresh array on every render. Matches the
 * Phase-2 chart-sync frozen-empty-ref pattern from the CLAUDE.md gotchas.
 */
export const EMPTY_AGENTS: readonly AgentSpec[] = Object.freeze([]);
