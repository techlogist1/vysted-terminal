import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { searxngChipMeta, SettingsPanel } from "@/components/SettingsPanel";
import { vystedModules } from "@/modules";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { resetKeybindingsStoreForTests, useKeybindingsStore } from "@/store/keybindings";
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

// Resolve the sidecar base instantly (no Tauri invoke / health probe under
// test); the per-test fetch stubs below decide what each endpoint returns.
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

const getSecretMock = vi.mocked(getSecret);

/** A 200 JSON response for the fetch stubs. */
function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

/** Stub global fetch with a path → payload router (unrouted paths 404). */
function routeFetch(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
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
    useProviderKeysStore.setState({ status: {}, probed: false });
    // Default: no network — every sidecar fetch fails fast and the surfaces
    // render their honest "unavailable" fallbacks. Tier tests route real paths.
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("no network under test"))),
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

  // ---- Preferences (R9 settings-truth: dead controls stay dead) ----

  it("the unread provider-preference-order group is gone (R9 kill)", () => {
    render(<SettingsPanel />);
    expect(screen.queryByText("Provider preference order")).toBeNull();
    expect(screen.queryByRole("button", { name: /Move .* up/ })).toBeNull();
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
    expect(fetchMock).toHaveBeenCalledWith("http://sidecar.test/search/searxng/setup", {
      method: "POST",
    });
  });

  it("Tier A [Stop] POSTs /search/searxng/teardown and renders the post-teardown state", async () => {
    const fetchMock = routeFetch({
      "/search/searxng/status": searxngStatus("ready", { url: "http://127.0.0.1:8888" }),
      "/search/searxng/teardown": searxngStatus("docker_present_not_setup"),
    });
    render(<SettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Stop" }));
    expect(await screen.findByRole("button", { name: "Set up" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("http://sidecar.test/search/searxng/teardown", {
      method: "POST",
    });
  });

  it("Tier A shows the honest fallback note whenever the instance is not ready", async () => {
    routeFetch({ "/search/searxng/status": searxngStatus("docker_present_not_setup") });
    render(<SettingsPanel />);
    expect(
      await screen.findByText(/Until set up, research uses limited keyless search/),
    ).toBeInTheDocument();
  });

  it("Tier A degrades honestly when the sidecar is unreachable", async () => {
    render(<SettingsPanel />); // default fetch stub rejects
    expect(
      await screen.findByText(/SearXNG status unavailable \(sidecar not connected\)/),
    ).toBeInTheDocument();
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

  it("swapping a per-stop model writes the store; unverified picks are marked estimates", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter" ? Promise.resolve("sk-or-key") : Promise.resolve(null),
    );
    render(<SettingsPanel />);
    const normal = await screen.findByLabelText("Normal research model");
    fireEvent.change(normal, { target: { value: "openai/o3-deep-research" } });
    expect(useSearchSettingsStore.getState().researchModels.normal).toBe("openai/o3-deep-research");
    // The unverified alternate's hint is flagged as an estimate.
    expect(screen.getByText("$10/M in · $40/M out · estimate")).toBeInTheDocument();
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
});
