/**
 * Typed bindings over the Rust core's bundled-engine commands
 * (`src-tauri/src/local_engine.rs`, R16 contract "Rust ↔ frontend: local engine").
 */

import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

export type EngineState = "stopped" | "starting" | "ready" | "crashed" | "failed";

export interface EngineStatus {
  state: EngineState;
  /** Set only when ready. */
  port: number | null;
  modelId: string | null;
  /** Crash restarts in the current window. */
  restarts: number;
  /** Plain-language reason when crashed/failed. */
  error: string | null;
  /** The engine's last stderr line. */
  detail: string | null;
}

export interface EngineStartArgs {
  modelPath: string;
  modelId: string;
  ctxSize?: number;
}

export const LOCAL_ENGINE_STATUS_EVENT = "local-engine://status";

export const STOPPED_ENGINE: EngineStatus = {
  state: "stopped",
  port: null,
  modelId: null,
  restarts: 0,
  error: null,
  detail: null,
};

export function startLocalEngine(args: EngineStartArgs): Promise<EngineStatus> {
  return invoke<EngineStatus>("local_engine_start", { ...args });
}

export function stopLocalEngine(): Promise<EngineStatus> {
  return invoke<EngineStatus>("local_engine_stop");
}

export function getLocalEngineStatus(): Promise<EngineStatus> {
  return invoke<EngineStatus>("local_engine_status");
}

export function onLocalEngineStatus(handler: (status: EngineStatus) => void): Promise<UnlistenFn> {
  return listen<EngineStatus>(LOCAL_ENGINE_STATUS_EVENT, (event) => handler(event.payload));
}
