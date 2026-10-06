/**
 * Notes persistence helpers.
 *
 * Each note is written atomically to disk as a `.md` file via the Rust
 * `write_text_atomic` command (SC-032: temp-file + rename, crash-safe).
 * The workspace blob carries a parallel mirror for cross-session restore;
 * this module handles the `.md` artifact.
 *
 * Falls back silently when `__TAURI_INTERNALS__` is absent (browser dev mode).
 */

import { invoke } from "@tauri-apps/api/core";

import { safeFilename } from "@/lib/safe-filename";

let appDataDirCache: string | null = null;

/**
 * Resolve the notes directory path (cached). The Rust core owns the app-data
 * dir (it passes `--data-dir` to the sidecar at boot), so we ask it directly
 * via the `get_app_data_dir` command — the authoritative source. The sidecar
 * `/health` does NOT expose `data_dir`, so it is only a best-effort legacy
 * fallback.
 */
async function resolveNotesDir(): Promise<string | null> {
  if (appDataDirCache !== null) return appDataDirCache;
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return null;
  }
  // The Rust core owns the data dir (it passes `--data-dir` to the sidecar), so
  // ask it directly. `/health` does NOT expose `data_dir` — legacy fallback only.
  try {
    const dir = await invoke<string>("get_app_data_dir");
    if (dir) {
      appDataDirCache = dir;
      return dir;
    }
  } catch {
    // Fall through to the legacy /health probe.
  }
  try {
    const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");
    const base = await getSidecarBaseUrl();
    const response = await fetch(`${base}/health`);
    if (!response.ok) return null;
    const health = (await response.json()) as { data_dir?: string };
    if (health.data_dir) {
      appDataDirCache = health.data_dir;
      return health.data_dir;
    }
  } catch {
    // Non-fatal — workspace-blob mirror is always written on save.
  }
  return null;
}

/**
 * Persist a note to disk as `{appData}/notes/<filename>.md` via the atomic
 * Rust command. Silently no-ops outside Tauri.
 */
export async function persistNoteMd(scope: string | undefined, markdown: string): Promise<void> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return;
  }
  try {
    const dir = await resolveNotesDir();
    if (!dir) return;

    const filename = scope ? `${safeFilename(scope.toUpperCase())}.md` : "general.md";
    const path = `${dir}/notes/${filename}`;
    await invoke("write_text_atomic", { path, contents: markdown });
  } catch {
    // Non-fatal — workspace blob is the primary durable store.
  }
}
