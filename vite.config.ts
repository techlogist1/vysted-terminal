import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Tauri loads the dev server from tauri.conf.json `build.devUrl` — the port
// here and there must agree, so strictPort fails loudly instead of drifting.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    host: "127.0.0.1",
    watch: {
      // Agent worktrees, build output, and the sidecar tree live inside the
      // repo root — without these ignores every teammate commit triggers a
      // full app reload mid-session.
      ignored: [
        "**/.claude/**",
        "**/out/**",
        "**/sidecar/**",
        "**/src-tauri/**",
        "**/graphify-out/**",
      ],
    },
  },
  build: {
    // Matches tauri.conf.json `build.frontendDist: "../out"`.
    outDir: "out",
    emptyOutDir: true,
    sourcemap: false,
  },
  // Static desktop bundle — relative asset URLs so the webview's custom
  // protocol resolves chunks without a server.
  base: "./",
});
