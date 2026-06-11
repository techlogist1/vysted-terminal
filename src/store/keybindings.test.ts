import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_KEYBINDINGS,
  formatBinding,
  matchesEvent,
  normalizeBinding,
  resetKeybindingsStoreForTests,
  useKeybindingsStore,
} from "./keybindings";

/** Build a minimal matchable KeyboardEvent-like object. */
function keyEvent(
  key: string,
  mods: Partial<{ metaKey: boolean; ctrlKey: boolean; altKey: boolean; shiftKey: boolean }> = {},
) {
  return {
    key,
    metaKey: mods.metaKey ?? false,
    ctrlKey: mods.ctrlKey ?? false,
    altKey: mods.altKey ?? false,
    shiftKey: mods.shiftKey ?? false,
  };
}

beforeEach(() => {
  resetKeybindingsStoreForTests();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("bindingFor", () => {
  it("returns the seeded default for a known action", () => {
    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+k");
    expect(useKeybindingsStore.getState().bindingFor("agent.mode.agent")).toBe("alt+1");
    expect(useKeybindingsStore.getState().bindingFor("changes.acceptAll")).toBe("mod+enter");
  });

  it("returns an override over the default", () => {
    useKeybindingsStore.getState().setBinding("palette.open", "mod+p");
    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+p");
  });

  it("normalises an override on the way in", () => {
    useKeybindingsStore.getState().setBinding("palette.open", "K+Mod");
    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+k");
  });

  it("returns empty string for an unknown action", () => {
    expect(useKeybindingsStore.getState().bindingFor("does.not.exist")).toBe("");
  });
});

describe("resetBinding", () => {
  it("reverts an action to its default", () => {
    const store = useKeybindingsStore.getState();
    store.setBinding("palette.open", "mod+p");
    expect(store.bindingFor("palette.open")).toBe("mod+p");
    store.resetBinding("palette.open");
    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+k");
  });

  it("is a no-op for an action with no override", () => {
    const before = useKeybindingsStore.getState().overrides;
    useKeybindingsStore.getState().resetBinding("palette.open");
    expect(useKeybindingsStore.getState().overrides).toEqual(before);
  });
});

describe("setOverrides", () => {
  it("replaces the whole overrides map and normalises entries", () => {
    useKeybindingsStore
      .getState()
      .setOverrides({ "agent.mode.agent": "Mod+P", "platform.save-workspace": "" });
    expect(useKeybindingsStore.getState().bindingFor("agent.mode.agent")).toBe("mod+p");
    // Empty string is dropped, so platform.save-workspace falls back to default.
    expect(useKeybindingsStore.getState().bindingFor("platform.save-workspace")).toBe("mod+s");
  });
});

describe("conflicts", () => {
  it("detects two actions bound to the same combo", () => {
    // Default keymap intentionally has no shell-action collisions; introduce one.
    useKeybindingsStore.getState().setBinding("agent.mode.agent", "mod+k");
    const conflicts = useKeybindingsStore.getState().conflicts();
    const collision = conflicts.find((c) => c.keys === "mod+k");
    expect(collision).toBeDefined();
    expect(collision?.actionIds).toContain("palette.open");
    expect(collision?.actionIds).toContain("agent.mode.agent");
  });

  it("reports no spurious conflicts on the default keymap shell actions", () => {
    const conflicts = useKeybindingsStore.getState().conflicts();
    // palette.open (mod+k) is unique; assert it is not flagged.
    expect(conflicts.some((c) => c.actionIds.includes("palette.open"))).toBe(false);
  });
});

describe("normalizeBinding", () => {
  it("lowercases and orders modifiers before the key", () => {
    expect(normalizeBinding("K+Mod")).toBe("mod+k");
    expect(normalizeBinding("Shift+Alt+P")).toBe("alt+shift+p");
    expect(normalizeBinding("  mod + enter ")).toBe("mod+enter");
  });
});

describe("formatBinding", () => {
  it("renders mod as ⌘ on macOS", () => {
    vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "Mac OS X" });
    expect(formatBinding("mod+k")).toBe("⌘K");
    expect(formatBinding("alt+1")).toBe("⌥1");
    expect(formatBinding("mod+enter")).toBe("⌘↵");
  });

  it("renders mod as Ctrl on non-mac", () => {
    vi.stubGlobal("navigator", { platform: "Win32", userAgent: "Windows NT" });
    expect(formatBinding("mod+k")).toBe("Ctrl+K");
    expect(formatBinding("alt+1")).toBe("Alt+1");
  });

  it("is SSR-safe (no navigator → treats as non-mac)", () => {
    vi.stubGlobal("navigator", undefined);
    expect(formatBinding("mod+k")).toBe("Ctrl+K");
  });
});

describe("DEFAULT_KEYBINDINGS copy budget", () => {
  it("keeps every default description short enough for the settings rows at the gated widths", () => {
    // Settings keybinding row geometry (R9 gate 9: zero truncated text).
    // Inline state (card ≥ 576px; 1280 default = ~590px inner row): ~128px of
    // fixed cluster chrome (Record + reset + gaps + kbd padding) leaves ~58
    // mono-caption chars shared by the description and the formatted combo.
    // Stacked state (catalogued min capture, ~345px inner row): the
    // description gets the full row ≈ 44 mono-caption chars on its own.
    vi.stubGlobal("navigator", { platform: "Win32", userAgent: "Windows NT" });
    for (const [actionId, def] of Object.entries(DEFAULT_KEYBINDINGS)) {
      const combined = def.description.length + formatBinding(def.keys).length;
      expect(combined, `${actionId}: "${def.description}"`).toBeLessThanOrEqual(56);
      expect(def.description.length, `${actionId}: "${def.description}"`).toBeLessThanOrEqual(43);
    }
  });
});

describe("matchesEvent", () => {
  it("matches mod+k as ⌘K on macOS (meta held, not ctrl)", () => {
    vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "Mac OS X" });
    expect(matchesEvent("mod+k", keyEvent("k", { metaKey: true }))).toBe(true);
    expect(matchesEvent("mod+k", keyEvent("k", { ctrlKey: true }))).toBe(false);
  });

  it("matches mod+k as Ctrl+K on non-mac (ctrl held, not meta)", () => {
    vi.stubGlobal("navigator", { platform: "Win32", userAgent: "Windows NT" });
    expect(matchesEvent("mod+k", keyEvent("k", { ctrlKey: true }))).toBe(true);
    expect(matchesEvent("mod+k", keyEvent("k", { metaKey: true }))).toBe(false);
  });

  it("requires the exact modifier set", () => {
    vi.stubGlobal("navigator", { platform: "Win32", userAgent: "Windows NT" });
    // alt also held → does not match a plain ctrl+k combo.
    expect(matchesEvent("mod+k", keyEvent("k", { ctrlKey: true, altKey: true }))).toBe(false);
    expect(matchesEvent("alt+1", keyEvent("1", { altKey: true }))).toBe(true);
  });

  it("returns false for a combo with no key", () => {
    expect(matchesEvent("mod", keyEvent("k", { metaKey: true }))).toBe(false);
    expect(matchesEvent("", keyEvent("k"))).toBe(false);
  });

  it("matches named keys (enter, backspace)", () => {
    vi.stubGlobal("navigator", { platform: "Win32", userAgent: "Windows NT" });
    expect(matchesEvent("mod+enter", keyEvent("Enter", { ctrlKey: true }))).toBe(true);
    expect(matchesEvent("mod+backspace", keyEvent("Backspace", { ctrlKey: true }))).toBe(true);
  });
});
