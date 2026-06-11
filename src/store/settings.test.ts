import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

import { autosaveLayout } from "@/lib/workspace";
import { DEFAULT_AGENT_ID, useActiveAgentStore } from "@/store/active-agent";
import {
  DEFAULT_SETTINGS,
  RAW_CHAT_SENTINEL,
  resetSettingsStoreForTests,
  settingsBundle,
  useSettingsStore,
} from "@/store/settings";

const autosaveMock = vi.mocked(autosaveLayout);

describe("settings store", () => {
  beforeEach(() => {
    resetSettingsStoreForTests();
    useActiveAgentStore.setState({ activeAgentId: DEFAULT_AGENT_ID });
    autosaveMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("seeds from the default bundle", () => {
    const s = useSettingsStore.getState();
    expect(s.defaultAgentId).toBe(DEFAULT_AGENT_ID);
    expect(s.region).toBe(DEFAULT_SETTINGS.region);
    expect(s.deepResearchBackend).toBe("native");
  });

  it("carries NO killed preference fields (R9 settings-truth)", () => {
    // The dead knobs died with their UI: written-never-read fields are theater.
    const bundle = settingsBundle() as unknown as Record<string, unknown>;
    for (const killed of [
      "themeKnobs",
      "paletteRecentsEnabled",
      "paletteScopedToPanel",
      "starterCockpitPanelIds",
      "panelDefaults",
      "providerPreferenceOrder",
    ]) {
      expect(bundle).not.toHaveProperty(killed);
    }
  });

  it("setters update state and trigger persistence", () => {
    const store = useSettingsStore.getState();

    store.setDefaultAgentId("buffett");
    expect(useSettingsStore.getState().defaultAgentId).toBe("buffett");

    store.setRegion("IN");
    expect(useSettingsStore.getState().region).toBe("IN");

    store.setDeepResearchBackend("perplexity");
    expect(useSettingsStore.getState().deepResearchBackend).toBe("perplexity");

    // Each setter self-persists.
    expect(autosaveMock).toHaveBeenCalledTimes(3);
  });

  // ---- defaultAgentId wiring (R9 D4: change → persist → reload → APPLIED) ----

  it("setDefaultAgentId applies the persona to the active-agent store immediately", () => {
    useSettingsStore.getState().setDefaultAgentId("graham");
    expect(useActiveAgentStore.getState().activeAgentId).toBe("graham");

    useSettingsStore.getState().setDefaultAgentId(null); // raw chat
    expect(useActiveAgentStore.getState().activeAgentId).toBeNull();
  });

  it("the boot restore (first setAll) seeds the active agent from the blob", () => {
    useSettingsStore.getState().setAll({ defaultAgentId: "munger" });
    expect(useActiveAgentStore.getState().activeAgentId).toBe("munger");
  });

  it("a later restore does NOT yank the live lens (default applies per session)", () => {
    useSettingsStore.getState().setAll({ defaultAgentId: "munger" }); // boot
    useActiveAgentStore.getState().setActiveAgent("graham"); // user switches lens
    useSettingsStore.getState().setAll({ defaultAgentId: "buffett" }); // layout load / import
    expect(useSettingsStore.getState().defaultAgentId).toBe("buffett");
    expect(useActiveAgentStore.getState().activeAgentId).toBe("graham");
  });

  it("an explicit raw-chat default round-trips via the sentinel", () => {
    useSettingsStore.getState().setDefaultAgentId(null);
    const bundle = settingsBundle();
    expect(bundle.defaultAgentId).toBe(RAW_CHAT_SENTINEL);

    resetSettingsStoreForTests();
    useSettingsStore.getState().setAll(bundle);
    expect(useSettingsStore.getState().defaultAgentId).toBeNull();
    expect(useActiveAgentStore.getState().activeAgentId).toBeNull();
  });

  it("a legacy blob's dead null coerces to the Copilot default", () => {
    // Pre-R9 the control was written-never-read, so a persisted null carried
    // no intent — restoring it must not strand the chat on raw mode.
    useSettingsStore.getState().setAll({ defaultAgentId: null });
    expect(useSettingsStore.getState().defaultAgentId).toBe(DEFAULT_AGENT_ID);
    expect(useActiveAgentStore.getState().activeAgentId).toBe(DEFAULT_AGENT_ID);
  });

  // ---- setAll hygiene ----

  it("setAll replaces the bundle and merges a partial blob over the seed", () => {
    useSettingsStore.getState().setAll({
      defaultAgentId: "munger",
      // intentionally omit the rest — they must fall back to the seed
    });
    const s = useSettingsStore.getState();
    expect(s.defaultAgentId).toBe("munger");
    expect(s.region).toBe(DEFAULT_SETTINGS.region);
    expect(s.deepResearchBackend).toBe("native");
  });

  it("setAll silently drops killed fields from an older blob", () => {
    useSettingsStore.getState().setAll({
      defaultAgentId: "buffett",
      themeKnobs: { accentIntensity: "vivid", density: "compact" },
      paletteRecentsEnabled: false,
      starterCockpitPanelIds: ["chart-panel"],
      providerPreferenceOrder: ["groq"],
      panelDefaults: { "chart-panel": { interval: "1D" } },
    } as never);
    const s = useSettingsStore.getState() as unknown as Record<string, unknown>;
    expect(s.defaultAgentId).toBe("buffett");
    for (const killed of [
      "themeKnobs",
      "paletteRecentsEnabled",
      "starterCockpitPanelIds",
      "providerPreferenceOrder",
      "panelDefaults",
    ]) {
      expect(s[killed]).toBeUndefined();
    }
  });

  it("setAll coerces a garbled region and a legacy deep-research backend", () => {
    useSettingsStore.getState().setAll({
      region: "ATLANTIS",
      deepResearchBackend: "tongyi",
    } as never);
    expect(useSettingsStore.getState().region).toBe(DEFAULT_SETTINGS.region);
    expect(useSettingsStore.getState().deepResearchBackend).toBe("native");
  });

  it("toBundle / settingsBundle snapshot the current preferences", () => {
    useSettingsStore.getState().setDefaultAgentId("buffett");
    useSettingsStore.getState().setRegion("IN");
    const bundle = settingsBundle();
    expect(bundle.defaultAgentId).toBe("buffett");
    expect(bundle.region).toBe("IN");
    expect(bundle.deepResearchBackend).toBe("native");
  });
});
