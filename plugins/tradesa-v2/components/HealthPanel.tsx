import { PlaceholderPanel } from "./_PlaceholderPanel";

export function HealthPanel() {
  return (
    <PlaceholderPanel
      panelTitle="Heartbeat & Health"
      panelDescription="Latest bot_health row (FD count, thread count, uptime, status) and recent kill_switch_events. Bot kill-switch control is on the Tradesa V2 side — Vysted observes only."
    />
  );
}

export default HealthPanel;
