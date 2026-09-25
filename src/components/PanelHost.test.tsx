import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { applyStartLayout, PanelHost, withPanelErrorBoundaries } from "@/components/PanelHost";
import type { VystedModule } from "@/lib/module-registry";
import { useModulesStore } from "@/store/modules";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useWorkspaceStore } from "@/store/workspace";

const loadWorkspaceMock = vi.hoisted(() => vi.fn(async (_name: string) => undefined));
// The fake dockview api the mocked `DockviewReact` hands to `onReady`.
const dockview = vi.hoisted(() => ({ api: null as unknown }));

vi.mock("@/lib/workspace", async () => {
  const actual = await vi.importActual<typeof import("@/lib/workspace")>("@/lib/workspace");
  return { ...actual, loadWorkspace: loadWorkspaceMock };
});

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763") };
});

vi.mock("dockview", async () => {
  const actual = await vi.importActual<typeof import("dockview")>("dockview");
  function DockviewReact({ onReady }: { onReady: (event: { api: unknown }) => void }) {
    useEffect(() => onReady({ api: dockview.api }), [onReady]);
    return null;
  }
  return { ...actual, DockviewReact };
});

type Listener = () => void;
interface FakePanelJson {
  contentComponent: string;
  width: number;
  height: number;
}

/** Enough of dockview's api for PanelHost's wiring: event emitters, and a
 *  `fromJSON` that materialises each saved panel at its saved size. */
function makeFakeDockview() {
  const listeners = { add: [] as Listener[], fromJSON: [] as Listener[] };
  const on = (list: Listener[]) => (fn: Listener) => {
    list.push(fn);
    return { dispose: () => list.splice(list.indexOf(fn), 1) };
  };
  const noop = () => ({ dispose: () => undefined });
  let panels: { id: string; api: Record<string, unknown> }[] = [];
  const api = {
    width: 1440,
    height: 900,
    get panels() {
      return panels;
    },
    onDidAddPanel: on(listeners.add),
    onDidLayoutFromJSON: on(listeners.fromJSON),
    onDidLayoutChange: noop,
    onDidActivePanelChange: noop,
    fromJSON: vi.fn((layout: { panels: Record<string, FakePanelJson> }) => {
      panels = Object.entries(layout.panels).map(([id, panel]) => ({
        id,
        view: { contentComponent: panel.contentComponent },
        api: {
          component: panel.contentComponent,
          width: panel.width,
          height: panel.height,
          setConstraints: vi.fn(),
          setSize: vi.fn(),
        },
      }));
      listeners.fromJSON.forEach((fn) => fn());
    }),
    toJSON: () => ({}),
    clear: vi.fn(() => {
      panels = [];
    }),
    addPanel: vi.fn(),
    getPanel: (id: string) => panels.find((panel) => panel.id === id),
    removePanel: vi.fn(),
  };
  return api;
}

const chartModule: VystedModule = {
  id: "chart",
  title: "Chart",
  panels: [{ id: "chart", title: "Chart", component: "chart-panel" }],
  commands: [],
  panelComponents: { "chart-panel": () => null },
};

function stubSidecar(autosave: unknown = null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      autosave !== null && String(url).endsWith("/workspace/__autosave__")
        ? ({ ok: true, status: 200, json: async () => autosave } as Response)
        : ({ ok: false, status: 404, json: async () => ({}) } as Response),
    ),
  );
}

/**
 * R15-LIFECYCLE-023: PanelHost hands dockview a component map in which every
 * panel sits behind its own error boundary, so one panel's render throw stays
 * in that panel and its siblings (portfolio, chat) keep rendering.
 */
describe("panel error boundaries", () => {
  it("a throwing panel shows the crash card; a sibling panel still renders; Reload remounts it", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined); // React's own report
    let broken = true;
    const guarded = withPanelErrorBoundaries({
      "news-panel": () => {
        if (broken) {
          throw new Error("feed.items is undefined");
        }
        return <p>News is back</p>;
      },
      "portfolio-panel": () => <p>Portfolio holdings</p>,
    });
    const News = guarded["news-panel"];
    const Portfolio = guarded["portfolio-panel"];

    render(
      <>
        <News />
        <Portfolio />
      </>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("This panel crashed.");
    expect(screen.getByText("feed.items is undefined")).toBeInTheDocument();
    expect(screen.getByText("Portfolio holdings")).toBeInTheDocument();

    broken = false;
    fireEvent.click(screen.getByRole("button", { name: "Reload panel" }));
    expect(screen.getByText("News is back")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

/**
 * R15-UI-087 (FR-038): the "Start with" preference. The launch restore has
 * already applied the last session; a named start layout then loads over it
 * through the ordinary layout loader.
 */
describe("start layout", () => {
  const api = {} as Parameters<typeof applyStartLayout>[0];

  beforeEach(() => {
    resetSettingsStoreForTests();
    loadWorkspaceMock.mockReset();
    useWorkspaceStore.setState({ dockviewApi: api } as never);
  });

  it("last session (the default) loads nothing over the restored session", async () => {
    await applyStartLayout(api);
    expect(loadWorkspaceMock).not.toHaveBeenCalled();
  });

  it("a named start layout loads that layout", async () => {
    useSettingsStore.getState().setStartLayout("Morning scan");
    await applyStartLayout(api);
    expect(loadWorkspaceMock).toHaveBeenCalledWith("Morning scan");
  });

  it("a missing start layout keeps the last session and does not throw", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    loadWorkspaceMock.mockRejectedValueOnce(
      new Error('Could not load workspace "Gone" (HTTP 404).'),
    );
    useSettingsStore.getState().setStartLayout("Gone");
    await expect(applyStartLayout(api)).resolves.toBeUndefined();
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining('start layout "Gone" did not load'),
      expect.any(Error),
    );
  });
});

describe("minimum sizes after fromJSON (R15-CODE-FRONTEND-025)", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useModulesStore.getState().registerModules([chartModule]);
    stubSidecar();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("fromJSON with a sub-minimum panel grows it", async () => {
    const api = makeFakeDockview();
    dockview.api = api;
    render(<PanelHost />);
    // Let the launch restore (no autosave → default layout) and its sweep settle.
    await waitFor(() => expect(api.clear).toHaveBeenCalled());
    await new Promise((resolve) => setTimeout(resolve, 150));

    // A named layout load after boot — not the launch restore.
    api.fromJSON({
      panels: { chart: { contentComponent: "chart-panel", width: 120, height: 500 } },
    });
    const chart = api.getPanel("chart")!.api as { setSize: ReturnType<typeof vi.fn> };
    await waitFor(() => expect(chart.setSize).toHaveBeenCalledWith({ width: 360 }));
    expect(chart.setSize).not.toHaveBeenCalledWith({ height: expect.anything() });
  });
});
