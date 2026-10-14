# r16-rc1 proof — release pipeline + self-update (15 Oct 2026, 04:43–04:57 IST)

Verdict: PASS (items 1 and 2). Linux AppImage: FAIL in both runs (linuxdeploy), allowed by the brief ("if it builds green"); fix in flight.

## Release pipeline (item 1)

- Tag v0.10.0-beta.1 (15be2463) -> run 38651694765; tag v0.10.0-beta.2 (d7a71a46) -> run 38651740130. Each: determine-tag, build-macos, build-windows, publish = success; build-linux = failure (continue-on-error).
- Draft prerelease per tag with stable names (Vysted-Terminal-macOS-AppleSilicon.dmg, Vysted-Terminal-Windows-x64-Setup.exe), Tauri versioned names, updater bundles + .sig, latest.json, SHA256SUMS.txt.
- Downloaded dmg sha256 efbecb60…51fac matches SHA256SUMS.txt; beta.2 Vysted-Terminal.app.tar.gz sha256 50abd579…2b3 matches.
- dmg layout: .background/background.png (660x400 PNG), Applications symlink, Vysted Terminal.app (CFBundleShortVersionString 0.10.0-beta.1, ad-hoc signature).
- Bundled engine: Contents/MacOS/llama-server + 10 ggml/llama dylibs beside it, LC_RPATH @loader_path; `llama-server --version` from the mounted dmg -> "version: 0.6.0-dev (build 11429, commit d81235049)".

## Self-update (item 2)

- beta.1 copied out of the dmg to a writable dir, launched with VYSTED_DATA_DIR=<scratch profile> and VYSTED_UPDATER_ENDPOINT=http://127.0.0.1:8787/latest.json; `scripts/release/serve-update.mjs --rewrite` served the unmodified beta.2 latest.json + signed bundle from the GitHub draft.
- The app showed "Vysted Terminal 0.10.0-beta.2 is available." (15 s check). Clicked "Restart to update" -> server log "200 GET /Vysted-Terminal.app.tar.gz" -> app log "[vysted] update 0.10.0-beta.2 installed, relaunching".
- After: on-disk bundle CFBundleShortVersionString 0.10.0-beta.2; new process tree only (no pre-update sidecar/MCP children left: teardown held); sidecar /health version "0.10.0-beta.2"; no update strip after relaunch (screenshot after-update-beta2.png).
- Packaged /local-models answers on beta.2: tier 16gb, recommended qwen3.5-9b (provisional), 4 Apache-2.0 models; hardware M1 Pro unified memory; Ollama models listed as installed.

## Test-state note

- The first-launch terms dialog in the scratch profile could not be clicked: a third-party always-on-top overlay window (Wispr Flow, layer 1000) covers its button and the rig may not move windows. The terms + onboarding acks were seeded into the throwaway profile (app-meta.json + a keychain item under the profile's own service vysted-terminal.profile.98886a418a7a, deleted afterwards). The operator's real profile was never touched. The GUI round must clear that overlay area (window placement) before driving the wizard.
