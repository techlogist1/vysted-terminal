import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

// `getSidecarBaseUrl` reaches into the Tauri runtime — stub it, same as
// `NodeEditorPanel.test.tsx`. R15-CODE-PLATFORM-017: the live preview now
// posts to the sidecar instead of evaluating with mathjs.
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999"),
}));

import { CodeNodeInspector } from "./code-node-inspector";

const baseConfig = { expression: "a + b", inputs: ["a", "b"] };

/** Build a `Response` whose body streams the given events as `/workflow/run` SSE frames. */
function sseResponse(events: Array<Record<string, unknown>>): Response {
  const body = events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("");
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body));
      controller.close();
    },
  });
  return new Response(stream, { status: 200 });
}

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

/** The two pre-existing "a + b" preview tests stub a real evaluator's answer:
 * a node-output of a+b when both are numeric, else the server's own
 * "Undefined symbol" node-error — exactly what `evaluate_code` produces. */
function stubSumOrUndefined(): void {
  fetchMock.mockImplementation(async (_url: string, init?: RequestInit) => {
    const payload = JSON.parse(String(init?.body)) as { inputs: Record<string, unknown> };
    const { a, b } = payload.inputs;
    if (typeof a === "number" && typeof b === "number") {
      return sseResponse([
        {
          kind: "node-output",
          runId: "r1",
          nodeId: "preview",
          outputs: { value: a + b },
          durationMs: 1,
        },
      ]);
    }
    const missing = typeof a !== "number" ? "a" : "b";
    return sseResponse([
      {
        kind: "node-error",
        runId: "r1",
        nodeId: "preview",
        message: `Undefined symbol ${missing}`,
        durationMs: 1,
      },
    ]);
  });
}

describe("CodeNodeInspector", () => {
  it("renders the expression editor, bindings, and preview zone", () => {
    render(<CodeNodeInspector config={baseConfig} onPatch={() => {}} />);
    expect(screen.getByTestId("code-node-inspector")).toBeInTheDocument();
    expect(screen.getByTestId("code-node-expression")).toHaveValue("a + b");
    expect(screen.getByTestId("code-binding-row-a")).toBeInTheDocument();
    expect(screen.getByTestId("code-binding-row-b")).toBeInTheDocument();
  });

  it("patches the expression on edit", () => {
    const onPatch = vi.fn();
    render(<CodeNodeInspector config={baseConfig} onPatch={onPatch} />);
    fireEvent.change(screen.getByTestId("code-node-expression"), {
      target: { value: "a * b" },
    });
    expect(onPatch).toHaveBeenCalledWith({ expression: "a * b" });
  });

  it("surfaces a parse error inline for a malformed expression", () => {
    render(<CodeNodeInspector config={{ expression: "a +", inputs: ["a"] }} onPatch={() => {}} />);
    expect(screen.getByTestId("code-node-error")).toBeInTheDocument();
  });

  it("flags an empty expression so a no-op node can't slip into a run", () => {
    render(<CodeNodeInspector config={{ expression: "", inputs: ["a"] }} onPatch={() => {}} />);
    expect(screen.getByTestId("code-node-error")).toHaveTextContent(/empty/);
  });

  it("adds the next free binding via the add button", () => {
    const onPatch = vi.fn();
    render(<CodeNodeInspector config={baseConfig} onPatch={onPatch} />);
    fireEvent.click(screen.getByTestId("code-binding-add"));
    expect(onPatch).toHaveBeenCalledWith({ inputs: ["a", "b", "c"] });
  });

  it("removes a binding via its remove button", () => {
    const onPatch = vi.fn();
    render(<CodeNodeInspector config={baseConfig} onPatch={onPatch} />);
    fireEvent.click(screen.getByTestId("code-binding-remove-b"));
    expect(onPatch).toHaveBeenCalledWith({ inputs: ["a"] });
  });

  it("commits a valid rename on blur and rejects an invalid identifier", () => {
    const onPatch = vi.fn();
    render(<CodeNodeInspector config={baseConfig} onPatch={onPatch} />);
    const input = screen.getByLabelText("Input binding a");
    fireEvent.change(input, { target: { value: "price" } });
    fireEvent.blur(input);
    expect(onPatch).toHaveBeenCalledWith({ inputs: ["price", "b"] });

    onPatch.mockClear();
    fireEvent.change(input, { target: { value: "9bad" } });
    fireEvent.blur(input);
    expect(onPatch).not.toHaveBeenCalled();
    expect(screen.getByText(/must not start with a digit/)).toBeInTheDocument();
  });

  it("evaluates the live preview against typed sample values", async () => {
    stubSumOrUndefined();
    render(<CodeNodeInspector config={baseConfig} onPatch={() => {}} />);
    fireEvent.change(screen.getByTestId("code-binding-sample-a"), { target: { value: "2" } });
    fireEvent.change(screen.getByTestId("code-binding-sample-b"), { target: { value: "5" } });
    await waitFor(() => expect(screen.getByTestId("code-node-preview")).toHaveTextContent("= 7"));
  });

  it("shows the honest eval error in the preview when a sample is missing", async () => {
    stubSumOrUndefined();
    render(<CodeNodeInspector config={baseConfig} onPatch={() => {}} />);
    fireEvent.change(screen.getByTestId("code-binding-sample-a"), { target: { value: "2" } });
    await waitFor(() =>
      expect(screen.getByTestId("code-node-preview")).toHaveTextContent(/Undefined symbol b/),
    );
  });
});

