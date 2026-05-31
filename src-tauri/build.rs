fn main() {
    // Dev-only: the tauri-plugin-mcp capability (`mcp:default`) is generated
    // into `capabilities/dev-tools.json` ONLY when the `dev-tools` Cargo
    // feature is enabled, and removed otherwise. This keeps release builds
    // clean — without the feature, the plugin that provides `mcp:default` is
    // compiled out, so a committed capability referencing it would fail the
    // Tauri build. The active file is git-ignored; the `.disabled` template is
    // tracked. See Cargo.toml `[features] dev-tools`.
    let dev_tools_cap = std::path::Path::new("capabilities/dev-tools.json");
    let template = std::path::Path::new("capabilities/.dev-tools.json.disabled");
    if std::env::var("CARGO_FEATURE_DEV_TOOLS").is_ok() {
        let should_copy = if dev_tools_cap.exists() {
            std::fs::read(template).ok() != std::fs::read(dev_tools_cap).ok()
        } else {
            true
        };
        if should_copy {
            std::fs::copy(template, dev_tools_cap)
                .expect("failed to copy dev-tools capability into place");
        }
    } else if dev_tools_cap.exists() {
        let _ = std::fs::remove_file(dev_tools_cap);
    }

    tauri_build::build()
}
