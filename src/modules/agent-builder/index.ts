import type { VystedModule } from "@/lib/module-registry";

import { AgentBuilderPanel } from "./AgentBuilderPanel";

/**
 * Agent Builder module — BLUEPRINT Module 36 (Custom Agent Builder).
 *
 * Surfaces the Custom Agent Builder panel: a form for defining a user
 * authored AI agent (id, name, philosophy, system prompt, tool allow-list,
 * default provider/model) plus a list of existing custom agents with
 * one-click edit/delete. Storage is sidecar-backed (SQLite via
 * `services.agents_store`); the chat sidebar's agent picker (Teammate A)
 * unions the result of `GET /agents` (first-party) with `GET /custom-agents`
 * (this module's output) through `useAgentsStore`.
 *
 * Custom-agent ids are always prefixed `custom:` — separation from the 12
 * first-party agent ids is structural, not a convention the UI tries to
 * enforce after the fact.
 *
 * Module 36 is explicitly NOT counted toward the 12-agent target (per the
 * Phase-3 plan brief). It is a builder, not an agent.
 */
export const agentBuilderModule: VystedModule = {
  id: "agent-builder",
  title: "Agent Builder",
  panels: [
    {
      id: "agent-builder",
      title: "Agent Builder",
      icon: "user-plus",
      component: "agent-builder-panel",
      singleton: true,
      defaultSize: { w: 6, h: 6 },
    },
  ],
  commands: [
    {
      id: "agent-builder.open",
      trigger: "agent-builder",
      title: "Open Agent Builder",
      description: "Create and edit custom AI agents",
      icon: "user-plus",
      opensPanel: "agent-builder",
    },
  ],
  panelComponents: {
    "agent-builder-panel": AgentBuilderPanel,
  },
};
