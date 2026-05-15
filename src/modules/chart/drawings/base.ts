/**
 * Drawing primitive base — boilerplate every kind shares.
 *
 * Each of the ten Phase-2 drawings is an `ISeriesPrimitive<Time>` (the same
 * pattern `IchimokuCloudPrimitive` and `VolumeProfilePrimitive` already use).
 * The base class collapses the lifecycle stubs (`attached`, `detached`,
 * `updateAllViews`, `paneViews`) so each kind only needs to implement the
 * canvas `draw()` method on its renderer.
 *
 * The renderer reads anchor coordinates through a converter the base sets up
 * on `attached` — `timeToCoordinate` (chart time scale) and `priceToCoordinate`
 * (the host candle series). Drawings that anchor on time-only or price-only
 * (vertical-line / horizontal-line) tolerate `null` from the converter.
 */

import type {
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
} from "lightweight-charts";

import type { DrawingPoint, DrawingSpec, DrawingStyle } from "../../../../types/drawings";

/** The renderer target type — pulled structurally from `IPrimitivePaneRenderer.draw`. */
export type DrawTarget = Parameters<IPrimitivePaneRenderer["draw"]>[0];

/** Default per-kind colour (amber-400) — overridable per drawing in `style.color`. */
export const DEFAULT_DRAWING_COLOR = "#e9a94d";

/** Convert a `DrawingStyle.lineStyle` to a canvas `setLineDash` pattern. */
export function dashPattern(lineStyle: DrawingStyle["lineStyle"]): readonly number[] {
  switch (lineStyle) {
    case "dashed":
      return [6, 4];
    case "dotted":
      return [2, 3];
    default:
      return [];
  }
}

/**
 * Concrete coordinates for a `DrawingPoint`. Anchored points report `x` and
 * `y`; "extend across visible range" anchors return `null` for the missing
 * axis so the renderer can fall back to the pane edges.
 */
export interface DrawingCoordinate {
  x: number | null;
  y: number | null;
}

/** Converter set on the renderer when the primitive is attached to a series. */
export interface DrawingConverters {
  timeToX: (time: number) => number | null;
  priceToY: (price: number) => number | null;
  paneSize: () => { width: number; height: number };
}

/**
 * Resolve a `DrawingPoint` to canvas coordinates using the chart's time scale
 * and the host series' price scale. Returns `null` axes for unpinned anchors.
 */
export function resolvePoint(
  point: DrawingPoint,
  converters: DrawingConverters,
): DrawingCoordinate {
  return {
    x: point.time === null ? null : converters.timeToX(point.time),
    y: point.price === null ? null : converters.priceToY(point.price),
  };
}

/**
 * Base renderer for a single drawing kind. Subclasses override `paint` with
 * their kind-specific canvas calls; the base wires the converters and the
 * spec for them.
 */
export abstract class DrawingRenderer implements IPrimitivePaneRenderer {
  protected spec: DrawingSpec | null = null;
  protected converters: DrawingConverters | null = null;

  setSpec(spec: DrawingSpec): void {
    this.spec = spec;
  }

  setConverters(converters: DrawingConverters): void {
    this.converters = converters;
  }

  draw(target: DrawTarget): void {
    const spec = this.spec;
    const converters = this.converters;
    if (!spec || !converters) {
      return;
    }
    target.useMediaCoordinateSpace((scope) => {
      const { context, mediaSize } = scope;
      // Stroke style + dash pattern shared by every kind — subclasses can
      // override on their context after calling super.
      context.strokeStyle = spec.style.color || DEFAULT_DRAWING_COLOR;
      context.lineWidth = spec.style.lineWidth || 1;
      context.fillStyle = spec.style.fillColor ?? "rgba(233, 169, 77, 0.12)";
      const pattern = dashPattern(spec.style.lineStyle);
      context.setLineDash(pattern.slice());
      this.paint({ context, mediaSize }, spec, converters);
    });
  }

  /** Kind-specific draw — override in subclasses. */
  protected abstract paint(
    scope: { context: CanvasRenderingContext2D; mediaSize: { width: number; height: number } },
    spec: DrawingSpec,
    converters: DrawingConverters,
  ): void;
}

/**
 * `IPrimitivePaneView` wrapper around a kind-specific renderer. Subclasses
 * pass their concrete renderer to the base via the constructor; the rest of
 * the lifecycle plumbing is shared.
 */
export class DrawingPaneView implements IPrimitivePaneView {
  constructor(private readonly _renderer: DrawingRenderer) {}

  setSpec(spec: DrawingSpec): void {
    this._renderer.setSpec(spec);
  }

  setConverters(converters: DrawingConverters): void {
    this._renderer.setConverters(converters);
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

/**
 * `ISeriesPrimitive` host for a single drawing. Built via the factory; one
 * primitive per `DrawingSpec.id`. The host owns the spec, runs the converters
 * setup on attach, and forwards spec updates to the pane view.
 */
export class DrawingPrimitive implements ISeriesPrimitive<Time> {
  private params: SeriesAttachedParameter<Time> | null = null;
  private spec: DrawingSpec;
  private readonly paneView: DrawingPaneView;

  constructor(spec: DrawingSpec, renderer: DrawingRenderer) {
    this.spec = spec;
    this.paneView = new DrawingPaneView(renderer);
    this.paneView.setSpec(spec);
  }

  /** Replace the spec and request a redraw. */
  setSpec(spec: DrawingSpec): void {
    this.spec = spec;
    this.paneView.setSpec(spec);
    this.updateAllViews();
    this.params?.requestUpdate();
  }

  attached(params: SeriesAttachedParameter<Time>): void {
    this.params = params;
    this.updateAllViews();
  }

  detached(): void {
    this.params = null;
  }

  updateAllViews(): void {
    const params = this.params;
    if (!params) {
      return;
    }
    const series = params.series;
    const timeScale = params.chart.timeScale();
    this.paneView.setConverters({
      timeToX: (time) => timeScale.timeToCoordinate(time as Time),
      priceToY: (price) => series.priceToCoordinate(price),
      paneSize: () => ({
        width: 0, // not used directly; renderer reads mediaSize from canvas
        height: 0,
      }),
    });
    this.paneView.setSpec(this.spec);
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this.paneView];
  }
}
