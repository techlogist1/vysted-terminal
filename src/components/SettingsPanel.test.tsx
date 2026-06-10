import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPanel, t1EngineStatusLine } from "@/components/SettingsPanel";
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
    // Research search tiers — the one search surface.
    expect(screen.getByRole("radiogroup", { name: "Research search tier" })).toBeInTheDocument();
    // Region
    expect(screen.getByLabelText("Region")).toBeInTheDocument();
    // Advanced
    expect(screen.getByRole("button", { name: /Open Marketplace/i })).toBeInTheDocument();
    expect(screen.getByLabelText("New layout name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Import settings/i })).toBeInTheDocument();
  });

  it("the custom SearXNG URL survives inside the t2 detail and writes the store", () => {
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Unlimited Research/));
    const url = screen.getByLabelText("SearXNG URL");
    expect(url).toBeInTheDocument();
    fireEvent.change(url, { target: { value: "http://10.0.0.5:8080" } });
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://10.0.0.5:8080");
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
    const t3 = tierRadio(/BYOK search \(hosted or Exa direct\)/);
    expect(t1).toHaveAttribute("aria-checked", "true");
    expect(t2).toHaveAttribute("aria-checked", "false");
    expect(t3).toHaveAttribute("aria-checked", "false");
  });

  it("selecting a tier updates the search-settings store", () => {
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/Unlimited Research/));
    expect(useSearchSettingsStore.getState().researchTier).toBe("t2_searxng");
    fireEvent.click(tierRadio(/BYOK search/));
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

  it("T3 defaults to the OpenRouter sub-mode with the engine segmented control", async () => {
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/BYOK search/));

    const modes = screen.getByRole("radiogroup", { name: "BYOK search mode" });
    expect(within(modes).getByRole("radio", { name: "Via OpenRouter" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(within(modes).getByRole("radio", { name: "Exa direct" })).toHaveAttribute(
      "aria-checked",
      "false",
    );

    const engines = screen.getByRole("radiogroup", { name: "Hosted search engine" });
    const firecrawl = within(engines).getByRole("radio", { name: "Firecrawl" });
    expect(firecrawl).toHaveAttribute("aria-checked", "true");
    // Honest default-engine cost line: free credits, then OpenRouter billing.
    expect(screen.getByText(/Starts on free credits/)).toBeInTheDocument();

    fireEvent.click(within(engines).getByRole("radio", { name: "Exa" }));
    expect(useSearchSettingsStore.getState().hostedEngine).toBe("exa");
    // Honest per-search cost line for Exa, flagged as driftable.
    expect(screen.getByText(/~\$0\.005 per search/)).toBeInTheDocument();
  });

  it("T3 points to AI Providers when no OpenRouter key is stored", async () => {
    getSecretMock.mockResolvedValue(null); // keychain reachable, no key
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/BYOK search/));
    expect(await screen.findByText(/add one under AI Providers above/)).toBeInTheDocument();
  });

  it("T3 shows key presence (never the value) when an OpenRouter key is stored", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "llm-provider:openrouter"
        ? Promise.resolve("sk-or-v1-secret")
        : Promise.resolve(null),
    );
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/BYOK search/));
    expect(await screen.findByText(/OpenRouter key configured/)).toBeInTheDocument();
    expect(screen.queryByText(/sk-or-v1-secret/)).toBeNull();
  });

  // ---- T3 "Exa direct" sub-mode (R8 — the legacy Exa keychain slot lives on) ----

  it("switching to Exa direct flips the store and swaps in the key card", async () => {
    getSecretMock.mockResolvedValue(null); // keychain reachable, no key stored
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/BYOK search/));

    const modes = screen.getByRole("radiogroup", { name: "BYOK search mode" });
    fireEvent.click(within(modes).getByRole("radio", { name: "Exa direct" }));
    expect(useSearchSettingsStore.getState().exaDirect).toBe(true);

    // The hosted engine control yields to the Exa key card.
    expect(screen.queryByRole("radiogroup", { name: "Hosted search engine" })).toBeNull();
    expect(
      await screen.findByText(/needs an Exa API key to run — add one below/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Exa API key")).toBeInTheDocument();
  });

  it("Exa direct shows key presence from the legacy keychain slot (never the value)", async () => {
    getSecretMock.mockImplementation((account: string) =>
      account === "plugin-secret:vysted-search-exa:exa_api_key"
        ? Promise.resolve("exa-secret-123")
        : Promise.resolve(null),
    );
    useSearchSettingsStore.getState().setExaDirect(true);
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/BYOK search/));

    expect(await screen.findByText(/Exa key configured/)).toBeInTheDocument();
    expect(screen.queryByText(/exa-secret-123/)).toBeNull();
    expect(screen.getByRole("button", { name: /Remove/ })).toBeInTheDocument();
  });

  it("saving an Exa key writes the legacy keychain slot and flips to configured", async () => {
    const { setSecret } = await import("@/lib/keychain");
    const setSecretMock = vi.mocked(setSecret);
    let stored: string | null = null;
    getSecretMock.mockImplementation(() => Promise.resolve(stored));
    setSecretMock.mockImplementation((_account: string, value: string) => {
      stored = value;
      return Promise.resolve();
    });

    useSearchSettingsStore.getState().setExaDirect(true);
    render(<SettingsPanel />);
    fireEvent.click(tierRadio(/BYOK search/));

    const input = await screen.findByLabelText("Exa API key");
    fireEvent.change(input, { target: { value: "exa_new_key" } });
    fireEvent.click(screen.getByRole("button", { name: "Save key" }));

    expect(await screen.findByText(/Exa key configured/)).toBeInTheDocument();
    expect(setSecretMock).toHaveBeenCalledWith(
      "plugin-secret:vysted-search-exa:exa_api_key",
      "exa_new_key",
    );
  });
});
