import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { applyStartLayout, withPanelErrorBoundaries } from "@/components/PanelHost";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useWorkspaceStore } from "@/store/workspace";

const loadWorkspaceMock = vi.hoisted(() => vi.fn(async (_name: string) => undefined));

vi.mock("@/lib/workspace", async () => {
  const actual = await vi.importActual<typeof import("@/lib/workspace")>("@/lib/workspace");
  return { ...actual, loadWorkspace: loadWorkspaceMock };
});

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

/**
 * R15-UI-087 (FR-038): the "Start with" preference. The launch restore has
 * already applied the last session; a named start layout then loads over it
 * through the ordinary layout loader.
 */
describe("start layout", () => {
  const api = {} as Parameters<typeof applyStartLayout>[0];

  beforeEach(() => {
    resetSettingsStoreForTests();
    loadWorkspaceMock.mockReset();
    useWorkspaceStore.setState({ dockviewApi: api } as never);
  });

  it("last session (the default) loads nothing over the restored session", async () => {
    await applyStartLayout(api);
    expect(loadWorkspaceMock).not.toHaveBeenCalled();
  });

  it("a named start layout loads that layout", async () => {
    useSettingsStore.getState().setStartLayout("Morning scan");
    await applyStartLayout(api);
    expect(loadWorkspaceMock).toHaveBeenCalledWith("Morning scan");
  });

  it("a missing start layout keeps the last session and does not throw", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    loadWorkspaceMock.mockRejectedValueOnce(
      new Error('Could not load workspace "Gone" (HTTP 404).'),
    );
    useSettingsStore.getState().setStartLayout("Gone");
    await expect(applyStartLayout(api)).resolves.toBeUndefined();
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining('start layout "Gone" did not load'),
      expect.any(Error),
    );
  });
});
