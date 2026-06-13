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
  NODE_CONFIG_FIELDS,
  SIDECAR_NODE_IDS,
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

describe("node-registry: first-party union (code node + sidecar kinds)", () => {
  it("includes every built-in, the code node, and the 12 v0.6.0 sidecar kinds", () => {
    expect(FIRST_PARTY_NODE_IDS).toEqual([...BUILT_IN_NODE_IDS, CODE_NODE_ID, ...SIDECAR_NODE_IDS]);
    expect(FIRST_PARTY_NODE_IDS).toHaveLength(23);
    for (const id of FIRST_PARTY_NODE_IDS) {
      expect(FIRST_PARTY_NODE_SPECS[id]?.id).toBe(id);
    }
  });

  it("mirrors exactly the node ids registry_v0_6_0.py registers server-side", () => {
    // One id per workflow_engine.register_node_type call across
    // macro_nodes / sec_nodes / quant_nodes / research_nodes / screener_nodes.
    expect([...SIDECAR_NODE_IDS].sort()).toEqual(
      [
        "data.fetch_macro_series",
        "data.fetch_sec_filing",
        "data.fetch_insider_transactions",
        "data.fetch_earnings_calendar",
        "data.fetch_earnings_history",
        "data.fetch_analyst_history",
        "data.fetch_price_target_history",
        "quant.price_option",
        "quant.compute_greeks",
        "quant.price_bond",
        "quant.yield_curve",
        "analysis.screener_query",
      ].sort(),
    );
  });

  it("every sidecar spec has a label, a valid category, and at least one output", () => {
    for (const id of SIDECAR_NODE_IDS) {
      const spec = FIRST_PARTY_NODE_SPECS[id];
      expect(spec.label.length).toBeGreaterThan(0);
      expect(["trigger", "action", "transform", "condition", "output"]).toContain(spec.category);
      expect(spec.outputs.length).toBeGreaterThan(0);
    }
  });

  it("quant + screener nodes have NO typed config form (free-form JSON editor)", () => {
    for (const id of [
      "quant.price_option",
      "quant.compute_greeks",
      "quant.price_bond",
      "quant.yield_curve",
      "analysis.screener_query",
    ]) {
      expect(NODE_CONFIG_FIELDS[id]).toBeUndefined();
    }
  });

  it("flat-config sidecar nodes get a typed form with handler-exact keys", () => {
    expect(NODE_CONFIG_FIELDS["data.fetch_macro_series"]?.map((f) => f.key)).toEqual([
      "series_id",
      "provider",
    ]);
    expect(defaultConfigFor("data.fetch_earnings_calendar")).toEqual({ days: 7 });
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
    id: "example.wait-for-decision",
    label: "Wait for Decision",
    category: "trigger",
    inputs: [],
    outputs: [{ id: "decision", label: "Decision", type: "object" }],
    description: "Block until an external source emits a decision event.",
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
      "data.fetch_macro_series",
      "data.fetch_sec_filing",
      "data.fetch_insider_transactions",
      "data.fetch_earnings_calendar",
      "data.fetch_earnings_history",
      "data.fetch_analyst_history",
      "data.fetch_price_target_history",
    ]);
    expect(groups.transform.map((e) => e.spec.id)).toEqual([
      "compute.indicator",
      "transform.json_path",
      "flow.sleep",
      CODE_NODE_ID,
      "quant.price_option",
      "quant.compute_greeks",
      "quant.price_bond",
      "quant.yield_curve",
      "analysis.screener_query",
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
