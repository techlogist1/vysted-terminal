import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
const REPO = "/Users/lokavyasingh/Documents/dev/vysted-terminal";
export default defineConfig({
  root: REPO,
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [path.join(REPO, "vitest.setup.ts")],
    include: [path.join(__dirname, "*.probe.test.tsx")],
    testTimeout: 60000,
  },
  resolve: { alias: { "@": path.join(REPO, "src") } },
  server: { fs: { allow: [REPO, __dirname] } },
});
