/**
 * Tradesa V2 wrapper — TradesaSettingsDialog Vitest suite.
 *
 * Verifies the keychain-write path (setSecret invoked for both URL +
 * key), the show/hide password toggle, the empty initial form, and
 * validation messages.
 *
 * Mocks `@tauri-apps/api/core::invoke` so `setSecret` calls become
 * deterministic.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { TradesaSettingsDialog } from "./TradesaSettingsDialog";
import { TRADESA_KEYCHAIN_ACCOUNTS } from "../connection";
import { installStubAdapter, makeConnectionState, resetStore } from "./_test-helpers";

beforeEach(() => {
  invokeMock.mockReset();
  invokeMock.mockResolvedValue(null);
  installStubAdapter({ probeState: makeConnectionState("healthy") });
});

afterEach(() => {
  cleanup();
  resetStore();
});

describe("TradesaSettingsDialog", () => {
  it("returns null when open=false", () => {
    const { container } = render(<TradesaSettingsDialog open={false} onClose={() => undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders empty form initially (no creds in keychain)", async () => {
    // getSecret returns null → form stays empty
    invokeMock.mockResolvedValue(null);
    render(<TradesaSettingsDialog open onClose={() => undefined} />);
    const urlInput = screen.getByTestId("tradesa-settings-url") as HTMLInputElement;
    const keyInput = screen.getByTestId("tradesa-settings-key") as HTMLInputElement;
    expect(urlInput.value).toBe("");
    expect(keyInput.value).toBe("");
    // Service-role key input defaults to password type (hidden)
    expect(keyInput.type).toBe("password");
  });

  it("show/hide toggle flips the password field to text type and back", () => {
    render(<TradesaSettingsDialog open onClose={() => undefined} />);
    const keyInput = screen.getByTestId("tradesa-settings-key") as HTMLInputElement;
    const toggle = screen.getByTestId("tradesa-settings-show-toggle");
    expect(keyInput.type).toBe("password");
    fireEvent.click(toggle);
    expect(keyInput.type).toBe("text");
    fireEvent.click(toggle);
    expect(keyInput.type).toBe("password");
  });

  it("rejects submit with no URL", async () => {
    render(<TradesaSettingsDialog open onClose={() => undefined} />);
    const form = screen.getByTestId("tradesa-settings-submit").closest("form")!;
    // Provide a key but no URL — browser will block the submit normally,
    // but we trigger handleSubmit directly to exercise our validation.
    const urlInput = screen.getByTestId("tradesa-settings-url") as HTMLInputElement;
    urlInput.removeAttribute("required");
    fireEvent.change(screen.getByTestId("tradesa-settings-key"), { target: { value: "abc" } });
    fireEvent.submit(form);
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-settings-error")).toHaveTextContent(/url/i);
    });
  });

  it("rejects submit when URL does not start with https://", async () => {
    render(<TradesaSettingsDialog open onClose={() => undefined} />);
    const urlInput = screen.getByTestId("tradesa-settings-url") as HTMLInputElement;
    urlInput.setAttribute("type", "text"); // bypass browser url validation
    fireEvent.change(urlInput, { target: { value: "ftp://no.example.com" } });
    fireEvent.change(screen.getByTestId("tradesa-settings-key"), { target: { value: "abc" } });
    fireEvent.submit(screen.getByTestId("tradesa-settings-submit").closest("form")!);
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-settings-error")).toHaveTextContent(/https/i);
    });
  });

  it("submits and writes both keychain entries via setSecret", async () => {
    const onClose = vi.fn();
    render(<TradesaSettingsDialog open onClose={onClose} />);

    fireEvent.change(screen.getByTestId("tradesa-settings-url"), {
      target: { value: "https://abcd.supabase.co" },
    });
    fireEvent.change(screen.getByTestId("tradesa-settings-key"), {
      target: { value: "sk-service-role-key" },
    });
    fireEvent.submit(screen.getByTestId("tradesa-settings-submit").closest("form")!);

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledWith("keychain_set", {
        account: TRADESA_KEYCHAIN_ACCOUNTS.supabaseUrl,
        secret: "https://abcd.supabase.co",
      });
      expect(invokeMock).toHaveBeenCalledWith("keychain_set", {
        account: TRADESA_KEYCHAIN_ACCOUNTS.supabaseServiceRoleKey,
        secret: "sk-service-role-key",
      });
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("clicking Cancel calls onClose without writing keychain", () => {
    const onClose = vi.fn();
    render(<TradesaSettingsDialog open onClose={onClose} />);
    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalledTimes(1);
    // No keychain_set calls — only the initial getSecret reads from useEffect
    const setCalls = invokeMock.mock.calls.filter((c) => c[0] === "keychain_set");
    expect(setCalls).toHaveLength(0);
  });
});
