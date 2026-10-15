import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingFlow } from "@/components/OnboardingFlow";
import { EXAMPLE_QUESTION } from "@/components/onboarding/example";
import { fetchLocalModelRecommendation, type LocalModelRecommendation } from "@/lib/hardware-fit";
import { STOPPED_ENGINE } from "@/lib/local-engine";
import { LocalModelsError } from "@/lib/local-models";
import { useAgentCommandStore } from "@/store/agent-command";
import { useAgentDockStore } from "@/store/agent-dock";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore, WARMING_UP } from "@/store/local-models";
import { useOnboardingStore } from "@/store/onboarding";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useSafetyStore } from "@/store/safety";
import { openExternal } from "@/components/onboarding/shared";
import type { CatalogModel, DownloadState, LocalHardwareInfo } from "../../types/data";

const appMeta = vi.hoisted(() => new Map<string, string>());
const secrets = vi.hoisted(() => new Map<string, string>());
const validateProvider = vi.hoisted(() => vi.fn());
const loadSymbolIntoChart = vi.hoisted(() => vi.fn());

vi.mock("@/lib/hardware-fit", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/hardware-fit")>()),
  fetchLocalModelRecommendation: vi.fn(),
  fetchOllamaStatus: vi.fn().mockResolvedValue({ running: false, endpoint: "", models: [] }),
}));
vi.mock("@/lib/keychain", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/keychain")>()),
  getSecret: vi.fn(async (k: string) => secrets.get(k) ?? null),
  setSecret: vi.fn(async (k: string, v: string) => void secrets.set(k, v)),
  getAppMeta: vi.fn(async (k: string) => appMeta.get(k) ?? null),
  setAppMeta: vi.fn(async (k: string, v: string) => void appMeta.set(k, v)),
}));
vi.mock("@/lib/provider-validation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/provider-validation")>()),
  validateProvider,
}));
vi.mock("@/lib/host-actions", () => ({ loadSymbolIntoChart }));
vi.mock("@/components/onboarding/shared", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/onboarding/shared")>()),
  openExternal: vi.fn(async () => undefined),
}));

const GB = 1024 ** 3;
const model = (id: string, gb: number, fits: CatalogModel["fits"] = "good"): CatalogModel => ({
  id,
  name: `Model ${id}`,
  family: "qwen",
  params: "8B",
  quant: "Q4",
  sizeBytes: gb * GB,
  diskNeededBytes: (gb + 1) * GB,
  minRamBytes: 8 * GB,
  licence: { id: "apache-2.0", name: "Apache 2.0", url: "https://example.org/licence" },
  purpose: `Good for everyday questions (${id}).`,
  url: "https://example.org/m.gguf",
  sha256: "0".repeat(64),
  fits,
});
const BIG = model("big", 5);
const SMALL = model("small", 2);
const TINY = model("tiny", 1);
const HW: LocalHardwareInfo = {
  os: "macos",
  arch: "arm64",
  totalRamBytes: 16 * GB,
  availableRamBytes: 10 * GB,
  gpu: null,
  freeDiskBytes: 100 * GB,
  modelsDir: "/data/models",
};
const dl = (state: DownloadState["state"], pct: number, error: string | null = null) => ({
  id: "big",
  state,
  receivedBytes: (BIG.sizeBytes * pct) / 100,
  totalBytes: BIG.sizeBytes,
  bytesPerSec: state === "downloading" ? 10 * 1024 ** 2 : null,
  error,
  retryable: true,
});

function _rec(estimated: boolean): LocalModelRecommendation {
  return {
    device: {
      ramGib: 8,
      gpuBudgetGib: 4.4,
      totalCores: 4,
      perfCores: 4,
      isAppleSilicon: false,
      arch: "AMD64",
      chip: "unknown",
      osName: "Windows",
      osVersion: "10",
      estimated,
    },
    candidates: [],
    recommended: null,
  };
}

