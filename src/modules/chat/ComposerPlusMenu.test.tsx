import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildPlusMenuSections, ComposerPlusMenu } from "./ComposerPlusMenu";
import { STATIC_MENTIONS } from "./mentions";

describe("buildPlusMenuSections", () => {
  it("derives Context / Scope / Route to sections from the mention catalog", () => {
    const sections = buildPlusMenuSections();
    expect(sections.map((s) => s.title)).toEqual(["Context", "Scope", "Route to"]);
    expect(sections[0].items.map((m) => m.token)).toEqual([
      "@chart",
      "@news",
      "@filings",
      "@terminal",
    ]);
    expect(sections[1].items.map((m) => m.token)).toEqual(["@watchlist", "@portfolio"]);
    expect(sections[2].items.map((m) => m.token)).toEqual(["@analyst", "@quant"]);
  });

  it("covers every static mention exactly once (the catalog is the source of truth)", () => {
    const flattened = buildPlusMenuSections().flatMap((s) => s.items.map((m) => m.token));
    expect(flattened.sort()).toEqual(STATIC_MENTIONS.map((m) => m.token).sort());
  });

  it("drops an empty section rather than rendering a bare header", () => {
    const surfacesOnly = STATIC_MENTIONS.filter((m) => m.kind === "surface");
    const sections = buildPlusMenuSections(surfacesOnly);
    expect(sections.map((s) => s.title)).toEqual(["Context"]);
  });
});

describe("ComposerPlusMenu", () => {
  afterEach(() => {
    cleanup();
  });

  it("opens the anchored menu and inserts the picked mention through the shared path", () => {
    const onInsertMention = vi.fn();
    const onSlashCommands = vi.fn();
    render(
      <ComposerPlusMenu onInsertMention={onInsertMention} onSlashCommands={onSlashCommands} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    expect(screen.getByRole("menu", { name: /insert into the composer/i })).toBeInTheDocument();
    // mouseDown (not click) so the composer keeps focus — mirror the real event.
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /@chart/i }));
    expect(onInsertMention).toHaveBeenCalledTimes(1);
    expect(onInsertMention.mock.calls[0][0].token).toBe("@chart");
    // Picking closes the menu.
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("the Slash commands row primes the `/` picker instead of inserting a mention", () => {
    const onInsertMention = vi.fn();
    const onSlashCommands = vi.fn();
    render(
      <ComposerPlusMenu onInsertMention={onInsertMention} onSlashCommands={onSlashCommands} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /slash commands/i }));
    expect(onSlashCommands).toHaveBeenCalledTimes(1);
    expect(onInsertMention).not.toHaveBeenCalled();
  });

  it("Escape dismisses the menu", () => {
    render(<ComposerPlusMenu onInsertMention={vi.fn()} onSlashCommands={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).toBeNull();
  });
});
