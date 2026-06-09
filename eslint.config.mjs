// Flat config for the Vite + React 19 shell (replaces eslint-config-next after
// the R7 migration): typescript-eslint recommended + react-hooks. The react
// plugin's JSX-runtime preset disables the legacy React-in-scope rules.
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

const config = [
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { react: reactPlugin, "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...reactPlugin.configs.flat["jsx-runtime"].rules,
      // Match the strictness the previous next config enforced.
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
    settings: { react: { version: "detect" } },
  },
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
      "**/node_modules/**",
      "**/out/**",
    ],
  },
];

export default config;
