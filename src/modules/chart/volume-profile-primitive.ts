/**
 * Volume Profile — a price-pane horizontal-histogram custom series primitive.
 *
 * The sidecar returns a `VolumeProfile` (a list of `{ price, volume }`
 * buckets); this primitive draws one horizontal bar per bucket, positioned
 * vertically by the candlestick series' `priceToCoordinate(price)` and
 * extending leftward from the right edge of the price pane with a width
 * proportional to the bucket's share of the maximum bucket volume.
 *
 * Implemented as an `ISeriesPrimitive<Time>` so it attaches to the existing
 * candle series and shares its price scale, which guarantees the histogram
 * stays aligned with the candles as the user pans and zooms.
 */

import type {
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
} from "lightweight-charts";

import type { VolumeProfileBucket } from "../../../types/data";

/**
 * The renderer target type — fancy-canvas's `CanvasRenderingTarget2D` —
 * is a transitive dep of lightweight-charts and is not directly exposed
 * from its types. We pull the type structurally from the `draw` signature
 * so we do not need a separate `fancy-canvas` import.
 */
type DrawTarget = Parameters<IPrimitivePaneRenderer["draw"]>[0];

/** Fill — amber-400 (#e9a94d) at ~20% alpha. */
const HISTOGRAM_FILL = "rgba(233, 169, 77, 0.2)";

/** Fraction of the pane width the longest bar takes. */
const MAX_BAR_FRACTION = 0.25;

class VolumeProfileRenderer implements IPrimitivePaneRenderer {
  private _buckets: readonly VolumeProfileBucket[] = [];
  private _priceToY: ((price: number) => number | null) | null = null;
  private _barHeightPx = 4;

  setBuckets(buckets: readonly VolumeProfileBucket[]): void {
    this._buckets = buckets;
  }

  setPriceConverter(priceToY: (price: number) => number | null): void {
    this._priceToY = priceToY;
  }

  setBarHeight(heightPx: number): void {
    this._barHeightPx = Math.max(1, heightPx);
  }

  draw(target: DrawTarget): void {
    const buckets = this._buckets;
    const priceToY = this._priceToY;
    if (buckets.length === 0 || priceToY === null) {
      return;
    }
    const maxVolume = buckets.reduce(
      (peak, bucket) => (bucket.volume > peak ? bucket.volume : peak),
      0,
    );
    if (maxVolume <= 0) {
      return;
    }
    const barHeight = this._barHeightPx;
    target.useMediaCoordinateSpace(({ context, mediaSize }) => {
      const paneWidth = mediaSize.width;
      const maxBarWidth = paneWidth * MAX_BAR_FRACTION;
      context.fillStyle = HISTOGRAM_FILL;
      for (const bucket of buckets) {
        const y = priceToY(bucket.price);
        if (y === null || !Number.isFinite(y)) {
          continue;
        }
        const width = (bucket.volume / maxVolume) * maxBarWidth;
        if (width <= 0) {
          continue;
        }
        context.fillRect(paneWidth - width, y - barHeight / 2, width, barHeight);
      }
    });
  }
}

class VolumeProfilePaneView implements IPrimitivePaneView {
  private readonly _renderer = new VolumeProfileRenderer();

  setBuckets(buckets: readonly VolumeProfileBucket[]): void {
    this._renderer.setBuckets(buckets);
  }

  setPriceConverter(priceToY: (price: number) => number | null): void {
    this._renderer.setPriceConverter(priceToY);
  }

  setBarHeight(heightPx: number): void {
    this._renderer.setBarHeight(heightPx);
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

/**
 * Volume Profile primitive — attach via `series.attachPrimitive(primitive)`
 * to the candle series. Call `setBuckets()` whenever the sidecar payload
 * refreshes.
 */
export class VolumeProfilePrimitive implements ISeriesPrimitive<Time> {
  private readonly _paneView = new VolumeProfilePaneView();
  private _params: SeriesAttachedParameter<Time> | null = null;
  private _buckets: readonly VolumeProfileBucket[] = [];

  /** Replace the histogram's buckets and request a redraw. */
  setBuckets(buckets: readonly VolumeProfileBucket[]): void {
    this._buckets = buckets;
    this._paneView.setBuckets(buckets);
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
    // Capture the series instance so the renderer's price converter calls
    // the same series this primitive is attached to.
    const series = params.series;
    this._paneView.setPriceConverter((price) => series.priceToCoordinate(price));
    if (this._buckets.length > 1) {
      // Derive bar height from the median bucket spacing so adjacent bars
      // touch but do not overlap on a typical 24-bucket profile.
      const sorted = [...this._buckets].sort((a, b) => a.price - b.price);
      const gaps: number[] = [];
      for (let i = 1; i < sorted.length; i += 1) {
        const previous = sorted[i - 1];
        const current = sorted[i];
        if (previous && current) {
          gaps.push(current.price - previous.price);
        }
      }
      if (gaps.length > 0) {
        const midPrice = sorted[Math.floor(sorted.length / 2)]?.price ?? sorted[0]?.price ?? 0;
        const adjacentPrice = midPrice + gaps[0]!;
        const yMid = series.priceToCoordinate(midPrice);
        const yAdj = series.priceToCoordinate(adjacentPrice);
        if (yMid !== null && yAdj !== null) {
          const pixelGap = Math.abs(yAdj - yMid);
          if (Number.isFinite(pixelGap) && pixelGap > 0) {
            this._paneView.setBarHeight(pixelGap);
          }
        }
      }
    }
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this._paneView];
  }
}
