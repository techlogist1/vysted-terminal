import type { VystedModule } from "@/lib/module-registry";

/**
 * Chat module — the agent surface.
 *
 * FR-001: the agent is the shell's dominant, resizable LEFT COLUMN (mounted by
 * `AgentDock` → `ChatSidebar`), NOT a dockview panel. It is therefore the one
 * module that contributes NO dockview panel/command/component: registering it as
 * a panel produced a second, identical agent surface ("AI Assistant") alongside
 * the shell column. Removing the registration means the agent surface is ONE
 * coherent thing, and any stale persisted "chat-sidebar" panel resolves to an
 * unknown component on restore → the boot path cleanly falls back to the default
 * cockpit (see `restoreLastSessionOrDefault`). The command palette's "Ask AI"
 * row reveals this dock and routes the query via the agent-command bus.
 */
export const chatModule: VystedModule = {
  id: "chat",
  title: "AI Assistant",
  panels: [],
  commands: [],
  panelComponents: {},
};
