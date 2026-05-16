import { describe, expect, it } from "vitest";

import type { NodeSpec } from "../../../types/plugin";
import {
  BUILT_IN_NODE_CONFIG_FIELDS,
  BUILT_IN_NODE_IDS,
  BUILT_IN_NODE_SPECS,
  buildRegistry,
  builtInEntries,
  defaultConfigFor,
  findEntry,
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

describe("node-registry: buildRegistry", () => {
  const pluginNode: NodeSpec = {
    id: "tradesa.wait-for-decision",
    label: "Wait for Decision",
    category: "trigger",
    inputs: [],
    outputs: [{ id: "decision", label: "Decision", type: "object" }],
    description: "Block until Tradesa emits a decision event.",
  };

  it("returns the 10 built-ins when there are no plugins", () => {
    const registry = buildRegistry([]);
    expect(registry).toHaveLength(BUILT_IN_NODE_IDS.length);
    expect(registry.every((e) => e.source === "built-in")).toBe(true);
  });

  it("appends plugin-contributed specs as source='plugin'", () => {
    const registry = buildRegistry([pluginNode]);
    expect(registry).toHaveLength(BUILT_IN_NODE_IDS.length + 1);
    const found = findEntry(registry, pluginNode.id);
    expect(found?.source).toBe("plugin");
    expect(found?.spec).toBe(pluginNode);
  });

  it("drops plugin specs whose id collides with a built-in (built-in wins)", () => {
    const collisionPlugin: NodeSpec = {
      ...pluginNode,
      id: "data.fetch_quote",
    };
    const registry = buildRegistry([collisionPlugin]);
    expect(registry).toHaveLength(BUILT_IN_NODE_IDS.length);
    const entry = findEntry(registry, "data.fetch_quote");
    expect(entry?.source).toBe("built-in");
  });
});

describe("node-registry: groupByCategory", () => {
  it("partitions built-in entries into the contract's five categories", () => {
    const groups = groupByCategory(builtInEntries());
    expect(groups.trigger.map((e) => e.spec.id)).toEqual([
      "data.fetch_quote",
      "data.fetch_history",
    ]);
    expect(groups.transform.map((e) => e.spec.id)).toEqual([
      "compute.indicator",
      "transform.json_path",
      "flow.sleep",
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
