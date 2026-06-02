import { describe, expect, it } from "vitest";

import { buildModelGroups, modelOptionLabel } from "@/lib/model-options";
import type { LLMModelOption } from "../../types/ai";

const opt = (id: string, supportsTools?: boolean | null): LLMModelOption => ({
  id,
  label: id,
  supportsTools,
});

describe("buildModelGroups", () => {
  it("groups tool-capable, unknown, and no-tool models when capability is known", () => {
    const { groups } = buildModelGroups(
      [opt("a/tools", true), opt("b/plain", false), opt("c/unknown", null)],
      "a/tools",
    );
    expect(groups.map((g) => g.label)).toEqual(["Tool-calling", "Other", "No tool-calling"]);
    expect(groups[0].options.map((o) => o.id)).toEqual(["a/tools"]);
    expect(groups[2].options.map((o) => o.id)).toEqual(["b/plain"]);
  });

  it("renders a single flat group when no tool-capability is known", () => {
    const { groups } = buildModelGroups([opt("x"), opt("y")], "x");
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBeNull();
    expect(groups[0].options.map((o) => o.id)).toEqual(["x", "y"]);
  });

  it("injects the selected model when it is absent from the catalog", () => {
    const { groups } = buildModelGroups([opt("a"), opt("b")], "custom/not-listed");
    const ids = groups.flatMap((g) => g.options.map((o) => o.id));
    expect(ids).toContain("custom/not-listed");
  });

  it("reports when the selected model is known to lack tool-calling", () => {
    const result = buildModelGroups([opt("a/tools", true), opt("b/plain", false)], "b/plain");
    expect(result.selectedIsNoTools).toBe(true);
    const ok = buildModelGroups([opt("a/tools", true), opt("b/plain", false)], "a/tools");
    expect(ok.selectedIsNoTools).toBe(false);
  });
});

describe("modelOptionLabel", () => {
  it("marks a non-tool-capable model", () => {
    expect(modelOptionLabel(opt("x/plain", false))).toBe("x/plain · no tools");
  });

  it("leaves tool-capable and unknown models unmarked", () => {
    expect(modelOptionLabel(opt("x/tool", true))).toBe("x/tool");
    expect(modelOptionLabel(opt("x/unknown", null))).toBe("x/unknown");
  });
});
