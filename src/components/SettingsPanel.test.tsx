import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPanel, nativeSearchStatus } from "@/components/SettingsPanel";
import { vystedModules } from "@/modules";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { resetKeybindingsStoreForTests, useKeybindingsStore } from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";

// Keep the preference setters from firing a real autosave (network) under test.
vi.mock("@/lib/workspace", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/workspace")>();
  return { ...actual, autosaveLayout: vi.fn(() => Promise.resolve()) };
});

// WS5: the native-tier status copy must be honest for EVERY provider/model combo
// — it must never claim a model has its own web search when it doesn't (the bug
// that prompted this: OpenRouter/DeepSeek defaults claimed native search that
// never fired). This locks the matrix so the copy can't silently rot.
describe("nativeSearchStatus (WS5 honest native-tier copy)", () => {
  it("provider-level providers claim the active model's own web search", () => {
    for (const p of ["anthropic", "openai", "gemini", "groq", "xai"] as const) {
      expect(nativeSearchStatus(p, null)).toMatch(/your active model's own web search/);
    }
  });
  it("an OpenRouter native-capable model claims OpenRouter-credit native search", () => {
    expect(nativeSearchStatus("openrouter", "native")).toMatch(
      /native web search.*OpenRouter credits/,
    );
  });
  it("an OpenRouter plugin model discloses the app fallback + a may-drift estimate, not auto-enabled", () => {
    const copy = nativeSearchStatus("openrouter", "plugin");
    expect(copy).toMatch(/fall back to the app's search tool/);
    expect(copy).toMatch(/may drift/);
    expect(copy).toMatch(/doesn't auto-enable/i);
  });
  it("OpenRouter-none and DeepSeek fall back to the app tool and never claim native", () => {
    for (const [provider, ws] of [
      ["openrouter", "none"],
      ["deepseek", null],
    ] as const) {
      const copy = nativeSearchStatus(provider, ws);
      expect(copy).toMatch(/app's own search tool/);
      expect(copy).not.toMatch(/your active model's own/);
    }
  });
});

describe("SettingsPanel", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useModulesStore.getState().registerModules(vystedModules);
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("lists every registered module", () => {
    render(<SettingsPanel />);
    // Scope to the Modules section — module titles like "Chart"/"News" also
    // appear in the new Preferences starter-cockpit picker, so a global
    // getByText would now match multiple nodes.
    const modulesSection = screen.getByRole("region", { name: "Modules" });
    for (const mod of vystedModules) {
      expect(within(modulesSection).getByText(mod.title)).toBeInTheDocument();
    }
  });

  it("toggling a module updates the modules store", () => {
    render(<SettingsPanel />);

    const chartToggle = screen.getByRole("switch", { name: "Chart enabled" });
    expect(chartToggle).toBeChecked();

    fireEvent.click(chartToggle);
    expect(useModulesStore.getState().enabled.chart).toBe(false);
    expect(chartToggle).not.toBeChecked();

    fireEvent.click(chartToggle);
    expect(useModulesStore.getState().enabled.chart).toBe(true);
    expect(chartToggle).toBeChecked();
  });

  it("the platform module toggle is not user-disableable", () => {
    render(<SettingsPanel />);

    const platformToggle = screen.getByRole("switch", { name: "Platform enabled" });
    expect(platformToggle).toBeChecked();
    expect(platformToggle).toBeDisabled();

    // Clicking the disabled toggle must not flip the platform module off.
    fireEvent.click(platformToggle);
    expect(useModulesStore.getState().enabled[PLATFORM_MODULE_ID]).not.toBe(false);
  });

  // ---- Keybindings (FR-039) ----

  it("renders a keybinding with its formatted combo", () => {
    render(<SettingsPanel />);
    // "Open command palette" defaults to mod+k → ⌘K (mac) or Ctrl+K elsewhere.
    const binding = screen.getByLabelText("Open command palette binding");
    expect(binding.textContent).toMatch(/K$/);
  });

  it("recording a key remaps the binding via setBinding", () => {
    render(<SettingsPanel />);

    fireEvent.click(
      screen.getByRole("button", { name: "Record binding for Open command palette" }),
    );

    // The button enters recording mode and captures the next keydown.
    const recordBtn = screen.getByRole("button", {
      name: "Record binding for Open command palette",
    });
    fireEvent.keyDown(recordBtn, { key: "p", ctrlKey: true, shiftKey: true });

    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("ctrl+shift+p");
  });

  it("surfaces a user-created conflict when two actions share a combo", () => {
    render(<SettingsPanel />);

    // Deliberately collide two actions onto the same unused combo (⌥9) and
    // assert the conflict warning names BOTH actions — proving the UI surfaces
    // the conflict a remap introduces (FR-039 / SC-011).
    fireEvent.click(
      screen.getByRole("button", { name: "Record binding for Open command palette" }),
    );
    fireEvent.keyDown(
      screen.getByRole("button", { name: "Record binding for Open command palette" }),
      { key: "9", altKey: true },
    );
    fireEvent.click(screen.getByRole("button", { name: "Record binding for Open news" }));
    fireEvent.keyDown(screen.getByRole("button", { name: "Record binding for Open news" }), {
      key: "9",
      altKey: true,
    });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/Conflicting bindings detected/i);
    expect(alert).toHaveTextContent(/Open command palette/);
    expect(alert).toHaveTextContent(/Open news/);
  });

  // ---- Preferences ----

  it("the provider preference order is reorderable", () => {
    useSettingsStore.getState().setProviderPreferenceOrder(["anthropic", "openai", "gemini"]);
    render(<SettingsPanel />);

    fireEvent.click(screen.getByRole("button", { name: "Move OpenAI up" }));

    expect(useSettingsStore.getState().providerPreferenceOrder.slice(0, 2)).toEqual([
      "openai",
      "anthropic",
    ]);
  });

  // ---- Export / Import (FR-037/FR-038/SC-010) ----

  it("export produces a bundle without secret values", () => {
    // Arrange a remap + a preference so the bundle is non-trivial.
    useKeybindingsStore.getState().setBinding("palette.open", "mod+shift+k");
    useSettingsStore.getState().setDefaultAgentId("buffett");

    let captured: string | null = null;
    const createObjectURL = vi.fn((blob: Blob) => {
      // Synchronously read the blob text via a spy on the constructor isn't
      // possible; instead intercept the Blob payload through a fake.
      void blob;
      return "blob:mock";
    });
    vi.stubGlobal("URL", {
      createObjectURL,
      revokeObjectURL: vi.fn(),
    } as unknown as typeof URL);

    // Capture the Blob payload the component builds.
    const realBlob = globalThis.Blob;
    vi.stubGlobal(
      "Blob",
      class extends realBlob {
        constructor(parts: BlobPart[], options?: BlobPropertyBag) {
          super(parts, options);
          captured = String(parts[0] ?? "");
        }
      } as unknown as typeof Blob,
    );

    render(<SettingsPanel />);
    fireEvent.click(screen.getByRole("button", { name: /Export settings/i }));

    expect(captured).not.toBeNull();
    const bundle = JSON.parse(captured!) as Record<string, unknown>;
    // The bundle carries remaps + preferences…
    expect(bundle.keybindingOverrides).toEqual({ "palette.open": "mod+shift+k" });
    expect((bundle.settings as { defaultAgentId: string }).defaultAgentId).toBe("buffett");
    // …and NEVER a secret/API-key field (FR-036/SC-010).
    const serialized = captured!.toLowerCase();
    expect(serialized).not.toMatch(/api[_-]?key/);
    expect(serialized).not.toMatch(/secret/);
    expect(serialized).not.toMatch(/token/);

    vi.unstubAllGlobals();
  });

  it("the export section states secrets are not exported", () => {
    render(<SettingsPanel />);
    const section = screen.getByRole("region", { name: "Export / Import" });
    expect(within(section).getByText(/never exported/i)).toBeInTheDocument();
  });

  // ---- R7 sectioned hierarchy ----

  it("groups the page into named sections with a jump nav", () => {
    render(<SettingsPanel />);
    expect(screen.getByRole("navigation", { name: "Settings sections" })).toBeInTheDocument();
    for (const name of [
      "AI Providers",
      "Web search",
      "Research",
      "Region & locale",
      "Interface",
      "Keybindings",
      "Advanced",
    ]) {
      expect(screen.getByRole("region", { name })).toBeInTheDocument();
    }
  });

  it("labels OpenRouter plainly — never as a broker", () => {
    render(<SettingsPanel />);
    expect(screen.queryByText(/OpenRouter \(broker\)/)).toBeNull();
    expect(screen.getAllByText("OpenRouter").length).toBeGreaterThan(0);
  });

  it("starter-cockpit chips toggle the settings store", () => {
    render(<SettingsPanel />);
    const chip = screen.getByRole("checkbox", { name: "Starter cockpit: Screener" });
    const before = useSettingsStore.getState().starterCockpitPanelIds.includes("screener-panel");

    fireEvent.click(chip);
    expect(useSettingsStore.getState().starterCockpitPanelIds.includes("screener-panel")).toBe(
      !before,
    );
  });

  it("every pre-R7 setting control is still reachable", () => {
    render(<SettingsPanel />);
    // AI providers
    expect(screen.getByLabelText("Default agent")).toBeInTheDocument();
    expect(screen.getByLabelText("Default provider")).toBeInTheDocument();
    expect(screen.getByLabelText("Default model")).toBeInTheDocument();
    // Web search
    expect(screen.getByLabelText("Search tier")).toBeInTheDocument();
    expect(screen.getByLabelText("SearXNG URL")).toBeInTheDocument();
    // Region, interface knobs
    expect(screen.getByLabelText("Region")).toBeInTheDocument();
    expect(screen.getByLabelText("Accent intensity")).toBeInTheDocument();
    expect(screen.getByLabelText("Density")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "Show recent commands" })).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Scope to the focused panel first" }),
    ).toBeInTheDocument();
    // Advanced
    expect(screen.getByRole("button", { name: /Open Marketplace/i })).toBeInTheDocument();
    expect(screen.getByLabelText("New layout name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Import settings/i })).toBeInTheDocument();
  });
});
