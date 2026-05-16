import type { VystedModule } from "@/lib/module-registry";

import { BrokerConnectPanel } from "./BrokerConnectPanel";
import { BrokerOrderEntry } from "./BrokerOrderEntry";

/**
 * Broker-connect module — Phase 5 panels.
 *
 * Two panels: the connection manager (list, status/mode badges, connect flow)
 * and the manual order-entry surface (form → propose → confirmation dialog).
 */
export const brokerConnectModule: VystedModule = {
  id: "broker-connect",
  title: "Broker Connect",
  panels: [
    {
      id: "broker-connect",
      title: "Connections",
      icon: "plug",
      component: "broker-connect-panel",
      singleton: true,
      defaultSize: { w: 5, h: 6 },
    },
    {
      id: "broker-order-entry",
      title: "Order Entry",
      icon: "send",
      component: "broker-order-entry",
      singleton: true,
      defaultSize: { w: 4, h: 5 },
    },
  ],
  commands: [
    {
      id: "broker-connect.open-connections",
      trigger: "broker connections",
      title: "Open Broker Connections",
      description: "Manage broker connections, modes, and read-only flags",
      icon: "plug",
      opensPanel: "broker-connect",
    },
    {
      id: "broker-connect.open-order-entry",
      trigger: "order entry",
      title: "Open Order Entry",
      description: "Manual order proposal surface (routes through confirmation)",
      icon: "send",
      opensPanel: "broker-order-entry",
    },
  ],
  panelComponents: {
    "broker-connect-panel": BrokerConnectPanel,
    "broker-order-entry": BrokerOrderEntry,
  },
};

export { BrokerConnectPanel } from "./BrokerConnectPanel";
export { BrokerOrderEntry } from "./BrokerOrderEntry";
