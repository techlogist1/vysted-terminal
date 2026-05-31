import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

import { autosaveLayout } from "@/lib/workspace";
import {
  DEFAULT_SETTINGS,
  resetSettingsStoreForTests,
  settingsBundle,
  useSettingsStore,
} from "@/store/settings";

const autosaveMock = vi.mocked(autosaveLayout);

describe("settings store", () => {
  beforeEach(() => {
    resetSettingsStoreForTests();
    autosaveMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("seeds from the default bundle", () => {
    const s = useSettingsStore.getState();
    expect(s.defaultAgentId).toBe(DEFAULT_SETTINGS.defaultAgentId);
    expect(s.providerPreferenceOrder).toEqual(DEFAULT_SETTINGS.providerPreferenceOrder);
    expect(s.paletteRecentsEnabled).toBe(true);
    expect(s.starterCockpitPanelIds).toEqual(DEFAULT_SETTINGS.starterCockpitPanelIds);
    expect(s.themeKnobs).toEqual({ accentIntensity: "normal", density: "comfortable" });
  });

  it("does not mutate the frozen default when a setter runs", () => {
    useSettingsStore.getState().setStarterCockpitPanelIds(["chart-panel"]);
    expect(DEFAULT_SETTINGS.starterCockpitPanelIds).toEqual([
      "chart-panel",
      "equity-overview-panel",
      "watchlist-panel",
      "news-panel",
      "portfolio-panel",
    ]);
  });

  it("setters update state and trigger persistence", () => {
    const store = useSettingsStore.getState();

    store.setDefaultAgentId("buffett");
    expect(useSettingsStore.getState().defaultAgentId).toBe("buffett");

    store.setPaletteRecentsEnabled(false);
    expect(useSettingsStore.getState().paletteRecentsEnabled).toBe(false);

    store.setPaletteScopedToPanel(true);
    expect(useSettingsStore.getState().paletteScopedToPanel).toBe(true);

    store.setThemeKnobs({ accentIntensity: "vivid" });
    expect(useSettingsStore.getState().themeKnobs.accentIntensity).toBe("vivid");
    // density untouched by a partial set
    expect(useSettingsStore.getState().themeKnobs.density).toBe("comfortable");

    // Each setter self-persists.
    expect(autosaveMock).toHaveBeenCalledTimes(4);
  });

  it("toggleStarterCockpitPanel adds and removes ids", () => {
    const store = useSettingsStore.getState();
    store.setStarterCockpitPanelIds([]);
    store.toggleStarterCockpitPanel("screener-panel", true);
    expect(useSettingsStore.getState().starterCockpitPanelIds).toContain("screener-panel");
    store.toggleStarterCockpitPanel("screener-panel", false);
    expect(useSettingsStore.getState().starterCockpitPanelIds).not.toContain("screener-panel");
  });

  it("moveProviderPreference reorders and clamps at the edges", () => {
    const store = useSettingsStore.getState();
    store.setProviderPreferenceOrder(["anthropic", "openai", "gemini"]);

    store.moveProviderPreference("openai", "up");
    expect(useSettingsStore.getState().providerPreferenceOrder).toEqual([
      "openai",
      "anthropic",
      "gemini",
    ]);

    // Moving the first item up is a no-op (clamped).
    store.moveProviderPreference("openai", "up");
    expect(useSettingsStore.getState().providerPreferenceOrder).toEqual([
      "openai",
      "anthropic",
      "gemini",
    ]);

    store.moveProviderPreference("gemini", "down");
    expect(useSettingsStore.getState().providerPreferenceOrder).toEqual([
      "openai",
      "anthropic",
      "gemini",
    ]);
  });

  it("setPanelDefault stores per-panel preferences", () => {
    useSettingsStore.getState().setPanelDefault("chart-panel", { interval: "1D" });
    expect(useSettingsStore.getState().panelDefaults["chart-panel"]).toEqual({ interval: "1D" });
  });

  it("setAll replaces the bundle and merges a partial blob over the seed", () => {
    useSettingsStore.getState().setAll({
      defaultAgentId: "munger",
      providerPreferenceOrder: ["groq", "ollama"],
      // intentionally omit the rest — they must fall back to the seed
    });
    const s = useSettingsStore.getState();
    expect(s.defaultAgentId).toBe("munger");
    expect(s.providerPreferenceOrder).toEqual(["groq", "ollama"]);
    expect(s.paletteRecentsEnabled).toBe(DEFAULT_SETTINGS.paletteRecentsEnabled);
    expect(s.themeKnobs).toEqual(DEFAULT_SETTINGS.themeKnobs);
  });

  it("toBundle / settingsBundle snapshot the current preferences", () => {
    useSettingsStore.getState().setDefaultAgentId("buffett");
    useSettingsStore.getState().setProviderPreferenceOrder(["anthropic", "openai"]);
    const bundle = settingsBundle();
    expect(bundle.defaultAgentId).toBe("buffett");
    // The snapshot is a copy — mutating it doesn't bleed into the store.
    bundle.providerPreferenceOrder.push("gemini");
    expect(useSettingsStore.getState().providerPreferenceOrder).toEqual(["anthropic", "openai"]);
  });
});
