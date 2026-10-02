import fs from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

import { collectPanels } from "@/lib/module-registry";
import { vystedModules } from "@/modules";

// Only panel ids matter here; keep the tiptap editor bundle out of the import graph.
vi.mock("@/modules/notes/NotesPanel", () => ({ NotesPanel: () => null }));

const SRC = path.resolve(__dirname, "..");

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [full] : [];
  });
}

// A panel id passed as a literal — `openPanel("x")` or a command's
// `opensPanel: "x"` — must name a registered PanelSpec id, not a component id:
// openPanel resolves by PanelSpec id and an unknown id opens nothing.
const LITERAL_RE = /\bopens?Panel(?:\(\s*|:\s*)["']([^"']+)["']/g;

describe("panel-id literals (R15-UI-065)", () => {
  it("every openPanel('literal') / opensPanel literal under src/ resolves to a registered panel", () => {
    const panelIds = new Set(collectPanels(vystedModules).map((panel) => panel.id));
    const literals: string[] = [];
    const unknown: string[] = [];
    for (const file of sourceFiles(SRC)) {
      for (const match of fs.readFileSync(file, "utf-8").matchAll(LITERAL_RE)) {
        literals.push(match[1]);
        if (!panelIds.has(match[1])) {
          unknown.push(`${path.relative(SRC, file)}: "${match[1]}"`);
        }
      }
    }
    expect(literals.length).toBeGreaterThan(10);
    expect(unknown).toEqual([]);
  });
});
