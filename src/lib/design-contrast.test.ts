import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// R15-UI-085: charcoal-600 is a border/disabled-fg token (tokens.css comment),
// not readable text (~1.98:1 on the panel surface). This file pins two things:
// (1) every text token in the ramp clears the WCAG floor R4_DESIGN_LANGUAGE.md
//     §7 sets for its role, against both background surfaces it is used on;
// (2) no future file reintroduces an unprefixed text-charcoal-600/-700 class
//     (a "disabled:"-scoped use, e.g. `disabled:text-charcoal-600`, is fine —
//     that is the token's documented role).

const REPO_ROOT = path.resolve(__dirname, "../..");
const TOKENS_CSS = fs.readFileSync(path.join(REPO_ROOT, "styles/tokens.css"), "utf-8");

function parseToken(name: string): string {
  const match = TOKENS_CSS.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`token --color-${name} not found in tokens.css`);
  return match[1];
}

// WCAG 2.x relative luminance + contrast ratio (sRGB, no gamma-corrected inputs).
function relativeLuminance(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const linear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
}

function contrastRatio(hexA: string, hexB: string): number {
  const lA = relativeLuminance(hexA);
  const lB = relativeLuminance(hexB);
  const lighter = Math.max(lA, lB);
  const darker = Math.min(lA, lB);
  return (lighter + 0.05) / (darker + 0.05);
}

const SURFACES = {
  panel: parseToken("charcoal-900"), // panel/card surface, the common case
  root: parseToken("charcoal-950"), // app well
};

// R4_DESIGN_LANGUAGE.md:271-277 — body text >=4.5:1, everything else (labels,
// meta, tertiary/secondary copy) >=3:1. charcoal-100 is the only token the
// design language documents as body copy; charcoal-200/300/400/500 and
// sage-500 are documented as secondary/tertiary/label/meta tokens.
const TEXT_TOKENS: Array<{ name: string; hex: string; floor: number }> = [
  { name: "charcoal-100", hex: parseToken("charcoal-100"), floor: 4.5 },
  { name: "charcoal-200", hex: parseToken("charcoal-200"), floor: 3 },
  { name: "charcoal-300", hex: parseToken("charcoal-300"), floor: 3 },
  { name: "charcoal-400", hex: parseToken("charcoal-400"), floor: 3 },
  { name: "charcoal-500", hex: parseToken("charcoal-500"), floor: 3 },
  { name: "sage-500", hex: parseToken("sage-500"), floor: 3 },
];

describe("design token contrast (R15-UI-085)", () => {
  for (const token of TEXT_TOKENS) {
    for (const [surfaceName, surfaceHex] of Object.entries(SURFACES)) {
      it(`${token.name} clears ${token.floor}:1 on ${surfaceName}`, () => {
        const ratio = contrastRatio(token.hex, surfaceHex);
        expect(ratio).toBeGreaterThanOrEqual(token.floor);
      });
    }
  }
});

// --- Source scan: no unprefixed text-charcoal-600/-700 outside this file's set. ---

function listTsxFiles(dir: string, out: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      listTsxFiles(full, out);
    } else if (entry.isFile() && entry.name.endsWith(".tsx") && !entry.name.endsWith(".test.tsx")) {
      out.push(full);
    }
  }
  return out;
}

// Matches a full Tailwind class token (variant chain + utility), e.g.
// "disabled:text-charcoal-600" or bare "text-charcoal-700".
const BANNED_TOKEN_RE = /[\w:/-]*text-charcoal-(?:600|700)[\w/-]*/g;

describe("no readable-text use of charcoal-600/700 (R15-UI-085)", () => {
  it("flags every unprefixed occurrence outside a disabled state", () => {
    const violations: string[] = [];
    for (const file of listTsxFiles(path.join(REPO_ROOT, "src"))) {
      const lines = fs.readFileSync(file, "utf-8").split("\n");
      lines.forEach((line, idx) => {
        const matches = line.match(BANNED_TOKEN_RE);
        if (!matches) return;
        for (const token of matches) {
          if (token.toLowerCase().includes("disabled")) continue;
          violations.push(`${path.relative(REPO_ROOT, file)}:${idx + 1} \`${token}\``);
        }
      });
    }
    expect(violations, `unprefixed charcoal-600/700 text use:\n${violations.join("\n")}`).toEqual(
      [],
    );
  });
});
