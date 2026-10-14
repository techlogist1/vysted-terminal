import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
const CAND = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/final-cand";
const U = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/fonb";
const port = process.env.FP_PORT ?? "52846";
export default defineConfig({
  root: CAND,
  cacheDir: path.join(U, ".vite"),
  plugins: [react()],
  test: {
    environment: "jsdom",
    environmentOptions: { jsdom: { url: `http://localhost:5173/?sidecar-port=${port}` } },
    globals: true,
    setupFiles: [path.join(CAND, "vitest.setup.ts")],
    dir: U,
    include: [process.env.FP_FILE ?? "**/*.fp.test.{ts,tsx}"],
    exclude: ["**/node_modules/**"],
    testTimeout: 110000,
    hookTimeout: 60000,
  },
  resolve: { alias: { "@": path.join(CAND, "src") } },
});
