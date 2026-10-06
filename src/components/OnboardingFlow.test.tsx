import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingFlow } from "@/components/OnboardingFlow";
import { fetchLocalModelRecommendation, type LocalModelRecommendation } from "@/lib/hardware-fit";
import { useSafetyStore } from "@/store/safety";
import { useOnboardingStore } from "@/store/onboarding";

vi.mock("@/lib/hardware-fit", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/hardware-fit")>()),
  fetchLocalModelRecommendation: vi.fn(),
  fetchOllamaStatus: vi.fn().mockResolvedValue({ running: false, endpoint: "", models: [] }),
}));

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

// R15-UI-052: the welcome step used to claim "web research run[s] right now"
// with no key (no keyless web-research surface exists) and "Nothing leaves
// this computer except the model calls you authorize" / the local path
// "fully private… offline" — but tickers and search queries go to public
// providers. Pins the corrected copy.

beforeEach(() => {
  useSafetyStore.setState({ firstLaunchTosAcked: true });
  useOnboardingStore.setState({ seen: false, forceOpen: false, forceStep: null });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

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
});

describe("OnboardingFlow local-model step device chip (R15-CROSS-PLATFORM-003)", () => {
  beforeEach(() => {
    useSafetyStore.setState({ firstLaunchTosAcked: true });
    useOnboardingStore.setState({ seen: true, forceOpen: true, forceStep: "local" });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows an 'estimated' chip when the sidecar could not measure RAM", async () => {
    vi.mocked(fetchLocalModelRecommendation).mockResolvedValue(_rec(true));
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    expect(await within(dialog).findByText(/estimated/i)).toBeInTheDocument();
  });

  it("shows no chip when RAM was measured", async () => {
    vi.mocked(fetchLocalModelRecommendation).mockResolvedValue(_rec(false));
    render(<OnboardingFlow />);
    const dialog = await screen.findByTestId("onboarding-flow");
    await within(dialog).findByText(/RAM/);
    expect(within(dialog).queryByText(/estimated/i)).not.toBeInTheDocument();
  });
});
