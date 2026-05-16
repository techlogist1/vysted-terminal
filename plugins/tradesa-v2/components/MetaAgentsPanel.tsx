import { PlaceholderPanel } from "./_PlaceholderPanel";

export function MetaAgentsPanel() {
  return (
    <PlaceholderPanel
      panelTitle="Self-Tuning · Discovery · Reflection"
      panelDescription="Three tabs over the bot's meta-agent output: tuning_proposals (pending operator approval via Telegram), discovery_hypotheses (re-enabled at closed_trades >= 100), and reflection_notes (one per closed trade)."
    />
  );
}

export default MetaAgentsPanel;
