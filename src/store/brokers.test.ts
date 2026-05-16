import { beforeEach, describe, expect, it, vi } from "vitest";

import * as sidecarClient from "@/lib/sidecar-client";

import { resetBrokersStoreForTests, useBrokersStore } from "@/store/brokers";

import type { BrokerState } from "../../types/broker";

const baseUrl = "http://127.0.0.1:1234";

function stubSidecar(): void {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue(baseUrl);
}

function makeState(partial: Partial<BrokerState> & Pick<BrokerState, "broker">): BrokerState {
  return {
    status: "disconnected",
    mode: "paper",
    readOnly: false,
    capabilities: {
      supportsEquity: true,
      supportsOptions: false,
      supportsCrypto: false,
      supportsForex: false,
      supportsFutures: false,
      requiresStaticIp: false,
    },
    ...partial,
  };
}

function mockFetchSequence(responses: Array<{ ok: boolean; body: unknown }>): void {
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      const r = responses[i] ?? { ok: false, body: {} };
      i += 1;
      return {
        ok: r.ok,
        status: r.ok ? 200 : 500,
        statusText: r.ok ? "OK" : "Error",
        json: async () => r.body,
      } as Response;
    }),
  );
}

describe("useBrokersStore", () => {
  beforeEach(() => {
    resetBrokersStoreForTests();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    stubSidecar();
  });

  it("refresh stores brokers by id and exposes status=ready", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce({
      brokers: [
        makeState({ broker: "alpaca" }),
        makeState({ broker: "kite" }),
        makeState({ broker: "ccxt-binance" }),
      ],
    });
    await useBrokersStore.getState().refresh();
    const s = useBrokersStore.getState();
    expect(s.status).toBe("ready");
    expect(s.brokers()).toHaveLength(3);
  });

  it("primaryBrokers and cryptoBrokers split on ccxt- prefix", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce({
      brokers: [
        makeState({ broker: "alpaca" }),
        makeState({ broker: "ccxt-binance" }),
        makeState({ broker: "ccxt-bybit" }),
        makeState({ broker: "ib" }),
      ],
    });
    await useBrokersStore.getState().refresh();
    expect(
      useBrokersStore
        .getState()
        .primaryBrokers()
        .map((b) => b.broker)
        .sort(),
    ).toEqual(["alpaca", "ib"]);
    expect(
      useBrokersStore
        .getState()
        .cryptoBrokers()
        .map((b) => b.broker)
        .sort(),
    ).toEqual(["ccxt-binance", "ccxt-bybit"]);
  });

  it("refreshOne overwrites a single broker entry", async () => {
    useBrokersStore.setState({
      byId: { alpaca: makeState({ broker: "alpaca", status: "disconnected" }) },
    });
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce(
      makeState({ broker: "alpaca", status: "connected" }),
    );
    await useBrokersStore.getState().refreshOne("alpaca");
    expect(useBrokersStore.getState().byId.alpaca?.status).toBe("connected");
  });

  it("connect POSTs credentials and triggers a refreshOne", async () => {
    mockFetchSequence([{ ok: true, body: {} }]);
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce(
      makeState({ broker: "alpaca", status: "connected" }),
    );
    await useBrokersStore.getState().connect("alpaca", { api_key: "k", api_secret: "s" });
    expect(useBrokersStore.getState().byId.alpaca?.status).toBe("connected");
  });

  it("setMode POSTs the new mode and refreshes", async () => {
    mockFetchSequence([{ ok: true, body: {} }]);
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce(
      makeState({ broker: "alpaca", mode: "live" }),
    );
    await useBrokersStore.getState().setMode("alpaca", "live");
    expect(useBrokersStore.getState().byId.alpaca?.mode).toBe("live");
  });

  it("setReadOnly POSTs the new flag and refreshes", async () => {
    mockFetchSequence([{ ok: true, body: {} }]);
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce(
      makeState({ broker: "alpaca", readOnly: true }),
    );
    await useBrokersStore.getState().setReadOnly("alpaca", true);
    expect(useBrokersStore.getState().byId.alpaca?.readOnly).toBe(true);
  });

  it("refresh records an error message on fetch failure", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockRejectedValueOnce(new Error("boom"));
    await useBrokersStore.getState().refresh();
    expect(useBrokersStore.getState().status).toBe("error");
    expect(useBrokersStore.getState().error).toMatch(/boom/);
  });
});
