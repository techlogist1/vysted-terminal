/**
 * Drawing factory — `DrawingSpec → DrawingPrimitive`.
 *
 * Maps each `DrawingKind` to its concrete renderer subclass and returns a
 * fully-wired `DrawingPrimitive` ready to be attached to the candle series.
 * The factory is the only place that knows the kind→renderer mapping, so
 * adding a new drawing kind is one switch arm + one new renderer class.
 */

import { DrawingPrimitive } from "./base";
import {
  EllipseRenderer,
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

/** Build a primitive for `spec`'s kind. */
export function createDrawingPrimitive(spec: DrawingSpec): DrawingPrimitive {
  switch (spec.kind) {
    case "trendline":
      return new DrawingPrimitive(spec, new TrendlineRenderer());
    case "horizontal-line":
      return new DrawingPrimitive(spec, new HorizontalLineRenderer());
    case "vertical-line":
      return new DrawingPrimitive(spec, new VerticalLineRenderer());
    case "ray":
      return new DrawingPrimitive(spec, new RayRenderer());
    case "rectangle":
      return new DrawingPrimitive(spec, new RectangleRenderer());
    case "ellipse":
      return new DrawingPrimitive(spec, new EllipseRenderer());
    case "fib-retracement":
      return new DrawingPrimitive(spec, new FibRetracementRenderer());
    case "fib-extension":
      return new DrawingPrimitive(spec, new FibExtensionRenderer());
    case "parallel-channel":
      return new DrawingPrimitive(spec, new ParallelChannelRenderer());
    case "text":
      return new DrawingPrimitive(spec, new TextRenderer());
  }
}

/** How many click-anchors a kind needs before it is fully defined. */
export function pointsRequired(kind: DrawingKind): 1 | 2 | 3 {
  switch (kind) {
    case "horizontal-line":
    case "vertical-line":
    case "text":
      return 1;
    case "trendline":
    case "ray":
    case "rectangle":
    case "ellipse":
    case "fib-retracement":
      return 2;
    case "fib-extension":
    case "parallel-channel":
      return 3;
  }
}

/** Default style for a freshly-created drawing — amber-400 solid 1px line. */
export const DEFAULT_DRAWING_STYLE = {
  color: "#e9a94d",
  lineWidth: 1,
  lineStyle: "solid" as const,
  fillColor: "rgba(233, 169, 77, 0.12)",
} as const;
