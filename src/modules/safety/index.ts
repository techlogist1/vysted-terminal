import type { VystedModule } from "@/lib/module-registry";

import { AuditLogViewer } from "./AuditLogViewer";

/**
 * Safety module — surfaces the audit log viewer as a dockable panel.
 *
 * The other safety UI surfaces (OrderConfirmationDialog, DisclaimerFlow) mount
 * at the app shell level rather than inside a panel — they need to be visible
 * regardless of layout state. (The kill-switch toolbar was removed from the UI
 * in the agent-native craft pass — read-only app, nothing to halt — while the
 * §6.5 mechanism in `kill_switch.rs` + the store slice stay intact and dormant.)
 */
export const safetyModule: VystedModule = {
  id: "safety",
  title: "Safety",
  panels: [
    {
      id: "audit-log",
      title: "Audit Log",
      icon: "shield",
      component: "audit-log-viewer",
      singleton: true,
      defaultSize: { w: 8, h: 6 },
    },
  ],
  commands: [
    {
      id: "safety.open-audit-log",
      trigger: "audit log",
      title: "Open Audit Log",
      description: "View the append-only order audit log",
      icon: "shield",
      opensPanel: "audit-log",
    },
  ],
  panelComponents: {
    "audit-log-viewer": AuditLogViewer,
  },
};

export { OrderConfirmationDialog } from "./OrderConfirmationDialog";
export { BrokerFirstConnectDialog, DisclaimerFlow, FirstLaunchTosDialog } from "./DisclaimerFlow";
export { AuditLogViewer } from "./AuditLogViewer";
