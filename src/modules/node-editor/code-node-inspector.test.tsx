import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { CodeNodeInspector } from "./code-node-inspector";

afterEach(() => {
  cleanup();
});

const baseConfig = { expression: "a + b", inputs: ["a", "b"] };

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

  it("evaluates the live preview against typed sample values", () => {
    render(<CodeNodeInspector config={baseConfig} onPatch={() => {}} />);
    fireEvent.change(screen.getByTestId("code-binding-sample-a"), { target: { value: "2" } });
    fireEvent.change(screen.getByTestId("code-binding-sample-b"), { target: { value: "5" } });
    expect(screen.getByTestId("code-node-preview")).toHaveTextContent("= 7");
  });

  it("shows the honest eval error in the preview when a sample is missing", () => {
    render(<CodeNodeInspector config={baseConfig} onPatch={() => {}} />);
    fireEvent.change(screen.getByTestId("code-binding-sample-a"), { target: { value: "2" } });
    expect(screen.getByTestId("code-node-preview")).toHaveTextContent(/Undefined symbol b/);
  });
});
