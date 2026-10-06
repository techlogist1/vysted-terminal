import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

/**
 * R15-DOCS-004 pin: PRODUCT_DESIGN_DECISIONS.md's banner marks §0–§7, §9, §10
 * SUPERSEDED (the retired "Warm Graphite" palette/scale/type, reversed by R6
 * "Pure Black" and R9 without ever being recorded). §8 and §11–§16 remain
 * binding. A source comment citing a dead section number is worse than no
 * citation — it points a future reader at content that no longer applies.
 */
const SUPERSEDED_SECTIONS = new Set([0, 1, 2, 3, 4, 5, 6, 7, 9, 10]);

const SCAN_ROOTS = ["src", "styles"];
const SCAN_EXTENSIONS = new Set([".ts", ".tsx", ".css", ".js", ".mjs"]);
const SKIP_DIRS = new Set(["node_modules", ".next", "out"]);

// This file's own doc comment above legitimately names the dead sections —
// exclude it from its own scan.
const SELF_PATH = path.resolve(__dirname, "design-doc-citations.test.ts");

const CITATION_RE = /PRODUCT_DESIGN_DECISIONS(?:\.md)?[^\n\d]{0,20}§\s*(\d+)/g;

function walk(dir: string, out: string[]): void {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (SCAN_EXTENSIONS.has(path.extname(entry.name))) {
      out.push(full);
    }
  }
}

describe("R15-DOCS-004: no live source cites a superseded PDD section", () => {
  it("finds zero citations of §0-7, §9, or §10", () => {
    const repoRoot = path.resolve(__dirname, "../..");
    const files: string[] = [];
    for (const root of SCAN_ROOTS) {
      const abs = path.join(repoRoot, root);
      if (fs.existsSync(abs)) walk(abs, files);
    }

    const offenders: string[] = [];
    for (const file of files) {
      if (path.resolve(file) === SELF_PATH) continue;
      const content = fs.readFileSync(file, "utf8");
      for (const match of content.matchAll(CITATION_RE)) {
        const section = Number(match[1]);
        if (SUPERSEDED_SECTIONS.has(section)) {
          offenders.push(`${path.relative(repoRoot, file)}: cites superseded §${section}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });
});
