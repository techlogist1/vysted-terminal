/**
 * Plugin-contributed agents → custom agents (FR-050 agent slice, US10 AS3).
 *
 * An agent-contributing marketplace plugin (e.g. `vysted-lenses`) declares
 * `AgentSpec`s via `getAgents()`. So those agents are genuinely RUNNABLE — not a
 * dead fixture — they are registered in the sidecar's custom-agent store on
 * enable (and removed on disable/remove). `agent_runtime.get_agent` resolves the
 * custom-agent store, so a registered plugin agent runs through the same loop as
 * a first-party persona, with the same §6.5-host-enforced tool gating. They then
 * appear in the agent surface's persona roster (via `useAgentsStore.customAgents`).
 */

import { CATALOG_BY_ID } from "@/lib/marketplace";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useAgentsStore } from "@/store/agents";

/** Custom-agent id for a plugin-contributed agent — `custom:`-prefixed, slug-safe. */
export function pluginAgentId(pluginId: string, agentId: string): string {
  const slug = `${pluginId}-${agentId}`.replace(/[^a-zA-Z0-9-]+/g, "-").replace(/-+/g, "-");
  return `custom:${slug}`;
}

/**
 * Register (or remove) an agent-plugin's agents in the sidecar custom-agent
 * store so they are invokable. No-op for non-agent plugins. Best-effort per
 * agent (a 409 on re-register is fine — idempotent); refreshes the roster after.
 */
export async function syncPluginAgents(pluginId: string, register: boolean): Promise<void> {
  const row = CATALOG_BY_ID[pluginId];
  if (!row) return;
  const instance = row.discovered.instance;
  if (!instance.capabilities.contributesAgents || !instance.getAgents) return;
  const agents = instance.getAgents();
  if (agents.length === 0) return;

  let base: string;
  try {
    base = await getSidecarBaseUrl();
  } catch {
    return; // outside the Tauri shell — nothing to register against
  }

  for (const agent of agents) {
    const id = pluginAgentId(pluginId, agent.id);
    try {
      if (register) {
        await fetch(new URL("/custom-agents", base).toString(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id,
            name: agent.name,
            philosophy: agent.philosophy,
            system_prompt: agent.systemPrompt,
            tools: agent.tools,
            default_provider: agent.defaultProvider,
            icon: agent.icon,
          }),
        });
      } else {
        await fetch(new URL(`/custom-agents/${encodeURIComponent(id)}`, base).toString(), {
          method: "DELETE",
        });
      }
    } catch {
      // Best-effort: a 409 (already registered) or transient error is non-fatal.
    }
  }
  await useAgentsStore.getState().refresh();
}
