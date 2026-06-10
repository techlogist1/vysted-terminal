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
 *
 * Usage: node scripts/audit-design-tokens.mjs [--report] [paths...]
 *   --report  print violations but exit 0 (inventory mode for the sweep team)
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const args = process.argv.slice(2);
const reportOnly = args.includes("--report");
const targets = args.filter((a) => !a.startsWith("--"));
const SCAN = targets.length ? targets : ["src", "plugins"];

const ALLOWED_STEPS = new Set(["0", "0.5", "1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "16", "20", "24"]);
const ALLOWED_FONT_PX = new Set([11, 13, 16, 19, 23, 28]);
const RHYTHM = "(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|gap-x|gap-y|space-x|space-y|h|min-h|max-h|size)";
// class-ish context: preceded by quote, space, colon (variant) or backtick
const STEP_RE = new RegExp(`(?<=["'\\\`\\s:])(?:-?)${RHYTHM}-(\\d+(?:\\.\\d+)?)(?=["'\\\`\\s])`, "g");
const ARB_RE = new RegExp(`(?<=["'\\\`\\s:])(?:-?)(?:${RHYTHM}|text)-\\[[^\\]]*(?:px|rem|em)[^\\]]*\\]`, "g");
const CSS_FONT_RE = /font-size:\s*([0-9.]+)(px|rem)/g;

const SKIP_DIRS = new Set(["node_modules", "dist", ".git", "target", "__pycache__"]);
const EXTS = new Set([".tsx", ".ts", ".css"]);
const SKIP_FILES = new Set(["styles/tokens.css"]); // the token source itself

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
for (const scanRoot of SCAN) {
  let abs = join(ROOT, scanRoot);
  try {
    statSync(abs);
  } catch {
    continue;
  }
  for (const file of walk(abs)) {
    const rel = relative(ROOT, file);
    if (SKIP_FILES.has(rel)) continue;
    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, i) => {
      if (line.includes("tokens-ok:")) return; // justified exception
      for (const m of line.matchAll(STEP_RE)) {
        if (!ALLOWED_STEPS.has(m[1])) violations.push(`${rel}:${i + 1}  off-grid step  ${m[0].trim()}`);
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
      }
    });
  }
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
console.log("design-token audit clean");
