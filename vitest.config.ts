import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "plugins/**/*.test.{ts,tsx}", "scripts/**/*.test.mjs"],
    coverage: {
      provider: "v8",
      thresholds: {
        // R15-RELEASE-011: no threshold + no gate meant coverage could regress
        // to zero unnoticed. `autoUpdate` ratchets this number UP to the real
        // measured coverage the next time `vitest run --coverage` passes (wired
        // into `ci-local`) and never down, so it self-bootstraps from this
        // starting floor without a hand-picked number, while still catching a
        // real regression below whatever was last measured.
        lines: 0,
        autoUpdate: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
