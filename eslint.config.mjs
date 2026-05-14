// Next.js 16's eslint-config-next ships native ESLint flat-config arrays —
// import and spread them directly (no FlatCompat shim needed on ESLint 10).
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [".next/**", "out/**", "node_modules/**", "src-tauri/**", "sidecar/**", "scripts/**"],
  },
];

export default config;
