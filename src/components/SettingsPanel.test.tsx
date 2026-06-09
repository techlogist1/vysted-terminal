import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPanel, nativeSearchStatus, t1EngineStatusLine } from "@/components/SettingsPanel";
import { vystedModules } from "@/modules";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { resetKeybindingsStoreForTests, useKeybindingsStore } from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { useProviderKeysStore } from "@/store/provider-keys";
import { resetSearchSettingsStoreForTests, useSearchSettingsStore } from "@/store/search-settings";
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

  // ---- R7 research search tiers (Track S) ----

  function tierRadio(name: RegExp) {
    const group = screen.getByRole("radiogroup", { name: "Research search tier" });
    return within(group).getByRole("radio", { name });
  }

  it("renders the three research tiers as radio rows, t1 selected by default", () => {
    render(<SettingsPanel />);
    const t1 = tierRadio(/Local scraping \(keyless\)/);
    const t2 = tierRadio(/Unlimited Research \(local SearXNG\)/);
    const t3 = tierRadio(/Hosted search \(BYOK via OpenRouter\)/);
    expect(t1).toHaveAttribute("aria-checked", "true");
    expect(t2).toHaveAttribute("aria-checked", "false");
    expect(t3).toHaveAttribute("aria-checked", "false");
  });

  it("selecting a tier updates the search-settings store", () => {
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Unlimited Research/));
    expect(useSearchSettingsStore.getState().researchTier).toBe("t2_searxng");
    fireEvent.click(tierRadio(/Hosted search/));
    expect(useSearchSettingsStore.getState().researchTier).toBe("t3_hosted");
  });

  it("t1 shows the live per-engine status line from /search/status", async () => {
    routeFetch({
      "/search/status": {
        tier: "t1_keyless",
        available: true,
        engines: [
          {
            id: "duckduckgo",
            label: "DuckDuckGo",
            state: "open",
            cooldown_remaining_s: 24.2,
            detail: "DuckDuckGo cooling down (24s)",
          },
          {
            id: "brave",
            label: "Brave",
            state: "closed",
            cooldown_remaining_s: 0,
            detail: "Brave available",
          },
          {
            id: "mojeek",
            label: "Mojeek",
            state: "closed",
            cooldown_remaining_s: 0,
            detail: "Mojeek available",
          },
        ],
      },
    });
    render(<SettingsPanel />);
    const line = await screen.findByTestId("t1-engine-status");
    expect(line).toHaveTextContent("DuckDuckGo — cooling down 24s · Brave — ok · Mojeek — ok");
  });

  it("t1 status line degrades honestly when the sidecar is unreachable", async () => {
    render(<SettingsPanel />); // default fetch stub rejects
    expect(
      await screen.findByText(/Engine status unavailable \(sidecar not connected\)/),
    ).toBeInTheDocument();
  });

  it("t1EngineStatusLine formats every breaker state honestly", () => {
    expect(
      t1EngineStatusLine([
        { id: "a", label: "DuckDuckGo", state: "open", cooldown_remaining_s: 23.6, detail: "" },
        { id: "b", label: "Brave", state: "half_open", cooldown_remaining_s: 0, detail: "" },
        { id: "c", label: "Mojeek", state: "closed", cooldown_remaining_s: 0, detail: "" },
      ]),
    ).toBe("DuckDuckGo — cooling down 24s · Brave — probing · Mojeek — ok");
  });

  // The T2 guided flow renders each sidecar state machine state VERBATIM.
  function searxngStatus(state: string, extra?: Partial<Record<string, unknown>>) {
    return { state, detail: null, reason: null, port: null, url: null, ...extra };
  }

  async function renderT2(routes: Record<string, unknown>) {
    const fetchMock = routeFetch(routes);
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Unlimited Research/));
    return fetchMock;
  }

  it("T2 not_installed_docker explains + shows a plain-text install hint (no link)", async () => {
    await renderT2({ "/search/searxng/status": searxngStatus("not_installed_docker") });
    expect(await screen.findByText(/Docker isn.t available on this machine/)).toBeInTheDocument();
    const hint = screen.getByText(/docs\.docker\.com/);
    expect(hint).toBeInTheDocument();
    expect(hint.closest("a")).toBeNull(); // plain text, no external nav
  });

  it("T2 docker_present_not_setup offers one-click [Set up]", async () => {
    await renderT2({ "/search/searxng/status": searxngStatus("docker_present_not_setup") });
    expect(await screen.findByRole("button", { name: "Set up" })).toBeInTheDocument();
  });

  it("T2 pulling renders the progress state with the sidecar's detail", async () => {
    await renderT2({
      "/search/searxng/status": searxngStatus("pulling", {
        detail: "pulling searxng/searxng (first run can take a few minutes)",
      }),
    });
    expect(await screen.findByText(/Pulling the SearXNG image/)).toBeInTheDocument();
    expect(screen.getByText(/first run can take a few minutes/)).toBeInTheDocument();
  });

  it("T2 starting renders the starting progress state", async () => {
    await renderT2({ "/search/searxng/status": searxngStatus("starting") });
    expect(await screen.findByText(/Starting the instance/)).toBeInTheDocument();
  });

  it("T2 ready shows the green OK + automatic routing + [Remove]", async () => {
    await renderT2({
      "/search/searxng/status": searxngStatus("ready", {
        port: 8888,
        url: "http://127.0.0.1:8888",
      }),
    });
    expect(
      await screen.findByText(/SearXNG is running at http:\/\/127\.0\.0\.1:8888/),
    ).toBeInTheDocument();
    expect(screen.getByText(/research searches use it automatically/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Remove/ })).toBeInTheDocument();
  });

  it("T2 error shows the reason + [Retry]", async () => {
    await renderT2({
      "/search/searxng/status": searxngStatus("error", {
        reason: "docker pull failed: no space left on device",
      }),
    });
    expect(
      await screen.findByText(/Setup failed: docker pull failed: no space left on device/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry/ })).toBeInTheDocument();
  });

  it("T2 [Set up] POSTs /search/searxng/setup and renders the returned pulling state", async () => {
    const fetchMock = await renderT2({
      "/search/searxng/status": searxngStatus("docker_present_not_setup"),
      "/search/searxng/setup": searxngStatus("pulling", {
        detail: "starting guided setup — checking docker",
      }),
    });
    fireEvent.click(await screen.findByRole("button", { name: "Set up" }));
    expect(await screen.findByText(/Pulling the SearXNG image/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("http://sidecar.test/search/searxng/setup", {
      method: "POST",
    });
  });

  it("T2 [Remove] POSTs /search/searxng/teardown and renders the post-teardown state", async () => {
    const fetchMock = await renderT2({
      "/search/searxng/status": searxngStatus("ready", { url: "http://127.0.0.1:8888" }),
      "/search/searxng/teardown": searxngStatus("docker_present_not_setup"),
    });
    fireEvent.click(await screen.findByRole("button", { name: /Remove/ }));
    expect(await screen.findByRole("button", { name: "Set up" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("http://sidecar.test/search/searxng/teardown", {
      method: "POST",
    });
  });

  it("T3 renders the engine segmented control; switching engines updates the store", async () => {
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Hosted search/));

    const engines = screen.getByRole("radiogroup", { name: "Hosted search engine" });
    const firecrawl = within(engines).getByRole("radio", { name: /Firecrawl \(default\)/ });
    expect(firecrawl).toHaveAttribute("aria-checked", "true");
    // Honest default-engine cost line: free credits, then OpenRouter billing.
    expect(screen.getByText(/Firecrawl starts on free credits/)).toBeInTheDocument();

    fireEvent.click(within(engines).getByRole("radio", { name: "Exa" }));
    expect(useSearchSettingsStore.getState().hostedEngine).toBe("exa");
    // Honest per-search cost line for Exa, flagged as driftable.
    expect(screen.getByText(/~\$0\.005 per search/)).toBeInTheDocument();
  });

  it("T3 points to AI Providers when no OpenRouter key is stored", async () => {
    getSecretMock.mockResolvedValue(null); // keychain reachable, no key
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Hosted search/));
    expect(await screen.findByText(/add one under AI Providers above/)).toBeInTheDocument();
  });

  it("T3 shows key presence (never the value) when an OpenRouter key is stored", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter"
        ? Promise.resolve("sk-or-v1-secret")
        : Promise.resolve(null),
    );
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Hosted search/));
    expect(await screen.findByText(/OpenRouter key configured/)).toBeInTheDocument();
    expect(screen.queryByText(/sk-or-v1-secret/)).toBeNull();
  });
});
