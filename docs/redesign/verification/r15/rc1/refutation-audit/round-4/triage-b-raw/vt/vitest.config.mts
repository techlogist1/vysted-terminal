import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  root: "/Users/lokavyasingh/Documents/dev/vysted-terminal",
  cacheDir: "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/vite-cache",
  plugins: [react()],
  test: { environment: "jsdom", globals: true, setupFiles: ["/Users/lokavyasingh/Documents/dev/vysted-terminal/vitest.setup.ts"], include: ["/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/rc1/refutation-audit/round-4/triage-b-raw/vt/*.test.ts"] },
  resolve: { alias: { "@": "/Users/lokavyasingh/Documents/dev/vysted-terminal/src" } },
});
