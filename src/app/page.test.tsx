import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

// CommandPalette uses Radix Dialog which needs a DOM environment — mock it to
// keep the test lightweight and focused on the Welcome panel content.
vi.mock("@/components/CommandPalette", () => ({
  CommandPalette: () => null,
}));

describe("Welcome panel (Page)", () => {
  it("renders the Welcome to Vysted Terminal heading", () => {
    render(<Page />);
    expect(
      screen.getByRole("heading", { name: /welcome to vysted terminal/i, level: 1 }),
    ).toBeInTheDocument();
  });

  it("renders the cmd+K hint text", () => {
    render(<Page />);
    expect(screen.getByText(/open command palette/i)).toBeInTheDocument();
  });
});
