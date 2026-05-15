import type { VystedModule } from "@/lib/module-registry";

import { ChatSidebar } from "./ChatSidebar";

/**
 * Chat sidebar module — streaming AI assistant with agent picker, slash
 * commands, and a panel-context badge.
 *
 * Phase 3, Teammate A. Slots into the first-launch layout per
 * BLUEPRINT §5.1 on the right side (~25% width). Custom Agent Builder
 * agents (Teammate C) appear in the picker once their endpoint is wired.
 */
export const chatModule: VystedModule = {
  id: "chat",
  title: "AI Assistant",
  panels: [
    {
      id: "chat",
      title: "AI Assistant",
      icon: "sparkles",
      component: "chat-sidebar",
      singleton: true,
      defaultSize: { w: 3, h: 12 },
    },
  ],
  commands: [
    {
      id: "chat.open",
      trigger: "ask",
      title: "Open AI Assistant",
      description: "Streaming chat with first-party agents and BYOK providers",
      icon: "sparkles",
      opensPanel: "chat",
    },
  ],
  panelComponents: {
    "chat-sidebar": ChatSidebar,
  },
};
