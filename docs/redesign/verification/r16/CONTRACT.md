# R16 wave contract (lead-owned; writers code to this, not around it)

Branch `005-r16-easy-install`. Every writer works in its own worktree and branch, first runs
`git reset --hard <base sha given in the brief>`, commits by path, pushes its branch after each
deliverable. Never edits another writer's owned files; if a shared file needs a hunk outside your
ownership, put the exact hunk in your final report instead.

## Shared names (fixed)

| Thing | Name |
| --- | --- |
| Bundled engine binary (externalBin) | `binaries/llama-server` → `src-tauri/binaries/llama-server-<triple>[.exe]` |
| Engine shared libs staging dir | `src-tauri/llama-libs/<triple>/` (git-ignored) |
| Pinned llama.cpp build | `b11429` (= release `v0.6.0`), assets verified by the GitHub asset `digest` sha256 |
| Asset per triple | `aarch64-apple-darwin` → `llama-b11429-bin-macos-arm64.tar.gz`; `x86_64-pc-windows-msvc` → `llama-b11429-bin-win-vulkan-x64.zip`; `x86_64-unknown-linux-gnu` → `llama-b11429-bin-ubuntu-x64.tar.gz` |
| LLM provider id for the bundled engine | `local` (label "On this computer") |
| Models dir | `<app-data-dir>/models/` (`<file>.gguf`, in-flight `<file>.gguf.part` + `<file>.gguf.part.json`) |
| Profile isolation env | existing `VYSTED_DATA_DIR`; when set, the keychain service becomes `vysted-terminal.profile.<first 12 hex of sha256(abs data dir)>` |
| Updater test endpoint env | `VYSTED_UPDATER_ENDPOINT` (only honoured when it is an `http://127.0.0.1:` or `https://` URL; signature check unchanged) |

## Rust ↔ frontend: local engine (writer: engine lifecycle)

Tauri commands (all `async`, return `Result<T, String>`):

- `local_engine_start({ modelPath: string, modelId: string, ctxSize?: number })` → `EngineStatus`. Rejects a path outside `<app-data-dir>/models/` or an Ollama blob path the sidecar returned; picks a free loopback port; spawns via `app.shell().sidecar("llama-server")` with `--host 127.0.0.1 --port <p> -m <path> --jinja -c <ctx> -ngl 999 --no-webui` (drop flags the pinned build rejects); waits for `GET /health` 200 (model load) up to 180 s. Starting while running a different model stops the old one first.
- `local_engine_stop()` → `EngineStatus`.
- `local_engine_status()` → `EngineStatus`.
- Event `local-engine://status` with the same `EngineStatus` on every transition.

```ts
type EngineState = "stopped" | "starting" | "ready" | "crashed" | "failed";
interface EngineStatus {
  state: EngineState;
  port: number | null;        // set only when ready
  modelId: string | null;
  restarts: number;            // crash restarts in the current window
  error: string | null;        // plain-language reason when crashed/failed (last stderr line kept in `detail`)
  detail: string | null;
}
```

Crash policy: an unexpected exit while `ready` → `crashed`, auto-restart with backoff 1 s / 4 s / 10 s; a 4th crash within 10 min → `failed` (no more restarts until the user starts it again). A start that never reaches health → `failed` with the reason. App exit kills the engine tree (same teardown discipline as the other sidecars).

## Frontend ↔ Python sidecar: local models (writer: model manager)

Router prefix `/local-models` (GET/PUT/POST/DELETE; no trading verbs in any name):

- `GET /local-models/hardware` → `{ os, arch, totalRamBytes, availableRamBytes, gpu: { name, vramBytes | null, unifiedMemory: bool } | null, freeDiskBytes, modelsDir }`
- `GET /local-models/catalog` → `{ models: CatalogModel[], recommendedId: string | null, tier: "8gb" | "16gb" | "32gb" | "under-8gb", reason: string }`
- `GET /local-models/installed` → `{ models: InstalledModel[], ollama: { running: bool, models: string[] } }`
- `POST /local-models/{id}/download` → `DownloadState` (idempotent; resumes a `.part` if present; 409 if disk space is short, body says how much is needed and how much is free)
- `POST /local-models/{id}/cancel` → `DownloadState` (keeps the `.part` for resume unless `?discard=true`)
- `GET /local-models/downloads` → `{ downloads: DownloadState[] }`
- `DELETE /local-models/{id}` → 204 (refuses with 409 if it is the engine's active model; the frontend stops the engine first)
- `PUT /local-models/engine` body `{ port: number | null, modelId: string | null }` → `{ baseUrl | null, modelId | null }`; port must be 1–65535, base URL is always built as `http://127.0.0.1:<port>/v1` (never taken from the body). Provider `local` reads this; when null, `local` reports `not_configured` with reason "The on-computer model isn't running".

```ts
interface CatalogModel {
  id: string; name: string; family: string; params: string; quant: string;
  sizeBytes: number; diskNeededBytes: number; minRamBytes: number;
  licence: { id: string; name: string; url: string };   // shown before download
  purpose: string;                                      // one plain sentence
  url: string; sha256: string;                          // pinned to a commit-addressed URL
  fits: "good" | "tight" | "too-big";                   // for this machine
}
interface InstalledModel { id: string; name: string; path: string; sizeBytes: number; verified: boolean; active: boolean }
interface DownloadState {
  id: string; state: "queued" | "downloading" | "verifying" | "done" | "paused" | "failed" | "cancelled";
  receivedBytes: number; totalBytes: number; bytesPerSec: number | null;
  error: string | null;        // plain language: "No internet connection", "Not enough disk space (needs 5.1 GB, 2.0 GB free)", "Download was interrupted — resume to continue"
  retryable: boolean;
}
```

Integrity: HTTP Range resume; sha256 over the whole file before the atomic rename; a mismatch deletes the file and fails with "The download was corrupted — try again"; transient network errors auto-retry with backoff (3 tries) then `paused` + `retryable`; `.part.json` records url, sha256, total so a relaunch shows `paused` at the right percentage; disk check before start and every 256 MB.

## Updater (writer: updater)

Tauri commands `update_check()` → `{ available: bool, version?, notes?, date? }`, `update_download_and_install()` with event `updater://progress { downloaded, total }`, and the existing process relaunch. Frontend `UpdatePrompt`: checks 15 s after boot and every 6 h; shows version + notes; "Restart to update"; if any model download is `downloading`/`verifying`, the button becomes "Update after the download finishes" and installs when it ends (downloads resume after relaunch anyway).

## Release artifacts (writer: release pipeline)

Stable asset names on every release (in addition to Tauri's versioned names and the updater files):
`Vysted-Terminal-macOS-AppleSilicon.dmg`, `Vysted-Terminal-Windows-x64-Setup.exe`, `Vysted-Terminal-Linux-x86_64.AppImage`, plus `SHA256SUMS.txt` and `latest.json`. Stable URL form: `https://github.com/techlogist1/vysted-terminal/releases/latest/download/<stable name>` (resolves only once the operator publishes).
