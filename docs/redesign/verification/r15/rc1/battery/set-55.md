# unplanned-10

Candidate 4097dac4. Raw output: `raw/set-55/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-024 | `cat src-tauri/capabilities/default.json`; `grep tauri-plugin-fs src-tauri/Cargo.toml package.json`; read `docs/BLUEPRINT.md:74-81` | `default.json` permissions are still `[core:default, notification:default, shell:allow-open]` — no `fs:*`/`tauri-plugin-fs`, matching the original repro exactly. BLUEPRINT.md §3.1 now documents this accurately: "custom atomic-write commands (`write_text_atomic`, `write_bytes_atomic`), not the `tauri-plugin-fs` capability (R15-CODE-PLATFORM-024: no fs:* permission is granted..., but notes persistence and CSV/PNG/PDF exports both write real files through these commands, a webview Blob download is only the non-Tauri dev fallback)". Confirmed `write_bytes_atomic` is a real Rust command (`src-tauri/src/lib.rs:422`, registered in the handler list `:514`) invoked from `src/lib/export-artifact.ts:104` — real file writes on the real path, doc now matches the real mechanism | holds |
| R15-CODE-PLATFORM-025 | `python3 -c "..."` on `tauri.conf.json` windows array; `grep -rln "popout\|pop-out\|newWindow\|WebviewWindow\|secondary window" src src-tauri/src/*.rs`; read `docs/BLUEPRINT.md:249,322` | Still exactly one fixed window, still 0 pop-out-code hits — matching the original repro. BLUEPRINT.md now correctly scopes it: "Multi-tab layout (dockview, shipped); multi-window (v1.0 roadmap, deferred — R15-CODE-PLATFORM-025)" and "pop-out to a second window is v1.0 roadmap — R15-CODE-PLATFORM-025)" — doc no longer overclaims a feature that isn't built | holds |

Summary: 2 holds. No regressions. Both fixes took the "correct BLUEPRINT.md" branch of their fix_shape (except 024, which also shipped the real write path); neither introduces or re-claims a capability that doesn't exist.
