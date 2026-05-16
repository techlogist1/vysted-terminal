/**
 * ScreenerCriteriaBuilder tests — Phase 6 (lead-completed v0.6.1).
 *
 * Exercises the discriminated-union editor: switching category between
 * numeric / string / set replaces the row's shape; numeric operator
 * "between" swaps the single value input for a (min, max) pair.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { useScreenerStore } from "@/store/screener";

import { ScreenerCriteriaBuilder } from "./ScreenerCriteriaBuilder";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ScreenerCriteriaBuilder", () => {
  it("renders the three default-seeded criteria", () => {
    render(<ScreenerCriteriaBuilder />);
    expect(screen.getByTestId("criterion-row-0")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-row-2")).toBeInTheDocument();
  });

  it("Add criterion appends a new row", () => {
    render(<ScreenerCriteriaBuilder />);
    fireEvent.click(screen.getByRole("button", { name: /add criterion/i }));
    expect(screen.getByTestId("criterion-row-3")).toBeInTheDocument();
  });

  it("Trash icon removes the row", () => {
    render(<ScreenerCriteriaBuilder />);
    const removes = screen.getAllByRole("button", { name: /remove criterion/i });
    fireEvent.click(removes[0]!);
    expect(useScreenerStore.getState().criteria).toHaveLength(2);
  });

  it("Switching category from numeric to string replaces the operator + value", () => {
    render(<ScreenerCriteriaBuilder />);
    const row0 = screen.getByTestId("criterion-row-0");
    const category = row0.querySelector('select[aria-label="criterion category"]')!;
    fireEvent.change(category, { target: { value: "string" } });

    expect(useScreenerStore.getState().criteria[0]!.operator).toBe("eq");
  });

  it("Switching operator to 'between' renders min + max inputs", () => {
    render(<ScreenerCriteriaBuilder />);
    const row0 = screen.getByTestId("criterion-row-0");
    const opSelect = row0.querySelector('select[aria-label="numeric operator"]')!;
    fireEvent.change(opSelect, { target: { value: "between" } });

    expect(screen.getByLabelText(/numeric min/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/numeric max/i)).toBeInTheDocument();
  });

  it("Empty criteria list renders a friendly placeholder", () => {
    useScreenerStore.getState().setCriteria([]);
    render(<ScreenerCriteriaBuilder />);
    expect(screen.getByText(/no criteria/i)).toBeInTheDocument();
  });
});
