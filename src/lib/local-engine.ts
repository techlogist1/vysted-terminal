/**
 * Typed bindings over the Rust core's bundled-engine commands
 * (`src-tauri/src/local_engine.rs`, R16 contract "Rust ↔ frontend: local engine").
 */

import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import type { LocalModelTier } from "../../types/data";

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

/**
 * The engine's `-c` by RAM tier. 16k is the floor a copilot turn fits in (the
 * Rust default; a round of 5 parallel large tool results can still overflow
 * it); a larger context admits more tools and longer tool results. Measured
 * engine peak RSS, granite-4.2-3b with q8_0 KV on Metal: 2.95 GiB at 16k,
 * 3.3 at 24k, 5.3 at 32k, 6.6 at 64k.
 */
export const CTX_SIZE_BY_TIER: Record<LocalModelTier, number> = {
  "under-8gb": 16384,
  "8gb": 24576,
  "16gb": 32768,
  "32gb": 65536,
};

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
