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

import type { DockviewApi, SerializedDockview } from "dockview";

import { applyDefaultLayout } from "@/config/default-layout";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useModulesStore } from "@/store/modules";
import { AUTOSAVE_LAYOUT_NAME, useWorkspaceStore } from "@/store/workspace";
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
  try {
    return (await response.json()) as string[];
  } catch {
    throw new WorkspaceError("Could not parse the workspace list response (malformed JSON).");
  }
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
  let workspace: SerializedWorkspace;
  try {
    workspace = (await response.json()) as SerializedWorkspace;
  } catch {
    throw new WorkspaceError(`Could not parse workspace "${trimmed}" (malformed JSON).`);
  }
  deserializeWorkspace(workspace);
}

/**
 * Restore the auto-saved "last session" cockpit if one exists, else apply the
 * bundled default layout. Called once on launch from PanelHost; this is what
 * makes a customised cockpit survive a relaunch (Track C). Never throws — a
 * failed restore falls back to the default so the app always boots usable.
 * Returns true when a saved session was restored.
 */
export async function restoreLastSessionOrDefault(
  api: DockviewApi,
  enabledPanelIds: Set<string>,
): Promise<boolean> {
  try {
    const response = await fetch(await workspaceUrl(AUTOSAVE_LAYOUT_NAME));
    if (response.ok) {
      const workspace = (await response.json()) as SerializedWorkspace;
      deserializeWorkspace(workspace);
      // The reserved slot's name is internal — present the restored cockpit
      // under the neutral "default" name, not "__autosave__".
      useWorkspaceStore.getState().setName("default");
      return true;
    }
  } catch {
    // Fall through to the default layout below.
  }
  applyDefaultLayout(api, enabledPanelIds);
  return false;
}

/**
 * Persist the current cockpit to the reserved autosave slot. Best-effort: a
 * transient sidecar failure is swallowed (the next layout change retries) and
 * the active workspace name is left unchanged. No-op before the layout mounts.
 */
export async function autosaveLayout(): Promise<void> {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    return;
  }
  try {
    const payload: SerializedWorkspace = {
      name: AUTOSAVE_LAYOUT_NAME,
      layout: api.toJSON(),
      enabledModules: useModulesStore.getState().enabled,
      chartDrawings: useChartDrawingsStore.getState().snapshot(),
    };
    await fetch(await workspaceUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: AUTOSAVE_LAYOUT_NAME, workspace: payload }),
    });
  } catch {
    // Best-effort autosave; ignore transient failures.
  }
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
