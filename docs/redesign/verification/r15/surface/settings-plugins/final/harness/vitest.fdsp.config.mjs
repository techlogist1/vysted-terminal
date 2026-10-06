const REPO = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/final-cand";
const SCR = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/fdsp/vt";
export default {
  root: REPO,
  cacheDir: SCR + "/.vite-cache",
  test: { environment: "jsdom", environmentOptions: { jsdom: { url: "http://localhost:5173" } }, globals: true, setupFiles: [REPO + "/vitest.setup.ts"], dir: SCR, include: ["**/*.fdsp.test.{ts,tsx}"], testTimeout: 240000, fileParallelism: false },
  resolve: { alias: { "@": REPO + "/src" } },
  server: { fs: { allow: ["/"] } },
};
