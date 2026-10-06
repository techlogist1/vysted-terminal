#!/usr/bin/env node
/**
 * R9 design-token audit — statically enforces R9_DESIGN_SYSTEM.md over src/ and plugins/.
 *
 * Checks (rhythm law §1, type law §2):
 *   1. Spacing utilities (p* m* gap* space-* h- min-h- max-h- size-) must use an
 *      allowed step: 0.5 1 2 3 4 5 6 7 8 10 12 16 20 24 (= 2..96px on the 8-pt grid
 *      with 4px half-steps; 28px reserved for controls). px/full/auto/screen/fit/min/max
 *      and fractions are layout, not rhythm — ignored. Widths (w-*) are layout
 *      dimensions and are not audited.
 *   2. Arbitrary values in rhythm namespaces (p-[7px], gap-[0.4rem], h-[18px]) and
 *      arbitrary text sizes (text-[12px]) are violations unless the line carries a
 *      `tokens-ok:` comment with a justification.
 *   3. Dead type sizes: raw font-size in CSS must be one of 11/13/16/19/23/28 px
 *      (or derive from a --text-* token). text-{12,14,15,17,18,22,...}px utilities fail.
 *   4. Stale var() fallbacks: `var(--token, fallback)` in a CSS file must agree with
 *      --token's current value in styles/tokens.css (px/rem compared numerically;
 *      functional values like cubic-bezier() are generic fallbacks, not mirrored
 *      literals, and are skipped) — a fallback only renders if the token is undefined,
 *      but a stale value is a misleading trap for a reader (R15-CODE-PLATFORM-070).
 *
 * Usage: node scripts/audit-design-tokens.mjs [--report] [paths...]
 *   --report  print violations but exit 0 (inventory mode for the sweep team)
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";

// import.meta.dirname, not URL.pathname: the latter is "/C:/..." on Windows, which
// resolves nowhere, so the audit walked zero files and printed clean (R15-CODE-PLATFORM-027).
const ROOT = resolve(import.meta.dirname, "..");
const args = process.argv.slice(2);
const reportOnly = args.includes("--report");
const targets = args.filter((a) => !a.startsWith("--"));
const SCAN = targets.length ? targets : ["src", "plugins"];

const ALLOWED_STEPS = new Set([
  "0",
  "0.5",
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "10",
  "12",
  "16",
  "20",
  "24",
]);
const ALLOWED_FONT_PX = new Set([11, 13, 16, 19, 23, 28]);
const RHYTHM =
  "(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|gap-x|gap-y|space-x|space-y|h|min-h|max-h|size)";
// class-ish context: preceded by quote, space, colon (variant) or backtick
const STEP_RE = new RegExp(
  `(?<=["'\\\`\\s:])(?:-?)${RHYTHM}-(\\d+(?:\\.\\d+)?)(?=["'\\\`\\s])`,
  "g",
);
const ARB_RE = new RegExp(
  `(?<=["'\\\`\\s:])(?:-?)(?:${RHYTHM}|text)-\\[[^\\]]*(?:px|rem|em)[^\\]]*\\]`,
  "g",
);
const CSS_FONT_RE = /font-size:\s*([0-9.]+)(px|rem)/g;
const VAR_FALLBACK_RE = /var\((--[a-z0-9-]+),\s*([^)]+)\)/gi;

const SKIP_DIRS = new Set(["node_modules", "dist", ".git", "target", "__pycache__"]);
const EXTS = new Set([".tsx", ".ts", ".css"]);
const SKIP_FILES = new Set(["styles/tokens.css"]); // the token source itself

// --- var() fallback vs styles/tokens.css (check 4) -------------------------
// tokenName -> literal value string, straight from the real @theme block.
// Composite values (font stacks that themselves reference var(...)) are not
// literal-mirrored anywhere, so they are excluded from this check.
const TOKEN_VALUES = new Map();
try {
  const tokensSrc = readFileSync(join(ROOT, "styles/tokens.css"), "utf8");
  for (const m of tokensSrc.matchAll(/^\s*(--[a-z0-9-]+):\s*([^;]+);/gim)) {
    const value = m[2].split("/*")[0].trim();
    if (!value.includes("var(")) TOKEN_VALUES.set(m[1], value);
  }
} catch {
  // styles/tokens.css missing (e.g. an isolated test fixture) — check 4 finds nothing.
}

const UNIT_RE = /^(-?[0-9.]+)(px|rem)?$/;
function fallbackDisagrees(fallback, tokenValue) {
  const fb = fallback.trim();
  const tok = tokenValue.trim();
  if (fb.toLowerCase() === tok.toLowerCase()) return false;
  if (tok.includes("(")) return false; // functional value (cubic-bezier, ...): generic fallback, not mirrored
  const fbM = UNIT_RE.exec(fb);
  const tokM = UNIT_RE.exec(tok);
  if (fbM && tokM) {
    const toPx = (m) => parseFloat(m[1]) * (m[2] === "rem" ? 16 : 1);
    return toPx(fbM) !== toPx(tokM);
  }
  return true;
}

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) {
      if (!SKIP_DIRS.has(name)) yield* walk(p);
    } else if (EXTS.has(name.slice(name.lastIndexOf(".")))) yield p;
  }
}

const violations = [];
let scanned = 0;
for (const scanRoot of SCAN) {
  const abs = resolve(ROOT, scanRoot);
  try {
    statSync(abs);
  } catch {
    continue;
  }
  for (const file of walk(abs)) {
    const rel = relative(ROOT, file).split(sep).join("/");
    if (SKIP_FILES.has(rel)) continue;
    scanned++;
    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, i) => {
      if (line.includes("tokens-ok:")) return; // justified exception
      for (const m of line.matchAll(STEP_RE)) {
        if (!ALLOWED_STEPS.has(m[1]))
          violations.push(`${rel}:${i + 1}  off-grid step  ${m[0].trim()}`);
      }
      for (const m of line.matchAll(ARB_RE)) {
        violations.push(`${rel}:${i + 1}  arbitrary value  ${m[0].trim()}`);
      }
      if (rel.endsWith(".css")) {
        for (const m of line.matchAll(CSS_FONT_RE)) {
          const px = m[2] === "rem" ? parseFloat(m[1]) * 16 : parseFloat(m[1]);
          if (!ALLOWED_FONT_PX.has(Math.round(px * 100) / 100)) {
            violations.push(`${rel}:${i + 1}  off-scale font-size  ${m[0]}`);
          }
        }
        for (const m of line.matchAll(VAR_FALLBACK_RE)) {
          const [full, name, fallback] = m;
          const tokenValue = TOKEN_VALUES.get(name);
          if (tokenValue !== undefined && fallbackDisagrees(fallback, tokenValue)) {
            violations.push(
              `${rel}:${i + 1}  stale var() fallback  ${full.trim()} (token: ${tokenValue})`,
            );
          }
        }
      }
    });
  }
}

if (scanned === 0) {
  console.error(
    `design-token audit scanned 0 files under ${SCAN.join(", ")}; refusing to report clean`,
  );
  process.exit(1);
}

if (violations.length) {
  const byFile = {};
  for (const v of violations) {
    const f = v.split(":")[0];
    byFile[f] = (byFile[f] ?? 0) + 1;
  }
  console.log(violations.join("\n"));
  console.log(`\n— per-file —`);
  Object.entries(byFile)
    .sort((a, b) => b[1] - a[1])
    .forEach(([f, n]) => console.log(`${String(n).padStart(4)}  ${f}`));
  console.log(`\n${violations.length} violation(s) of R9_DESIGN_SYSTEM.md`);
  process.exit(reportOnly ? 0 : 1);
}
console.log(`design-token audit clean (${scanned} files)`);
