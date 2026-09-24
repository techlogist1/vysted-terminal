import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  AUTO_APPLIED_KINDS,
  autoApplies,
  PROPOSED_CHANGE_KINDS,
} from "../../types/proposed-change";

// AUTO_APPLIED_KINDS is the one declaration of the auto-apply set
// (R15-DOCS-016/017/018) — `autoApplies` must be a pure projection of it, and
// docs/CURRENT_STATE.md must name it rather than hand-counting the write set.
describe("AUTO_APPLIED_KINDS — the one declaration of the auto-apply set", () => {
  it("autoApplies agrees with AUTO_APPLIED_KINDS for every proposed-change kind", () => {
    const autoAppliedByPredicate = PROPOSED_CHANGE_KINDS.filter((kind) => autoApplies(kind));
    expect(new Set(autoAppliedByPredicate)).toEqual(new Set(AUTO_APPLIED_KINDS));
    expect(autoAppliedByPredicate).toHaveLength(AUTO_APPLIED_KINDS.length);
  });

  it("docs/CURRENT_STATE.md names AUTO_APPLIED_KINDS by name", () => {
    const docsPath = path.resolve(__dirname, "../../docs/CURRENT_STATE.md");
    const docs = readFileSync(docsPath, "utf-8");
    const linesNamingIt = docs.split("\n").filter((line) => line.includes("AUTO_APPLIED_KINDS"));
    // §3.10 and §4 each describe the staged ProposedChange path by quoting the
    // constant; at least these two live mentions must survive edits to the doc.
    expect(linesNamingIt.length).toBeGreaterThanOrEqual(2);
  });

  it("docs/CURRENT_STATE.md points the write set at HOST_ACTION_NAMES, not a hand count", () => {
    const docsPath = path.resolve(__dirname, "../../docs/CURRENT_STATE.md");
    const docs = readFileSync(docsPath, "utf-8");
    expect(docs).toContain("HOST_ACTION_NAMES");
  });
});
