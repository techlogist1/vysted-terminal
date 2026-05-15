/**
 * Workspace serialization — `.vysted-workspace` save/load.
 *
 * A workspace captures two things: the dockview panel layout and the modules
 * `enabled` map. Serialising both means reloading a workspace restores not just
 * which panels are open and where, but which modules are active. The sidecar
 * owns the files (`/workspace` endpoints); this module is the frontend half —
 * it builds the payload from the live stores and applies a loaded payload back
 * onto them.
 *
 * The shape is deliberately open: `SerializedWorkspace` carries the two fields
 * the platform needs plus an index signature so a future phase can add keys
 * without a sidecar change (the sidecar stores the body opaquely).
 */

import type { SerializedDockview } from "dockview";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";
import type { WorkspaceDrawings } from "../../types/drawings";

/** The serialised form of a workspace, persisted as a `.vysted-workspace` file. */
export interface SerializedWorkspace {
  /** Workspace name — also the file name on the sidecar. */
  name: string;
  /** The dockview layout, as produced by `DockviewApi.toJSON()`. */
  layout: SerializedDockview;
  /** The modules `enabled` map at save time. */
  enabledModules: Record<string, boolean>;
  /**
   * Per-chart-panel drawings collection (Phase 2). Optional for backward
   * compatibility with workspaces saved before drawings shipped.
   */
  chartDrawings?: WorkspaceDrawings;
  /** Open to future-phase additions; the sidecar stores the body opaquely. */
  [key: string]: unknown;
}

/** Thrown when a workspace operation cannot complete. */
export class WorkspaceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkspaceError";
  }
}

/**
 * Capture the current workspace from the live stores: the dockview layout plus
 * the modules `enabled` map plus per-chart-panel drawings. Throws if the
 * dockview layout has not mounted yet.
 */
export function serializeWorkspace(name: string): SerializedWorkspace {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  return {
    name,
    layout: api.toJSON(),
    enabledModules: useModulesStore.getState().enabled,
    chartDrawings: useChartDrawingsStore.getState().snapshot(),
  };
}

/**
 * Apply a loaded workspace back onto the live stores: restore the modules
 * `enabled` map, then the dockview layout, then the active workspace name.
 * Throws if the dockview layout has not mounted yet. Drawings (Phase 2) are
 * restored last and only when the loaded workspace carries them so older
 * workspaces still apply cleanly.
 */
export function deserializeWorkspace(workspace: SerializedWorkspace): void {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  // Restore the enabled map first so the panel components a layout references
  // resolve against the same module set that was active when it was saved.
  useModulesStore.getState().setEnabledMap(workspace.enabledModules);
  api.fromJSON(workspace.layout);
  useWorkspaceStore.getState().setName(workspace.name);
  if (workspace.chartDrawings) {
    useChartDrawingsStore.getState().replaceAll(workspace.chartDrawings);
  } else {
    useChartDrawingsStore.getState().replaceAll({ byPanel: {} });
  }
}

/** Build the sidecar `/workspace` URL, optionally for a single named workspace. */
async function workspaceUrl(name?: string): Promise<string> {
  const base = await getSidecarBaseUrl();
  const path = name === undefined ? "/workspace" : `/workspace/${encodeURIComponent(name)}`;
  return new URL(path, base).toString();
}

/** List the names of every workspace saved on the sidecar. */
export async function listWorkspaces(): Promise<string[]> {
  const response = await fetch(await workspaceUrl());
  if (!response.ok) {
    throw new WorkspaceError(`Could not list workspaces (HTTP ${response.status}).`);
  }
  return (await response.json()) as string[];
}

/**
 * Serialise the current workspace under `name` and persist it on the sidecar,
 * overwriting any existing workspace with the same name.
 */
export async function saveWorkspace(name: string): Promise<void> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new WorkspaceError("A workspace name is required.");
  }
  const workspace = serializeWorkspace(trimmed);
  const response = await fetch(await workspaceUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: trimmed, workspace }),
  });
  if (!response.ok) {
    throw new WorkspaceError(`Could not save workspace "${trimmed}" (HTTP ${response.status}).`);
  }
}

/** Load a saved workspace from the sidecar and apply it to the live stores. */
export async function loadWorkspace(name: string): Promise<void> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new WorkspaceError("A workspace name is required.");
  }
  const response = await fetch(await workspaceUrl(trimmed));
  if (!response.ok) {
    throw new WorkspaceError(`Could not load workspace "${trimmed}" (HTTP ${response.status}).`);
  }
  const workspace = (await response.json()) as SerializedWorkspace;
  deserializeWorkspace(workspace);
}

/** Delete a saved workspace from the sidecar. */
export async function deleteWorkspace(name: string): Promise<void> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new WorkspaceError("A workspace name is required.");
  }
  const response = await fetch(await workspaceUrl(trimmed), { method: "DELETE" });
  if (!response.ok) {
    throw new WorkspaceError(`Could not delete workspace "${trimmed}" (HTTP ${response.status}).`);
  }
}
