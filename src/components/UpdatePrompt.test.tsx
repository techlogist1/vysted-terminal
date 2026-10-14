import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DOWNLOAD_POLL_MS,
  FIRST_CHECK_MS,
  RECHECK_MS,
  UpdatePrompt,
} from "@/components/UpdatePrompt";
import type { UpdateProgress } from "@/lib/updater";

const checkForUpdate = vi.fn();
const hasActiveModelDownload = vi.fn();
const installUpdate = vi.fn();
vi.mock("@/lib/updater", () => ({
  checkForUpdate: () => checkForUpdate(),
  hasActiveModelDownload: () => hasActiveModelDownload(),
  installUpdate: (cb: (p: UpdateProgress) => void) => installUpdate(cb),
}));

const AVAILABLE = { available: true, version: "0.10.1", notes: "Faster charts." };

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("UpdatePrompt", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    checkForUpdate.mockReset().mockResolvedValue(AVAILABLE);
    hasActiveModelDownload.mockReset().mockResolvedValue(false);
    installUpdate.mockReset().mockReturnValue(new Promise(() => {}));
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("checks 15 s after boot and every 6 h", async () => {
    checkForUpdate.mockResolvedValue({ available: false });
    render(<UpdatePrompt />);
    await advance(FIRST_CHECK_MS - 1);
    expect(checkForUpdate).not.toHaveBeenCalled();
    await advance(1);
    expect(checkForUpdate).toHaveBeenCalledTimes(1);
    await advance(RECHECK_MS);
    expect(checkForUpdate).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows the version and notes, and Later hides it", async () => {
    render(<UpdatePrompt />);
    await advance(FIRST_CHECK_MS);
    expect(screen.getByText(/0\.10\.1 is available/)).toBeTruthy();
    expect(screen.queryByText("Faster charts.")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /What's new/ }));
    expect(screen.getByText("Faster charts.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Later/ }));
    await advance(1000);
    expect(screen.queryByText(/is available/)).toBeNull();
  });

  it("installs on Restart to update and shows progress", async () => {
    let report: (p: UpdateProgress) => void = () => {};
    installUpdate.mockImplementation((cb: (p: UpdateProgress) => void) => {
      report = cb;
      return new Promise(() => {});
    });
    render(<UpdatePrompt />);
    await advance(FIRST_CHECK_MS);
    fireEvent.click(screen.getByRole("button", { name: "Restart to update" }));
    expect(installUpdate).toHaveBeenCalledTimes(1);
    act(() => report({ downloaded: 50, total: 200 }));
    expect(screen.getByText(/25%/)).toBeTruthy();
  });

  it("surfaces an install failure and lets the user retry", async () => {
    installUpdate.mockRejectedValueOnce(new Error("bad signature"));
    render(<UpdatePrompt />);
    await advance(FIRST_CHECK_MS);
    fireEvent.click(screen.getByRole("button", { name: "Restart to update" }));
    await advance(0);
    expect(screen.getByText(/could not be installed/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Restart to update" })).toBeTruthy();
  });

  it("waits for an active model download, then installs on its own", async () => {
    hasActiveModelDownload.mockResolvedValue(true);
    render(<UpdatePrompt />);
    await advance(FIRST_CHECK_MS);
    const button = screen.getByRole("button", { name: "Update after the download finishes" });
    fireEvent.click(button);
    await advance(DOWNLOAD_POLL_MS);
    expect(installUpdate).not.toHaveBeenCalled();
    hasActiveModelDownload.mockResolvedValue(false);
    await advance(DOWNLOAD_POLL_MS);
    expect(installUpdate).toHaveBeenCalledTimes(1);
  });
});
