// Next.js 16's eslint-config-next ships native ESLint flat-config arrays —
// import and spread them directly (no FlatCompat shim needed on ESLint 10).
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    // `.claude/**` and the `**/` variants keep agent worktrees and any nested
    // build output (e.g. a teammate's `pnpm build` inside `.claude/worktrees/`)
    // from polluting lint with library type-definitions and generated chunks.
    ignores: [
      ".next/**",
      "out/**",
      "node_modules/**",
      "src-tauri/**",
      "sidecar/**",
      "scripts/**",
      ".claude/**",
      "**/.next/**",
      "**/node_modules/**",
      "**/out/**",
    ],
  },
];

export default config;
