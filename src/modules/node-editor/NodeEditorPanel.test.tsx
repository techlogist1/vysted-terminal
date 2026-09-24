import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { usePluginsStore } from "@/store/plugins";
import { useWorkflowStore } from "@/store/workflow";

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

// R15-CODE-PLATFORM-017: spy on the mathjs evaluator while keeping every
// other export (compileCodeExpression, the constants) real, so a run test
// can assert it is NEVER called — the server is the only evaluator now.
const evaluateCodeExpressionSpy = vi.fn();
vi.mock("./code-node", async () => {
  const actual = await vi.importActual<typeof import("./code-node")>("./code-node");
  return {
    ...actual,
    evaluateCodeExpression: (...args: Parameters<typeof actual.evaluateCodeExpression>) => {
      evaluateCodeExpressionSpy(...args);
      return actual.evaluateCodeExpression(...args);
    },
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
  evaluateCodeExpressionSpy.mockReset();
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
            unreadable: [],
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

  it("lists an unreadable saved row as not openable by this version", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (input.toString().endsWith("/workflow/saved")) {
        return new Response(
          JSON.stringify({
            workflows: [],
            unreadable: [{ id: "wf-old", name: "Old flow", reason: "extra inputs" }],
          }),
          { status: 200 },
        );
      }
      return new Response("{}", { status: 200 });
    });

    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    const row = await screen.findByTestId("unreadable-workflow-wf-old");
    expect(within(row).getByText("Old flow")).toBeInTheDocument();
    expect(within(row).getByText("Can't be opened by this version")).toBeInTheDocument();
    expect(within(row).queryByRole("button")).toBeNull();
    expect(screen.queryByText("No saved workflows yet.")).toBeNull();
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

  // --- Run lifecycle vs. the SSE stream -------------------------------------
  // The engine validates BEFORE emitting run-start and the router swallows
  // the exception, so a rejected spec closes the stream with ZERO frames.
  // These tests load a one-server-node workflow, click Run against a seeded
  // stream, and assert the overlay's final verdict is honest.

  const serverNodeSpec = {
    id: "wf-run",
    name: "Run target",
    version: 1,
    updatedAt: 10,
    nodes: [{ id: "n1", type: "data.fetch_quote", position: { x: 0, y: 0 }, config: {} }],
    edges: [],
  };

  function sseResponse(frames: ReadonlyArray<Record<string, unknown>>): Response {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(controllerArg) {
        for (const frame of frames) {
          controllerArg.enqueue(encoder.encode(`data: ${JSON.stringify(frame)}\n\n`));
        }
        controllerArg.close();
      },
    });
    return new Response(body, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  }

  async function loadWorkflowAndRun(runFrames: ReadonlyArray<Record<string, unknown>>) {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/workflow/saved")) {
        return new Response(JSON.stringify({ workflows: [serverNodeSpec], unreadable: [] }), {
          status: 200,
        });
      }
      if (url.endsWith("/workflow/saved/wf-run")) {
        return new Response(JSON.stringify(serverNodeSpec), { status: 200 });
      }
      if (url.endsWith("/workflow/run") && init?.method === "POST") {
        return sseResponse(runFrames);
      }
      return new Response("{}", { status: 200 });
    });

    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    fireEvent.click(await screen.findByText("Run target"));
    const runButton = screen.getByRole("button", { name: "Run" });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);
  }

  it("reports run-error, not a false ok, when the run stream closes with zero frames", async () => {
    await loadWorkflowAndRun([]);
    expect(await screen.findByTestId("run-status-error")).toBeInTheDocument();
    expect(screen.getByText(/ended without a terminal frame/)).toBeInTheDocument();
    expect(screen.queryByTestId("run-status-ok")).not.toBeInTheDocument();
  });

  it("reports run-error when the stream dies after run-start with no terminal frame", async () => {
    await loadWorkflowAndRun([
      { kind: "run-start", runId: "run-1", startedAt: 1 },
      {
        kind: "node-start",
        runId: "run-1",
        nodeId: "n1",
        nodeType: "data.fetch_quote",
        startedAt: 1,
      },
    ]);
    expect(await screen.findByTestId("run-status-error")).toBeInTheDocument();
    expect(screen.getByText(/ended without a terminal frame/)).toBeInTheDocument();
  });

  it("still reports ok when the stream ends with a proper run-complete frame", async () => {
    await loadWorkflowAndRun([
      { kind: "run-start", runId: "run-1", startedAt: 1 },
      {
        kind: "node-start",
        runId: "run-1",
        nodeId: "n1",
        nodeType: "data.fetch_quote",
        startedAt: 1,
      },
      {
        kind: "node-output",
        runId: "run-1",
        nodeId: "n1",
        outputs: { quote: { price: 1 } },
        durationMs: 2,
      },
      { kind: "run-complete", runId: "run-1", durationMs: 3 },
    ]);
    expect(await screen.findByTestId("run-status-ok")).toBeInTheDocument();
  });

  it("surfaces a server run-error message even when no node-error frames arrived", async () => {
    await loadWorkflowAndRun([
      { kind: "run-start", runId: "run-1", startedAt: 1 },
      { kind: "run-error", runId: "run-1", message: "engine-level failure", durationMs: 2 },
    ]);
    expect(await screen.findByTestId("run-status-error")).toBeInTheDocument();
    expect(screen.getByText("engine-level failure")).toBeInTheDocument();
  });

  it("a notify_desktop intent in the run stream reaches the desktop-notification queue", async () => {
    useWorkflowStore.getState().clearAll();
    await loadWorkflowAndRun([
      { kind: "run-start", runId: "run-n", startedAt: 1 },
      {
        kind: "node-output",
        runId: "run-n",
        nodeId: "n1",
        outputs: {
          notified: true,
          title: "Workflow",
          message: "AAPL crossed 200",
          intent: "desktop-notification",
        },
        durationMs: 1,
      },
      { kind: "run-complete", runId: "run-n", durationMs: 2 },
    ]);
    await screen.findByTestId("run-status-ok");
    expect(useWorkflowStore.getState().pendingNotifications).toMatchObject([
      { runId: "run-n", nodeId: "n1", message: "AAPL crossed 200" },
    ]);
  });

  it("a stream that breaks mid-run renders run-error and ends the run log in run-error", async () => {
    const encoder = new TextEncoder();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/workflow/saved")) {
        return new Response(JSON.stringify({ workflows: [serverNodeSpec], unreadable: [] }), {
          status: 200,
        });
      }
      if (url.endsWith("/workflow/saved/wf-run")) {
        return new Response(JSON.stringify(serverNodeSpec), { status: 200 });
      }
      if (url.endsWith("/workflow/run") && init?.method === "POST") {
        // First read yields run-start; the next read fails (connection reset).
        let pulls = 0;
        const body = new ReadableStream<Uint8Array>({
          pull(c) {
            pulls += 1;
            if (pulls === 1) {
              const frame = { kind: "run-start", runId: "run-x", startedAt: 1 };
              c.enqueue(encoder.encode(`data: ${JSON.stringify(frame)}\n\n`));
            } else {
              c.error(new Error("connection reset"));
            }
          },
        });
        return new Response(body, { status: 200 });
      }
      return new Response("{}", { status: 200 });
    });
    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    fireEvent.click(await screen.findByText("Run target"));
    const runButton = screen.getByRole("button", { name: "Run" });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);
    expect(await screen.findByTestId("run-status-error")).toBeInTheDocument();
    expect(screen.queryByTestId("run-status-ok")).not.toBeInTheDocument();
    expect(useWorkflowStore.getState().runs["run-x"]?.at(-1)).toMatchObject({
      kind: "run-error",
      message: expect.stringContaining("connection reset"),
    });
  });

  it("sends the chat's provider and model selection with the run for agent nodes", async () => {
    await loadWorkflowAndRun([
      { kind: "run-start", runId: "run-1", startedAt: 1 },
      { kind: "run-complete", runId: "run-1", durationMs: 3 },
    ]);
    await screen.findByTestId("run-status-ok");
    const runCall = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/workflow/run"));
    const body = JSON.parse(String(runCall?.[1]?.body)) as Record<string, unknown>;
    const provider = useLLMProvidersStore.getState().defaultProviderId;
    expect(body).toMatchObject({
      provider,
      model: useModelSelectionStore.getState().modelFor(provider),
    });
  });

  it("sends a code node in the FULL spec to /workflow/run and never evaluates it with mathjs (R15-CODE-PLATFORM-017)", async () => {
    const codeSpec = {
      id: "wf-code",
      name: "Code target",
      version: 1,
      updatedAt: 10,
      nodes: [
        {
          id: "c1",
          type: "transform.code",
          position: { x: 0, y: 0 },
          config: { expression: "round(2.5)", inputs: [] },
        },
      ],
      edges: [],
    };
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/workflow/saved")) {
        return new Response(JSON.stringify({ workflows: [codeSpec], unreadable: [] }), {
          status: 200,
        });
      }
      if (url.endsWith("/workflow/saved/wf-code")) {
        return new Response(JSON.stringify(codeSpec), { status: 200 });
      }
      if (url.endsWith("/workflow/run") && init?.method === "POST") {
        // The server (Python ast, `code_node.py`) is the one that computes
        // this — 3 (round-half-away-from-zero), never a locally-run mathjs
        // value.
        return sseResponse([
          { kind: "run-start", runId: "run-c", startedAt: 1 },
          {
            kind: "node-output",
            runId: "run-c",
            nodeId: "c1",
            outputs: { value: 3 },
            durationMs: 1,
          },
          { kind: "run-complete", runId: "run-c", durationMs: 2 },
        ]);
      }
      return new Response("{}", { status: 200 });
    });

    render(<NodeEditorPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    fireEvent.click(await screen.findByText("Code target"));
    const runButton = screen.getByRole("button", { name: "Run" });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);

    await screen.findByTestId("run-status-ok");
    const runCall = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/workflow/run"));
    const body = JSON.parse(String(runCall?.[1]?.body)) as {
      spec?: { nodes?: Array<{ type: string }> };
    };
    const sentNodeTypes = (body.spec?.nodes ?? []).map((n) => n.type);
    expect(sentNodeTypes).toContain("transform.code");
    expect(evaluateCodeExpressionSpy).not.toHaveBeenCalled();
  });

  it("plugin-contributed nodes from usePluginsStore.nodes appear in the palette", async () => {
    await act(async () => {
      usePluginsStore.setState({
        plugins: [],
        dataSources: [],
        agents: [],
        nodes: [
          {
            id: "example.wait-for-decision",
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
    expect(screen.getByTestId("palette-card-example.wait-for-decision")).toBeInTheDocument();
  });
});
