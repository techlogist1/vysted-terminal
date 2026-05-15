/**
 * Ichimoku Cloud — a price-pane series primitive that fills the band between
 * Senkou Span A and Senkou Span B.
 *
 * The sidecar emits the two Senkou lines on an extended timeline (historical
 * bars + 26 future bars), so the primitive can draw the conventional forward-
 * projected cloud without the chart truncating it at the series edge. Sage
 * (positive) fill where A >= B, negative-clay fill where B > A.
 */

import type {
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
} from "lightweight-charts";

import type { IndicatorPoint } from "../../../types/data";

/** Sage @ 15% alpha — bullish cloud (Senkou A above Senkou B). */
const POSITIVE_FILL = "rgba(143, 166, 124, 0.15)";
/** Negative-clay @ 15% alpha — bearish cloud (Senkou B above Senkou A). */
const NEGATIVE_FILL = "rgba(200, 101, 75, 0.15)";

/** Internal coordinate of a time-aligned Senkou sample after conversion. */
interface CloudPoint {
  x: number;
  yA: number;
  yB: number;
}

/**
 * Same target type trick as the Volume Profile primitive — pull the renderer
 * target structurally from `IPrimitivePaneRenderer.draw` rather than reaching
 * into fancy-canvas (a transitive dep of lightweight-charts).
 */
type DrawTarget = Parameters<IPrimitivePaneRenderer["draw"]>[0];

/** Convert an ISO-8601 string to the lightweight-charts UTCTimestamp (seconds). */
function isoToTime(iso: string): Time | null {
  const seconds = Math.floor(new Date(iso).getTime() / 1000);
  return Number.isFinite(seconds) ? (seconds as Time) : null;
}

class IchimokuCloudRenderer implements IPrimitivePaneRenderer {
  private _points: readonly CloudPoint[] = [];

  setPoints(points: readonly CloudPoint[]): void {
    this._points = points;
  }

  draw(target: DrawTarget): void {
    const points = this._points;
    if (points.length < 2) {
      return;
    }
    target.useMediaCoordinateSpace(({ context }) => {
      // Walk consecutive pairs and fill each trapezoid separately so the
      // colour can flip at the A/B crossover without a polygon-clipping pass.
      for (let i = 1; i < points.length; i += 1) {
        const prev = points[i - 1];
        const current = points[i];
        if (!prev || !current) {
          continue;
        }
        const prevAboveOrEq = prev.yA <= prev.yB; // canvas y grows downward
        const currentAboveOrEq = current.yA <= current.yB;
        const fillPositive = prevAboveOrEq && currentAboveOrEq;
        const fillNegative = !prevAboveOrEq && !currentAboveOrEq;
        // Skip the rare A/B-crossover segment; the visual gap is tiny at
        // typical zoom levels and avoiding it sidesteps a polygon split.
        if (!fillPositive && !fillNegative) {
          continue;
        }
        context.beginPath();
        context.moveTo(prev.x, prev.yA);
        context.lineTo(current.x, current.yA);
        context.lineTo(current.x, current.yB);
        context.lineTo(prev.x, prev.yB);
        context.closePath();
        context.fillStyle = fillPositive ? POSITIVE_FILL : NEGATIVE_FILL;
        context.fill();
      }
    });
  }
}

class IchimokuCloudPaneView implements IPrimitivePaneView {
  private readonly _renderer = new IchimokuCloudRenderer();

  setPoints(points: readonly CloudPoint[]): void {
    this._renderer.setPoints(points);
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

/**
 * Ichimoku cloud primitive — attach to the candle series; call `setBands`
 * with the two Senkou point arrays each time the indicator payload refreshes.
 */
export class IchimokuCloudPrimitive implements ISeriesPrimitive<Time> {
  private readonly _paneView = new IchimokuCloudPaneView();
  private _params: SeriesAttachedParameter<Time> | null = null;
  private _senkouA: readonly IndicatorPoint[] = [];
  private _senkouB: readonly IndicatorPoint[] = [];

  /** Replace the two Senkou band lines and request a redraw. */
  setBands(senkouA: readonly IndicatorPoint[], senkouB: readonly IndicatorPoint[]): void {
    this._senkouA = senkouA;
    this._senkouB = senkouB;
    this.updateAllViews();
    this._params?.requestUpdate();
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this._params = param;
    this.updateAllViews();
  }

  detached(): void {
    this._params = null;
  }

  updateAllViews(): void {
    const params = this._params;
    if (!params) {
      return;
    }
    const series = params.series;
    const timeScale = params.chart.timeScale();
    const bByTime = new Map<number, number>();
    for (const point of this._senkouB) {
      if (point.value === null) {
        continue;
      }
      const time = isoToTime(point.time);
      if (time === null) {
        continue;
      }
      bByTime.set(time as number, point.value);
    }
    const cloud: CloudPoint[] = [];
    for (const point of this._senkouA) {
      if (point.value === null) {
        continue;
      }
      const time = isoToTime(point.time);
      if (time === null) {
        continue;
      }
      const bValue = bByTime.get(time as number);
      if (bValue === undefined) {
        continue;
      }
      const x = timeScale.timeToCoordinate(time);
      const yA = series.priceToCoordinate(point.value);
      const yB = series.priceToCoordinate(bValue);
      if (x === null || yA === null || yB === null) {
        continue;
      }
      cloud.push({ x, yA, yB });
    }
    cloud.sort((a, b) => a.x - b.x);
    this._paneView.setPoints(cloud);
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this._paneView];
  }
}
