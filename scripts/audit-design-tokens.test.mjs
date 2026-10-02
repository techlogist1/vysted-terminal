// @vitest-environment node
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const SCRIPT = join(import.meta.dirname, "audit-design-tokens.mjs");
const REPO_ROOT = join(import.meta.dirname, "..");
let root;

const audit = (...targets) =>
  spawnSync(process.execPath, [SCRIPT, ...targets], { encoding: "utf8" });

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "token-audit-"));
});

afterEach(() => rmSync(root, { recursive: true, force: true }));

describe("audit-design-tokens", () => {
  it("exits non-zero when it scanned zero files instead of printing clean", () => {
    mkdirSync(join(root, "empty"));
    const r = audit(join(root, "empty"), join(root, "missing"));
    expect(r.status).not.toBe(0);
    expect(r.stdout).not.toContain("clean");
  });

  it("exits non-zero on an off-grid step and an arbitrary text size", () => {
    writeFileSync(join(root, "Panel.tsx"), `<div className="gap-1.5 text-[12px]" />\n`);
    const r = audit(root);
    expect(r.status).toBe(1);
    expect(r.stdout).toContain("off-grid step  gap-1.5");
    expect(r.stdout).toContain("arbitrary value  text-[12px]");
  });

  it("exits zero on an on-grid file", () => {
    writeFileSync(join(root, "Panel.tsx"), `<div className="gap-2 px-3 text-xs" />\n`);
    const r = audit(root);
    expect(r.status).toBe(0);
    expect(r.stdout).toContain("design-token audit clean (1 files)");
  });

  it("body font-feature-settings enables zero (matches tokens.css's slashed-zero claim)", () => {
    const css = readFileSync(join(REPO_ROOT, "src/app/globals.css"), "utf8");
    const match = css.match(/font-feature-settings:\s*([^;]+);/);
    expect(match).not.toBeNull();
    expect(match[1]).toContain('"zero" 1');
  });

  it("a mismatched fallback fails the audit", () => {
    // --color-charcoal-900 is #161616 in the real styles/tokens.css; this fallback
    // is a stale value that no longer matches.
    writeFileSync(
      join(root, "stale.css"),
      `.panel { background: var(--color-charcoal-900, #1a1814); }\n`,
    );
    const r = audit(root);
    expect(r.status).toBe(1);
    expect(r.stdout).toContain("stale var() fallback");
    expect(r.stdout).toContain("--color-charcoal-900, #1a1814");
  });

  it("an agreeing fallback passes the audit", () => {
    writeFileSync(
      join(root, "fresh.css"),
      `.panel { background: var(--color-charcoal-900, #161616); }\n`,
    );
    const r = audit(root);
    expect(r.status).toBe(0);
  });
});
