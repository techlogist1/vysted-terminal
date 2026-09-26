import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import * as axeMatchers from "vitest-axe/matchers";

import { buildSettingsExport, searxngChipMeta, SettingsPanel } from "@/components/SettingsPanel";
import { CATALOG_BY_ID } from "@/lib/marketplace";
import { moduleForPlugin } from "@/lib/plugin-bootstrap";
import { vystedModules } from "@/modules";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { resetKeybindingsStoreForTests, useKeybindingsStore } from "@/store/keybindings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useMarketplaceStore } from "@/store/marketplace";
import { resetModelCatalogStoreForTests, useModelCatalogStore } from "@/store/model-catalog";
import { resetModelSelectionStoreForTests, useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useProviderKeysStore } from "@/store/provider-keys";
import {
  DEFAULT_RESEARCH_MODELS,
  resetSearchSettingsStoreForTests,
  useSearchSettingsStore,
} from "@/store/search-settings";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";

// Keep the preference setters from firing a real autosave (network) under test.
vi.mock("@/lib/workspace", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/workspace")>();
  return { ...actual, autosaveLayout: vi.fn(() => Promise.resolve()) };
});

// The core reports a bound engine; the shared `sidecarGet`/`sidecarRequest`
// resolve through it (and one `/health` probe, which every stub answers).
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string) => {
    if (cmd === "get_sidecar_port") {
      return { port: 51763, state: "ready", reason: null };
    }
    throw new Error(`no Tauri core under test (${cmd})`);
  }),
}));

// Resolve the sidecar base instantly for the sections still on
// getSidecarBaseUrl; the per-test fetch stubs decide what each endpoint returns.
vi.mock("@/lib/sidecar-client", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/sidecar-client")>();
  return { ...actual, getSidecarBaseUrl: vi.fn(() => Promise.resolve("http://sidecar.test")) };
});

// Keychain: keep the real KEYCHAIN_NAMESPACES; default the Tauri-backed reads
// to a rejection (exactly what `invoke` does outside the shell) — individual
// tests override `getSecret` to simulate stored keys.
vi.mock("@/lib/keychain", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/keychain")>();
  return {
    ...actual,
    getSecret: vi.fn(() => Promise.reject(new Error("no keychain under test"))),
    setSecret: vi.fn(() => Promise.resolve()),
    deleteSecret: vi.fn(() => Promise.resolve()),
  };
});

import { getSecret } from "@/lib/keychain";
import { SIDECAR_UNREACHABLE } from "@/lib/sidecar-client";

const getSecretMock = vi.mocked(getSecret);

// R15-UI-071: no automated accessibility gate existed at all. `toHaveNoViolations`
// runs the real axe-core ruleset against the rendered DOM — this catches
// unlabelled controls, missing landmarks, etc. that a static lint rule
// (jsx-a11y/label-has-associated-control) cannot, since it can only see JSX,
// not the accessible name the browser actually computes at runtime.
expect.extend(axeMatchers);

/** A 200 JSON response for the fetch stubs. */
function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

/** Stub global fetch with a path → payload router (unrouted paths 404; the
 *  readiness probe `/health` always answers). */
