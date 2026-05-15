/**
 * Agents store — first-party agents (sidecar JSON configs) + Custom Agent
 * Builder records, unified for the chat sidebar's picker.
 *
 * Two slices, two wire shapes:
 *
 * - **First-party** — from ``GET /agents`` (Teammate A). The sidecar
 *   deliberately omits ``systemPrompt`` from this wire shape (agents are
 *   discovered from ``sidecar/agents/*.json`` at startup; their prompts
 *   live server-side). Records here are :type:`AgentSummary`.
 * - **Custom** — from ``GET /custom-agents`` (Teammate C / BLUEPRINT
 *   module 36). User-defined agents authored through the Custom Agent
 *   Builder UI. Records here are :type:`AgentSpec` (with ``systemPrompt``)
 *   so the builder's edit form can rehydrate from the store without a
 *   second fetch. Custom ids are always ``custom:``-prefixed —
 *   :func:`isCustomAgent` is the predicate.
 *
 * The chat sidebar's agent picker reads :func:`selectFirstPartyAgents` and
 * :func:`selectCustomAgents`, which both return ``readonly AgentSummary[]``
 * — the picker only needs ``{id, name, philosophy}``. For custom agents
 * the summary view is precomputed on every ``setCustomAgents`` so the
 * selector stays referentially stable (CLAUDE.md ``useSyncExternalStore``
 * gotcha — fresh arrays cause infinite render loops).
 *
 * The Custom Agent Builder panel reads ``state.customAgents`` directly to
 * get the full :type:`AgentSpec` records it edits.
 *
 * No localStorage / sessionStorage — both sources are sidecar-backed per
 * the CLAUDE.md sidecar-owned-persistence convention.
 */

import { create } from "zustand";

import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type { LLMProviderId } from "../../types/ai";
import type { AgentSpec } from "../../types/plugin";

// ---------------------------------------------------------------------------
// Custom-agent identity
// ---------------------------------------------------------------------------

/** Required prefix on every custom-agent id; mirrors the sidecar's enforcement. */
export const CUSTOM_AGENT_ID_PREFIX = "custom:";

/** Predicate: ``true`` if this agent was authored in the Custom Agent Builder. */
export function isCustomAgent(agent: { id: string }): boolean {
  return agent.id.startsWith(CUSTOM_AGENT_ID_PREFIX);
}

// ---------------------------------------------------------------------------
// Wire-shape mappers
// ---------------------------------------------------------------------------

/** Picker-facing summary; chat sidebar iterates this for both groups. */
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

/** Wire shape of ``GET /agents`` (Teammate A) — Pydantic snake_case. */
interface FirstPartyAgentWire {
  id: string;
  name: string;
  philosophy: string;
  tools: string[];
  default_provider: LLMProviderId;
  default_model?: string | null;
  icon?: string | null;
}

/** Wire shape of ``GET /custom-agents`` (Teammate C) — Pydantic snake_case. */
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

/** Map a first-party row to the picker's :type:`AgentSummary` shape. */
export function rowToSummary(row: FirstPartyAgentWire): AgentSummary {
  return {
    id: row.id,
    name: row.name,
    philosophy: row.philosophy,
    tools: row.tools,
    defaultProvider: row.default_provider,
    defaultModel: row.default_model ?? null,
    icon: row.icon ?? null,
    origin: "first-party",
  };
}

/** Map a custom-agent wire record to the locked :type:`AgentSpec` shape. */
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

