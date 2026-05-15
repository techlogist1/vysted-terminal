/**
 * Drawing renderers — one class per `DrawingKind`.
 *
 * Each subclass overrides `paint(scope, spec, converters)` to draw its kind on
 * the canvas. Anchor resolution goes through `resolvePoint`; missing axes
 * (`null` x or y) fall back to pane edges so axis-independent kinds (the
 * horizontal-line and vertical-line) render across the visible region.
 *
 * Fib-retracement and fib-extension share a `FIB_LEVELS` constant; the
 * parallel-channel projects its third anchor's y-offset onto the trendline
 * direction; rectangle and ellipse normalise their two anchors into the
 * lexicographic order before drawing.
 */

import { DrawingRenderer, resolvePoint, type DrawingConverters } from "./base";
import type { DrawingPoint, DrawingSpec } from "../../../../types/drawings";

/** Standard fib retracement / extension levels. */
export const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1] as const;

interface PaintScope {
  context: CanvasRenderingContext2D;
  mediaSize: { width: number; height: number };
}

// --------------------------------------------------------------------------
// Trendline — two anchored points joined by a segment
// --------------------------------------------------------------------------

export class TrendlineRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = resolvePoint(spec.points[0] ?? blankPoint(), converters);
    const b = resolvePoint(spec.points[1] ?? blankPoint(), converters);
    if (a.x === null || a.y === null || b.x === null || b.y === null) {
      return;
    }
    const { context } = scope;
    context.beginPath();
    context.moveTo(a.x, a.y);
    context.lineTo(b.x, b.y);
    context.stroke();
  }
}

// --------------------------------------------------------------------------
// Horizontal line — pinned to a single price, extends across the visible pane
// --------------------------------------------------------------------------

export class HorizontalLineRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const point = spec.points[0];
    if (!point || point.price === null) {
      return;
    }
    const y = converters.priceToY(point.price);
    if (y === null) {
      return;
    }
    const { context, mediaSize } = scope;
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(mediaSize.width, y);
    context.stroke();
  }
}

// --------------------------------------------------------------------------
// Vertical line — pinned to a single time, extends top-to-bottom
// --------------------------------------------------------------------------

export class VerticalLineRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const point = spec.points[0];
    if (!point || point.time === null) {
      return;
    }
    const x = converters.timeToX(point.time);
    if (x === null) {
      return;
    }
    const { context, mediaSize } = scope;
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, mediaSize.height);
    context.stroke();
  }
}

// --------------------------------------------------------------------------
// Ray — half-line from anchor through second point, extending right
// --------------------------------------------------------------------------

export class RayRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = resolvePoint(spec.points[0] ?? blankPoint(), converters);
    const b = resolvePoint(spec.points[1] ?? blankPoint(), converters);
    if (a.x === null || a.y === null || b.x === null || b.y === null) {
      return;
    }
    const { context, mediaSize } = scope;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    if (dx === 0 && dy === 0) {
      return;
    }
    // Project to the right edge of the pane; keep going further if the second
    // anchor is to the left of the first (the ray points whichever direction
    // the user dragged).
    const targetX = dx >= 0 ? mediaSize.width : 0;
    const t = dx === 0 ? 0 : (targetX - a.x) / dx;
    const targetY = a.y + dy * t;
    context.beginPath();
    context.moveTo(a.x, a.y);
    context.lineTo(targetX, targetY);
    context.stroke();
  }
}

// --------------------------------------------------------------------------
// Rectangle — axis-aligned, two diagonal corners, fill + stroke
// --------------------------------------------------------------------------

export class RectangleRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = resolvePoint(spec.points[0] ?? blankPoint(), converters);
    const b = resolvePoint(spec.points[1] ?? blankPoint(), converters);
    if (a.x === null || a.y === null || b.x === null || b.y === null) {
      return;
    }
    const x = Math.min(a.x, b.x);
    const y = Math.min(a.y, b.y);
    const width = Math.abs(b.x - a.x);
    const height = Math.abs(b.y - a.y);
    const { context } = scope;
    context.fillRect(x, y, width, height);
    context.strokeRect(x, y, width, height);
  }
}

// --------------------------------------------------------------------------
// Ellipse — bounding-box, fill + stroke
// --------------------------------------------------------------------------

export class EllipseRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = resolvePoint(spec.points[0] ?? blankPoint(), converters);
    const b = resolvePoint(spec.points[1] ?? blankPoint(), converters);
    if (a.x === null || a.y === null || b.x === null || b.y === null) {
      return;
    }
    const cx = (a.x + b.x) / 2;
    const cy = (a.y + b.y) / 2;
    const rx = Math.abs(b.x - a.x) / 2;
    const ry = Math.abs(b.y - a.y) / 2;
    const { context } = scope;
    context.beginPath();
    context.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    context.fill();
    context.stroke();
  }
}

