import { describe, expect, it, vi } from "vitest";

import { DrawingPrimitive } from "./base";
import { DEFAULT_DRAWING_STYLE, createDrawingPrimitive, pointsRequired } from "./factory";
import {
  EllipseRenderer,
  FIB_LEVELS,
  FibExtensionRenderer,
  FibRetracementRenderer,
  HorizontalLineRenderer,
  ParallelChannelRenderer,
  RayRenderer,
  RectangleRenderer,
  TextRenderer,
  TrendlineRenderer,
  VerticalLineRenderer,
} from "./renderers";
import type { DrawingKind, DrawingSpec } from "../../../../types/drawings";

const ALL_KINDS: DrawingKind[] = [
  "trendline",
  "horizontal-line",
  "vertical-line",
  "ray",
  "rectangle",
  "ellipse",
  "fib-retracement",
  "fib-extension",
  "parallel-channel",
  "text",
];

function makeSpec(kind: DrawingKind, points: DrawingSpec["points"]): DrawingSpec {
  return {
    id: `test-${kind}`,
    panelId: "p",
    kind,
    points,
    style: { ...DEFAULT_DRAWING_STYLE },
    createdAt: 0,
  };
}

/** A canvas-like recorder — tracks every command so renderers can be asserted. */
type MockCtx = CanvasRenderingContext2D & {
  __calls: Array<{ method: string; args: unknown[] }>;
};

function makeMockContext(): MockCtx {
  const calls: Array<{ method: string; args: unknown[] }> = [];
  const target = new Proxy(
    {},
    {
      get: (_, key: string) => {
        if (key === "__calls") {
          return calls;
        }
        return (...args: unknown[]) => {
          calls.push({ method: key, args });
        };
      },
      set: (_, key: string, value: unknown) => {
        calls.push({ method: `set:${key}`, args: [value] });
        return true;
      },
    },
  ) as MockCtx;
  return target;
}

/**
 * Wrap a mock context in the minimal shape `IPrimitivePaneRenderer.draw`
 * expects — a `useMediaCoordinateSpace` adapter that hands the context and
 * media size into the renderer's drawing callback.
 */
function makeDrawTarget(ctx: MockCtx): Parameters<TrendlineRenderer["draw"]>[0] {
  return {
    useMediaCoordinateSpace: (
      cb: (scope: {
        context: CanvasRenderingContext2D;
        mediaSize: { width: number; height: number };
        bitmapSize: { width: number; height: number };
      }) => void,
    ) => cb({ context: ctx, mediaSize, bitmapSize: mediaSize }),
  } as never;
}

const converters = {
  timeToX: (time: number) => time / 1_000_000,
  priceToY: (price: number) => 1000 - price,
  paneSize: () => ({ width: 800, height: 600 }),
};

const mediaSize = { width: 800, height: 600 };

describe("drawing factory", () => {
  it("creates a primitive for every kind", () => {
    for (const kind of ALL_KINDS) {
      const spec = makeSpec(kind, [
        { time: 1, price: 100 },
        { time: 2, price: 110 },
        { time: 3, price: 105 },
      ]);
      const primitive = createDrawingPrimitive(spec);
      expect(primitive).toBeInstanceOf(DrawingPrimitive);
    }
  });

  it("declares correct point counts per kind", () => {
    expect(pointsRequired("text")).toBe(1);
    expect(pointsRequired("horizontal-line")).toBe(1);
    expect(pointsRequired("vertical-line")).toBe(1);
    expect(pointsRequired("trendline")).toBe(2);
    expect(pointsRequired("ray")).toBe(2);
    expect(pointsRequired("rectangle")).toBe(2);
    expect(pointsRequired("ellipse")).toBe(2);
    expect(pointsRequired("fib-retracement")).toBe(2);
    expect(pointsRequired("fib-extension")).toBe(3);
    expect(pointsRequired("parallel-channel")).toBe(3);
  });
});

describe("trendline renderer", () => {
  it("draws a single segment between the two anchors", () => {
    const ctx = makeMockContext();
    const renderer = new TrendlineRenderer();
    const spec = makeSpec("trendline", [
      { time: 1_000_000, price: 100 },
      { time: 2_000_000, price: 110 },
    ]);
    renderer.setSpec(spec);
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const moveTo = ctx.__calls.find((c) => c.method === "moveTo");
    const lineTo = ctx.__calls.find((c) => c.method === "lineTo");
    expect(moveTo).toBeDefined();
    expect(lineTo).toBeDefined();
  });
});

describe("horizontal line renderer", () => {
  it("strokes a full-width line at the price-converted y", () => {
    const ctx = makeMockContext();
    const renderer = new HorizontalLineRenderer();
    renderer.setSpec(makeSpec("horizontal-line", [{ time: null, price: 100 }]));
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const moveTo = ctx.__calls.find((c) => c.method === "moveTo");
    const lineTo = ctx.__calls.find((c) => c.method === "lineTo");
    expect(moveTo?.args).toEqual([0, 900]); // y = 1000 - 100
    expect(lineTo?.args).toEqual([800, 900]);
  });
});

describe("vertical line renderer", () => {
  it("strokes a full-height line at the time-converted x", () => {
    const ctx = makeMockContext();
    const renderer = new VerticalLineRenderer();
    renderer.setSpec(makeSpec("vertical-line", [{ time: 5_000_000, price: null }]));
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const moveTo = ctx.__calls.find((c) => c.method === "moveTo");
    const lineTo = ctx.__calls.find((c) => c.method === "lineTo");
    expect(moveTo?.args).toEqual([5, 0]);
    expect(lineTo?.args).toEqual([5, 600]);
  });
});