const actions = {
  refresh: vi.fn(),
  download: vi.fn(),
  activate: vi.fn(),
  cancel: vi.fn(),
};

function seedModels(over: Partial<ReturnType<typeof useLocalModelsStore.getState>> = {}) {
  useLocalModelsStore.setState({
    hardware: HW,
    catalog: { models: [BIG, SMALL], recommendedId: "big", tier: "16gb", reason: "" },
    installed: [],
    downloads: {},
    activeModelId: null,
    loadError: null,
    ...actions,
    ...over,
  });
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

beforeEach(() => {
  appMeta.clear();
  secrets.clear();
  for (const fn of Object.values(actions)) fn.mockReset();
  actions.refresh.mockResolvedValue(undefined);
  actions.download.mockResolvedValue(dl("downloading", 0));
  actions.activate.mockResolvedValue({ ...STOPPED_ENGINE, state: "ready", port: 1 });
  validateProvider.mockReset().mockResolvedValue({ ok: true, reason: null, detail: null });
  loadSymbolIntoChart.mockReset();
  vi.mocked(openExternal).mockReset().mockResolvedValue(undefined);
  vi.mocked(fetchLocalModelRecommendation).mockResolvedValue(_rec(false));
  useSafetyStore.setState({ firstLaunchTosAcked: true });
  useOnboardingStore.setState({
    seen: false,
    forceOpen: false,
    forceStep: null,
    waitingQuestion: null,
  });
  useLocalEngineStore.setState({ status: STOPPED_ENGINE });
  useAppStore.setState({ sidecarStatus: "connected" });
  useProviderKeysStore.setState({ refreshOne: vi.fn().mockResolvedValue(undefined) });
  useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
  useAgentDockStore.setState({ collapsed: true });
  useAgentCommandStore.setState({ command: null });
  seedModels();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// R15-UI-052: the first step must state the real data flow, never "nothing
// leaves this computer", and never call the local path fully private/offline.
describe("OnboardingFlow welcome step (R15-UI-052)", () => {
  it("does not claim keyless web research, and states the real data-flow instead of 'nothing leaves this computer'", async () => {
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    expect(dialog).not.toHaveTextContent(
      /live quotes, charts, news, screeners and web research run right now/i,
    );
    expect(dialog).not.toHaveTextContent(/nothing leaves this computer/i);
    expect(dialog).toHaveTextContent(/market data and web searches go to public providers/i);
  });

  it("the local-model path card does not claim 'fully private' / 'offline'", async () => {
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    expect(dialog).not.toHaveTextContent(/fully private/i);
    expect(dialog).not.toHaveTextContent(/it's yours and offline/i);
  });

  it("asks how Vysted should think, with the three choices", async () => {
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    expect(dialog).toHaveTextContent("How should Vysted think?");
    for (const name of [/On this computer/, /My own API key/, /Skip for now/]) {
      expect(within(dialog).getByRole("button", { name })).toBeInTheDocument();
    }
  });

  // F4: on a short window (minHeight 600) the local step is taller than the
  // viewport — the dialog must clamp to it and scroll, never clip its buttons.
  it("is height-capped to the viewport and scrolls instead of clipping", async () => {
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    expect(dialog).toHaveClass("max-h-[calc(100dvh-2rem)]", "overflow-y-auto"); // tokens-ok: asserts the viewport clamp
    expect(dialog).not.toHaveClass("overflow-hidden");
  });

  it("waits for the terms first", async () => {
    useSafetyStore.setState({ firstLaunchTosAcked: false });
    render(<OnboardingFlow />);
    await flush();
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
  });
});

describe("OnboardingFlow local-model step device chip (R15-CROSS-PLATFORM-003)", () => {
  beforeEach(() => {
    useOnboardingStore.setState({ seen: true, forceOpen: true, forceStep: "local" });
  });

  it("shows an 'estimated' chip when the sidecar could not measure RAM", async () => {
    vi.mocked(fetchLocalModelRecommendation).mockResolvedValue(_rec(true));
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    expect(await within(dialog).findByText(/estimated/i)).toBeInTheDocument();
  });

  it("shows no chip when RAM was measured", async () => {
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    await within(dialog).findByText(/RAM/);
    await flush();
    expect(within(dialog).queryByText(/estimated/i)).not.toBeInTheDocument();
  });
});

describe("On this computer", () => {
  async function openLocal(ready = true) {
    render(<OnboardingFlow />);
    fireEvent.click(await screen.findByRole("button", { name: /On this computer/ }));
    if (ready) await screen.findByRole("radiogroup", { name: "Models" });
  }

  it("Back returns to the choice step on a first run (not a re-open)", async () => {
    await openLocal();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByText("How should Vysted think?")).toBeInTheDocument();
  });

  it("preselects the recommended model and shows size, disk, purpose and the licence before the download button", async () => {
    await openLocal();
    const radio = screen.getByRole("radio", { name: /Model big/ });
    expect(radio).toHaveAttribute("aria-checked", "true");
    expect(radio).toHaveTextContent("5.0 GB download");
    expect(radio).toHaveTextContent("needs 6.0 GB free");
    expect(radio).toHaveTextContent("Good for everyday questions (big).");
    expect(radio).toHaveTextContent("Runs well here");
    const licence = within(radio).getByText(/Licence: Apache 2.0/);
    const button = screen.getByRole("button", { name: /Download Model big/ });
    expect(licence.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("starting the download lets the user continue to the tour, which waits behind the download", async () => {
    await openLocal();
    actions.download.mockImplementation(async () => {
      useLocalModelsStore.setState({ downloads: { big: dl("downloading", 42) } });
      return dl("downloading", 42);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Download Model big/ }));
    });
    expect(actions.download).toHaveBeenCalledWith("big");
    expect(screen.getByTestId("download-active")).toHaveTextContent(
      /We'll finish in the background/,
    );
    fireEvent.click(screen.getByRole("button", { name: /Continue/ }));
    expect(await screen.findByTestId("onboarding-tour")).toBeInTheDocument();
    expect(appMeta.get("onboarding-complete")).toBe("local");
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByTestId("onboarding-tour")).toHaveTextContent(
      "Your model is still downloading (42%) — we'll let you know",
    );
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    });
    expect(useOnboardingStore.getState().waitingQuestion).toBe(EXAMPLE_QUESTION);
    expect(useAgentCommandStore.getState().command).toBeNull();
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
  });

  it("first launch while the data engine is still starting says so and retries quietly", async () => {
    vi.useFakeTimers();
    seedModels({ catalog: null, hardware: null, loadError: WARMING_UP });
    useAppStore.setState({ sidecarStatus: "connecting" });
    useOnboardingStore.setState({ forceOpen: true, forceStep: "local" });
    render(<OnboardingFlow />);
    await flush();
    expect(
      screen.getByText(/Getting things ready — the first launch takes about a minute/),
    ).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    const before = actions.refresh.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(actions.refresh.mock.calls.length).toBeGreaterThan(before);
  });

  it("no internet: the failed download explains itself and offers Retry / own key / skip", async () => {
    seedModels({ downloads: { big: dl("failed", 0, "No internet connection") } });
    await openLocal();
    const notice = screen.getByTestId("download-stopped");
    expect(notice).toHaveTextContent("No internet connection");
    fireEvent.click(within(notice).getByRole("button", { name: "Try again" }));
    expect(actions.download).toHaveBeenCalledWith("big");
    fireEvent.click(within(notice).getByRole("button", { name: "Use my own key" }));
    expect(await screen.findByRole("radiogroup", { name: "Provider" })).toBeInTheDocument();
  });

  it("no internet when starting the download says so", async () => {
    vi.stubGlobal("navigator", { ...navigator, onLine: false });
    actions.download.mockRejectedValue(new TypeError("Load failed"));
    await openLocal();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Download Model big/ }));
    });
    expect(screen.getByTestId("start-error")).toHaveTextContent("No internet connection");
  });

  it("a download that died shows paused at the right percent with Resume", async () => {
    seedModels({
      downloads: { big: dl("paused", 37, "Download was interrupted — resume to continue") },
    });
    await openLocal();
    const notice = screen.getByTestId("download-stopped");
    expect(notice).toHaveTextContent("paused at 37%");
    fireEvent.click(within(notice).getByRole("button", { name: "Resume" }));
    expect(actions.download).toHaveBeenCalledWith("big");
  });

  it("not enough disk: shows the numbers and picks a smaller model", async () => {
    seedModels({ hardware: { ...HW, freeDiskBytes: 4 * GB } });
    await openLocal();
    const notice = screen.getByTestId("disk-short");
    expect(notice).toHaveTextContent("needs 6.0 GB free and there is 4.0 GB");
    expect(screen.getByRole("button", { name: /Download Model big/ })).toBeDisabled();
    fireEvent.click(within(notice).getByRole("button", { name: /Pick Model small/ }));
    expect(screen.getByRole("radio", { name: /Model small/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.queryByTestId("disk-short")).toBeNull();
  });

  it("a 409 from the download shows the server's numbers", async () => {
    actions.download.mockRejectedValue(new LocalModelsError("disk", "short", 7 * GB, 3 * GB));
    await openLocal();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Download Model big/ }));
    });
    expect(screen.getByTestId("disk-short")).toHaveTextContent(
      "needs 7.0 GB free and there is 3.0 GB",
    );
  });

  it("low memory: a plain warning with a way to use your own key", async () => {
    seedModels({ hardware: { ...HW, availableRamBytes: 2 * GB } });
    await openLocal();
    const notice = screen.getByTestId("low-ram");
    expect(notice).toHaveTextContent(/Closing your web browser/);
    fireEvent.click(within(notice).getByRole("button", { name: /Use my own key/ }));
    expect(await screen.findByRole("radiogroup", { name: "Provider" })).toBeInTheDocument();
  });

  it("low memory also shows for a tight fit or a small machine", async () => {
    seedModels({
      catalog: {
        models: [model("big", 5, "tight")],
        recommendedId: "big",
        tier: "8gb",
        reason: "",
      },
    });
    await openLocal();
    expect(screen.getByTestId("low-ram")).toBeInTheDocument();
  });

  it("the engine will not start: reason + Try again / smaller model / own key", async () => {
    seedModels({
      installed: [
        {
          id: "big",
          name: "Model big",
          path: "/m/big.gguf",
          sizeBytes: 1,
          verified: true,
          active: false,
        },
      ],
    });
    useLocalEngineStore.setState({
      status: { ...STOPPED_ENGINE, state: "failed", modelId: "big", error: "Not enough memory." },
    });
    actions.activate.mockResolvedValue({ ...STOPPED_ENGINE, state: "failed" });
    await openLocal();
    const notice = screen.getByTestId("engine-failed");
    expect(notice).toHaveTextContent("Not enough memory.");
    await act(async () => {
      fireEvent.click(within(notice).getByRole("button", { name: "Try again" }));
    });
    expect(actions.activate).toHaveBeenCalledWith("big");
    expect(screen.getByTestId("engine-failed")).toBeInTheDocument();
    fireEvent.click(within(notice).getByRole("button", { name: "Use a smaller model" }));
    expect(screen.getByRole("radio", { name: /Model small/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("a real load error (not warming up) offers Try again, own key and skip", async () => {
    useAppStore.setState({ sidecarStatus: "connected" });
    seedModels({ catalog: null, hardware: null, loadError: "sidecar said no" });
    useOnboardingStore.setState({ forceOpen: true, forceStep: "local" });
    render(<OnboardingFlow />);
    await screen.findByText(/Couldn't load the list of models/);
    expect(screen.getByText(/sidecar said no/)).toBeInTheDocument();
    const before = actions.refresh.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(actions.refresh.mock.calls.length).toBeGreaterThan(before);
  });

  it("clicking a model's own tile selects it, and the keyboard selects it too", async () => {
    await openLocal();
    fireEvent.click(screen.getByRole("radio", { name: /Model small/ }));
    expect(screen.getByRole("radio", { name: /Model small/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.keyDown(screen.getByRole("radio", { name: /Model big/ }), { key: "Enter" });
    expect(screen.getByRole("radio", { name: /Model big/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("clicking the licence link opens it externally without also selecting a different model", async () => {
    await openLocal();
    fireEvent.click(screen.getByRole("radio", { name: /Model small/ }));
    const radio = screen.getByRole("radio", { name: /Model big/ });
    fireEvent.click(within(radio).getByText(/Licence: Apache 2.0/));
    expect(openExternal).toHaveBeenCalledWith(BIG.licence.url);
    // The licence click must not have re-selected Model big over Model small.
    expect(screen.getByRole("radio", { name: /Model small/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("picking a smaller model among two candidates compares them by disk size", async () => {
    seedModels({
      catalog: { models: [BIG, SMALL, TINY], recommendedId: "big", tier: "16gb", reason: "" },
      hardware: { ...HW, freeDiskBytes: 4 * GB },
    });
    await openLocal();
    const notice = screen.getByTestId("disk-short");
    fireEvent.click(within(notice).getByRole("button", { name: /Pick Model small/ }));
    expect(screen.getByRole("radio", { name: /Model small/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("a model already installed outside the catalog can be used directly, and a start failure shows plainly", async () => {
    seedModels({
      installed: [
        {
          id: "extra",
          name: "Extra Model",
          path: "/m/extra.gguf",
          sizeBytes: 1,
          verified: true,
          active: false,
        },
      ],
    });
    await openLocal();
    const row = screen.getByText("Extra Model").closest("div")!;
    actions.activate.mockResolvedValueOnce({ ...STOPPED_ENGINE, state: "ready", port: 1 });
    await act(async () => {
      fireEvent.click(within(row).getByRole("button", { name: "Use this one" }));
    });
    expect(actions.activate).toHaveBeenCalledWith("extra");
    expect(await screen.findByTestId("onboarding-tour")).toBeInTheDocument();
  });

  it("using the selected (already installed) model surfaces a plain message when activation throws", async () => {
    seedModels({
      installed: [
        {
          id: "big",
          name: "Model big",
          path: "/m/big.gguf",
          sizeBytes: 1,
          verified: true,
          active: false,
        },
      ],
    });
    actions.activate.mockRejectedValue(new Error("sidecar vanished"));
    await openLocal();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Use Model big/ }));
    });
    expect(screen.getByTestId("start-error")).toHaveTextContent("sidecar vanished");
  });

  it("a download failure that is neither a disk error nor offline shows its own message", async () => {
    actions.download.mockRejectedValue(new Error("sidecar exploded"));
    await openLocal();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Download Model big/ }));
    });
    expect(screen.getByTestId("start-error")).toHaveTextContent("sidecar exploded");
  });

  it("the local step's own Skip for now link ends the flow the same as the top-level one", async () => {
    await openLocal();
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    expect(await screen.findByTestId("onboarding-tour")).toBeInTheDocument();
    expect(appMeta.get("onboarding-complete")).toBe("skip");
  });
});

describe("My own API key", () => {
  async function openKey() {
    render(<OnboardingFlow />);
    fireEvent.click(await screen.findByRole("button", { name: /My own API key/ }));
    await screen.findByRole("radiogroup", { name: "Provider" });
  }

  it("lists OpenRouter first and validates the key before saving it and making it the default", async () => {
    await openKey();
    const radios = within(screen.getByRole("radiogroup", { name: "Provider" })).getAllByRole(
      "radio",
    );
    expect(radios[0]).toHaveTextContent("OpenRouter");
    expect(radios.map((r) => r.textContent)).not.toContain("On this computer");
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: " sk-or-1 " } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(validateProvider).toHaveBeenCalledWith("openrouter", { apiKey: "sk-or-1" });
    expect(secrets.get("llm-provider:openrouter")).toBe("sk-or-1");
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("openrouter");
    expect(await screen.findByTestId("onboarding-tour")).toBeInTheDocument();
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    fireEvent.click(screen.getByRole("button", { name: /Ask:/ }));
    expect(useAgentCommandStore.getState().command?.prompt).toBe(EXAMPLE_QUESTION);
    expect(useAgentDockStore.getState().collapsed).toBe(false);
  });

  it("a rejected key is never saved", async () => {
    validateProvider.mockResolvedValue({ ok: false, reason: "invalid", detail: null });
    await openKey();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "bad" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toHaveTextContent("didn't accept that key");
    expect(secrets.size).toBe(0);
  });

  it("no internet says so plainly", async () => {
    vi.stubGlobal("navigator", { ...navigator, onLine: false });
    validateProvider.mockResolvedValue({ ok: false, reason: "unreachable", detail: "x" });
    await openKey();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "k" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toHaveTextContent("No internet connection");
  });
});

describe("shows once", () => {
  it("Skip for now writes the marker and ends on the chart example", async () => {
    render(<OnboardingFlow />);
    fireEvent.click(await screen.findByRole("button", { name: /Skip for now/ }));
    await screen.findByTestId("onboarding-tour");
    expect(appMeta.get("onboarding-complete")).toBe("skip");
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Show Reliance on the chart/ }));
    });
    expect(loadSymbolIntoChart).toHaveBeenCalledWith("RELIANCE.NS", "1d", "IN");
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
  });

  it("skipping the tour still counts as done", async () => {
    render(<OnboardingFlow />);
    fireEvent.click(await screen.findByRole("button", { name: /Skip for now/ }));
    await screen.findByTestId("onboarding-tour");
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Skip the tour" }));
    });
    expect(appMeta.get("onboarding-complete")).toBe("skip");
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
  });

  it("never opens again once the marker exists", async () => {
    appMeta.set("onboarding-complete", "skip");
    useOnboardingStore.setState({ seen: null });
    render(<OnboardingFlow />);
    await flush();
    expect(useOnboardingStore.getState().seen).toBe(true);
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
  });

  it("a CTA re-opens it at the key step, and saving closes without the tour", async () => {
    useOnboardingStore.setState({ seen: true });
    render(<OnboardingFlow />);
    act(() => useOnboardingStore.getState().open("key"));
    fireEvent.change(await screen.findByLabelText(/API key/), { target: { value: "k" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.queryByTestId("onboarding-tour")).toBeNull();
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
    expect(useOnboardingStore.getState().forceOpen).toBe(false);
  });

  it("on a re-open, Back closes the whole flow instead of returning to the choice step", async () => {
    useOnboardingStore.setState({ seen: true, forceOpen: true, forceStep: "local" });
    render(<OnboardingFlow />);
    await screen.findByRole("radiogroup", { name: "Models" });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Back" }));
    });
    expect(screen.queryByTestId("onboarding-flow")).toBeNull();
    expect(appMeta.get("onboarding-complete")).toBe("seen");
  });

  it("ignores Escape and an outside click while the dialog is open", async () => {
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    fireEvent.keyDown(dialog, { key: "Escape", code: "Escape" });
    expect(screen.getByTestId("onboarding-flow")).toBeInTheDocument();
    fireEvent.pointerDown(document.body);
    fireEvent.mouseDown(document.body);
    expect(screen.getByTestId("onboarding-flow")).toBeInTheDocument();
  });
});
