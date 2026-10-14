import react from "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/final-cand/node_modules/@vitejs/plugin-react/dist/index.js";
const ROOT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/final-cand";
export default {
  root: ROOT,
  cacheDir: "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/fdpn/vt/.vite",
  plugins: [react()],
  test: { environment: "jsdom", environmentOptions: { jsdom: { url: "http://localhost:5173" } }, globals: true, setupFiles: [ROOT + "/vitest.setup.ts"], dir: "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/fdpn/vt", include: ["**/*.fdpn.test.{ts,tsx}"], testTimeout: 400000, fileParallelism: false },
  resolve: { alias: { "@": ROOT + "/src" } },
  server: { fs: { allow: ["/"] } },
};
