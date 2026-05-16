import type { VystedModule } from "@/lib/module-registry";

import { NodeEditorPanel } from "./NodeEditorPanel";

/**
 * Node Editor module — Phase-4 visual workflow surface.
 *
 * Surfaces the Node Editor panel: a react-flow canvas with a left
 * palette of node types (10 built-ins from
 * `sidecar/services/workflow_nodes/builtin.py` + plugin-contributed
 * `NodeSpec`s via the locked `VystedPlugin.contributesNodes` capability),
 * a right properties panel for the selected node, and a run overlay
 * fed by the `POST /workflow/run` SSE stream.
 *
 * Workflows persist to the sidecar (`POST /workflow/save`,
 * `GET /workflow/saved`) — no localStorage per the CLAUDE.md
 * sidecar-owned-persistence convention.
 */
export const nodeEditorModule: VystedModule = {
  id: "node-editor",
  title: "Node Editor",
  panels: [
    {
      id: "node-editor",
      title: "Node Editor",
      icon: "share-2",
      component: "node-editor-panel",
      singleton: true,
      defaultSize: { w: 10, h: 8 },
    },
  ],
  commands: [
    {
      id: "node-editor.open",
      trigger: "node-editor",
      title: "Open Node Editor",
      description: "Compose workflows visually",
      icon: "share-2",
      opensPanel: "node-editor",
    },
  ],
  panelComponents: {
    "node-editor-panel": NodeEditorPanel,
  },
};
