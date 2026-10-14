import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetSearchSettingsStoreForTests, useSearchSettingsStore } from "@/store/search-settings";

import { DepthControl } from "./DepthControl";

afterEach(() => {
  cleanup();
  resetSearchSettingsStoreForTests();
});

beforeEach(() => {
  resetSearchSettingsStoreForTests();
});

describe("DepthControl cost estimate (R15-RESEARCH-040, FR-073)", () => {
  it("Tier B + ULTRA renders an estimate before dispatch", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    render(<DepthControl depth="ultra" onChange={vi.fn()} liveDepth={null} expandable={false} />);
    expect(screen.getByText(/^~\$\d+\.\d{2} est\.$/)).toBeInTheDocument();
  });

  it("Tier A (Unlimited Local) shows no cost estimate — nothing is billed", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_a");
    render(<DepthControl depth="ultra" onChange={vi.fn()} liveDepth={null} expandable={false} />);
    expect(screen.queryByText(/est\.$/)).not.toBeInTheDocument();
  });

  it("Tier B renders an estimate for every stop, not only Ultra", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    render(<DepthControl depth="normal" onChange={vi.fn()} liveDepth={null} expandable={false} />);
    expect(screen.getByText(/^~\$\d+\.\d{2} est\.$/)).toBeInTheDocument();
  });

  it("the expandable pill shows the estimate beside the ACTIVE stop only", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    render(<DepthControl depth="ultra" onChange={vi.fn()} liveDepth={null} expandable />);
    expect(screen.getAllByText(/^~\$\d+\.\d{2} est\.$/)).toHaveLength(1);
  });
});
