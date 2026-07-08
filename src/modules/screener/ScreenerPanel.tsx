"use client";

import { useCallback, useState } from "react";
import { Play, Square, AlertCircle, BookmarkPlus, BookmarkX, FolderOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";
import { useScreenerStore } from "@/store/screener";

import type { ScreenerUniverseId } from "../../../types/screener";
import { ScreenerCriteriaBuilder } from "./ScreenerCriteriaBuilder";
import { ScreenerPresets } from "./ScreenerPresets";
import { ScreenerResultsTable } from "./ScreenerResultsTable";

const UNIVERSE_LABELS: Record<ScreenerUniverseId, string> = {
  sp500: "S&P 500",
  nifty50: "NIFTY 50",
  "crypto-top50": "Crypto top 50",
  custom: "Custom tickers",
  "nse-all": "NSE — full market",
  "bse-all": "BSE — full market",
  "india-all": "India — NSE + BSE",
};

/** Format an epoch-seconds timestamp as a human-ago string (e.g. "4m ago"). */
function fmtAgo(epochSec: number): string {
  const diffSec = Math.max(0, Math.floor(Date.now() / 1000) - epochSec);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

/** Epoch seconds → a short "as of" date ("Jun 16"; year appended when it is
 *  not the current year) for the snapshot-basis label (D52). */
function fmtAsOfDate(epochSec: number): string {
  const d = new Date(epochSec * 1000);
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  if (d.getFullYear() !== new Date().getFullYear()) {
    opts.year = "numeric";
  }
  return d.toLocaleDateString("en-US", opts);
}

/** Designed short forms for the machine-readable skip reasons (D53) — a raw
 *  wire token never reaches the coverage line. Unknown reasons de-snake. */
function skipReasonLabel(reason: string): string {
  if (reason.startsWith("missing_field:")) {
    return `missing ${reason.slice("missing_field:".length)}`;
  }
  switch (reason) {
    case "rate_limited":
      return "rate-limited";
    case "not_found":
      return "not found";
    case "no_data":
      return "no data";
    case "timeout":
      return "timed out";
    case "correctness_gate":
      return "unverifiable";
    default:
      return reason.replace(/_/g, " ");
  }
}

const N = (n: number): string => n.toLocaleString("en-US");

/**
 * Screener panel — R10 rebuild.
 *
 * Layout: universe picker (top row) + saved-screens strip + criteria builder +
 * "Run / Cancel" action + results table (bottom). Default criteria
 * (P/E < 20 AND market cap > 100B AND sector = "Technology") are seeded
 * so the panel renders in a populated-state shape on first mount.
 */
export function ScreenerPanel() {
  const universe = useScreenerStore((s) => s.universe);
  const setUniverse = useScreenerStore((s) => s.setUniverse);
  const customSymbols = useScreenerStore((s) => s.customSymbols);
  const setCustomSymbols = useScreenerStore((s) => s.setCustomSymbols);
  const universeMeta = useScreenerStore((s) => s.universeMeta);
  const universeStatus = useScreenerStore((s) => s.universeStatus);
  const loadUniverse = useScreenerStore((s) => s.loadUniverse);
  const runScreener = useScreenerStore((s) => s.runScreener);
  const cancelRun = useScreenerStore((s) => s.cancelRun);
  const status = useScreenerStore((s) => s.status);
  const error = useScreenerStore((s) => s.error);
  const progress = useScreenerStore((s) => s.progress);
  const lastResult = useScreenerStore((s) => s.lastResult);
  const savedScreens = useScreenerStore((s) => s.savedScreens);
  const saveScreen = useScreenerStore((s) => s.saveScreen);
  const deleteScreen = useScreenerStore((s) => s.deleteScreen);
  const loadScreen = useScreenerStore((s) => s.loadScreen);

  const [saveName, setSaveName] = useState("");
  const [showSaveInput, setShowSaveInput] = useState(false);

  // Load the selected universe's ticker metadata. Auto-retries on a cold-boot
  // sidecar bind (and re-arms on reconnect) so a panel mounted before the
  // sidecar was ready self-heals instead of latching a dead universe count.
  const loadDefault = useCallback(async () => {
    if (universe === "custom") return;
    await loadUniverse(universe);
    if (useScreenerStore.getState().universeStatus[universe] === "error") {
      throw new Error(`Failed to load universe ${universe}`);
    }
  }, [universe, loadUniverse]);
  useRetryOnSidecarReady(loadDefault, [universe]);

  const universeInfo = universeMeta[universe];
  const isRunning = status === "loading";

  // Freshness label — three tiers with correct labels per the frozen contract:
  //   quotes_as_of   → "quotes"       (600s quote tier)
  //   valuation_as_of → "valuation"   (6h v7 valuation tier)
  //   deep_as_of     → "deep fields"  (7d .info deep tier — ROE, margins, growth)
  // Brief example: "quotes 4m ago · deep fields 2d ago" maps "deep fields"
  // to deep_as_of, NOT valuation_as_of.
  function freshnessLine(): string | null {
    const f = lastResult?.freshness;
    if (!f) return null;
    const parts: string[] = [];
    if (f.quotes_as_of) parts.push(`quotes ${fmtAgo(f.quotes_as_of)}`);
    if (f.valuation_as_of) parts.push(`valuation ${fmtAgo(f.valuation_as_of)}`);
    if (f.deep_as_of) parts.push(`deep fields ${fmtAgo(f.deep_as_of)}`);
    return parts.length > 0 ? parts.join(" · ") : null;
  }

  // D52: the serving-basis mix — "1,900 live · 775 snapshot (as of Jun 16)".
  // Known bases render in a fixed order; an unexpected basis key still renders
  // (never silently dropped). The snapshot count carries the seed pack's honest
  // as-of date from freshness.seed_as_of when present.
  function basisLine(): string | null {
    const counts = lastResult?.basis_counts;
    if (!counts) return null;
    const seedAsOf = lastResult?.freshness?.seed_as_of;
    const order = ["live", "mixed", "snapshot"];
    const keys = [
      ...order.filter((k) => k in counts),
      ...Object.keys(counts)
        .filter((k) => !order.includes(k))
        .sort(),
    ];
    const parts: string[] = [];
    for (const key of keys) {
      const n = counts[key];
      if (typeof n !== "number" || n <= 0) continue;
      const asOf = key === "snapshot" && seedAsOf ? ` (as of ${fmtAsOfDate(seedAsOf)})` : "";
      parts.push(`${N(n)} ${key}${asOf}`);
    }
    return parts.length > 0 ? parts.join(" · ") : null;
  }

  // D53: aggregate the itemized skip ledger into a compact reason breakdown —
  // "554 unavailable — 300 rate-limited · 254 missing roe" (top 3 reasons,
  // tail collapsed into "other") so a user can tell "throttled, retry" from
  // "permanently absent" without reading a raw ledger.
  function skipBreakdown(): string | null {
    const details = lastResult?.skip_details;
    if (!details || details.length === 0) return null;
    const counts = new Map<string, number>();
    for (const d of details) {
      counts.set(d.reason, (counts.get(d.reason) ?? 0) + 1);
    }
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const parts = sorted.slice(0, 3).map(([reason, n]) => `${N(n)} ${skipReasonLabel(reason)}`);
    const tail = sorted.slice(3).reduce((sum, [, n]) => sum + n, 0);
    if (tail > 0) {
      parts.push(`${N(tail)} other`);
    }
    return `${N(details.length)} unavailable — ${parts.join(" · ")}`;
  }

  const handleSave = () => {
    const trimmed = saveName.trim();
    if (!trimmed) return;
    saveScreen(trimmed);
    setSaveName("");
    setShowSaveInput(false);
  };

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden p-3">
      {/* ── Universe picker row ─────────────────────────────────────────── */}
      <div className="border-border flex flex-wrap items-end gap-3 border-b pb-3">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="screener-universe"
            className="text-muted-foreground text-caption tracking-wide uppercase"
          >
            Universe
          </label>
          <select
            id="screener-universe"
            aria-label="universe"
            value={universe}
            onChange={(e) => setUniverse(e.target.value as ScreenerUniverseId)}
            className="border-border bg-charcoal-850 rounded-control text-body h-8 border px-2"
          >
            {(Object.keys(UNIVERSE_LABELS) as ScreenerUniverseId[]).map((id) => (
              <option key={id} value={id}>
                {UNIVERSE_LABELS[id]}
              </option>
            ))}
          </select>
          {universe !== "custom" &&
            (universeStatus[universe] === "loading" ? (
              <span className="text-muted-foreground text-micro animate-pulse">
                Loading universe…
              </span>
            ) : universeStatus[universe] === "error" ? (
              <span className="text-destructive text-micro">Failed to load universe</span>
            ) : universeInfo ? (
              <span className="text-muted-foreground text-micro">
                {universeInfo.symbols.length} tickers · {universeInfo.asset_class}
              </span>
            ) : null)}
        </div>
        {universe === "custom" && (
          <div className="flex min-w-[16rem] flex-1 flex-col gap-1">
            <label
              htmlFor="screener-custom-symbols"
              className="text-muted-foreground text-caption tracking-wide uppercase"
            >
              Symbols (comma or space)
            </label>
            <input
              id="screener-custom-symbols"
              type="text"
              value={customSymbols}
              onChange={(e) => setCustomSymbols(e.target.value)}
              placeholder="AAPL MSFT NVDA"
              className="border-border bg-charcoal-850 rounded-control text-body h-8 border px-2"
            />
          </div>
        )}
        {universe === "custom" && customSymbols.trim() === "" && (
          <span className="text-warning text-micro">Enter at least one ticker to screen.</span>
        )}
        {/* Run / Cancel morph button */}
        <div className="ml-auto">
          {isRunning ? (
            <Button onClick={cancelRun} variant="outline" data-testid="cancel-screener-button">
              <Square className={"mr-1 size-3.5" /* tokens-ok: 14px icon — R9 §3 rung for h-8 */} />
              Cancel
            </Button>
          ) : (
            <Button
              onClick={() => void runScreener()}
              disabled={universe === "custom" && customSymbols.trim() === ""}
              data-testid="run-screener-button"
            >
              <Play className={"mr-1 size-3.5" /* tokens-ok: 14px icon — R9 §3 rung for h-8 */} />
              Run screener
            </Button>
          )}
        </div>
      </div>

      {/* ── Progress line (R10 D40: honest, not spinner-forever) ────────── */}
      {isRunning && (
        <div className="shrink-0 space-y-1" data-testid="screener-progress">
          <div className="text-muted-foreground text-caption tabular-nums">
            {progress
              ? progress.detail
              : // No progress frames yet — be honest: we are sending the request.
                // On the streaming path this resolves quickly; on the unary fallback
                // progress stays null for the entire run so we label it accordingly.
                "Sending request…"}
          </div>
          {/* Determinate 2px progress bar — zinc-700 track, lume fill.
              When progress is null (e.g. unary path), show a thin indeterminate
              pulse rather than a 0% bar that falsely implies 0% done. */}
          {progress ? (
            <div className="bg-charcoal-700 h-0.5 w-full overflow-hidden rounded-none">
              <div
                className="bg-lume h-full transition-[width] duration-300"
                style={{
                  width:
                    progress.total > 0
                      ? `${Math.min(100, (progress.done / progress.total) * 100).toFixed(1)}%`
                      : "0%",
                }}
              />
            </div>
          ) : (
            <div className="bg-charcoal-700 h-0.5 w-full overflow-hidden rounded-none">
              <div className="bg-lume h-full w-1/3 animate-pulse transition-[width] duration-300" />
            </div>
          )}
        </div>
      )}

      {/* ── Error banner ──────────────────────────────────────────────────── */}
      {error && (
        <div className="border-destructive/40 text-destructive text-body flex items-center gap-2 rounded-none border px-3 py-2">
          <AlertCircle className="size-4 shrink-0" />
          <span className="flex-1">
            {error.startsWith("POST /screener/run")
              ? "Screener failed: " +
                error.replace(/^POST \/screener\/run\S* failed \(\d+\):\s*/, "").slice(0, 120)
              : error.slice(0, 120)}
          </span>
          <button
            type="button"
            className="text-caption ml-auto shrink-0 underline"
            onClick={() => void runScreener()}
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Saved-screens strip ───────────────────────────────────────────── */}
      <div className="shrink-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground text-micro shrink-0 tracking-wide uppercase">
            {">"} Saved
          </span>
          {savedScreens.length === 0 && (
            <span className="text-muted-foreground text-micro">No saved screens</span>
          )}
          {savedScreens.map((screen) => (
            <div key={screen.name} className="flex items-center">
              <button
                type="button"
                onClick={() => loadScreen(screen.name)}
                className="border-border bg-charcoal-850 text-muted-foreground rounded-control text-micro hover:border-charcoal-500 hover:text-charcoal-100 border px-2 py-0.5 transition-colors"
                data-testid={`load-screen-${screen.name}`}
              >
                <FolderOpen className="mr-1 inline size-3" />
                {screen.name}
              </button>
              <button
                type="button"
                onClick={() => deleteScreen(screen.name)}
                aria-label={`Delete saved screen ${screen.name}`}
                className="text-muted-foreground hover:text-destructive ml-0.5 p-0.5 transition-colors"
                data-testid={`delete-screen-${screen.name}`}
              >
                <BookmarkX className="size-3" />
              </button>
            </div>
          ))}
          {/* Save current screen — inline name input, not a modal */}
          {showSaveInput ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSave();
                  if (e.key === "Escape") {
                    setShowSaveInput(false);
                    setSaveName("");
                  }
                }}
                placeholder="Screen name…"
                autoFocus
                className="border-border bg-charcoal-850 rounded-control text-caption h-6 border px-2"
                data-testid="save-screen-input"
              />
              <button
                type="button"
                onClick={handleSave}
                disabled={saveName.trim() === ""}
                className="text-micro text-muted-foreground hover:text-charcoal-100 disabled:opacity-40"
                data-testid="save-screen-confirm"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSaveInput(false);
                  setSaveName("");
                }}
                className="text-micro text-muted-foreground hover:text-charcoal-100"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowSaveInput(true)}
              className="border-border bg-charcoal-850 text-muted-foreground rounded-control text-micro hover:border-charcoal-500 hover:text-charcoal-100 border px-2 py-0.5 transition-colors"
              data-testid="open-save-screen"
            >
              <BookmarkPlus className="mr-1 inline size-3" />
              Save screen
            </button>
          )}
        </div>
      </div>

      {/* ── Result header: coverage + PARTIAL badge + freshness ───────────── */}
      {lastResult && (
        <div className="shrink-0 space-y-0.5">
          {/* PARTIAL badge: shown whenever partial=true, independent of coverage.
              VYSTED_DESIGN.md:458 — signal colors appear as text or 1px markers,
              never a filled background. Badge is text-only (text-warning), no bg. */}
          {lastResult.partial && (
            <div className="text-caption flex items-center gap-2">
              <span
                className="text-warning text-micro border-warning/50 rounded-none border px-1 py-0.5 font-medium tracking-wide uppercase"
                data-testid="partial-badge"
              >
                PARTIAL
              </span>
              {lastResult.coverage && (
                <span className="text-muted-foreground">{lastResult.coverage}</span>
              )}
            </div>
          )}
          {!lastResult.partial && lastResult.coverage && (
            <div className="text-muted-foreground text-caption">{lastResult.coverage}</div>
          )}
          {/* D53: an honest, quiet one-liner when the run detected upstream
              throttling and degraded to cached/snapshot basis — text-only
              (signal colors never fill a background). */}
          {lastResult.throttled && (
            <div className="text-warning text-micro" data-testid="throttle-notice">
              Data provider is throttling this IP — showing cached/snapshot values; they refresh
              automatically.
            </div>
          )}
          {/* D52: the serving-basis mix for the returned rows. */}
          {basisLine() && (
            <div className="text-muted-foreground text-micro" data-testid="basis-counts">
              {basisLine()}
            </div>
          )}
          {/* D53: WHY symbols were unavailable, not just how many. */}
          {skipBreakdown() && (
            <div className="text-muted-foreground text-micro" data-testid="skip-breakdown">
              {skipBreakdown()}
            </div>
          )}
          {freshnessLine() && (
            <div className="text-muted-foreground text-micro">{freshnessLine()}</div>
          )}
        </div>
      )}

      <div className="shrink-0">
        <ScreenerPresets />
      </div>
      <div className="shrink-0">
        <ScreenerCriteriaBuilder />
      </div>
      <div className="min-h-0 flex-1">
        <ScreenerResultsTable />
      </div>
    </div>
  );
}
