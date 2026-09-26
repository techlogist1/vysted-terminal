// Flat config for the Vite + React 19 shell (replaces eslint-config-next after
// the R7 migration): typescript-eslint recommended + react-hooks. The react
// plugin's JSX-runtime preset disables the legacy React-in-scope rules.
import tseslint from "typescript-eslint";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

const config = [
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { react: reactPlugin, "react-hooks": reactHooks, "jsx-a11y": jsxA11y },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...reactPlugin.configs.flat["jsx-runtime"].rules,
      // R15-UI-071: no automated accessibility gate existed at all. Scoped to
      // the one rule the entry names (control-labelling — the concrete gap:
      // 74/76 <input>s with neither id/name nor a checked label association)
      // rather than the full jsx-a11y `recommended` bundle, which spans
      // unrelated concerns (alt-text, anchor validity, media captions, …)
      // this low never audited across the ~39 affected files — pulling all
      // of it in blind risks flooding the rc1 `pnpm lint` gate with
      // unaudited findings. Widening the rule set is a follow-up, not this
      // fix. `assert: "either"` accepts EITHER a wrapping/`htmlFor` label OR
      // an `aria-label`/`aria-labelledby` on the control itself, matching
      // the pattern already used throughout (e.g. ToggleSwitch's
      // `<label><input aria-label .../></label>`); the default "both" would
      // flag every one of those as a false positive.
      "jsx-a11y/label-has-associated-control": ["error", { assert: "either" }],
      // Match the strictness the previous next config enforced.
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // R15-UI-009/UI-025 (D-B4-20): the desktop WKWebView implements none of
      // these — they silently no-op instead of erroring, so the bug hides
      // until someone clicks it on macOS. Use a real UI affordance instead.
      "no-restricted-properties": [
        "error",
        {
          object: "window",
          property: "prompt",
          message: "window.prompt is a no-op in the Tauri desktop webview — use an inline popover.",
        },
        {
          object: "window",
          property: "alert",
          message:
            "window.alert is a no-op in the Tauri desktop webview — use an inline banner/toast.",
        },
        {
          object: "window",
          property: "confirm",
          message:
            "window.confirm is a no-op in the Tauri desktop webview — use an inline confirm control.",
        },
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
      "coverage/**",
      // Verification evidence harnesses (R15 surface drives) run under their own
      // vitest configs; they are captured evidence, not product source.
      "docs/redesign/verification/**",
    ],
  },
];

export default config;
