import { beforeEach, describe, expect, it, vi } from "vitest";

const appMeta = vi.hoisted(() => new Map<string, string>());

vi.mock("@/lib/keychain", () => ({
  KEYCHAIN_NAMESPACES: { appMeta: (k: string) => `app-meta:${k}` },
  getSecret: vi.fn(),
  setSecret: vi.fn(),
  getAppMeta: vi.fn(async (key: string) => appMeta.get(key) ?? null),
  setAppMeta: vi.fn(async (key: string, value: string) => {
    appMeta.set(key, value);
  }),
}));

import { getSecret, setAppMeta, setSecret } from "@/lib/keychain";
import { useOnboardingStore } from "@/store/onboarding";

const mockGet = vi.mocked(getSecret);
const mockSet = vi.mocked(setSecret);
const mockSetMeta = vi.mocked(setAppMeta);

describe("onboarding store — first-run gate", () => {
  beforeEach(() => {
    useOnboardingStore.setState({ seen: null, bannerDismissed: null, forceOpen: false });
    appMeta.clear();
    vi.clearAllMocks();
  });

  it("seen=false when no completion marker is stored (first run)", async () => {
    mockGet.mockResolvedValue(null);
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(false);
  });

  it("seen=true when a legacy keychain marker exists, and it is carried into app-meta", async () => {
    mockGet.mockResolvedValue("2026-06-03|cloud");
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(true);
    expect(mockGet).toHaveBeenCalledWith("app-meta:onboarding-complete");
    expect(appMeta.get("onboarding-complete")).toBe("2026-06-03|cloud");
  });

  it("refresh tolerates a keychain reject (non-Tauri) → seen=false", async () => {
    mockGet.mockRejectedValue(new Error("no keychain"));
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(false);
  });

  it("rejecting keychain keeps seen:true once markSeen ran (R15-CROSS-PLATFORM-011)", async () => {
    // Linux with no Secret Service provider: every keychain call rejects, yet
    // the flow must not reappear on the next launch.
    mockGet.mockRejectedValue(new Error("secret-store-unavailable: no provider"));
    mockSet.mockRejectedValue(new Error("secret-store-unavailable: no provider"));
    await useOnboardingStore.getState().markSeen("keyless");

    useOnboardingStore.setState({ seen: null });
    await useOnboardingStore.getState().refresh();
    expect(useOnboardingStore.getState().seen).toBe(true);
    expect(mockSet).not.toHaveBeenCalled();
  });

  it("markSeen persists the choice durably + sets seen + clears forceOpen", async () => {
    useOnboardingStore.setState({ forceOpen: true });
    await useOnboardingStore.getState().markSeen("cloud");
    expect(mockSetMeta).toHaveBeenCalledWith("onboarding-complete", "cloud");
    expect(useOnboardingStore.getState().seen).toBe(true);
    expect(useOnboardingStore.getState().forceOpen).toBe(false);
  });

  it("open() forces the flow open (CTA re-entry)", () => {
    useOnboardingStore.getState().open();
    expect(useOnboardingStore.getState().forceOpen).toBe(true);
  });

  it("a dismissed setup banner stays dismissed on the next launch (R15-UI-019)", async () => {
    await useOnboardingStore.getState().dismissBanner();
    expect(mockSetMeta).toHaveBeenCalledWith("onboarding-banner-dismissed", "dismissed");

    // Next launch: a fresh store reads the marker back.
    useOnboardingStore.setState({ bannerDismissed: null });
    await useOnboardingStore.getState().refreshBanner();
    expect(useOnboardingStore.getState().bannerDismissed).toBe(true);
    expect(mockGet).not.toHaveBeenCalled();
  });
});
