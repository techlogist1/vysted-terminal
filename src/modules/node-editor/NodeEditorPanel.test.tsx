import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { usePluginsStore } from "@/store/plugins";

import { NodeEditorPanel } from "./NodeEditorPanel";

// `getSidecarBaseUrl` reaches into the Tauri runtime — stub it.
vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999"),
  };
});

// react-flow renders an SVG canvas; jsdom doesn't implement layout APIs it
// needs (`ResizeObserver`, `getBoundingClientRect` for the pane). We stub
// just enough so the component mounts. The drop / connect interactions
// are not exercised in these tests — those need real events (Playwright).
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Global `fetch` mock — each test seeds the responses it expects.
const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
  vi.stubGlobal("DOMMatrixReadOnly", class {});
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => new Response("{}", { status: 200 }));
  usePluginsStore.setState({
    plugins: [],
    dataSources: [],
    agents: [],
    nodes: [],
    runtime: null,
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("NodeEditorPanel", () => {
  it("renders the toolbar, palette, properties panel, and canvas", () => {
    render(<NodeEditorPanel />);
    expect(screen.getByTestId("node-editor-panel")).toBeInTheDocument();
    expect(screen.getByTestId("node-palette")).toBeInTheDocument();
    expect(screen.getByTestId("properties-panel")).toBeInTheDocument();
    // Toolbar buttons.
    expect(screen.getByRole("button", { name: "New" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("disables the Run button when the canvas is empty", () => {
    render(<NodeEditorPanel />);
    expect(screen.getByRole("button", { name: "Run" })).toBeDisabled();
  });

  it("opens the save dialog when the Save button is clicked", async () => {
    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByTestId("workflow-save-dialog")).toBeInTheDocument();
    expect(screen.getByText("Save workflow")).toBeInTheDocument();
  });

  it("POSTs /workflow/save with a WorkflowSpec when the dialog form submits", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/workflow/save") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as {
          id: string;
          name: string;
          nodes: unknown[];
          edges: unknown[];
        };
        expect(body.name).toBe("My workflow");
        expect(body.nodes).toEqual([]);
        expect(body.edges).toEqual([]);
        return new Response(JSON.stringify({ ...body, updatedAt: 1 }), { status: 200 });
      }
      return new Response("{}", { status: 200 });
    });

    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    const dialog = await screen.findByTestId("workflow-save-dialog");
    fireEvent.change(within(dialog).getByLabelText("Workflow name"), {
      target: { value: "My workflow" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(dialog).not.toBeInTheDocument();
    });
  });

  it("opens the Load dialog and lists summaries returned by /workflow/saved", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (input.toString().endsWith("/workflow/saved")) {
        return new Response(
          JSON.stringify({
            workflows: [
              {
                id: "wf-a",
                name: "Research: AAPL",
                description: "fetch + indicator + log",
                version: 1,
                nodes: [],
                edges: [],
                updatedAt: 10,
              },
              {
                id: "wf-b",
                name: "Research: MSFT",
                version: 1,
                nodes: [],
                edges: [],
                updatedAt: 20,
              },
            ],
          }),
          { status: 200 },
        );
      }
      return new Response("{}", { status: 200 });
    });

    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    expect(await screen.findByText("Load workflow")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Research: AAPL")).toBeInTheDocument();
      expect(screen.getByText("Research: MSFT")).toBeInTheDocument();
    });
  });

  it("surfaces an error message when /workflow/save returns a non-2xx", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (input.toString().endsWith("/workflow/save") && init?.method === "POST") {
        return new Response("nope", { status: 500 });
      }
      return new Response("{}", { status: 200 });
    });
    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    const dialog = await screen.findByTestId("workflow-save-dialog");
    fireEvent.change(within(dialog).getByLabelText("Workflow name"), {
      target: { value: "fail-case" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(within(dialog).getByText(/save failed/i)).toBeInTheDocument();
    });
  });

  it("plugin-contributed nodes from usePluginsStore.nodes appear in the palette", async () => {
    await act(async () => {
      usePluginsStore.setState({
        plugins: [],
        dataSources: [],
        agents: [],
        nodes: [
          {
            id: "tradesa.wait-for-decision",
            label: "Wait for Decision",
            category: "trigger",
            inputs: [],
            outputs: [{ id: "out", label: "Decision", type: "object" }],
          },
        ],
        runtime: null,
      });
    });
    render(<NodeEditorPanel />);
    expect(screen.getByTestId("palette-card-tradesa.wait-for-decision")).toBeInTheDocument();
  });
});
