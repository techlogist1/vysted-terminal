const REPO = "/Users/lokavyasingh/Documents/dev/vysted-terminal";
const SCR = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c/vt";
export default {
  root: REPO,
  test: { environment: "jsdom", globals: true, setupFiles: [REPO + "/vitest.setup.ts"], dir: SCR, include: ["**/*.s2c.test.{ts,tsx}"], testTimeout: 240000, fileParallelism: false },
  resolve: { alias: { "@": REPO + "/src" } },
  server: { fs: { allow: ["/"] } },
};
