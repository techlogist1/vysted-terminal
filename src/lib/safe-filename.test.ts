import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { safeFilename } from "./safe-filename";

// R15-CROSS-PLATFORM-006: notes-persistence.ts and NotesPanel.tsx each had
// their own partial sanitiser (stripped only `/` and `\`), so Windows-illegal
// names like "NSE:RELIANCE" or "CON" silently failed to write. One shared
// helper, used at both call sites.

const ILLEGAL_CHAR_RE = /[<>:"/\\|?*\x00-\x1f]/;
const RESERVED_DEVICE_NAMES = new Set([
  "CON",
  "PRN",
  "AUX",
  "NUL",
  "COM1",
  "COM2",
  "COM3",
  "COM4",
  "COM5",
  "COM6",
  "COM7",
  "COM8",
  "COM9",
  "LPT1",
  "LPT2",
  "LPT3",
  "LPT4",
  "LPT5",
  "LPT6",
  "LPT7",
  "LPT8",
  "LPT9",
]);

describe("safeFilename", () => {
  it.each(["NSE:RELIANCE", "CON", "a?b", "x."])("maps %s to a Windows-legal name", (input) => {
    const out = safeFilename(input);
    expect(out.length).toBeGreaterThan(0);
    expect(ILLEGAL_CHAR_RE.test(out)).toBe(false);
    expect(TRAILING_DOT_OR_SPACE(out)).toBe(false);
    const base = out.includes(".") ? out.slice(0, out.indexOf(".")) : out;
    expect(RESERVED_DEVICE_NAMES.has(base.toUpperCase())).toBe(false);
  });

  it("leaves an already-safe name unchanged", () => {
    expect(safeFilename("AAPL")).toBe("AAPL");
    expect(safeFilename("NIFTY_50")).toBe("NIFTY_50");
  });
});

function TRAILING_DOT_OR_SPACE(name: string): boolean {
  return /[. ]$/.test(name);
}

describe("safeFilename call sites", () => {
  it("notes-persistence.ts and NotesPanel.tsx both route through the shared helper", () => {
    const libDir = path.resolve(__dirname);
    const notesDir = path.resolve(libDir, "../modules/notes");
    const persistence = fs.readFileSync(path.join(notesDir, "notes-persistence.ts"), "utf8");
    const panel = fs.readFileSync(path.join(notesDir, "NotesPanel.tsx"), "utf8");

    expect(persistence).toMatch(/safeFilename/);
    expect(panel).toMatch(/safeFilename/);
  });
});
