import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
  sidecarGet: vi.fn(),
}));

import {
  applyHostAction,
  describeHostAction,
  HAND_ACTION_INVENTORY,
  HOST_ACTION_NAMES,
} from "@/lib/host-actions";
import { resetAgentAutonomyStoreForTests } from "@/store/agent-autonomy";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import {
  resetProposedChangesStoreForTests,
  useProposedChangesStore,
} from "@/store/proposed-changes";
import { useWorkspaceStore } from "@/store/workspace";

// R15-AGENT-084: every hand action is either agent-drivable or excluded on purpose.
describe("hand-action inventory", () => {
  const rows = Object.entries(HAND_ACTION_INVENTORY);

  it("maps every row to a real host action or an exclusion reason", () => {
    for (const [action, target] of rows) {
      if (typeof target === "string") {
        expect(HOST_ACTION_NAMES.has(target), action).toBe(true);
      } else {
        expect(target.excluded.trim(), action).not.toBe("");
      }
    }
  });

  it("covers every host action", () => {
    const mapped = new Set(
      rows.flatMap(([, target]) => (typeof target === "string" ? [target] : [])),
    );
    expect(mapped).toEqual(HOST_ACTION_NAMES);
  });
});

describe("add_chart_drawing", () => {
  const view = { symbol: "RELIANCE", timeframe: "1d", indicators: [], compare: null };

  beforeEach(() => {
    resetAgentAutonomyStoreForTests();
    resetProposedChangesStoreForTests();
    useChartDrawingsStore.setState({ byPanel: {}, views: { chart: view } });
    const chart = { id: "chart", api: { component: "chart-panel" } };
    useWorkspaceStore.setState({
      dockviewApi: {
        panels: [chart],
        getPanel: (id: string) => (id === "chart" ? chart : undefined),
      },
    } as never);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({}) })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    useWorkspaceStore.setState({ dockviewApi: null } as never);
  });

  it("adds exactly one drawing to the open chart's view", () => {
    const label = applyHostAction("add_chart_drawing", {
      kind: "trendline",
      points: [
        { time: "2026-03-02T00:00:00Z", price: 1210.5 },
        { time: "2026-06-01T00:00:00Z", price: 1450 },
      ],
    });

    expect(label).toBe("Drew a trendline on RELIANCE 1d");
    const drawings = useChartDrawingsStore.getState().getDrawings("chart");
    expect(drawings).toHaveLength(1);
    expect(drawings[0]).toMatchObject({
      panelId: "chart",
      symbol: "RELIANCE",
      timeframe: "1d",
      kind: "trendline",
      points: [
        { time: Date.UTC(2026, 2, 2) / 1000, price: 1210.5 },
        { time: Date.UTC(2026, 5, 1) / 1000, price: 1450 },
      ],
    });
  });

  it("stages for review and a rejected proposal draws nothing", () => {
    const store = useProposedChangesStore.getState();
    const { id } = store.enqueue({
      toolCallId: "t1",
      name: "add_chart_drawing",
      input: { kind: "horizontal-line", points: [{ price: 1450 }] },
      batchId: "b1",
    });
    expect(useProposedChangesStore.getState().changes[0]).toMatchObject({
      kind: "chart",
      status: "pending",
    });

    store.reject(id);

    expect(useChartDrawingsStore.getState().getDrawings("chart")).toHaveLength(0);
  });

  it("refuses honestly when no chart is open or a kind is not agent-drawable", () => {
    useChartDrawingsStore.setState({ views: {} });
    const noChart = { kind: "horizontal-line", points: [{ price: 1450 }] };
    expect(describeHostAction("add_chart_drawing", noChart).after).toMatch(
      /can't apply — no chart is open/,
    );
    expect(applyHostAction("add_chart_drawing", noChart)).toBeNull();

    useChartDrawingsStore.setState({ views: { chart: view } });
    const ellipse = { kind: "ellipse", points: [{ price: 1 }, { price: 2 }] };
    expect(applyHostAction("add_chart_drawing", ellipse)).toBeNull();
    expect(useChartDrawingsStore.getState().getDrawings("chart")).toHaveLength(0);
  });
});
