import { PlaceholderPanel } from "./_PlaceholderPanel";

export function SettingsPanel() {
  return (
    <PlaceholderPanel
      panelTitle="Settings & Drift"
      panelDescription="Live bot_settings snapshot (operator-tunable config the bot hot-reloads every 55s) plus drift detection vs the previous snapshot the wrapper saw. Read-only display."
    />
  );
}

export default SettingsPanel;
