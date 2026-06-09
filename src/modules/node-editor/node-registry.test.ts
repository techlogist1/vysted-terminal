import { describe, expect, it } from "vitest";

import type { NodeSpec } from "../../../types/plugin";
import { CODE_NODE_ID } from "./code-node";
import {
  BUILT_IN_NODE_CONFIG_FIELDS,
  BUILT_IN_NODE_IDS,
  BUILT_IN_NODE_SPECS,
  CODE_NODE_SPEC,
  FIRST_PARTY_NODE_IDS,
  FIRST_PARTY_NODE_SPECS,
  buildRegistry,
  defaultConfigFor,
  findEntry,
  firstPartyEntries,
  groupByCategory,
} from "./node-registry";

describe("node-registry: built-in specs", () => {
  it("ships exactly the 10 documented built-in node ids", () => {
    expect(BUILT_IN_NODE_IDS).toEqual([
      "data.fetch_quote",
      "data.fetch_history",
      "compute.indicator",
      "ai.agent_invoke",
      "logic.branch",
      "logic.compare",
      "action.log",
      "action.notify_desktop",
      "transform.json_path",
      "flow.sleep",
    ]);
  });

  it("every built-in id has a matching NodeSpec with a non-empty label", () => {
    for (const id of BUILT_IN_NODE_IDS) {
      const spec = BUILT_IN_NODE_SPECS[id];
      expect(spec.id).toBe(id);
      expect(spec.label.length).toBeGreaterThan(0);
      expect(["trigger", "action", "transform", "condition", "output"]).toContain(spec.category);
    }
  });

  it("every built-in id has a config-field schema entry", () => {
    for (const id of BUILT_IN_NODE_IDS) {
      const fields = BUILT_IN_NODE_CONFIG_FIELDS[id];
      expect(fields).toBeDefined();
    }
  });

  it("defaultConfigFor returns declared defaults for built-in nodes", () => {
    const cfg = defaultConfigFor("flow.sleep");
    expect(cfg).toEqual({ duration_ms: 1000 });
    const indicator = defaultConfigFor("compute.indicator");
    expect(indicator).toEqual({ indicator: "rsi", period: 14 });
  });

  it("defaultConfigFor returns {} for unknown / plugin node types", () => {
    expect(defaultConfigFor("plugin.something")).toEqual({});
  });
});

describe("node-registry: first-party union (code node)", () => {
  it("includes every built-in plus the code node", () => {
    expect(FIRST_PARTY_NODE_IDS).toEqual([...BUILT_IN_NODE_IDS, CODE_NODE_ID]);
    for (const id of FIRST_PARTY_NODE_IDS) {
      expect(FIRST_PARTY_NODE_SPECS[id]?.id).toBe(id);
    }
  });

  it("ships the code node as a transform with one value output", () => {
    expect(CODE_NODE_SPEC.category).toBe("transform");
    expect(CODE_NODE_SPEC.outputs).toEqual([{ id: "value", label: "Value", type: "any" }]);
  });

  it("defaultConfigFor the code node returns a runnable serializable spec", () => {
    const cfg = defaultConfigFor(CODE_NODE_ID);
    expect(cfg).toEqual({ expression: "a + b", inputs: ["a", "b"] });
    // Mutating the returned config must not leak into the next drop.
    (cfg["inputs"] as string[]).push("mutated");
    expect(defaultConfigFor(CODE_NODE_ID)).toEqual({ expression: "a + b", inputs: ["a", "b"] });
  });
});

describe("node-registry: buildRegistry", () => {
  const pluginNode: NodeSpec = {
    id: "tradesa.wait-for-decision",
    label: "Wait for Decision",
    category: "trigger",
    inputs: [],
    outputs: [{ id: "decision", label: "Decision", type: "object" }],
    description: "Block until Tradesa emits a decision event.",
  };

  it("returns every first-party node when there are no plugins", () => {
    const registry = buildRegistry([]);
    expect(registry).toHaveLength(FIRST_PARTY_NODE_IDS.length);
    expect(registry.every((e) => e.source === "built-in")).toBe(true);
  });

  it("appends plugin-contributed specs as source='plugin'", () => {
    const registry = buildRegistry([pluginNode]);
    expect(registry).toHaveLength(FIRST_PARTY_NODE_IDS.length + 1);
    const found = findEntry(registry, pluginNode.id);
    expect(found?.source).toBe("plugin");
    expect(found?.spec).toBe(pluginNode);
  });

  it("drops plugin specs whose id collides with a first-party id (first-party wins)", () => {
    const collisionPlugin: NodeSpec = {
      ...pluginNode,
      id: "data.fetch_quote",
    };
    const registry = buildRegistry([collisionPlugin]);
    expect(registry).toHaveLength(FIRST_PARTY_NODE_IDS.length);
    const entry = findEntry(registry, "data.fetch_quote");
    expect(entry?.source).toBe("built-in");
  });
});

describe("node-registry: groupByCategory", () => {
  it("partitions first-party entries into the contract's five categories", () => {
    const groups = groupByCategory(firstPartyEntries());
    expect(groups.trigger.map((e) => e.spec.id)).toEqual([
      "data.fetch_quote",
      "data.fetch_history",
    ]);
    expect(groups.transform.map((e) => e.spec.id)).toEqual([
      "compute.indicator",
      "transform.json_path",
      "flow.sleep",
      CODE_NODE_ID,
    ]);
    expect(groups.condition.map((e) => e.spec.id)).toEqual(["logic.branch", "logic.compare"]);
    expect(groups.action.map((e) => e.spec.id)).toEqual([
      "ai.agent_invoke",
      "action.log",
      "action.notify_desktop",
    ]);
    expect(groups.output).toEqual([]);
  });
});
