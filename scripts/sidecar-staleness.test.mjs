// @vitest-environment node
import { mkdirSync, mkdtempSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { assertFresh, isStale } from "./sidecar-staleness.mjs";

const OLD = new Date("2026-01-01T00:00:00Z");
const BIN_TIME = new Date("2026-02-01T00:00:00Z");
const NEW = new Date("2026-03-01T00:00:00Z");

let root;
let src;
let bin;

/** Write `rel` under the source dir with mtime `when`. */
function put(rel, when = OLD) {
  const p = join(src, rel);
  mkdirSync(join(p, ".."), { recursive: true });
  writeFileSync(p, "x");
  utimesSync(p, when, when);
  return p;
}

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "staleness-"));
  src = join(root, "src");
  put("main.py");
  bin = join(root, "sidecar-bin");
  writeFileSync(bin, "bin");
  utimesSync(bin, BIN_TIME, BIN_TIME);
});

afterEach(() => rmSync(root, { recursive: true, force: true }));

describe("isStale", () => {
  it("is false when every source file predates the binary", () => {
    expect(isStale(bin, src)).toBe(false);
    expect(() => assertFresh(bin, src)).not.toThrow();
  });

  it("is true when a source file is newer than the binary", () => {
    put("services/x.py", NEW);
    expect(isStale(bin, src)).toBe(true);
    expect(() => assertFresh(bin, src)).toThrow(/STALE SIDECAR/);
  });

  it("is true when the binary is missing", () => {
    expect(isStale(join(root, "nope"), src)).toBe(true);
    expect(() => assertFresh(join(root, "nope"), src)).toThrow(/missing/);
  });

  it("prunes excludeDirs and the build/venv scratch dirs", () => {
    put("sub/main.py", NEW);
    put(".venv/lib/site.py", NEW);
    put("build/x.py", NEW);
    expect(isStale(bin, src, { excludeDirs: [join(src, "sub")] })).toBe(false);
  });

  it("counts a newer extraFile (the build recipe)", () => {
    const recipe = join(root, "recipe.mjs");
    writeFileSync(recipe, "r");
    utimesSync(recipe, NEW, NEW);
    expect(isStale(bin, src, { extraFiles: [recipe] })).toBe(true);
  });
});
