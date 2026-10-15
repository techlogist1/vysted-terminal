import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setSecret } from "@/lib/keychain";
import { validateProvider } from "@/lib/provider-validation";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useProviderKeysStore } from "@/store/provider-keys";
import { KeyStep, OPENROUTER_DEFAULT_MODEL } from "./KeyStep";
import { openExternal } from "./shared";

vi.mock("@/lib/provider-validation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/provider-validation")>()),
  validateProvider: vi.fn(),
}));
vi.mock("@/lib/keychain", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/keychain")>()),
  setSecret: vi.fn(async () => undefined),
}));
vi.mock("./shared", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./shared")>()),
  openExternal: vi.fn(async () => undefined),
}));

const onBack = vi.fn();
const onDone = vi.fn();

beforeEach(() => {
  onBack.mockReset();
  onDone.mockReset();
  vi.mocked(validateProvider).mockReset().mockResolvedValue({
    ok: true,
    reason: null,
    detail: null,
  });
  vi.mocked(setSecret).mockReset().mockResolvedValue(undefined);
  vi.mocked(openExternal).mockReset().mockResolvedValue(undefined);
  useAppStore.setState({ sidecarStatus: "connected" });
  useProviderKeysStore.setState({ refreshOne: vi.fn().mockResolvedValue(undefined) });
  useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
  useModelSelectionStore.setState({ overrides: {} });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderKeyStep() {
  return render(<KeyStep onBack={onBack} onDone={onDone} />);
}

describe("KeyStep", () => {
  it("does nothing when the form is submitted with no key typed", () => {
    const { container } = renderKeyStep();
    fireEvent.submit(container.querySelector("form")!);
    expect(validateProvider).not.toHaveBeenCalled();
  });

  it("clicking Back calls onBack", () => {
    renderKeyStep();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("reports offline plainly when the key check fails unreachable while the browser is offline", async () => {
    vi.stubGlobal("navigator", { ...navigator, onLine: false });
    vi.mocked(validateProvider).mockResolvedValue({
      ok: false,
      reason: "unreachable",
      detail: null,
    });
    renderKeyStep();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "k" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "No internet connection. Connect and try again.",
    );
    expect(setSecret).not.toHaveBeenCalled();
  });

  it("reports the data engine is still warming up when unreachable while online but not yet connected", async () => {
    useAppStore.setState({ sidecarStatus: "connecting" });
    vi.mocked(validateProvider).mockResolvedValue({
      ok: false,
      reason: "unreachable",
      detail: null,
    });
    renderKeyStep();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "k" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/Getting things ready/);
  });

  it("reports an unreachable provider plainly once online and connected", async () => {
    vi.mocked(validateProvider).mockResolvedValue({
      ok: false,
      reason: "unreachable",
      detail: null,
    });
    renderKeyStep();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "k" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/wasn't rejected — try again/);
  });

  it("shows a plain error and never calls onDone when saving to the keychain fails", async () => {
    vi.mocked(setSecret).mockRejectedValue(new Error("keychain locked"));
    renderKeyStep();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "sk-1" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Couldn't save the key on this computer. Try again.",
    );
    expect(onDone).not.toHaveBeenCalled();
  });

  it("switching providers resets any shown error and re-checks the new provider's key", async () => {
    vi.mocked(validateProvider).mockResolvedValue({ ok: false, reason: "invalid", detail: null });
    renderKeyStep();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: "bad" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Anthropic" }));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("radio", { name: "Anthropic" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("typing again after a rejected key clears the error", async () => {
    vi.mocked(validateProvider).mockResolvedValue({ ok: false, reason: "invalid", detail: null });
    renderKeyStep();
    const input = screen.getByLabelText(/API key/);
    fireEvent.change(input, { target: { value: "bad" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(screen.getByRole("alert")).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "bad2" } });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("opens the provider's key page via openExternal, never a real navigation", () => {
    renderKeyStep();
    fireEvent.click(screen.getByRole("button", { name: /Get a OpenRouter key/ }));
    expect(openExternal).toHaveBeenCalledWith("https://openrouter.ai/keys");
  });

  it("on success saves the key, makes the provider default and sets the OpenRouter model", async () => {
    renderKeyStep();
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: " sk-or-1 " } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Check & save/ }));
    });
    expect(setSecret).toHaveBeenCalledWith("llm-provider:openrouter", "sk-or-1");
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("openrouter");
    expect(useModelSelectionStore.getState().modelFor("openrouter")).toBe(OPENROUTER_DEFAULT_MODEL);
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});
