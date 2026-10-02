import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KeyEntryDialog } from "@/components/KeyEntryDialog";

const setSecretMock = vi.hoisted(() => vi.fn(async () => undefined));
const validateMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/keychain", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/keychain")>()),
  setSecret: setSecretMock,
}));

vi.mock("@/lib/provider-validation", () => ({
  validateProvider: validateMock,
  // The keyless default is ready, so a save never moves the default here.
  probeReadiness: vi.fn(async () => ({ ok: true, reason: null, detail: null })),
}));

describe("KeyEntryDialog", () => {
  beforeEach(() => {
    setSecretMock.mockClear();
    validateMock.mockReset();
  });
  afterEach(cleanup);

  it("trims a pasted key before validating and saving it (R15-UI-057)", async () => {
    validateMock.mockResolvedValue({ ok: true, reason: null, detail: null });
    render(<KeyEntryDialog open providerId="openai" onOpenChange={() => {}} />);
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: " sk-test \n" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(setSecretMock).toHaveBeenCalled());
    expect(validateMock.mock.calls[0][1]).toMatchObject({ apiKey: "sk-test" });
    expect(setSecretMock).toHaveBeenCalledWith("llm-provider:openai", "sk-test");
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("Cancel stays enabled while validating and aborts the request (R15-UI-013)", async () => {
    let signal: AbortSignal | undefined;
    validateMock.mockImplementation(
      (_provider: string, opts: { signal?: AbortSignal }) =>
        new Promise((_, reject) => {
          signal = opts.signal;
          opts.signal?.addEventListener("abort", () => reject(new DOMException("", "AbortError")));
        }),
    );
    const onOpenChange = vi.fn();
    const { rerender } = render(
      <KeyEntryDialog open providerId="openai" onOpenChange={onOpenChange} />,
    );
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-test" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("button", { name: "Validating…" });

    const cancel = screen.getByRole("button", { name: "Cancel" });
    expect(cancel).toBeEnabled();
    fireEvent.click(cancel);
    expect(onOpenChange).toHaveBeenCalledWith(false);
    rerender(<KeyEntryDialog open={false} providerId="openai" onOpenChange={onOpenChange} />);

    await waitFor(() => expect(signal?.aborted).toBe(true));
    expect(setSecretMock).not.toHaveBeenCalled();
  });

  it("a missing OS secret store shows the typed unavailable state (R15-CROSS-PLATFORM-011)", async () => {
    validateMock.mockResolvedValue({ ok: true, reason: null, detail: null });
    setSecretMock.mockRejectedValueOnce(
      "secret-store-unavailable: Platform secure storage failure: no provider" as never,
    );
    render(<KeyEntryDialog open providerId="openai" onOpenChange={() => {}} />);
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-test" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(/Secret store unavailable/)).toBeInTheDocument();
  });
});
