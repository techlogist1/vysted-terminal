import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

/**
 * R15-CODE-FRONTEND-024 pin: `fuzzy.ts` had tests but no consumer (the
 * command palette ranks via cmdk, not this module) and
 * `notes-persistence.ts`'s `exportNoteMd` had no caller — both deleted.
 * Grep over `src` for their symbol names should stay empty forever.
 */
const DEAD_SYMBOLS = ["fuzzyRank", "fuzzyScore", "fuzzyScoreWithIndices", "exportNoteMd"];

const SCAN_ROOT = "src";
const SCAN_EXTENSIONS = new Set([".ts", ".tsx"]);
const SKIP_DIRS = new Set(["node_modules", ".next", "out"]);

const SELF_PATH = path.resolve(__dirname, "dead-surface.test.ts");

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

describe("R15-CODE-FRONTEND-024: no live source references a deleted dead-code symbol", () => {
  it("finds zero references to fuzzyRank/fuzzyScore/exportNoteMd under src/", () => {
    const repoRoot = path.resolve(__dirname, "../..");
    const files: string[] = [];
    walk(path.join(repoRoot, SCAN_ROOT), files);

    const offenders: string[] = [];
    for (const file of files) {
      if (path.resolve(file) === SELF_PATH) continue;
      const content = fs.readFileSync(file, "utf8");
      for (const symbol of DEAD_SYMBOLS) {
        if (content.includes(symbol)) {
          offenders.push(`${path.relative(repoRoot, file)}: references dead symbol ${symbol}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });
});
