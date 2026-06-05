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

let appDataDirCache: string | null = null;

/**
 * Resolve the notes directory path. We call `get_sidecar_port` once at
 * startup which also boots the sidecar, so the app-data dir path can be
 * inferred by the frontend from a convention: we store it in a module-level
 * cache on first successful call.
 *
 * Implementation: the Tauri `path` plugin exposes `appDataDir()` but is not
 * installed in this app. Instead the sidecar is passed `--data-dir` at boot,
 * which means the app-data dir is only known to Rust at runtime.
 *
 * To avoid adding the `tauri-plugin-path` dependency, we use the workaround
 * of calling a thin Rust command `get_app_data_dir` — but that would require
 * a new Rust command. Instead, we store the dir path the first time a note
 * is persisted by calling `write_text_atomic` with a sentinel read-back.
 *
 * Simpler approach: use the sidecar `/workspace` base URL to resolve it.
 * The sidecar knows its `--data-dir` and exposes it via `/health`.
 * We call `GET /health` and extract `data_dir`.
 */
async function resolveNotesDir(): Promise<string | null> {
  if (appDataDirCache !== null) return appDataDirCache;
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return null;
  }
  try {
    // Import lazily to avoid SSR issues.
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

    const filename = scope ? `${scope.toUpperCase().replace(/[/\\]/g, "_")}.md` : "general.md";
    const path = `${dir}/notes/${filename}`;
    await invoke("write_text_atomic", { path, contents: markdown });
  } catch {
    // Non-fatal — workspace blob is the primary durable store.
  }
}

/**
 * Write a note to a user-specified path. Used for `.md` export (sharing).
 * Falls back to `{appData}/notes/exports/` if the path resolver cannot
 * produce a user-facing save dialog (no `tauri-plugin-dialog` installed).
 */
export async function exportNoteMd(
  markdown: string,
  suggestedFilename: string,
): Promise<string | null> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return null;
  }
  try {
    const dir = await resolveNotesDir();
    const exportDir = dir ? `${dir}/notes/exports` : null;
    if (!exportDir) return null;

    const path = `${exportDir}/${suggestedFilename}`;
    await invoke("write_text_atomic", { path, contents: markdown });
    return path;
  } catch {
    return null;
  }
}
