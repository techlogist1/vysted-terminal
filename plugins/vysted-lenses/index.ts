/**
 * Vysted Lenses — a first-party agent-collection marketplace plugin.
 *
 * The reference instance of the AGENT slice of the one extension model
 * (FR-050/US10): agents are install/enable/configure/remove marketplace plugins,
 * not a hardcoded path. This pack contributes the "Quant Tutor" lens — an
 * educational agent that explains what it reads rather than just answering.
 * Pre-installed (bundled + enabled by default) so first run is populated, yet
 * removable through the marketplace like any plugin (SC-013).
 *
 * Its `getAgents()` AgentSpecs are surfaced to the host via the plugin runtime's
 * `collectAgents()` projection and merged into the agent surface's persona
 * roster, so a plugin-contributed agent is genuinely runnable — its `tools` are
 * real catalog ids gated by the same §6.5 host enforcement as every agent.
 */

import type { AgentSpec, HealthStatus, PluginCapabilities, VystedPlugin } from "../../types/plugin";

const capabilities: PluginCapabilities = {
  contributesData: false,
  contributesPanels: false,
  contributesCommands: false,
  contributesAgents: true,
  contributesNodes: false,
  supportsControlPlane: false,
};

const agents: AgentSpec[] = [
  {
    id: "quant-tutor",
    name: "Quant Tutor",
    philosophy: "Teaches as it analyzes — explains every figure it fetches in plain language.",
    systemPrompt:
      "You are the Quant Tutor, an educational finance lens inside Vysted Terminal. Your job is to make the user smarter, not just to answer. Ground EVERY factual claim in a tool call — never invent a price, ratio, or rate. When you fetch a figure (price_data, fundamentals, macro_series, earnings_history, analyst_history), state the number AND briefly explain what it means and why it matters, as a patient teacher would. When the user gestures at the screen ('this', 'it', 'my chart'), call get_terminal_state first to resolve what they're looking at. Keep it concrete, calm, and jargon-light; define a term the first time you use it. You read the terminal and can stage changes for the user to review, but you never claim a change is done until they accept it.",
    tools: [
      "get_terminal_state",
      "get_portfolio",
      "price_data",
      "fundamentals",
      "macro_series",
      "earnings_history",
      "analyst_history",
    ],
    defaultProvider: "anthropic",
    icon: "graduation-cap",
  },
];

export const lensesPlugin: VystedPlugin = {
  pluginId: "vysted-lenses",
  pluginName: "Vysted Lenses (agent pack)",
  pluginType: "agent-collection",
  version: "1.0.0",
  capabilities,

  async initialize(): Promise<void> {
    // Stateless — agents are declarative; the host runs them through the
    // sidecar agent loop with the user's BYOK provider.
  },

  async shutdown(): Promise<void> {
    // Nothing to tear down.
  },

  async healthCheck(): Promise<HealthStatus> {
    return {
      status: "healthy",
      message: `${agents.length} agent lens available.`,
      checkedAt: Date.now(),
    };
  },

  getAgents(): AgentSpec[] {
    return agents.map((agent) => ({ ...agent, tools: [...agent.tools] }));
  },
};

export default lensesPlugin;
