import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";
import type { CommandSpec } from "../../types/plugin";

/**
 * Execute a cmd+K command: open its panel (`opensPanel`), or run its
 * control-plane handler (`commandId`). Mirrors the two ways the plugin contract
 * lets a `CommandSpec` act.
 */
export function executeCommand(command: CommandSpec): void {
  if (command.opensPanel) {
    useWorkspaceStore.getState().openPanel(command.opensPanel);
    return;
  }
  if (command.commandId) {
    const handler = useModulesStore.getState().commandHandler(command.commandId);
    handler?.();
  }
}