describe("ray renderer", () => {
  it("projects to the right edge when direction is positive", () => {
    const ctx = makeMockContext();
    const renderer = new RayRenderer();
    renderer.setSpec(
      makeSpec("ray", [
        { time: 1_000_000, price: 100 },
        { time: 2_000_000, price: 110 },
      ]),
    );
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const lineTo = ctx.__calls.find((c) => c.method === "lineTo");
    // Line projects to x = 800 (right edge).
    expect(lineTo?.args[0]).toBe(800);
  });
});

describe("rectangle renderer", () => {
  it("draws an axis-aligned rect from min to max corners", () => {
    const ctx = makeMockContext();
    const renderer = new RectangleRenderer();
    renderer.setSpec(
      makeSpec("rectangle", [
        { time: 2_000_000, price: 100 }, // x=2, y=900
        { time: 1_000_000, price: 110 }, // x=1, y=890
      ]),
    );
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const fillRect = ctx.__calls.find((c) => c.method === "fillRect");
    expect(fillRect?.args).toEqual([1, 890, 1, 10]);
  });
});

describe("ellipse renderer", () => {
  it("draws an ellipse with bounding-box axes", () => {
    const ctx = makeMockContext();
    const renderer = new EllipseRenderer();
    renderer.setSpec(
      makeSpec("ellipse", [
        { time: 1_000_000, price: 100 },
        { time: 3_000_000, price: 120 },
      ]),
    );
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const ellipse = ctx.__calls.find((c) => c.method === "ellipse");
    expect(ellipse).toBeDefined();
    // Centre = (1+3)/2 = 2, (880+900)/2 = 890. rx = 1, ry = 10.
    expect(ellipse!.args[0]).toBe(2);
    expect(ellipse!.args[1]).toBe(890);
    expect(ellipse!.args[2]).toBe(1);
    expect(ellipse!.args[3]).toBe(10);
  });
});

describe("fib retracement renderer", () => {
  it("strokes one line per fib level", () => {
    const ctx = makeMockContext();
    const renderer = new FibRetracementRenderer();
    renderer.setSpec(
      makeSpec("fib-retracement", [
        { time: 1_000_000, price: 100 },
        { time: 2_000_000, price: 200 },
      ]),
    );
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const strokes = ctx.__calls.filter((c) => c.method === "stroke");
    expect(strokes.length).toBe(FIB_LEVELS.length);
  });
});

describe("fib extension renderer", () => {
  it("strokes one line per fib level using a third anchor", () => {
    const ctx = makeMockContext();
    const renderer = new FibExtensionRenderer();
    renderer.setSpec(
      makeSpec("fib-extension", [
        { time: 1_000_000, price: 100 },
        { time: 2_000_000, price: 150 },
        { time: 3_000_000, price: 130 },
      ]),
    );
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const strokes = ctx.__calls.filter((c) => c.method === "stroke");
    expect(strokes.length).toBe(FIB_LEVELS.length);
  });
});

describe("parallel channel renderer", () => {
  it("strokes the trendline and the parallel boundary, then fills", () => {
    const ctx = makeMockContext();
    const renderer = new ParallelChannelRenderer();
    renderer.setSpec(
      makeSpec("parallel-channel", [
        { time: 1_000_000, price: 100 },
        { time: 2_000_000, price: 110 },
        { time: 1_500_000, price: 95 },
      ]),
    );
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    expect(ctx.__calls.filter((c) => c.method === "stroke").length).toBe(2);
    expect(ctx.__calls.find((c) => c.method === "fill")).toBeDefined();
  });
});

describe("text renderer", () => {
  it("draws the kindOptions.text label at the anchor", () => {
    const ctx = makeMockContext();
    const renderer = new TextRenderer();
    renderer.setSpec({
      id: "t",
      panelId: "p",
      kind: "text",
      points: [{ time: 5_000_000, price: 200 }],
      style: { ...DEFAULT_DRAWING_STYLE },
      kindOptions: { text: "support", fontSize: 14 },
      createdAt: 0,
    });
    renderer.setConverters(converters);
    renderer.draw(makeDrawTarget(ctx));
    const fillText = ctx.__calls.find((c) => c.method === "fillText");
    expect(fillText?.args[0]).toBe("support");
  });
});

describe("DrawingPrimitive lifecycle", () => {
  it("attaches with a series, requests update on setSpec, detaches cleanly", () => {
    const requestUpdate = vi.fn();
    const series = {
      priceToCoordinate: (price: number) => 1000 - price,
    };
    const timeScale = {
      timeToCoordinate: (time: number) => time / 1_000_000,
    };
    const params = {
      series,
      chart: { timeScale: () => timeScale },
      requestUpdate,
    } as never;
    const spec = makeSpec("trendline", [
      { time: 1, price: 100 },
      { time: 2, price: 110 },
    ]);
    const primitive = createDrawingPrimitive(spec);
    primitive.attached(params);
    primitive.setSpec({ ...spec, label: "renamed" });
    expect(requestUpdate).toHaveBeenCalled();
    primitive.detached();
    // After detach, setSpec is a no-op for requestUpdate (params is null).
    requestUpdate.mockClear();
    primitive.setSpec({ ...spec, label: "again" });
    expect(requestUpdate).not.toHaveBeenCalled();
  });
});
