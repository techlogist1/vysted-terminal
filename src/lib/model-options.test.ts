import { describe, expect, it } from "vitest";

import { buildModelGroups, modelOptionLabel, modelSearchPip } from "@/lib/model-options";
import type { LLMModelOption } from "../../types/ai";

const opt = (id: string, supportsTools?: boolean | null): LLMModelOption => ({
  id,
  label: id,
  supportsTools,
});

const optWithSearch = (
  id: string,
  webSearch: LLMModelOption["webSearch"],
  supportsTools?: boolean | null,
): LLMModelOption => ({ id, label: id, supportsTools, webSearch });

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

  it("appends a filled search pip for native web-search models (WS5)", () => {
    expect(modelOptionLabel(optWithSearch("x/native", "native", true))).toBe("x/native · ⌕");
  });

  it("appends an outline search pip for plugin-available models (WS5)", () => {
    expect(modelOptionLabel(optWithSearch("x/plugin", "plugin", true))).toBe("x/plugin · ⌕?");
  });

  it("omits the search pip for none/unknown models", () => {
    expect(modelOptionLabel(optWithSearch("x/none", "none", true))).toBe("x/none");
    expect(modelOptionLabel(opt("x/unset", true))).toBe("x/unset");
  });

  it("combines the no-tools marker with the search pip", () => {
    expect(modelOptionLabel(optWithSearch("x/both", "native", false))).toBe(
      "x/both · no tools · ⌕",
    );
  });
});

describe("modelSearchPip", () => {
  it("maps each capability to its glyph", () => {
    expect(modelSearchPip(optWithSearch("a", "native"))).toBe(" · ⌕");
    expect(modelSearchPip(optWithSearch("a", "plugin"))).toBe(" · ⌕?");
    expect(modelSearchPip(optWithSearch("a", "none"))).toBe("");
    expect(modelSearchPip(optWithSearch("a", null))).toBe("");
  });
});
