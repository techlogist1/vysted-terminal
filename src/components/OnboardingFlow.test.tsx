import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OnboardingFlow } from "@/components/OnboardingFlow";
import { useSafetyStore } from "@/store/safety";
import { useOnboardingStore } from "@/store/onboarding";

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