function routeFetch(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    if (path === "/health") {
      return Promise.resolve(jsonResponse({ status: "ok" }));
    }
    if (path in routes) {
      return Promise.resolve(jsonResponse(routes[path]));
    }
    return Promise.resolve(new Response("{}", { status: 404 }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("SettingsPanel", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useModulesStore.getState().registerModules(vystedModules);
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
    resetSearchSettingsStoreForTests();
    resetModelSelectionStoreForTests();
    useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
    useProviderKeysStore.setState({ status: {}, probed: false });
    // Default: the engine is up but refuses every request — the surfaces render
    // their honest "unavailable" fallbacks. Tier tests route real paths.
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) =>
        new URL(String(input)).pathname === "/health"
          ? Promise.resolve(jsonResponse({ status: "ok" }))
          : Promise.reject(new TypeError("no network under test")),
      ),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
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

  // R15-CODE-PLATFORM-013: a bridged plugin module's toggle must route through
  // the marketplace lifecycle owner (runtime + plugins.db), not the bare
  // modules-store setter — otherwise the workspace-persisted "off" is silently
  // undone on relaunch when the runtime re-attaches from plugins.db.
  it("toggling a bridged plugin module routes through the marketplace lifecycle, not setModuleEnabled directly", () => {
    const mod = moduleForPlugin(CATALOG_BY_ID["vysted-example"]);
    if (!mod) throw new Error("vysted-example plugin has no panels/commands to bridge");
    useModulesStore.getState().appendModules([mod]);
    useModulesStore.getState().setModuleEnabled(mod.id, true);

    const disableSpy = vi
      .spyOn(useMarketplaceStore.getState(), "disable")
      .mockResolvedValue(undefined);

    render(<SettingsPanel />);
    const toggle = screen.getByRole("switch", { name: "Vysted Example Plugin enabled" });
    expect(toggle).toBeChecked();

    fireEvent.click(toggle);

    expect(disableSpy).toHaveBeenCalledWith("vysted-example");
    // The lifecycle owner (marketplace.disable → runtime.disablePlugin) is
    // mocked out here, so it never actually flips the module map — the point
    // is that SettingsPanel no longer flips it directly for a plugin:* row.
    expect(useModulesStore.getState().enabled["plugin:vysted-example"]).not.toBe(false);
    disableSpy.mockRestore();
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

  it("keeps every keybinding row's label column flex-1 so the cluster never wraps on copy length (D2)", () => {
    render(<SettingsPanel />);
    // Row shape: kbd → cluster div → row div; the label column is the row's
    // first child. flex-1 (basis-0) means description width never decides the
    // wrap point — every row keeps its kbd/Record/reset cluster inline on one
    // aligned column at default width, with truncate as the live last resort.
    const kbds = screen.getAllByLabelText(/ binding$/);
    expect(kbds.length).toBeGreaterThan(0);
    for (const kbd of kbds) {
      const labelCol = kbd.parentElement?.parentElement?.firstElementChild;
      expect(labelCol?.className).toContain("flex-1");
      expect(labelCol?.className).toContain("min-w-0");
    }
  });

  it("recording a key remaps the binding via setBinding, collapsing the platform-primary modifier to mod", () => {
    render(<SettingsPanel />);

    fireEvent.click(
      screen.getByRole("button", { name: "Record binding for Open command palette" }),
    );

    // The button enters recording mode and captures the next keydown. jsdom's
    // default navigator resolves non-mac here, so Ctrl IS the platform-primary
    // modifier and must collapse to "mod" (R15-UI-027) — literal "ctrl" is
    // reserved for a genuinely non-primary Control press (see the mac-only
    // "mod" case in the isMacPlatform-stubbed test below).
    const recordBtn = screen.getByRole("button", {
      name: "Record binding for Open command palette",
    });
    fireEvent.keyDown(recordBtn, { key: "p", ctrlKey: true, shiftKey: true });

    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+shift+p");
  });

  it("recording Cmd+K on macOS records mod+k and is caught as a real conflict with the mod+k default (R15-UI-027)", () => {
    vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "Mac OS X" });
    render(<SettingsPanel />);

    // Record Cmd+K (metaKey) onto "Toggle agent panel" — the SAME physical
    // chord as "Open command palette"'s mod+k default. Pre-fix, the recorder
    // emitted a platform-literal "meta+k", which `conflicts()` (grouping by
    // resolved combo string) would never match against "mod+k" — a real
    // macOS collision went undetected. Cmd is the mac platform-primary
    // modifier, so the fixed recorder must emit "mod", not "meta".
    fireEvent.click(screen.getByRole("button", { name: "Record binding for Toggle agent panel" }));
    fireEvent.keyDown(
      screen.getByRole("button", { name: "Record binding for Toggle agent panel" }),
      { key: "k", metaKey: true },
    );
    expect(useKeybindingsStore.getState().bindingFor("agent.toggle")).toBe("mod+k");

    const conflicts = useKeybindingsStore.getState().conflicts();
    const collision = conflicts.find((c) => c.keys === "mod+k");
    expect(collision?.actionIds).toContain("palette.open");
    expect(collision?.actionIds).toContain("agent.toggle");
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

  // ---- Preferences (R9 settings-truth: dead controls stay dead) ----

  // R9 killed an UNREAD preference-order group; R15-UI-087 rebuilt it with its
  // consumer (the chat's provider fallback), so the order control is live now.
  it("the provider fallback order is live: the arrows reorder the rows and the store (R15-UI-087)", () => {
    render(<SettingsPanel />);
    const before = useSettingsStore.getState().providerOrder;
    const second = useLLMProvidersStore.getState().providers.find((p) => p.id === before[1])!;
    fireEvent.click(screen.getByRole("button", { name: `Move ${second.label} up` }));
    expect(useSettingsStore.getState().providerOrder.slice(0, 2)).toEqual([before[1], before[0]]);
    expect(screen.getByRole("button", { name: `Move ${second.label} up` })).toBeDisabled();
  });

  it("the dead Interface section is gone — no region, no nav chip, no knobs (R9 kill)", () => {
    render(<SettingsPanel />);
    expect(screen.queryByRole("region", { name: "Interface" })).toBeNull();
    const nav = screen.getByRole("navigation", { name: "Settings sections" });
    expect(within(nav).queryByRole("button", { name: "Interface" })).toBeNull();
    // The written-never-read knobs died with it (defect V6 + friends).
    expect(screen.queryByLabelText("Accent intensity")).toBeNull();
    expect(screen.queryByLabelText("Density")).toBeNull();
    expect(screen.queryByRole("switch", { name: "Show recent commands" })).toBeNull();
    expect(screen.queryByRole("switch", { name: "Scope to the focused panel first" })).toBeNull();
    expect(screen.queryByText(/Starter cockpit/)).toBeNull();
  });

  it("picking a default agent applies it to the active chat lens", () => {
    render(<SettingsPanel />);
    fireEvent.change(screen.getByLabelText("Default agent"), { target: { value: "" } });
    expect(useSettingsStore.getState().defaultAgentId).toBeNull();
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

  // ---- Import gating + SettingsExport v2 (R15-UI-058) ----

  function fileInput() {
    return screen.getByLabelText("Import settings file") as HTMLInputElement;
  }

  function doImport(json: unknown) {
    const file = new File([JSON.stringify(json)], "import.json", { type: "application/json" });
    fireEvent.change(fileInput(), { target: { files: [file] } });
  }

  it("a file recognising nothing (an empty object) reports an error, not success", async () => {
    render(<SettingsPanel />);
    doImport({});
    expect(await screen.findByText(/expected a Vysted export/i)).toBeInTheDocument();
  });

  it("another app's JSON ({theme:'dark'}) reports an error, not success", async () => {
    render(<SettingsPanel />);
    doImport({ theme: "dark" });
    expect(await screen.findByText(/expected a Vysted export/i)).toBeInTheDocument();
  });

  it("a bundle lacking region preserves the CURRENT region instead of resetting it", async () => {
    useSettingsStore.getState().setRegion("IN");
    render(<SettingsPanel />);
    doImport({ settings: { defaultAgentId: "munger" } }); // no `region` field at all
    await screen.findByText(/Imported settings/i);
    expect(useSettingsStore.getState().defaultAgentId).toBe("munger");
    expect(useSettingsStore.getState().region).toBe("IN");
  });

  it("keybindingOverrides with a bogus action id merges instead of wiping the existing remap", async () => {
    useKeybindingsStore.getState().setBinding("changes.acceptAll", "mod+shift+enter");
    render(<SettingsPanel />);
    doImport({
      keybindingOverrides: { "no.such.action": "mod+z", "palette.open": 42 },
    });
    await screen.findByText(/Imported settings/i);
    const overrides = useKeybindingsStore.getState().overrides;
    expect(overrides["changes.acceptAll"]).toBe("mod+shift+enter"); // survives
    expect(overrides["no.such.action"]).toBeUndefined(); // unknown action rejected
    expect(overrides["palette.open"]).toBeUndefined(); // non-string value rejected
  });

  it("round-trips search settings, default provider/model and module toggles", async () => {
    useSearchSettingsStore.getState().setSearxngUrl("https://searx.example.com");
    useLLMProvidersStore.getState().setDefaultProviderId("openrouter");
    useModelSelectionStore.getState().setModel("openrouter", "anthropic/claude-3.5-sonnet");
    useModulesStore.getState().setModuleEnabled("chart", false);

    const exported = buildSettingsExport();
    expect(exported.searchSettings.searxngUrl).toBe("https://searx.example.com");
    expect(exported.defaultProviderId).toBe("openrouter");
    expect(exported.defaultModel).toBe("anthropic/claude-3.5-sonnet");
    expect(exported.enabledModules.chart).toBe(false);

    // Reset the live state so the import assertion proves restoration, not survival.
    resetSearchSettingsStoreForTests();
    resetModelSelectionStoreForTests();
    useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
    useModulesStore.getState().setModuleEnabled("chart", true);

    render(<SettingsPanel />);
    doImport(exported);
    await screen.findByText(/Imported settings/i);

    expect(useSearchSettingsStore.getState().searxngUrl).toBe("https://searx.example.com");
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("openrouter");
    expect(useModelSelectionStore.getState().overrides.openrouter).toBe(
      "anthropic/claude-3.5-sonnet",
    );
    expect(useModulesStore.getState().enabled.chart).toBe(false);
  });

  it("R15-UI-058: search-settings setAll preserves the CURRENT searxngUrl when a later bundle omits it", () => {
    useSearchSettingsStore.getState().setSearxngUrl("https://searx.example.com");
    // A partial re-import that only carries a research-model tweak must not
    // silently reset the SearXNG URl back to "" (the same merge-over-seed
    // class fixed for settings.ts region and keybindings.ts overrides).
    useSearchSettingsStore.getState().setAll({
      researchModels: { ...DEFAULT_RESEARCH_MODELS, normal: "perplexity/sonar-pro" },
    });
    const s = useSearchSettingsStore.getState();
    expect(s.searxngUrl).toBe("https://searx.example.com");
    expect(s.researchModels.normal).toBe("perplexity/sonar-pro");
  });

  it("an unrecognised defaultProviderId is rejected (no such provider)", async () => {
    render(<SettingsPanel />);
    doImport({ defaultProviderId: "not-a-real-provider", defaultModel: "x" });
    expect(await screen.findByText(/expected a Vysted export/i)).toBeInTheDocument();
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("ollama");
  });

  it("Region & locale states the actual default and what region controls (R15-DATA-092)", () => {
    render(<SettingsPanel />);
    const section = screen.getByRole("region", { name: "Region & locale" });
    // Not "only number formatting" — the copy names the sidecar-side effects.
    expect(within(section).getByText(/symbol resolver/i)).toBeInTheDocument();
    // Not "Defaults to United States" — the real default is India.
    expect(within(section).getByText(/defaults to india/i)).toBeInTheDocument();
    expect(within(section).queryByText(/defaults to united states/i)).toBeNull();
  });

  // ---- R8 sectioned hierarchy (ONE search surface) ----

  it("groups the page into named sections with a jump nav", () => {
    render(<SettingsPanel />);
    expect(screen.getByRole("navigation", { name: "Settings sections" })).toBeInTheDocument();
    for (const name of ["AI Providers", "Research", "Region & locale", "Keybindings", "Advanced"]) {
      expect(screen.getByRole("region", { name })).toBeInTheDocument();
    }
  });

  it("the legacy Web search section is gone — no section, no nav chip, no docker snippet", () => {
    render(<SettingsPanel />);
    expect(screen.queryByRole("region", { name: "Web search" })).toBeNull();
    const nav = screen.getByRole("navigation", { name: "Settings sections" });
    expect(within(nav).queryByRole("button", { name: "Web search" })).toBeNull();
    // The legacy tier select and the manual docker-run snippet died with it.
    expect(screen.queryByLabelText("Search tier")).toBeNull();
    expect(screen.queryByText(/docker run -d -p 8080:8080/)).toBeNull();
  });

  it("labels OpenRouter plainly — never as a broker", () => {
    render(<SettingsPanel />);
    expect(screen.queryByText(/OpenRouter \(broker\)/)).toBeNull();
    expect(screen.getAllByText("OpenRouter").length).toBeGreaterThan(0);
  });

  it("every surviving setting control is still reachable", () => {
    render(<SettingsPanel />);
    // AI providers
    expect(screen.getByLabelText("Default agent")).toBeInTheDocument();
    expect(screen.getByLabelText("Default provider")).toBeInTheDocument();
    expect(screen.getByLabelText("Default model")).toBeInTheDocument();
    // Research tiers — the one search surface.
    expect(screen.getByRole("radiogroup", { name: "Research tier" })).toBeInTheDocument();
    // Region
    expect(screen.getByLabelText("Region")).toBeInTheDocument();
    // Advanced
    expect(screen.getByRole("button", { name: /Open Marketplace/i })).toBeInTheDocument();
    expect(screen.getByLabelText("New layout name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Import settings/i })).toBeInTheDocument();
  });

  // ---- R9 research tiers (two tiers — D1 on Team A's contract) ----

  function tierRadio(name: RegExp) {
    const group = screen.getByRole("radiogroup", { name: "Research tier" });
    return within(group).getByRole("radio", { name });
  }

  it("renders exactly two tier cards as radios, Unlimited (Local) selected by default", () => {
    render(<SettingsPanel />);
    const group = screen.getByRole("radiogroup", { name: "Research tier" });
    expect(within(group).getAllByRole("radio")).toHaveLength(2);
    expect(tierRadio(/Unlimited \(Local\)/)).toHaveAttribute("aria-checked", "true");
    expect(tierRadio(/Hosted research model/)).toHaveAttribute("aria-checked", "false");
  });

  it("selecting a tier updates the search-settings store", () => {
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Hosted research model/));
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
    fireEvent.click(tierRadio(/Unlimited \(Local\)/));
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("the three-tier surface is gone — no keyless tier, no BYOK scraper, no Exa (R9 kill)", () => {
    render(<SettingsPanel />);
    expect(screen.queryByText(/Local scraping \(keyless\)/)).toBeNull();
    expect(screen.queryByText(/BYOK search/)).toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "BYOK search mode" })).toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "Hosted search engine" })).toBeNull();
    expect(screen.queryByText(/Exa direct/)).toBeNull();
    expect(screen.queryByLabelText("Exa API key")).toBeNull();
    expect(screen.queryByTestId("t1-engine-status")).toBeNull();
  });

  it("searxngChipMeta speaks the designed chip vocabulary for every state", () => {
    expect(searxngChipMeta("not_installed_docker").label).toBe("Docker not found");
    expect(searxngChipMeta("docker_present_not_setup").label).toBe("Not set up");
    expect(searxngChipMeta("pulling").label).toBe("Pulling");
    expect(searxngChipMeta("starting").label).toBe("Starting");
    expect(searxngChipMeta("ready").label).toBe("Ready");
    expect(searxngChipMeta("error").label).toBe("Error");
    // R15-RESEARCH-028: the container answers but its engines are blocked —
    // distinct wording + styling from both "ready" and "error".
    expect(searxngChipMeta("degraded").label).toBe("Degraded — engines blocked");
    // An unknown state names itself honestly rather than guessing.
    expect(searxngChipMeta("rebooting").label).toBe("rebooting");
  });

  // The Tier A flow renders each sidecar state machine state VERBATIM.
  function searxngStatus(state: string, extra?: Partial<Record<string, unknown>>) {
    return { state, detail: null, reason: null, port: null, url: null, ...extra };
  }

  async function chipText(): Promise<string | null> {
    const chip = await screen.findByTestId("searxng-status-chip");
    return chip.textContent;
  }

  it("Tier A not_installed_docker: honest chip + copy + plain-text install hint (no link), no action", async () => {
    routeFetch({ "/search/searxng/status": searxngStatus("not_installed_docker") });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Docker not found");
    expect(screen.getByText(/Docker isn.t available on this machine/)).toBeInTheDocument();
    const hint = screen.getByText(/docs\.docker\.com/);
    expect(hint.closest("a")).toBeNull(); // plain text, no external nav
    expect(screen.queryByRole("button", { name: "Set up" })).toBeNull();
  });

  it("Tier A docker_present_not_setup: 'Not set up' chip + ONE [Set up] action", async () => {
    routeFetch({ "/search/searxng/status": searxngStatus("docker_present_not_setup") });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Not set up");
    expect(screen.getByRole("button", { name: "Set up" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
  });

  it("Tier A pulling: progress chip + sidecar detail, no action while transitional", async () => {
    routeFetch({
      "/search/searxng/status": searxngStatus("pulling", {
        detail: "pulling searxng/searxng (first run can take a few minutes)",
      }),
    });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Pulling");
    expect(screen.getByText(/Pulling the SearXNG image/)).toBeInTheDocument();
    expect(screen.getByText(/first run can take a few minutes/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Set up" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
  });

  it("Tier A ready: green chip + health line + [Stop]; the fallback note disappears", async () => {
    routeFetch({
      "/search/searxng/status": searxngStatus("ready", {
        port: 8888,
        url: "http://127.0.0.1:8888",
      }),
    });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Ready");
    expect(
      screen.getByText(/Running at http:\/\/127\.0\.0\.1:8888 — research searches route/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(screen.queryByText(/Until set up, research uses limited keyless search/)).toBeNull();
  });

  it("Tier A error: reason + [Retry]", async () => {
    routeFetch({
      "/search/searxng/status": searxngStatus("error", {
        reason: "docker pull failed: no space left on device",
      }),
    });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Error");
    expect(
      screen.getByText(/Setup failed: docker pull failed: no space left on device/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("Tier A degraded: warning chip + engines-blocked reason + [Stop] (R15-RESEARCH-028)", async () => {
    routeFetch({
      "/search/searxng/status": searxngStatus("degraded", {
        reason: "no results from any engine across 3 real queries",
      }),
    });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Degraded — engines blocked");
    expect(
      screen.getByText(/Degraded — engines blocked \(no results from any engine across 3 real/),
    ).toBeInTheDocument();
    // It's still a running container — Stop, not Retry (nothing to retry).
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });

  it("Tier A [Set up] POSTs /search/searxng/setup and renders the returned pulling state", async () => {
    const fetchMock = routeFetch({
      "/search/searxng/status": searxngStatus("docker_present_not_setup"),
      "/search/searxng/setup": searxngStatus("pulling", {
        detail: "starting guided setup — checking docker",
      }),
    });
    render(<SettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Set up" }));
    expect(await screen.findByText(/Pulling the SearXNG image/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:51763/search/searxng/setup",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("Tier A [Stop] POSTs /search/searxng/teardown and renders the post-teardown state", async () => {
    const fetchMock = routeFetch({
      "/search/searxng/status": searxngStatus("ready", { url: "http://127.0.0.1:8888" }),
      "/search/searxng/teardown": searxngStatus("docker_present_not_setup"),
    });
    render(<SettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Stop" }));
    expect(await screen.findByRole("button", { name: "Set up" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:51763/search/searxng/teardown",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("Tier A shows the honest fallback note whenever the instance is not ready", async () => {
    routeFetch({ "/search/searxng/status": searxngStatus("docker_present_not_setup") });
    render(<SettingsPanel />);
    // Settle on the loaded state first: the loading branch shows the note too.
    expect(await chipText()).toBe("Not set up");
    expect(
      screen.getByText(/Until set up, research uses limited keyless search/),
    ).toBeInTheDocument();
  });

  it("Tier A degrades honestly when the sidecar is unreachable", async () => {
    render(<SettingsPanel />); // default fetch stub rejects
    expect(
      await screen.findByText(`SearXNG status unavailable: ${SIDECAR_UNREACHABLE}`),
    ).toBeInTheDocument();
  });

  // R15-RESEARCH-032: a failure keeps its reason, and the status is re-read.
  it("a status 500 shows the sidecar's reason, not 'not connected'", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) =>
        Promise.resolve(
          new URL(String(input)).pathname === "/health"
            ? jsonResponse({ status: "ok" })
            : new Response(JSON.stringify({ detail: "docker daemon not reachable" }), {
                status: 500,
              }),
        ),
      ),
    );
    render(<SettingsPanel />);
    expect(
      await screen.findByText("SearXNG status unavailable: docker daemon not reachable"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Hardware detection unavailable: docker daemon not reachable"),
    ).toBeInTheDocument();
  });

  it("the tab turning visible re-reads the status, so a stale 'Ready' follows the container", async () => {
    routeFetch({ "/search/searxng/status": searxngStatus("ready") });
    render(<SettingsPanel />);
    expect(await chipText()).toBe("Ready");

    // The container died outside the app.
    routeFetch({
      "/search/searxng/status": searxngStatus("error", { reason: "container exited (137)" }),
    });
    fireEvent(document, new Event("visibilitychange"));

    expect(await screen.findByText(/Setup failed: container exited \(137\)/)).toBeInTheDocument();
    expect(await chipText()).toBe("Error");
  });

  it("a failed [Set up] shows why instead of nothing", async () => {
    const fetchMock = routeFetch({
      "/search/searxng/status": searxngStatus("docker_present_not_setup"),
    });
    const routed = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation((input: RequestInfo | URL) =>
      new URL(String(input)).pathname === "/search/searxng/setup"
        ? Promise.resolve(
            new Response(JSON.stringify({ detail: "docker pull denied" }), { status: 500 }),
          )
        : routed(input),
    );
    render(<SettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Set up" }));
    expect(await screen.findByText(/docker pull denied/)).toBeInTheDocument();
  });

  it("the custom SearXNG URL lives behind the Advanced disclosure and writes the store", () => {
    render(<SettingsPanel />);
    // Collapsed by default — open the disclosure first (the honest user path).
    fireEvent.click(screen.getByText("Advanced: custom instance URL"));
    const url = screen.getByLabelText("SearXNG URL");
    fireEvent.change(url, { target: { value: "http://10.0.0.5:8080" } });
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://10.0.0.5:8080");
  });

  // ---- Tier B (hosted research model) ----

  it("Tier B without a key shows the key CTA — never dead model selects", async () => {
    getSecretMock.mockResolvedValue(null); // keychain reachable, no key
    render(<SettingsPanel />);
    expect(
      await screen.findByText(/research stays on the local tier until one is added/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add OpenRouter key/ })).toBeInTheDocument();
    expect(screen.queryByLabelText("Normal research model")).toBeNull();
    expect(screen.queryByLabelText("Deep research model")).toBeNull();
    expect(screen.queryByLabelText("Ultra research model")).toBeNull();
  });

  it("Tier B with a key shows key presence (never the value) + three per-stop rows", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter"
        ? Promise.resolve("sk-or-v1-secret")
        : Promise.resolve(null),
    );
    render(<SettingsPanel />);
    expect(await screen.findByText(/OpenRouter key configured/)).toBeInTheDocument();
    expect(screen.queryByText(/sk-or-v1-secret/)).toBeNull();
    expect(screen.getByLabelText("Normal research model")).toBeInTheDocument();
    expect(screen.getByLabelText("Deep research model")).toBeInTheDocument();
    expect(screen.getByLabelText("Ultra research model")).toBeInTheDocument();
  });

  it("Tier B per-stop rows render the verified pricing hints from the shared constant", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter" ? Promise.resolve("sk-or-key") : Promise.resolve(null),
    );
    render(<SettingsPanel />);
    await screen.findByLabelText("Normal research model");
    // The three verified defaults render their exact verified hints.
    expect(screen.getByText("$1/M in · $1/M out · $5/1k searches")).toBeInTheDocument();
    expect(screen.getByText("$2/M in · $8/M out · $5/1k searches")).toBeInTheDocument();
    expect(
      screen.getByText("$2/M in · $8/M out · $5/1k searches · $3/M reasoning"),
    ).toBeInTheDocument();
  });

  it("swapping a per-stop model writes the store; live-verified prices render unflagged", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter" ? Promise.resolve("sk-or-key") : Promise.resolve(null),
    );
    render(<SettingsPanel />);
    const normal = await screen.findByLabelText("Normal research model");
    // (R15-LIFECYCLE-006: the swap target was a now-retired o3 slug; the
    // behaviour under test is unchanged on a live option.)
    fireEvent.change(normal, { target: { value: "perplexity/sonar-pro" } });
    expect(useSearchSettingsStore.getState().researchModels.normal).toBe("perplexity/sonar-pro");
    // The picker prices were verified live (priceVerified: true), so the hint
    // renders WITHOUT the estimate flag.
    expect(screen.getByText("$3/M in · $15/M out · $5/1k searches")).toBeInTheDocument();
    // The other stops are untouched.
    expect(useSearchSettingsStore.getState().researchModels.deep).toBe(
      DEFAULT_RESEARCH_MODELS.deep,
    );
    expect(useSearchSettingsStore.getState().researchModels.ultra).toBe(
      DEFAULT_RESEARCH_MODELS.ultra,
    );
  });

  it("a persisted custom slug stays selectable (never silently deselected)", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter" ? Promise.resolve("sk-or-key") : Promise.resolve(null),
    );
    useSearchSettingsStore.getState().setResearchModel("deep", "acme/research-x1");
    render(<SettingsPanel />);
    const deep = (await screen.findByLabelText("Deep research model")) as HTMLSelectElement;
    expect(deep.value).toBe("acme/research-x1");
    expect(screen.getByText("Custom model — pricing on its OpenRouter page")).toBeInTheDocument();
  });

  // ---- R15-LIFECYCLE-006: options absent from the live catalog are badged ----

  /** Seed a FRESH live OpenRouter catalog (the TTL cache skips the fetch). */
  function liveCatalog(ids: string[]) {
    useModelCatalogStore.setState({
      byProvider: {
        openrouter: {
          models: ids.map((id) => ({ id, label: id })),
          source: "live",
          fetchedAt: Date.now(),
          loading: false,
        },
      },
    });
  }

  it("a static option absent from the live catalog is badged unavailable", async () => {
    resetModelCatalogStoreForTests();
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter" ? Promise.resolve("sk-or-key") : Promise.resolve(null),
    );
    // The ULTRA default (sonar-deep-research) is missing from this catalog.
    liveCatalog(["perplexity/sonar", "perplexity/sonar-reasoning-pro", "perplexity/sonar-pro"]);
    render(<SettingsPanel />);
    expect(
      await screen.findByText(/ultra research will fail until you pick another model/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/normal research will fail/)).toBeNull();
    const ultra = screen.getByLabelText("Ultra research model") as HTMLSelectElement;
    expect(ultra.value).toBe(DEFAULT_RESEARCH_MODELS.ultra); // never silently rewritten
    expect(
      within(ultra).getByRole("option", { name: /Sonar Deep Research \(unavailable\)/ }),
    ).toBeInTheDocument();
  });

  it("a persisted selection absent from the live catalog is badged, not rewritten", async () => {
    resetModelCatalogStoreForTests();
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter" ? Promise.resolve("sk-or-key") : Promise.resolve(null),
    );
    useSearchSettingsStore.getState().setResearchModel("deep", "openai/o3-deep-research");
    liveCatalog([
      "perplexity/sonar",
      "perplexity/sonar-reasoning-pro",
      "perplexity/sonar-deep-research",
    ]);
    render(<SettingsPanel />);
    expect(
      await screen.findByText(/deep research will fail until you pick another model/),
    ).toBeInTheDocument();
    expect(useSearchSettingsStore.getState().researchModels.deep).toBe("openai/o3-deep-research");
  });

  it("Copy diagnostics previews the redacted bundle before anything is copied", async () => {
    routeFetch({
      "/system/diagnostics": { version: "0.8.0", logTail: ["[sidecar] GET /quotes/<id>"] },
    });
    const writeText = vi.fn(() => Promise.resolve());
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });

    render(<SettingsPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Copy diagnostics" }));

    const preview = await screen.findByLabelText("Diagnostics preview");
    expect(preview.textContent).toContain("[sidecar] GET /quotes/<id>");
    expect(writeText).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Copy to clipboard" }));
    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(preview.textContent);
  });

  it("has no axe violations in its default (Preferences) state (R15-UI-071 smoke)", async () => {
    const { container } = render(<SettingsPanel />);
    // Let the async sidecar-status probes settle before scanning — several
    // sections render a different (still-labelled) fallback once /health
    // resolves, and scanning mid-fetch would pin a transient DOM instead.
    await screen.findByRole("region", { name: "Modules" });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