/** Map a custom-agent :type:`AgentSpec` to the picker's :type:`AgentSummary`. */
function customSpecToSummary(spec: AgentSpec): AgentSummary {
  return {
    id: spec.id,
    name: spec.name,
    philosophy: spec.philosophy,
    tools: spec.tools,
    defaultProvider: spec.defaultProvider as LLMProviderId,
    defaultModel: null,
    icon: spec.icon ?? null,
    origin: "custom",
  };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

/** Status of an async fetch slice. */
export type AgentsLoadStatus = "idle" | "loading" | "ready" | "error";

interface AgentsState {
  /** First-party summaries from ``GET /agents``. */
  firstPartyAgents: AgentSummary[];
  /** Custom-builder records from ``GET /custom-agents`` (full :type:`AgentSpec`). */
  customAgents: AgentSpec[];
  /** Pre-computed picker view of customAgents — referentially stable per set. */
  customSummaries: AgentSummary[];

  firstPartyStatus: AgentsLoadStatus;
  firstPartyError: string | null;
  customStatus: AgentsLoadStatus;
  customError: string | null;

  /** Convenience for callers (e.g. A's chat sidebar) that just want a boolean. */
  loading: boolean;
  /** Mirrors firstPartyError so existing A consumers keep working unchanged. */
  error: string | null;

  /** Replace first-party agents (Teammate A's seed path / direct manipulation). */
  setFirstPartyAgents: (next: AgentSummary[]) => void;
  /** Replace custom agents (Teammate C's builder save path). */
  setCustomAgents: (next: AgentSpec[]) => void;

  /** Fetch the first-party list from the sidecar. */
  refreshFirstParty: () => Promise<void>;
  /** Fetch the custom list from the sidecar. */
  refreshCustom: () => Promise<void>;
  /** Convenience: refresh both in parallel. Chat sidebar (A) calls this on mount. */
  refresh: () => Promise<void>;
  /** Alias for :func:`refresh` — present so Teammate C's existing call sites compile. */
  refreshAll: () => Promise<void>;
}

export const useAgentsStore = create<AgentsState>((set, get) => ({
  firstPartyAgents: [],
  customAgents: [],
  customSummaries: [],
  firstPartyStatus: "idle",
  firstPartyError: null,
  customStatus: "idle",
  customError: null,
  loading: false,
  error: null,

  setFirstPartyAgents: (next) =>
    set({
      firstPartyAgents: next,
      firstPartyStatus: "ready",
      firstPartyError: null,
      error: null,
    }),

  setCustomAgents: (next) =>
    set({
      customAgents: next,
      customSummaries: next.map(customSpecToSummary),
      customStatus: "ready",
      customError: null,
    }),

  refreshFirstParty: async () => {
    set({ firstPartyStatus: "loading", firstPartyError: null });
    try {
      const rows = await sidecarGet<FirstPartyAgentWire[]>("/agents");
      const summaries = rows.map(rowToSummary);
      set({
        firstPartyAgents: summaries,
        firstPartyStatus: "ready",
        firstPartyError: null,
        error: null,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load first-party agents";
      set({ firstPartyStatus: "error", firstPartyError: message, error: message });
    }
  },

  refreshCustom: async () => {
    set({ customStatus: "loading", customError: null });
    try {
      const base = await getSidecarBaseUrl();
      const response = await fetch(new URL("/custom-agents", base).toString());
      if (!response.ok) {
        // Soft-fail: keep the slice empty so the picker still renders.
        set({ customAgents: [], customSummaries: [], customStatus: "ready", customError: null });
        return;
      }
      const wire = (await response.json()) as CustomAgentWire[];
      const specs = wire.map(fromCustomAgentWire);
      set({
        customAgents: specs,
        customSummaries: specs.map(customSpecToSummary),
        customStatus: "ready",
        customError: null,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load custom agents";
      set({ customStatus: "error", customError: message });
    }
  },

  refresh: async () => {
    set({ loading: true });
    const { refreshFirstParty, refreshCustom } = get();
    await Promise.all([refreshFirstParty(), refreshCustom()]);
    set({ loading: false });
  },

  refreshAll: async () => {
    await get().refresh();
  },
}));

// ---------------------------------------------------------------------------
// Selectors — referentially-stable views the chat picker subscribes to
// ---------------------------------------------------------------------------

/** Stable empty list — reused so an idle store does not mint fresh arrays. */
const EMPTY_AGENTS: readonly AgentSummary[] = Object.freeze([]);

/** Picker selector for first-party agents. */
export function selectFirstPartyAgents(state: AgentsState): readonly AgentSummary[] {
  return state.firstPartyAgents.length > 0 ? state.firstPartyAgents : EMPTY_AGENTS;
}

/** Picker selector for custom agents (summary view of the full :type:`AgentSpec` slice). */
export function selectCustomAgents(state: AgentsState): readonly AgentSummary[] {
  return state.customSummaries.length > 0 ? state.customSummaries : EMPTY_AGENTS;
}

/** Look one agent up by id, regardless of origin. */
export function selectAgentById(state: AgentsState, agentId: string): AgentSummary | null {
  return (
    state.firstPartyAgents.find((a) => a.id === agentId) ??
    state.customSummaries.find((a) => a.id === agentId) ??
    null
  );
}
