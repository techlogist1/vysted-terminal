/**
 * Vysted Terminal — chart drawing tools.
 *
 * Type contract for the ten Phase-2 drawing tools (Teammate A) and the workspace
 * persistence layer that round-trips them through `.vysted-workspace` JSON.
 *
 * Each drawing kind is rendered by a dedicated `ISeriesPrimitive` attached to
 * the chart panel's candle series — the same pattern the existing
 * `IchimokuCloudPrimitive` and `VolumeProfilePrimitive` already use. The
 * drawing's *state* (kind, anchor points, style) is plain serializable data so
 * workspace round-trip is trivial; the renderer is rebuilt from the state on
 * panel mount.
 *
 * Foundation commit F3 — consumed by Teammate A (creates drawings) and the
 * workspace store (serializes them).
 */

// ---------------------------------------------------------------------------
// Drawing kinds
// ---------------------------------------------------------------------------

/** The ten drawing tools shipped in v0.3.0. */
export type DrawingKind =
  | "trendline" // two-point sloped line
  | "horizontal-line" // single price level, full width
  | "vertical-line" // single time, full height
  | "ray" // half-line from one anchor through another, extending to the edge
  | "rectangle" // two-point axis-aligned box
  | "ellipse" // two-point bounding-box ellipse
  | "fib-retracement" // two-point fib levels (0/0.236/0.382/0.5/0.618/0.786/1)
  | "fib-extension" // three-point projection of the same fib levels
  | "parallel-channel" // three-point channel: two anchors define the trend, third sets channel width
  | "text"; // free-text annotation anchored at one point

// ---------------------------------------------------------------------------
// Anchor points
// ---------------------------------------------------------------------------

/**
 * One anchor point on the chart. `time` is the lightweight-charts
 * `UTCTimestamp` (seconds since epoch); `price` is the domain price value.
 * Drawings that don't pin to a time use `null` (e.g. horizontal-line) — the
 * renderer interprets `null` as "extend across the visible range".
 */
export interface DrawingPoint {
  /** UTC seconds; `null` for time-axis-independent drawings. */
  time: number | null;
  /** Price value; `null` for price-axis-independent drawings (vertical-line). */
  price: number | null;
}

// ---------------------------------------------------------------------------
// Style
// ---------------------------------------------------------------------------

/**
 * Visual style shared by every drawing kind. Per-kind extensions (fib level
 * colours, text font size, etc.) live on `DrawingSpec.kindOptions`, which is
 * intentionally unstructured so each renderer can read what it needs without
 * forcing every kind to declare every field.
 */
export interface DrawingStyle {
  /** Stroke colour as a CSS hex (`#RRGGBB`); palette-driven default. */
  color: string;
  /** Stroke width in CSS pixels. */
  lineWidth: number;
  /** Stroke style — solid is the default; dashed/dotted are for projection lines. */
  lineStyle?: "solid" | "dashed" | "dotted";
  /** Optional fill colour for closed shapes (rectangle, ellipse, channel). */
  fillColor?: string;
}

// ---------------------------------------------------------------------------
// Drawing record
// ---------------------------------------------------------------------------

/**
 * One drawing on a chart panel. Serializes verbatim into the workspace JSON
 * under the chart panel's drawings collection. Stable `id` lets the renderer
 * reconcile state changes without rebuilding every primitive on every edit.
 */
export interface DrawingSpec {
  /** Stable per-drawing identifier (uuid-like; generator is Teammate A's call). */
  id: string;
  /** Which chart panel instance this drawing belongs to (multi-chart panels are non-singleton). */
  panelId: string;
  kind: DrawingKind;
  /** Two-three points depending on kind; the renderer asserts the right count. */
  points: DrawingPoint[];
  style: DrawingStyle;
  /** Free-form per-kind options (text content, fib levels, channel ratio). */
  kindOptions?: Record<string, unknown>;
  /** Whether the drawing is locked from accidental drag/edit. */
  locked?: boolean;
  /** Free-text label shown next to the drawing (optional). */
  label?: string;
  /** Epoch milliseconds when the drawing was created. */
  createdAt: number;
}

// ---------------------------------------------------------------------------
// Persistence — workspace serialization
// ---------------------------------------------------------------------------

/**
 * The shape stored in `.vysted-workspace` JSON for the drawings layer. Keyed
 * by `panelId` so each chart panel instance gets its own collection — multi-
 * chart sync (Phase 2) can have several chart panels open simultaneously, each
 * with independent drawings.
 */
export interface WorkspaceDrawings {
  /** Drawings collection per chart-panel id. */
  byPanel: Record<string, DrawingSpec[]>;
}
