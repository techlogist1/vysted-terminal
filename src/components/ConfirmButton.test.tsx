import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmButton } from "@/components/ConfirmButton";

// The shared two-step inline confirm (R15-UI-018): first click arms, second
// click (within the window) acts; every destructive-action site in the shell
// (agent builder, workspace dialog, settings, portfolio) routes through this
// one primitive, so its arm/confirm/timeout contract is pinned here once.

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("ConfirmButton", () => {
  it("does not call onConfirm on the first click; arms instead", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmButton onConfirm={onConfirm} aria-label="Delete thing">
        Delete
      </ConfirmButton>,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText("Confirm delete?")).toBeInTheDocument();
  });

  it("calls onConfirm on a second click within the arm window", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmButton onConfirm={onConfirm} aria-label="Delete thing">
        Delete
      </ConfirmButton>,
    );
    const button = screen.getByRole("button");
    fireEvent.click(button);
    fireEvent.click(button);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("disarms after 4s — a click after the window arms again instead of confirming", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmButton onConfirm={onConfirm} aria-label="Delete thing">
        Delete
      </ConfirmButton>,
    );
    const button = screen.getByRole("button");
    fireEvent.click(button);
    act(() => {
      vi.advanceTimersByTime(4001);
    });
    fireEvent.click(button);
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText("Confirm delete?")).toBeInTheDocument();
  });

  it("renders a custom armedLabel while armed", () => {
    render(
      <ConfirmButton onConfirm={vi.fn()} aria-label="Reset" armedLabel="Confirm reset?">
        Reset to default
      </ConfirmButton>,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Confirm reset?")).toBeInTheDocument();
    expect(screen.queryByText("Reset to default")).not.toBeInTheDocument();
  });
});
