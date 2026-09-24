import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { withPanelErrorBoundaries } from "@/components/PanelHost";

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