// --------------------------------------------------------------------------
// Fib retracement — two anchors define swing, levels fill across pane
// --------------------------------------------------------------------------

export class FibRetracementRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = spec.points[0];
    const b = spec.points[1];
    if (!a || !b || a.price === null || b.price === null) {
      return;
    }
    const yA = converters.priceToY(a.price);
    const yB = converters.priceToY(b.price);
    if (yA === null || yB === null) {
      return;
    }
    const xA = a.time === null ? 0 : (converters.timeToX(a.time) ?? 0);
    const { context, mediaSize } = scope;
    context.font = "10px ui-monospace, monospace";
    context.textBaseline = "middle";
    for (const level of FIB_LEVELS) {
      const price = a.price + (b.price - a.price) * level;
      const y = converters.priceToY(price);
      if (y === null) {
        continue;
      }
      context.beginPath();
      context.moveTo(xA, y);
      context.lineTo(mediaSize.width, y);
      context.stroke();
      context.fillStyle = spec.style.color || "#e9a94d";
      context.fillText(`${(level * 100).toFixed(1)}%  ${price.toFixed(2)}`, xA + 4, y - 6);
    }
    void yB;
  }
}

// --------------------------------------------------------------------------
// Fib extension — three-anchor projection of the same level set
// --------------------------------------------------------------------------

export class FibExtensionRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = spec.points[0];
    const b = spec.points[1];
    const c = spec.points[2];
    if (!a || !b || !c || a.price === null || b.price === null || c.price === null) {
      return;
    }
    const swing = b.price - a.price;
    const xC = c.time === null ? 0 : (converters.timeToX(c.time) ?? 0);
    const { context, mediaSize } = scope;
    context.font = "10px ui-monospace, monospace";
    context.textBaseline = "middle";
    for (const level of FIB_LEVELS) {
      const price = c.price + swing * level;
      const y = converters.priceToY(price);
      if (y === null) {
        continue;
      }
      context.beginPath();
      context.moveTo(xC, y);
      context.lineTo(mediaSize.width, y);
      context.stroke();
      context.fillStyle = spec.style.color || "#e9a94d";
      context.fillText(`${(level * 100).toFixed(1)}%  ${price.toFixed(2)}`, xC + 4, y - 6);
    }
  }
}

// --------------------------------------------------------------------------
// Parallel channel — two anchors define trend, third sets channel width
// --------------------------------------------------------------------------

export class ParallelChannelRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const a = resolvePoint(spec.points[0] ?? blankPoint(), converters);
    const b = resolvePoint(spec.points[1] ?? blankPoint(), converters);
    const c = resolvePoint(spec.points[2] ?? blankPoint(), converters);
    if (a.x === null || a.y === null || b.x === null || b.y === null || c.y === null) {
      return;
    }
    // Channel width — vertical offset of the third anchor from the trendline.
    const dx = b.x - a.x;
    const slope = dx === 0 ? 0 : (b.y - a.y) / dx;
    const trendlineYatC = a.y + slope * ((c.x ?? a.x) - a.x);
    const offset = c.y - trendlineYatC;
    const { context } = scope;
    // Trendline:
    context.beginPath();
    context.moveTo(a.x, a.y);
    context.lineTo(b.x, b.y);
    context.stroke();
    // Parallel boundary:
    context.beginPath();
    context.moveTo(a.x, a.y + offset);
    context.lineTo(b.x, b.y + offset);
    context.stroke();
    // Channel fill:
    context.beginPath();
    context.moveTo(a.x, a.y);
    context.lineTo(b.x, b.y);
    context.lineTo(b.x, b.y + offset);
    context.lineTo(a.x, a.y + offset);
    context.closePath();
    context.fill();
  }
}

// --------------------------------------------------------------------------
// Text annotation — single anchored label
// --------------------------------------------------------------------------

export class TextRenderer extends DrawingRenderer {
  protected paint(scope: PaintScope, spec: DrawingSpec, converters: DrawingConverters): void {
    const point = spec.points[0];
    if (!point) {
      return;
    }
    const x = point.time === null ? 8 : converters.timeToX(point.time);
    const y = point.price === null ? 16 : converters.priceToY(point.price);
    if (x === null || y === null) {
      return;
    }
    const text =
      typeof spec.kindOptions?.text === "string" && spec.kindOptions.text.length > 0
        ? spec.kindOptions.text
        : (spec.label ?? "label");
    const fontSize =
      typeof spec.kindOptions?.fontSize === "number" ? spec.kindOptions.fontSize : 12;
    const { context } = scope;
    context.font = `${fontSize}px ui-monospace, monospace`;
    context.textBaseline = "top";
    context.fillStyle = spec.style.color || "#e9a94d";
    context.setLineDash([]);
    context.fillText(text, x + 4, y - fontSize - 2);
  }
}

function blankPoint(): DrawingPoint {
  return { time: null, price: null };
}