describe("CodeNodeInspector preview — server-evaluated, never mathjs (R15-CODE-PLATFORM-017)", () => {
  it("a log() call the server disallows shows its real error, never a mathjs answer", async () => {
    fetchMock.mockImplementation(async () =>
      sseResponse([
        {
          kind: "node-error",
          runId: "r1",
          nodeId: "preview",
          message: "disallowed syntax: Call",
          durationMs: 1,
        },
      ]),
    );
    render(
      <CodeNodeInspector config={{ expression: "log(x, 10)", inputs: ["x"] }} onPatch={() => {}} />,
    );
    fireEvent.change(screen.getByTestId("code-binding-sample-x"), { target: { value: "100" } });
    await waitFor(() =>
      expect(screen.getByTestId("code-node-preview")).toHaveTextContent("disallowed syntax: Call"),
    );
    expect(screen.getByTestId("code-node-preview")).not.toHaveTextContent("= 2");

    const [, init] = fetchMock.mock.calls[0]!;
    const body = JSON.parse(String((init as RequestInit).body)) as {
      spec: { nodes: Array<{ type: string; config: Record<string, unknown> }> };
    };
    expect(body.spec.nodes[0]!.type).toBe("transform.code");
    expect(body.spec.nodes[0]!.config.expression).toBe("log(x, 10)");
  });

  it("round(x, 2) shows the server's float-precision answer, not a rounder mathjs one", async () => {
    fetchMock.mockImplementation(async () =>
      sseResponse([
        {
          kind: "node-output",
          runId: "r1",
          nodeId: "preview",
          outputs: { value: 1 },
          durationMs: 1,
        },
      ]),
    );
    render(
      <CodeNodeInspector
        config={{ expression: "round(x, 2)", inputs: ["x"] }}
        onPatch={() => {}}
      />,
    );
    fireEvent.change(screen.getByTestId("code-binding-sample-x"), { target: { value: "1.005" } });
    await waitFor(() => expect(screen.getByTestId("code-node-preview")).toHaveTextContent("= 1"));
  });

  it("a nested ternary without grouping parens shows the server's parse error", async () => {
    fetchMock.mockImplementation(async () =>
      sseResponse([
        {
          kind: "node-error",
          runId: "r1",
          nodeId: "preview",
          message: "transform.code: parse error: invalid syntax",
          durationMs: 1,
        },
      ]),
    );
    render(
      <CodeNodeInspector
        config={{ expression: "a > b ? a : c > d ? c : d", inputs: ["a", "b", "c", "d"] }}
        onPatch={() => {}}
      />,
    );
    fireEvent.change(screen.getByTestId("code-binding-sample-a"), { target: { value: "1" } });
    fireEvent.change(screen.getByTestId("code-binding-sample-b"), { target: { value: "2" } });
    fireEvent.change(screen.getByTestId("code-binding-sample-c"), { target: { value: "3" } });
    fireEvent.change(screen.getByTestId("code-binding-sample-d"), { target: { value: "4" } });
    await waitFor(() =>
      expect(screen.getByTestId("code-node-preview")).toHaveTextContent(/parse error/),
    );
  });
});
