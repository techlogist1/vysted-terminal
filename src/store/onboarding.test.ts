import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/keychain", () => ({
  KEYCHAIN_NAMESPACES: { appMeta: (k: string) => `app-meta:${k}` },
  getSecret: vi.fn(),
  setSecret: vi.fn(),
}));

import { getSecret, setSecret } from "@/lib/keychain";
import { useOnboardingStore } from "@/store/onboarding";

const mockGet = vi.mocked(getSecret);
const mockSet = vi.mocked(setSecret);

describe("onboarding store — first-run gate", () => {
  beforeEach(() => {
    useOnboardingStore.setState({ seen: null, bannerDismissed: null, forceOpen: false });
    vi.clearAllMocks();
  });

  it("seen=false when no completion marker is stored (first run)", async () => {
    mockGet.mockResolvedValue(null);
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(false);
  });

  it("seen=true when a completion marker exists (returning user)", async () => {
    mockGet.mockResolvedValue("2026-06-03|cloud");
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(true);
  });

  it("refresh tolerates a keychain reject (non-Tauri) → seen=false", async () => {
    mockGet.mockRejectedValue(new Error("no keychain"));
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(false);
  });

  it("markSeen persists the choice durably + sets seen + clears forceOpen", async () => {
    useOnboardingStore.setState({ forceOpen: true });
    await useOnboardingStore.getState().markSeen("cloud");
    expect(mockSet).toHaveBeenCalledWith("app-meta:onboarding-complete", "cloud");
    expect(useOnboardingStore.getState().seen).toBe(true);
    expect(useOnboardingStore.getState().forceOpen).toBe(false);
  });

  it("open() forces the flow open (CTA re-entry)", () => {
    useOnboardingStore.getState().open();
    expect(useOnboardingStore.getState().forceOpen).toBe(true);
  });

  it("a dismissed setup banner stays dismissed on the next launch (R15-UI-019)", async () => {
    await useOnboardingStore.getState().dismissBanner();
    expect(mockSet).toHaveBeenCalledWith("app-meta:onboarding-banner-dismissed", "dismissed");

    // Next launch: a fresh store reads the marker back.
    useOnboardingStore.setState({ bannerDismissed: null });
    mockGet.mockResolvedValue("dismissed");
    await useOnboardingStore.getState().refreshBanner();
    expect(mockGet).toHaveBeenCalledWith("app-meta:onboarding-banner-dismissed");
    expect(useOnboardingStore.getState().bannerDismissed).toBe(true);
  });
});
