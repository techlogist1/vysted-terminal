/**
 * Screener store tests — R10 update (Phase 6 original; v0.6.1 lead-completed frontend).
 *
 * The store's runs now try POST /screener/run/stream first (R10 streaming
 * contract), then fall back to POST /screener/run when the stream endpoint
 * returns 404 (older sidecar). Tests mock fetch to return 404 on the stream
 * endpoint and 200 on the unary endpoint so the fallback path is exercised;
 * a separate streaming test wires up newline-delimited JSON frames. sidecarGet
 * is still mocked for GET /screener/universe.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ScreenerResult, ScreenerUniverse } from "../../types/screener";
import { deserializeSavedScreens, serializeSavedScreens, type SavedScreen } from "./screener";

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

/** Mock fetch so /screener/run/stream returns 404 (older sidecar simulation)
 *  and /screener/run returns the given body. This exercises the fallback path. */
function mockFetchFallback(result: ScreenerResult) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    if (String(url).includes("/stream")) {
      return new Response(null, { status: 404 });
    }
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

/** Build a ReadableStream that yields newline-delimited JSON frames simulating
 *  the /screener/run/stream SSE contract (progress then result). */
function makeStreamResponse(result: ScreenerResult): Response {
  const frame = JSON.stringify({ event: "result", ...result }) + "\n";
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(frame));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "application/x-ndjson" },
  });
}

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
    it("falls back to /screener/run when /screener/run/stream returns 404 (older sidecar)", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);

      const result = await useScreenerStore.getState().runScreener();
      expect(result).toEqual(RESULT_SAMPLE);
      expect(useScreenerStore.getState().lastResult).toEqual(RESULT_SAMPLE);
      expect(useScreenerStore.getState().status).toBe("ready");

      // Two fetch calls: first /stream (404), then /screener/run (200).
      expect(fetchMock).toHaveBeenCalledTimes(2);
      const [streamUrl] = fetchMock.mock.calls[0]!;
      const [unaryUrl, init] = fetchMock.mock.calls[1]!;
      expect(String(streamUrl)).toContain("/screener/run/stream");
      expect(String(unaryUrl)).toContain("/screener/run");
      const body = JSON.parse(String(init!.body));
      expect(body.universe).toBe("sp500");
      expect(body.criteria).toHaveLength(3);
      expect(body.limit).toBe(200);
    });

    it("consumes the streaming endpoint when available and surfaces the result frame", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue(makeStreamResponse(RESULT_SAMPLE));

      const result = await useScreenerStore.getState().runScreener();
      expect(result).toEqual(RESULT_SAMPLE);
      expect(useScreenerStore.getState().lastResult).toEqual(RESULT_SAMPLE);
      expect(useScreenerStore.getState().status).toBe("ready");
      // Progress clears after run.
      expect(useScreenerStore.getState().progress).toBeNull();
    });

    it("for the custom universe, serialises custom_symbols from the raw text", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);

      useScreenerStore.getState().setUniverse("custom");
      useScreenerStore.getState().setCustomSymbols("aapl, msft\nnvda");
      await useScreenerStore.getState().runScreener();

      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
      const body = JSON.parse(String(init!.body));
      expect(body.custom_symbols).toEqual(["AAPL", "MSFT", "NVDA"]);
    });

    it("combinator='and' (default) sends no group; criteria stay flat", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);
      await useScreenerStore.getState().runScreener();
      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group).toBeUndefined();
      expect(body.criteria).toHaveLength(3);
    });

    it("combinator='or' sends a flat OR group over the same criteria", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);
      useScreenerStore.getState().setCombinator("or");
      await useScreenerStore.getState().runScreener();
      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group).toBeDefined();
      expect(body.group.combinator).toBe("or");
      expect(body.group.criteria).toHaveLength(3);
      // criteria stays populated alongside group (older readers + match-index).
      expect(body.criteria).toHaveLength(3);
    });

    it("advanced mode sends the NESTED group tree verbatim", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);
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
      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group.combinator).toBe("or");
      expect(body.group.criteria).toHaveLength(2);
      // The second child is itself a group (real nesting).
      expect(body.group.criteria[1].combinator).toBe("and");
      expect(body.group.criteria[1].criteria).toHaveLength(2);
    });

    it("advanced mode with NO nesting falls back to the flat path (no group)", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);
      const s = useScreenerStore.getState();
      s.setAdvanced(true);
      // A flat group of leaves under AND — expressible without `group`.
      s.setGroup({
        combinator: "and",
        criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
      });
      await useScreenerStore.getState().runScreener();
      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
      const body = JSON.parse(String(init!.body));
      expect(body.group).toBeUndefined();
    });

    it("a custom formula rides the request — evaluated SERVER-SIDE (R7 Pillar 3)", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);
      useScreenerStore.getState().setFormula("pe < 33 and roe > 0.1");
      await useScreenerStore.getState().runScreener();
      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
      const body = JSON.parse(String(init!.body));
      expect(body.formula).toBe("pe < 33 and roe > 0.1");
    });

    it("a blank formula is stripped from the request (no-op filter)", async () => {
      const fetchMock = mockFetchFallback(RESULT_SAMPLE);
      useScreenerStore.getState().setFormula("   ");
      await useScreenerStore.getState().runScreener();
      // call[0] = /stream (404), call[1] = /screener/run (200)
      const [, init] = fetchMock.mock.calls[1]!;
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

  describe("savedScreens (R10 §2)", () => {
    it("saveScreen persists the current draft under a name", () => {
      useScreenerStore.getState().setFormula("pe < 15");
      useScreenerStore.getState().saveScreen("Value Filter");
      const screens = useScreenerStore.getState().savedScreens;
      expect(screens).toHaveLength(1);
      expect(screens[0]!.name).toBe("Value Filter");
      expect(screens[0]!.formula).toBe("pe < 15");
      expect(screens[0]!.universe).toBe("sp500");
      expect(screens[0]!.criteria).toHaveLength(3);
    });

    it("saveScreen replaces an existing screen with the same name", () => {
      useScreenerStore.getState().saveScreen("My Screen");
      useScreenerStore.getState().setFormula("roe > 0.2");
      useScreenerStore.getState().saveScreen("My Screen");
      const screens = useScreenerStore.getState().savedScreens;
      expect(screens).toHaveLength(1);
      expect(screens[0]!.formula).toBe("roe > 0.2");
    });

    it("deleteScreen removes the named screen", () => {
      useScreenerStore.getState().saveScreen("Alpha");
      useScreenerStore.getState().saveScreen("Beta");
      expect(useScreenerStore.getState().savedScreens).toHaveLength(2);
      useScreenerStore.getState().deleteScreen("Alpha");
      const screens = useScreenerStore.getState().savedScreens;
      expect(screens).toHaveLength(1);
      expect(screens[0]!.name).toBe("Beta");
    });

    it("deleteScreen on a missing name is a no-op", () => {
      useScreenerStore.getState().saveScreen("Exists");
      useScreenerStore.getState().deleteScreen("Does Not Exist");
      expect(useScreenerStore.getState().savedScreens).toHaveLength(1);
    });

    it("loadScreen restores universe, criteria, formula, and combinator", () => {
      useScreenerStore.getState().setUniverse("nifty50");
      useScreenerStore.getState().setFormula("pe < 20");
      useScreenerStore.getState().setCombinator("or");
      useScreenerStore.getState().saveScreen("India Value");

      // Mutate state to something else.
      useScreenerStore.getState().setUniverse("sp500");
      useScreenerStore.getState().setFormula("");
      useScreenerStore.getState().setCombinator("and");

      // Load the saved screen.
      useScreenerStore.getState().loadScreen("India Value");
      const s = useScreenerStore.getState();
      expect(s.universe).toBe("nifty50");
      expect(s.formula).toBe("pe < 20");
      expect(s.combinator).toBe("or");
    });

    it("loadScreen on a missing name is a no-op", () => {
      const before = useScreenerStore.getState().universe;
      useScreenerStore.getState().loadScreen("Ghost");
      expect(useScreenerStore.getState().universe).toBe(before);
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

describe("serializeSavedScreens / deserializeSavedScreens (R10 workspace.ts seam)", () => {
  const SAMPLE: SavedScreen[] = [
    {
      name: "Tech Value",
      universe: "sp500",
      criteria: [{ field: "pe_ratio", operator: "lt", value: 20 }],
      combinator: "and",
      formula: "roe > 0.15",
    },
  ];

  it("round-trips cleanly through JSON", () => {
    const raw = serializeSavedScreens(SAMPLE);
    expect(deserializeSavedScreens(raw)).toEqual(SAMPLE);
  });

  it("deserializeSavedScreens returns [] for null/undefined/empty", () => {
    expect(deserializeSavedScreens(null)).toEqual([]);
    expect(deserializeSavedScreens(undefined)).toEqual([]);
    expect(deserializeSavedScreens("")).toEqual([]);
  });

  it("deserializeSavedScreens drops entries missing name or universe", () => {
    const garbage = JSON.stringify([
      { name: "ok", universe: "sp500", criteria: [], combinator: "and" },
      { universe: "sp500", criteria: [] }, // no name → dropped
      { name: "x" }, // no universe → dropped
    ]);
    const result = deserializeSavedScreens(garbage);
    expect(result).toHaveLength(1);
    expect(result[0]!.name).toBe("ok");
  });

  it("deserializeSavedScreens returns [] on malformed JSON", () => {
    expect(deserializeSavedScreens("{not valid json")).toEqual([]);
  });
});
