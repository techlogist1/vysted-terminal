import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingBanner } from "@/components/OnboardingBanner";
import { __resetProviderProbeCacheForTests } from "@/lib/provider-validation";
import { DEFAULT_PROVIDERS, useLLMProvidersStore } from "@/store/llm-providers";
import { resetModelSelectionStoreForTests } from "@/store/model-selection";
import { useOnboardingStore } from "@/store/onboarding";
import { useProviderKeysStore } from "@/store/provider-keys";

vi.mock("@/lib/sidecar-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

const fetchMock = vi.fn();
function answerValidate(body: { ok: boolean; reason: string | null; detail: string | null }) {
  fetchMock.mockImplementation(
    async () =>
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );
}
const NOT_RUNNING = { ok: false, reason: "unreachable", detail: "Could not reach Ollama." };

describe("OnboardingBanner (R15-UI-019)", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    __resetProviderProbeCacheForTests();
    resetModelSelectionStoreForTests();
    useLLMProvidersStore.setState({ providers: DEFAULT_PROVIDERS, defaultProviderId: "ollama" });
    // The mount-time refreshes read the keychain; keep the seeded state instead.
    useProviderKeysStore.setState({ status: {}, probed: true, refresh: async () => {} });
    useOnboardingStore.setState({ bannerDismissed: false, refreshBanner: async () => {} });
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("no banner for a working local model with no cloud key", async () => {
    answerValidate({ ok: true, reason: null, detail: null });
    render(<OnboardingBanner />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows when no key is set and the local model is not reachable", async () => {
    answerValidate(NOT_RUNNING);
    render(<OnboardingBanner />);
    expect(await screen.findByRole("status")).toHaveTextContent(/Add a cloud provider key/);
  });

  it("does not claim nothing leaves the machine (R15-UI-052) — only keys do not", async () => {
    answerValidate(NOT_RUNNING);
    render(<OnboardingBanner />);
    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent(/market data and web searches still go to public providers/i);
    expect(status).not.toHaveTextContent(/nothing leaves this machine/i);
  });

  it("a dismissal survives a remount", async () => {
    answerValidate(NOT_RUNNING);
    const first = render(<OnboardingBanner />);
    fireEvent.click(await screen.findByRole("button", { name: "Dismiss" }));
    first.unmount();

    render(<OnboardingBanner />);
    expect(useOnboardingStore.getState().bannerDismissed).toBe(true);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
