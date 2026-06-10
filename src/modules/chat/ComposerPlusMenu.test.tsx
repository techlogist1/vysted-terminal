import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAgentAutonomyStoreForTests, useAgentAutonomyStore } from "@/store/agent-autonomy";

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

const FIRST_PARTY = [
  { id: "copilot", name: "Copilot" },
  { id: "buffett", name: "Warren Buffett" },
];

function renderMenu(overrides: Partial<Parameters<typeof ComposerPlusMenu>[0]> = {}) {
  const props = {
    onInsertMention: vi.fn(),
    onSlashCommands: vi.fn(),
    personaLabel: "Warren Buffett",
    firstParty: FIRST_PARTY,
    custom: [{ id: "my-agent", name: "My Agent" }],
    activeAgentId: "buffett",
    onPersonaChange: vi.fn(),
    mode: "agent" as const,
    onModeChange: vi.fn(),
    ...overrides,
  };
  render(<ComposerPlusMenu {...props} />);
  return props;
}

function openMenu() {
  fireEvent.click(screen.getByRole("button", { name: /insert context/i }));
}

describe("ComposerPlusMenu", () => {
  beforeEach(() => {
    resetAgentAutonomyStoreForTests();
  });

  afterEach(() => {
    cleanup();
  });

  it("opens the anchored menu and inserts the picked mention through the shared path", () => {
    const props = renderMenu();
    openMenu();
    expect(screen.getByRole("menu", { name: /composer menu/i })).toBeInTheDocument();
    // mouseDown (not click) so the composer keeps focus — mirror the real event.
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /@chart/i }));
    expect(props.onInsertMention).toHaveBeenCalledTimes(1);
    expect((props.onInsertMention as ReturnType<typeof vi.fn>).mock.calls[0][0].token).toBe(
      "@chart",
    );
    // Picking closes the menu.
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("the Slash commands row primes the `/` picker instead of inserting a mention", () => {
    const props = renderMenu();
    openMenu();
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /slash commands/i }));
    expect(props.onSlashCommands).toHaveBeenCalledTimes(1);
    expect(props.onInsertMention).not.toHaveBeenCalled();
  });

  it("the Persona row shows the DISPLAY NAME and drills into the roster", () => {
    const props = renderMenu();
    openMenu();
    const personaRow = screen.getByRole("menuitem", { name: /persona — warren buffett/i });
    expect(personaRow.textContent).toContain("Warren Buffett");
    fireEvent.mouseDown(personaRow);
    // Drill view: first-party + custom rosters, concierge (copilot) first.
    const rows = screen.getAllByRole("menuitemradio").map((el) => el.textContent);
    expect(rows[0]).toContain("Copilot");
    expect(screen.getByRole("menuitemradio", { name: /my agent/i })).toBeInTheDocument();
    // The active persona is checked; picking another switches and closes.
    expect(screen.getByRole("menuitemradio", { name: /warren buffett/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.mouseDown(screen.getByRole("menuitemradio", { name: /copilot/i }));
    expect(props.onPersonaChange).toHaveBeenCalledWith("copilot");
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("the Autonomy rows flip ASK/AUTO without closing the menu (it's a mode)", () => {
    renderMenu();
    openMenu();
    expect(screen.getByRole("menuitemradio", { name: /^ASK/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.mouseDown(screen.getByRole("menuitemradio", { name: /^AUTO/ }));
    expect(useAgentAutonomyStore.getState().autonomy).toBe("auto");
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitemradio", { name: /^AUTO/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("the Mode rows switch Agent ↔ Delegate", () => {
    const props = renderMenu();
    openMenu();
    expect(screen.getByRole("menuitemradio", { name: /agent \(/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.mouseDown(screen.getByRole("menuitemradio", { name: /delegate/i }));
    expect(props.onModeChange).toHaveBeenCalledWith("delegate");
  });

  it("Escape dismisses the menu; reopening lands back on the root view", () => {
    renderMenu();
    openMenu();
    fireEvent.mouseDown(screen.getByRole("menuitem", { name: /persona/i }));
    expect(screen.getByRole("menuitem", { name: /back/i })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).toBeNull();
    openMenu();
    // Root view again — the persona drill state does not leak across opens.
    expect(screen.getByRole("menuitem", { name: /persona/i })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /back/i })).toBeNull();
  });
});
