// Dev-only bridge for the tauri-plugin-mcp test-automation rig
// (DaveDev42/tauri-plugin-mcp). Initializes the in-webview JS bridge that the
// `tauri-mcp` MCP server drives over a loopback socket — snapshot, click, fill,
// and console/network log capture.
//
// Hard dev-only guarantee: the dynamic `import("tauri-plugin-mcp")` sits behind
// a `process.env.NODE_ENV === "production"` early-return. Next.js inlines
// `process.env.NODE_ENV` and dead-code-eliminates the branch in the
// static-export production build, so the `tauri-plugin-mcp` devDependency
// (absent from release installs) is never referenced or bundled. The Rust
// plugin that answers this bridge is likewise compiled out of release builds
// via the Cargo `dev-tools` feature.
export function initDevMcpBridge(): void {
  if (process.env.NODE_ENV === "production") return;
  if (typeof window === "undefined") return;
  void import("tauri-plugin-mcp")
    .then(({ initMcpBridge }) => initMcpBridge())
    .catch((err) => {
      // Expected outside the Tauri webview (e.g. a plain browser at :3000).
      console.warn("[mcp] dev bridge init skipped:", err);
    });
}
