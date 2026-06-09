import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

import {
  CustomStrategyEditor,
  validateCustomDefinition,
  type CustomValidateResult,
} from "./custom-strategy-editor";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const VALID_RESULT: CustomValidateResult = {
  ok: true,
  errors: [],
  indicators: ["rsi(14)", "sma(20)", "sma(50)"],
  requiredBars: 50,
};

const INVALID_RESULT: CustomValidateResult = {
  ok: false,
  errors: [{ rule: "entry", message: "unknown identifier 'smaa'", position: 8 }],
  indicators: [],
  requiredBars: 0,
};

function jsonResponse(body: CustomValidateResult): Response {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

const fetchMock = vi.fn();

const DEFAULT_VALUES = {
  entry: "sma(20) > sma(50)",
  exit: "rsi(14) > 70",
  position_size: 100,
};

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("validateCustomDefinition", () => {
  it("POSTs the definition to the sidecar validate route", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(VALID_RESULT));
    const result = await validateCustomDefinition({
      entry: "sma(20) > sma(50)",
      exit: "rsi(14) > 70",
      positionSize: 100,
    });
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://127.0.0.1:9000/backtest/strategies/custom/validate");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      entry: "sma(20) > sma(50)",
      exit: "rsi(14) > 70",
      positionSize: 100,
    });
  });

  it("throws on a non-OK response", async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500 } as unknown as Response);
    await expect(
      validateCustomDefinition({ entry: "close > 1", exit: "close < 1" }),
    ).rejects.toThrow("500");
  });
});

describe("CustomStrategyEditor", () => {
  it("renders entry/exit rule editors and position size from values", () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_RESULT));
    render(<CustomStrategyEditor values={DEFAULT_VALUES} onChange={vi.fn()} debounceMs={0} />);
    expect(screen.getByTestId("custom-rule-entry")).toHaveValue("sma(20) > sma(50)");
    expect(screen.getByTestId("custom-rule-exit")).toHaveValue("rsi(14) > 70");
    expect(screen.getByLabelText("position_size")).toHaveValue(100);
  });

  it("shows the indicators + warm-up summary when the definition validates", async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_RESULT));
    const onValidityChange = vi.fn();
    render(
      <CustomStrategyEditor
        values={DEFAULT_VALUES}
        onChange={vi.fn()}
        onValidityChange={onValidityChange}
        debounceMs={0}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("custom-valid-summary")).toHaveTextContent(
        "uses rsi(14), sma(20), sma(50) · needs 50 bars",
      );
    });
    expect(onValidityChange).toHaveBeenLastCalledWith(true);
  });

  it("renders the inline error with caret position and reports invalid", async () => {
    fetchMock.mockResolvedValue(jsonResponse(INVALID_RESULT));
    const onValidityChange = vi.fn();
    render(
      <CustomStrategyEditor
        values={{ ...DEFAULT_VALUES, entry: "close > smaa(20)" }}
        onChange={vi.fn()}
        onValidityChange={onValidityChange}
        debounceMs={0}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("rule-error-entry")).toHaveTextContent(
        "entry: unknown identifier 'smaa' (col 9)",
      );
    });
    // The caret line points at the offending character.
    const caretPre = screen.getByTestId("rule-error-entry").querySelector("pre");
    expect(caretPre?.textContent).toContain("close > smaa(20)");
    expect(caretPre?.textContent?.endsWith(`${" ".repeat(8)}^`)).toBe(true);
    expect(onValidityChange).toHaveBeenLastCalledWith(false);
  });

  it("does not block the run when the validator is unreachable", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const onValidityChange = vi.fn();
    render(
      <CustomStrategyEditor
        values={DEFAULT_VALUES}
        onChange={vi.fn()}
        onValidityChange={onValidityChange}
        debounceMs={0}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("custom-validate-offline")).toBeInTheDocument();
    });
    expect(onValidityChange).toHaveBeenLastCalledWith(true);
  });

  it("bubbles rule edits through onChange", () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_RESULT));
    const onChange = vi.fn();
    render(<CustomStrategyEditor values={DEFAULT_VALUES} onChange={onChange} debounceMs={0} />);
    fireEvent.change(screen.getByTestId("custom-rule-entry"), {
      target: { value: "ema(9) > ema(21)" },
    });
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_VALUES, entry: "ema(9) > ema(21)" });
  });

  it("re-validates after an edit and recovers to valid", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(INVALID_RESULT))
      .mockResolvedValue(jsonResponse(VALID_RESULT));
    const onValidityChange = vi.fn();
    const { rerender } = render(
      <CustomStrategyEditor
        values={{ ...DEFAULT_VALUES, entry: "close > smaa(20)" }}
        onChange={vi.fn()}
        onValidityChange={onValidityChange}
        debounceMs={0}
      />,
    );
    await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(false));
    rerender(
      <CustomStrategyEditor
        values={DEFAULT_VALUES}
        onChange={vi.fn()}
        onValidityChange={onValidityChange}
        debounceMs={0}
      />,
    );
    await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(true));
    expect(screen.queryByTestId("rule-error-entry")).not.toBeInTheDocument();
  });
});
