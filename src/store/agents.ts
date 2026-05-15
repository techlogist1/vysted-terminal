/**
 * Agents store — union of first-party agents (sidecar JSON) and custom agents
 * (Custom Agent Builder).
 *
 * First-party agents come from ``GET /agents`` (Teammate A's sidecar router).
 * Custom user-defined agents come from ``GET /custom-agents`` (Teammate C
 * lands the endpoint; this store is forward-compatible — when C's endpoint
 * is unreachable, the custom slice stays empty rather than throwing).
 *
 * The chat sidebar's agent picker reads :func:`selectAgentGroups` so the
 * dropdown can render "First-party" vs "Custom" headers without duplicating
 * the grouping logic.
 */

import { create } from "zustand";

import { sidecarGet } from "@/lib/sidecar-client";
import type { LLMProviderId } from "../../types/ai";

/** Summary surfaced in the agent picker; mirrors ``AgentSummary`` Pydantic model. */
export interface AgentSummary {
  id: string;
  name: string;
  philosophy: string;
  tools: string[];
  defaultProvider: LLMProviderId;
  defaultModel?: string | null;
  icon?: string | null;
  /** ``"first-party"`` for shipped JSON configs, ``"custom"`` for builder-defined. */
  origin: "first-party" | "custom";
}

interface SidecarAgentRow {
  id: string;
  name: string;
  philosophy: string;
  tools: string[];
  default_provider: LLMProviderId;
  default_model?: string | null;
  icon?: string | null;
}

interface AgentsState {
  firstParty: AgentSummary[];
  custom: AgentSummary[];
  loading: boolean;
  error: string | null;
  /** Refresh both slices in parallel; custom failures are non-fatal. */
  refresh: () => Promise<void>;
}

/**
 * Map a sidecar agent row to the store's :class:`AgentSummary` shape.
 *
 * Exported for testability — both the first-party and custom routes share
 * the wire schema, so unit tests can build a row and verify the mapping
 * without spinning the store.
 */
export function rowToSummary(row: SidecarAgentRow, origin: AgentSummary["origin"]): AgentSummary {
  return {
    id: row.id,
    name: row.name,
    philosophy: row.philosophy,
    tools: row.tools,
    defaultProvider: row.default_provider,
    defaultModel: row.default_model ?? null,
    icon: row.icon ?? null,
    origin,
  };
}

export const useAgentsStore = create<AgentsState>((set) => ({
  firstParty: [],
  custom: [],
  loading: false,
  error: null,
  refresh: async () => {
    set({ loading: true, error: null });
    // First-party: hard failure surfaces as an error string; custom: soft fail.
    let firstParty: AgentSummary[] = [];
    let error: string | null = null;
    try {
      const rows = await sidecarGet<SidecarAgentRow[]>("/agents");
      firstParty = rows.map((row) => rowToSummary(row, "first-party"));
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to load first-party agents";
    }
    let custom: AgentSummary[] = [];
    try {
      const rows = await sidecarGet<SidecarAgentRow[]>("/custom-agents");
      custom = rows.map((row) => rowToSummary(row, "custom"));
    } catch {
      // Teammate C's endpoint may not be wired yet; leave custom empty.
    }
    set({ firstParty, custom, loading: false, error });
  },
}));

const EMPTY_AGENT_LIST: readonly AgentSummary[] = Object.freeze([]);

/**
 * Per-slice selectors for the agent picker — Zustand v5 enforces
 * referentially stable selector returns, so two separate selectors are
 * cheaper than computing a fresh `{firstParty, custom}` object on each
 * render (which causes the `useSyncExternalStore` infinite loop in CLAUDE.md
 * gotchas).
 */
export function selectFirstPartyAgents(state: AgentsState): readonly AgentSummary[] {
  return state.firstParty.length > 0 ? state.firstParty : EMPTY_AGENT_LIST;
}

export function selectCustomAgents(state: AgentsState): readonly AgentSummary[] {
  return state.custom.length > 0 ? state.custom : EMPTY_AGENT_LIST;
}

/** Look one agent up by id, regardless of origin. */
export function selectAgentById(state: AgentsState, agentId: string): AgentSummary | null {
  return (
    state.firstParty.find((a) => a.id === agentId) ??
    state.custom.find((a) => a.id === agentId) ??
    null
  );
}
