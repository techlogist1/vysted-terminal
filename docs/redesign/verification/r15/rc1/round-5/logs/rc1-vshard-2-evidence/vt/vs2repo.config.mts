import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
const WT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-9bc600e-fix-int";
export default defineConfig({
  root: WT,
  cacheDir: "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard2-r5/vt/.vite",
  plugins: [react()],
  server: { fs: { strict: false } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [WT + "/vitest.setup.ts"],
    dir: WT + "/src",
    include: ["lib/host-actions.test.ts","modules/chat/context-provider.test.ts","modules/chat/SuggestionChips.test.tsx","store/panel-context.test.ts"],
  },
  resolve: { dedupe: ["react", "react-dom"], alias: { "@testing-library/react": WT + "/node_modules/@testing-library/react", "react-dom": WT + "/node_modules/react-dom", "react": WT + "/node_modules/react", "@": path.resolve(WT, "src") } },
});
