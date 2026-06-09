/**
 * Screener store tests — Phase 6 (Teammate Sc backend; v0.6.1 lead-completed frontend).
 *
 * The store's runs go through ``fetch`` (POST /screener/run) and
 * ``sidecarGet`` (GET /screener/universe). Both are mocked at the
 * module boundary.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ScreenerResult, ScreenerUniverse } from "../../types/screener";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

import { useScreenerStore } from "./screener";

const RESULT_SAMPLE: ScreenerResult = {
  universe: "sp500",
  evaluated_count: 100,
  skipped_count: 0,
  result_count: 2,
  rows: [
    {
      symbol: "AAPL",
      name: "Apple Inc.",
      sector: "Technology",
      industry: "Consumer Electronics",
      market_cap: 3_000_000_000_000,
      pe_ratio: 31.2,
      price: 192.5,
      change_percent_1d: 1.5,
      volume: 51_000_000,
      matched_criteria: [0, 1, 2],
    },
    {
      symbol: "MSFT",
      name: "Microsoft Corporation",
      sector: "Technology",
      industry: "Software",
      market_cap: 3_200_000_000_000,
      pe_ratio: 35.0,
      price: 420.0,
      change_percent_1d: -0.5,
      volume: 22_000_000,
      matched_criteria: [0, 1, 2],
    },
  ],
  duration_ms: 280.0,
};

const UNIVERSE_SAMPLE: ScreenerUniverse = {
  id: "sp500",
  label: "S&P 500 (snapshot)",
  symbols: ["AAPL", "MSFT", "NVDA"],
  asset_class: "equity",
};

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
  vi.mocked(sidecarGet).mockReset();
  vi.spyOn(globalThis, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useScreenerStore", () => {
  describe("setters", () => {
    it("setUniverse updates the universe", () => {
      useScreenerStore.getState().setUniverse("nifty50");
      expect(useScreenerStore.getState().universe).toBe("nifty50");
    });

    it("setCustomSymbols updates the raw text", () => {
      useScreenerStore.getState().setCustomSymbols("AAPL, MSFT");
      expect(useScreenerStore.getState().customSymbols).toBe("AAPL, MSFT");
    });

    it("addCriterion / removeCriterion / updateCriterion manage the list", () => {
      const start = useScreenerStore.getState().criteria.length;
      useScreenerStore.getState().addCriterion({ field: "beta", operator: "gt", value: 1 });
      expect(useScreenerStore.getState().criteria.length).toBe(start + 1);

      useScreenerStore
        .getState()
        .updateCriterion(start, { field: "beta", operator: "lt", value: 0.5 });
      const updated = useScreenerStore.getState().criteria[start];
      expect(updated.operator).toBe("lt");

      useScreenerStore.getState().removeCriterion(start);
      expect(useScreenerStore.getState().criteria.length).toBe(start);
    });
  });

  describe("runScreener", () => {
    it("posts /screener/run with the current draft and stores the result", async () => {
      const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response(JSON.stringify(RESULT_SAMPLE), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const result = await useScreenerStore.getState().runScreener();
      expect(result).toEqual(RESULT_SAMPLE);
      expect(useScreenerStore.getState().lastResult).toEqual(RESULT_SAMPLE);
      expect(useScreenerStore.getState().status).toBe("ready");

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0]!;
      expect(String(url)).toContain("/screener/run");
      const body = JSON.parse(String(init!.body));
      expect(body.universe).toBe("sp500");
      expect(body.criteria).toHaveLength(3);
      expect(body.limit).toBe(200);
    });

    it("for the custom universe, serialises custom_symbols from the raw text", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }),
      );

      useScreenerStore.getState().setUniverse("custom");
      useScreenerStore.getState().setCustomSymbols("aapl, msft\nnvda");
      await useScreenerStore.getState().runScreener();

      const fetchMock = vi.mocked(globalThis.fetch);
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.custom_symbols).toEqual(["AAPL", "MSFT", "NVDA"]);
    });

    it("combinator='and' (default) sends no group; criteria stay flat", async () => {
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }));
      await useScreenerStore.getState().runScreener();
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group).toBeUndefined();
      expect(body.criteria).toHaveLength(3);
    });

    it("combinator='or' sends a flat OR group over the same criteria", async () => {
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }));
      useScreenerStore.getState().setCombinator("or");
      await useScreenerStore.getState().runScreener();
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group).toBeDefined();
      expect(body.group.combinator).toBe("or");
      expect(body.group.criteria).toHaveLength(3);
      // criteria stays populated alongside group (older readers + match-index).
      expect(body.criteria).toHaveLength(3);
    });

    it("advanced mode sends the NESTED group tree verbatim", async () => {
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }));
      const s = useScreenerStore.getState();
      s.setAdvanced(true);
      s.setGroup({
        combinator: "or",
        criteria: [
          { field: "dividend_yield", operator: "gt", value: 0.04 },
          {
            combinator: "and",
            criteria: [
              { field: "pe_ratio", operator: "lt", value: 15 },
              { field: "roe", operator: "gt", value: 0.2 },
            ],
          },
        ],
      });
      await useScreenerStore.getState().runScreener();
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group.combinator).toBe("or");
      expect(body.group.criteria).toHaveLength(2);
      // The second child is itself a group (real nesting).
      expect(body.group.criteria[1].combinator).toBe("and");
      expect(body.group.criteria[1].criteria).toHaveLength(2);
    });

    it("advanced mode with NO nesting falls back to the flat path (no group)", async () => {
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }));
      const s = useScreenerStore.getState();
      s.setAdvanced(true);
      // A flat group of leaves under AND — expressible without `group`.
      s.setGroup({
        combinator: "and",
        criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
      });
      await useScreenerStore.getState().runScreener();
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group).toBeUndefined();
    });

    it("a custom formula rides the request — evaluated SERVER-SIDE (R7 Pillar 3)", async () => {
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }));
      useScreenerStore.getState().setFormula("pe < 33 and roe > 0.1");
      await useScreenerStore.getState().runScreener();
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.formula).toBe("pe < 33 and roe > 0.1");
    });

    it("a blank formula is stripped from the request (no-op filter)", async () => {
      const fetchMock = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response(JSON.stringify(RESULT_SAMPLE), { status: 200 }));
      useScreenerStore.getState().setFormula("   ");
      await useScreenerStore.getState().runScreener();
      const [, init] = fetchMock.mock.calls[0]!;
      const body = JSON.parse(String(init!.body));
      expect(body.formula).toBeUndefined();
    });

    it("an unparseable formula fails the run inline with the caret column — no request fires", async () => {
      const fetchMock = vi.spyOn(globalThis, "fetch");
      useScreenerStore.getState().setFormula("pe <");
      const result = await useScreenerStore.getState().runScreener();
      expect(result).toBeNull();
      expect(fetchMock).not.toHaveBeenCalled();
      expect(useScreenerStore.getState().status).toBe("error");
      expect(useScreenerStore.getState().error).toContain("Formula:");
      expect(useScreenerStore.getState().error).toContain("(col 5)");
    });

    it("applyFilters writes a nested group + flips to advanced mode", () => {
      useScreenerStore.getState().applyFilters({
        criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
        group: {
          combinator: "or",
          criteria: [
            { field: "roe", operator: "gt", value: 0.2 },
            {
              combinator: "and",
              criteria: [{ field: "dividend_yield", operator: "gt", value: 0.03 }],
            },
          ],
        },
      });
      expect(useScreenerStore.getState().advanced).toBe(true);
      expect(useScreenerStore.getState().group?.combinator).toBe("or");
      expect(useScreenerStore.getState().criteria).toHaveLength(1);
    });

    it("captures errors and sets status=error", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ detail: "boom" }), { status: 500 }),
      );

      const result = await useScreenerStore.getState().runScreener();
      expect(result).toBeNull();
      expect(useScreenerStore.getState().status).toBe("error");
      expect(useScreenerStore.getState().error).toContain("boom");
    });
  });

  describe("loadUniverse", () => {
    it("loads + caches the universe metadata", async () => {
      vi.mocked(sidecarGet).mockResolvedValueOnce(UNIVERSE_SAMPLE);

      const out = await useScreenerStore.getState().loadUniverse("sp500");
      expect(out).toEqual(UNIVERSE_SAMPLE);
      expect(useScreenerStore.getState().universeMeta["sp500"]).toEqual(UNIVERSE_SAMPLE);

      // second call → cached, no extra fetch
      vi.mocked(sidecarGet).mockClear();
      await useScreenerStore.getState().loadUniverse("sp500");
      expect(sidecarGet).not.toHaveBeenCalled();
    });

    it("returns null for the custom universe", async () => {
      const out = await useScreenerStore.getState().loadUniverse("custom");
      expect(out).toBeNull();
      expect(sidecarGet).not.toHaveBeenCalled();
    });
  });
});
