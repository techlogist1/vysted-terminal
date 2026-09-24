import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { useSettingsStore } from "@/store/settings";
import type { OptionChain } from "../../../types/data";
import { OptionChainPanel } from "./OptionChainPanel";

const optionChain = vi.fn();
vi.mock("@/lib/sidecar-client", () => ({
  sidecarApi: { optionChain: (...args: unknown[]) => optionChain(...args) },
}));

const contract = {
  expiry: "2026-09-29",
  last_price: 82.05,
  settle_price: 82.05,
  volume: 2432163,
  implied_volatility: null,
};

const CHAIN: OptionChain = {
  symbol: "NIFTY",
  expiry: "2026-09-29",
  expiries: ["2026-09-29", "2026-10-06"],
  underlying_price: 23063.1,
  contracts: [
    {
      ...contract,
      strike: 23000,
      option_type: "call",
      open_interest: 3885960,
      change_in_oi: 2550210,
    },
    {
      ...contract,
      strike: 23000,
      option_type: "put",
      open_interest: 11757550,
      change_in_oi: -918215,
    },
  ],
  as_of: "2026-09-24",
  provider: "nse-fo-bhavcopy",
  currency: "INR",
  freshness: "eod",
};

beforeEach(() => {
  useSettingsStore.setState({ region: "IN" });
  optionChain.mockReset().mockResolvedValue(CHAIN);
});

afterEach(() => {
  cleanup();
});

describe("OptionChainPanel", () => {
  it("renders call and put open interest per strike, dated end of day", async () => {
    render(<OptionChainPanel />);
    fireEvent.click(screen.getByTestId("option-chain-load"));
    const row = await screen.findByTestId("option-chain-row-23000");
    expect(optionChain).toHaveBeenCalledWith("NIFTY", undefined);
    expect(row.textContent).toContain("3,885,960");
    expect(row.textContent).toContain("+2,550,210");
    expect(row.textContent).toContain("11,757,550");
    expect(row.textContent).toContain("-918,215");
    expect(screen.getByTestId("option-chain-meta").textContent).toContain("as of 2026-09-24");
  });

  it("reloads on an expiry pick", async () => {
    render(<OptionChainPanel />);
    fireEvent.click(screen.getByTestId("option-chain-load"));
    const select = await screen.findByTestId("option-chain-expiry");
    fireEvent.change(select, { target: { value: "2026-10-06" } });
    expect(optionChain).toHaveBeenLastCalledWith("NIFTY", "2026-10-06");
  });
});
