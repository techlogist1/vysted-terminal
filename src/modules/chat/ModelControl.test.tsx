/**
 * ModelControl — trigger render tests.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LLMProviderInfo } from "../../../types/ai";

import { ModelControl } from "./ModelControl";

afterEach(() => {
  cleanup();
});

const PROVIDERS: LLMProviderInfo[] = [
  { id: "anthropic", label: "Anthropic", requiresKey: true, knownModels: ["claude-opus-4-8"] },
];

const BASE_PROPS = {
  providers: PROVIDERS,
  provider: "anthropic" as const,
  model: "claude-opus-4-8",
  providerConfigured: true,
  onProviderChange: vi.fn(),
  onModelChange: vi.fn(),
};

describe("ModelControl", () => {
  it("R15-UI-072: the trigger contains a chevron icon", () => {
    render(<ModelControl {...BASE_PROPS} density="full" />);
    expect(screen.getByTestId("model-control-chevron")).toBeInTheDocument();
  });

  it("renders a chevron at every density", () => {
    for (const density of ["full", "short", "icon"] as const) {
      const { unmount } = render(<ModelControl {...BASE_PROPS} density={density} />);
      expect(screen.getByTestId("model-control-chevron")).toBeInTheDocument();
      unmount();
    }
  });
});
