import { fireEvent, render, screen } from "@testing-library/react";
import { Inbox } from "lucide-react";
import { describe, expect, it, vi } from "vitest";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders the icon, headline, and hint", () => {
    render(<EmptyState icon={Inbox} headline="No ratings history" hint="Ratings appear here." />);
    expect(screen.getByTestId("empty-state-icon")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-headline")).toHaveTextContent("No ratings history");
    expect(screen.getByTestId("empty-state-hint")).toHaveTextContent("Ratings appear here.");
  });

  it("renders the headline in the secondary-bright tier (charcoal-200, panel-title)", () => {
    render(<EmptyState icon={Inbox} headline="Empty" />);
    const headline = screen.getByTestId("empty-state-headline");
    expect(headline.className).toContain("text-charcoal-200");
    expect(headline.className).toContain("text-panel-title");
  });

  it("omits the hint when none is given", () => {
    render(<EmptyState icon={Inbox} headline="Empty" />);
    expect(screen.queryByTestId("empty-state-hint")).toBeNull();
  });

  it("omits the CTA by default", () => {
    render(<EmptyState icon={Inbox} headline="Empty" />);
    expect(screen.queryByTestId("empty-state-cta")).toBeNull();
  });

  it("renders a CTA and fires onClick", () => {
    const onClick = vi.fn();
    render(
      <EmptyState icon={Inbox} headline="No brokers" cta={{ label: "Connect broker", onClick }} />,
    );
    const cta = screen.getByTestId("empty-state-cta");
    expect(cta).toHaveTextContent("Connect broker");
    fireEvent.click(cta);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("lifts a primary CTA to the brighter neutral outline", () => {
    render(
      <EmptyState
        icon={Inbox}
        headline="No brokers"
        cta={{ label: "Connect broker", onClick: () => {}, primary: true }}
      />,
    );
    const cta = screen.getByTestId("empty-state-cta");
    expect(cta.className).toContain("text-charcoal-100");
  });

  it("R15-UI-066: variant 'error' renders role=alert and a distinct icon", () => {
    const { rerender } = render(<EmptyState icon={Inbox} headline="No mail" />);
    const emptyIcon = screen.getByTestId("empty-state-icon");
    expect(screen.getByTestId("empty-state")).not.toHaveAttribute("role", "alert");
    const emptyIconClass = emptyIcon.getAttribute("class");

    rerender(<EmptyState icon={Inbox} headline="Could not load mail" variant="error" />);
    expect(screen.getByTestId("empty-state")).toHaveAttribute("role", "alert");
    const errorIcon = screen.getByTestId("empty-state-icon");
    // The caller passed the same `icon={Inbox}` for both — the icon must
    // still read as distinct (a negative tint at minimum), not the same
    // lucide icon in the same tone as the empty state.
    expect(errorIcon.getAttribute("class")).not.toBe(emptyIconClass);
    expect(errorIcon.getAttribute("class")).toContain("text-negative");
  });
});
