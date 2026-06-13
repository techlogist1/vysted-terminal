"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Archive,
  ChevronDown,
  ChevronRight,
  ClipboardCopy,
  ExternalLink,
  FlaskConical,
  Globe,
  RefreshCw,
  Telescope,
  X,
} from "lucide-react";

import type {
  BriefDepth,
  BriefDisambiguation,
  BriefSource,
  BriefSourceType,
  BriefStep,
  ResearchBriefData,
} from "../../../types/brief";
import { ProvenanceBadge, StalenessBadge } from "@/components/DataBadges";
import {
  bodyCitesWeb,
  briefDepthTier,
  composeBriefMarkdown,
  dedupeSources,
  deriveSourceType,
  formatBriefSpend,
  formatBriefTokens,
  nextBriefDepth,
} from "@/lib/brief-ingest";
import { formatElapsed, ResearchActivity } from "@/modules/chat/ResearchActivity";
import { researchDepthPrompt, useAgentCommandStore } from "@/store/agent-command";
import { useBriefStore, type BriefPanelState } from "@/store/brief";
import { useWorkspaceStore } from "@/store/workspace";
import type { ResearchStepView } from "@/store/chat-history";
import { BriefBody } from "./brief-blocks";

const IS_DEV = process.env.NODE_ENV !== "production";

/** Derive a bare domain from a URL, falling back to the raw string on parse error. */
function domainOf(source: BriefSource): string {
  if (source.domain) {
    return source.domain;
  }
  try {
    return new URL(source.url).hostname.replace(/^www\./, "");
  } catch {
    return source.url;
  }
}

// The brief BODY is now rendered as a typed-block document (metric cards, tables,
// prose with live ticker chips + citation chips) by `BriefBody` in `brief-blocks`
// — deterministically derived from the brief, never a wall of raw markdown.

// --- metadata header -------------------------------------------------------

function ModeBadge({ mode }: { mode: ResearchBriefData["mode"] }) {
  const deep = mode === "DEEP";
  return (
    <span
      className={`rounded-control text-micro px-1 py-0.5 font-mono font-medium tracking-wide uppercase ${
        deep ? "bg-charcoal-850 text-charcoal-300" : "bg-charcoal-800 text-charcoal-300"
      }`}
      title={deep ? "Deep research run" : "Fast research run"}
    >
      {mode}
    </span>
  );
}

// --- depth mirror — a THIN, READ-ONLY echo of the current tier (FR-115) -----

const DEPTH_LABEL: Record<BriefDepth, string> = {
  quick: "FAST",
  deep: "DEEP",
  heavy: "HEAVY",
};

/**
 * Depth mirror — a READ-ONLY echo of the tier this brief reached. The single
 * actionable "Go deeper" escalation lives in the CHAT surface (one source of
 * truth, FR-115); this panel only REFLECTS the current depth so the brief and
 * the chat never carry two independently-actionable controls that can race. The
 * Telescope glyph + the chat control share the same idiom (border-charcoal-700 /
 * text-micro / rounded-control) so the mirror reads as the same concept.
 */
function DepthMirror({ brief }: { brief: ResearchBriefData }) {
  const current = briefDepthTier(brief);
  const next = nextBriefDepth(current);
  return (
    <span
      title={
        next
          ? `Depth ${DEPTH_LABEL[current]} — go deeper from the chat depth control.`
          : "This is the deepest research tier."
      }
      className="border-charcoal-700 text-charcoal-400 rounded-control text-micro ml-auto flex shrink-0 items-center gap-1 border px-2 py-0.5 font-mono"
    >
      <Telescope className="size-3" /> {DEPTH_LABEL[current]}
      {!next ? <span className="text-charcoal-500">· deepest</span> : null}
    </span>
  );
}

function MetaHeader({ brief }: { brief: ResearchBriefData }) {
  // R8 Proportion Law §6: a zero-token segment is OMITTED (never "0 tok") and
  // "$0.0000" never renders (zero spend omitted; below $0.005 → "<$0.01").
  const tokenLabel = formatBriefTokens(brief.cost?.tokens);
  const spendLabel = formatBriefSpend(brief.cost?.spendUsd);
  return (
    <header className="border-charcoal-700 flex flex-col gap-2 border-b px-4 py-3">
      {/* R8 Proportion Law §3.4: the meta row declares its collapse — chips
          never shrink mid-glyph (shrink-0 + nowrap) and the row WRAPS to a
          second line instead of overlapping ("92 SOURCES FOR $0.0000" colliding
          with the symbol chip on the live screenshot). Only the symbol (user
          content) may truncate with an honest ellipsis. */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <ModeBadge mode={brief.mode} />
        {brief.symbol ? (
          <span
            className="text-micro text-charcoal-100 max-w-40 truncate font-mono font-medium"
            title={brief.symbol}
          >
            {brief.symbol}
          </span>
        ) : null}
        <span className="text-charcoal-500 text-micro font-mono whitespace-nowrap">
          {brief.sourceCount} source{brief.sourceCount === 1 ? "" : "s"}
        </span>
        {tokenLabel ? (
          <span
            className="text-charcoal-500 text-micro font-mono whitespace-nowrap"
            title={`${brief.cost?.tokens} tokens`}
          >
            · {tokenLabel}
          </span>
        ) : null}
        {spendLabel ? (
          <span className="text-charcoal-500 text-micro font-mono whitespace-nowrap">
            · {spendLabel}
          </span>
        ) : null}
        {/* Read-only depth mirror — the actionable "Go deeper" escalation lives
            in the chat surface (one source of truth); this only reflects the
            tier this brief reached (FR-115). */}
        <DepthMirror brief={brief} />
      </div>
      {/* Provenance line: WHERE the brief drew from (web vs structured-data-only)
          and WHEN it was produced, so a cached/offline run is never mistaken for
          a fresh web pull. Subtle by design — it sits under the mode/cost row.
          NB: this badge keys off REAL web sources (http(s) URLs), NOT the
          reconciled `webAvailable` flag — that flag is true whenever ANY source
          (incl. synthetic `vysted://` structured-provenance legs) was cited, so
          using it here would falsely claim "web" for a structured-only run. */}
      <div className="flex flex-wrap items-center gap-2">
        <ProvenanceBadge
          provider={
            (brief.sources ?? []).some((s) => /^https?:\/\//i.test(s.url))
              ? "web + structured data"
              : "structured data"
          }
        />
        {typeof brief.createdAt === "number" ? (
          <StalenessBadge freshness="eod" asOf={brief.createdAt} />
        ) : null}
      </div>
      <h2 className="text-charcoal-100 text-panel-title leading-snug">{brief.query}</h2>
    </header>
  );
}

// --- sources tray ----------------------------------------------------------

function FaviconDot({ domain }: { domain: string }) {
  const [errored, setErrored] = useState(false);
  if (errored) {
    return (
      <span aria-hidden="true" className="bg-charcoal-600 mt-1 size-3 shrink-0 rounded-full" />
    );
  }
  return (
    // Favicon is best-effort: Google's S2 service, falling back to a neutral
    // dot if it 404s or the user is offline. `referrerPolicy=no-referrer` keeps
    // the brief query out of the request.
    <img
      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=32`}
      alt=""
      width={12}
      height={12}
      referrerPolicy="no-referrer"
      onError={() => setErrored(true)}
      className="rounded-control mt-1 size-3 shrink-0"
    />
  );
}

/** Per-type label for the quiet source-type badge. */
const SOURCE_TYPE_LABEL: Record<BriefSourceType, string> = {
  news: "news",
  research: "research",
  filing: "filing",
  web: "web",
};

/**
 * A small, quiet source-category badge (news / research / filing / web). Stays
 * tertiary by design — same warm-neutral surface as the domain chip, no accent
 * fill — so it reads as metadata, never as the one accent affordance.
 */
function SourceTypeBadge({ type }: { type: BriefSourceType }) {
  return (
    <span className="border-charcoal-700 text-charcoal-400 bg-charcoal-850 rounded-control text-micro shrink-0 border px-1 py-0.5 font-mono tracking-wide uppercase">
      {SOURCE_TYPE_LABEL[type]}
    </span>
  );
}

function SourceRow({
  index,
  source,
  registerRef,
}: {
  index: number;
  source: BriefSource;
  registerRef: (n: number, el: HTMLLIElement | null) => void;
}) {
  const domain = domainOf(source);
  const sourceType = deriveSourceType(source);
  return (
    <li
      ref={(el) => registerRef(index, el)}
      className="border-charcoal-800 target:bg-charcoal-875 flex gap-2 border-b px-4 py-3 last:border-b-0"
      data-source-index={index}
    >
      <span className="text-charcoal-500 text-micro w-4 shrink-0 pt-0.5 text-right font-mono">
        {index}
      </span>
      <FaviconDot domain={domain} />
      <div className="flex min-w-0 flex-col gap-1">
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="text-charcoal-100 group text-caption hover:text-charcoal-100 inline-flex items-start gap-1 leading-snug transition-colors"
        >
          <span className="min-w-0">{source.title || source.url}</span>
          <ExternalLink className="text-charcoal-600 group-hover:text-charcoal-100 mt-0.5 size-3 shrink-0" />
        </a>
        <div className="flex flex-wrap items-center gap-2">
          <SourceTypeBadge type={sourceType} />
          <span className="text-charcoal-500 bg-charcoal-850 rounded-control text-micro max-w-full truncate px-1 py-px font-mono">
            {domain}
          </span>
        </div>
        {source.excerpt ? (
          <p className="text-charcoal-400 text-micro line-clamp-3 leading-relaxed">
            {source.excerpt}
          </p>
        ) : null}
      </div>
    </li>
  );
}

// --- dev step-log tray -----------------------------------------------------

const STEP_STATUS_COLOR: Record<BriefStep["status"], string> = {
  ok: "text-positive",
  error: "text-negative",
  skipped: "text-charcoal-500",
};

function StepLog({ steps }: { steps: BriefStep[] }) {
  return (
    <ul className="flex flex-col">
      {steps.map((step, i) => (
        <li
          key={i}
          className="border-charcoal-850 text-micro flex items-center gap-2 border-b px-4 py-1 font-mono last:border-b-0"
        >
          <span className={`shrink-0 ${STEP_STATUS_COLOR[step.status]}`} aria-hidden="true">
            ●
          </span>
          <span className="text-charcoal-400 w-16 shrink-0 tracking-wide uppercase">
            {step.kind}
          </span>
          <span className="text-charcoal-300 min-w-0 flex-1 truncate" title={step.detail}>
            {step.detail}
          </span>
          {typeof step.latencyMs === "number" ? (
            <span className="text-charcoal-600 shrink-0">{step.latencyMs}ms</span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

// --- collapsible tray shell ------------------------------------------------

function Tray({
  title,
  count,
  defaultOpen,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(Boolean(defaultOpen));
  return (
    <section className="border-charcoal-700 border-t">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="text-charcoal-300 hover:text-charcoal-100 text-micro flex w-full items-center gap-2 px-4 py-2 font-mono tracking-wide uppercase transition-colors"
      >
        {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        {title}
        {typeof count === "number" ? (
          <span className="text-charcoal-500 normal-case">({count})</span>
        ) : null}
      </button>
      {open ? <div>{children}</div> : null}
    </section>
  );
}

// --- keyless-fallback nudge --------------------------------------------------

/**
 * The honest keyless-fallback nudge (R9 gate 2): when the published brief's
 * backend id is `keyless-fallback` — SearXNG wasn't ready, the run silently
 * fell back to the rate-limited keyless engines — ONE quiet banner says so and
 * links to Settings → Research. Never rendered for the searxng /
 * research-model backends; dismissible per-brief (the parent keys dismissal
 * on the brief identity, so the next run's banner re-appears honestly).
 */
function KeylessFallbackNudge({ onDismiss }: { onDismiss: () => void }) {
  const openSettings = useCallback(() => {
    useWorkspaceStore.getState().openPanel("settings");
  }, []);
  return (
    <div className="border-charcoal-700 bg-charcoal-925 mx-3 mt-3 flex items-start gap-2 rounded-none border px-3 py-2">
      <Globe className="text-charcoal-400 mt-0.5 size-3 shrink-0" aria-hidden />
      <p className="text-charcoal-300 text-caption min-w-0 flex-1 leading-relaxed">
        Limited keyless search —{" "}
        <button
          type="button"
          onClick={openSettings}
          className="text-charcoal-100 hover:text-lume cursor-pointer underline underline-offset-2 transition-colors"
          title="Open Settings → Research"
        >
          set up Unlimited local research
        </button>{" "}
        for full capability.
      </p>
      <button
        type="button"
        aria-label="Dismiss the keyless search notice"
        onClick={onDismiss}
        className="text-charcoal-500 hover:text-charcoal-200 shrink-0 cursor-pointer transition-colors"
      >
        <X className="size-3" aria-hidden />
      </button>
    </div>
  );
}

// --- lifecycle surfaces (R10 D39) -------------------------------------------

/** The in-flight run as the chat trace's view shape. */
function stepsToViews(steps: BriefStep[]): ResearchStepView[] {
  return steps.map((step, i) => ({
    stepKind: step.kind,
    detail: step.detail,
    latencyMs: step.latencyMs,
    status: step.status,
    index: i + 1,
  }));
}

/**
 * IN-FLIGHT — a designed working state, never a broken empty panel mid-run:
 * pulsing zinc skeleton blocks on the 8pt grid, the live "Researching — DEEP ·
 * 42s" caption (real elapsed time, the run's true depth), and the live
 * research-step trace. Each tick also feeds the store's watchdog so a run
 * that outlived its depth wall settles to archived instead of spinning.
 */
function InFlightView({ run }: { run: Extract<BriefPanelState, { phase: "in_flight" }> }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => {
      setNow(Date.now());
      useBriefStore.getState().watchdogTick();
    }, 1_000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col gap-4 overflow-y-auto px-4 py-4">
      <p className="text-caption text-charcoal-300 font-mono" aria-live="polite">
        Researching — {DEPTH_LABEL[run.depth]} ·{" "}
        <span className="tabular-nums">{formatElapsed(Math.max(0, now - run.startedAt))}</span>
      </p>
      {(run.query || run.symbol) && (
        <p className="text-charcoal-100 text-panel-title leading-snug">{run.query || run.symbol}</p>
      )}
      {/* Skeleton: a metric-grid ghost + reading-line ghosts, all on the 8pt
          grid — the shape the published brief will take. */}
      <div className="grid grid-cols-2 gap-2" aria-hidden>
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="bg-charcoal-850 h-12 animate-pulse" />
        ))}
      </div>
      <div className="flex flex-col gap-2" aria-hidden>
        <div className="bg-charcoal-850 h-4 w-3/4 animate-pulse" />
        <div className="bg-charcoal-850 h-4 w-full animate-pulse" />
        <div className="bg-charcoal-850 h-4 w-5/6 animate-pulse" />
      </div>
      {run.steps.length > 0 && (
        <ResearchActivity steps={stepsToViews(run.steps)} active startedAt={run.startedAt} />
      )}
    </div>
  );
}

/**
 * ARCHIVED — a quiet provenance strip over the brief: the micro eyebrow names
 * WHEN the artifact was produced (a restored/superseded/failed-run brief can
 * never read as current — E3), and Refresh re-runs the SAME subject at the
 * brief's own depth through the one agent send path.
 */
function ArchivedBanner({ brief }: { brief: ResearchBriefData }) {
  const refresh = useCallback(() => {
    const subject = brief.symbol || brief.query;
    if (!subject) {
      return;
    }
    const depth = briefDepthTier(brief);
    useAgentCommandStore.getState().send(researchDepthPrompt(subject, depth), depth);
  }, [brief]);
  const produced = new Date(brief.createdAt).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <div className="border-charcoal-700 bg-charcoal-925 mx-3 mt-3 flex items-center gap-2 border px-3 py-2">
      <Archive className="text-charcoal-400 size-3 shrink-0" aria-hidden />
      <span className="text-micro text-charcoal-400 min-w-0 flex-1 truncate font-mono">
        Archived · produced {produced}
      </span>
      <button
        type="button"
        onClick={refresh}
        title="Re-run this research now (same depth)"
        className="border-charcoal-700 text-charcoal-300 hover:text-lume rounded-control text-micro flex h-6 shrink-0 cursor-pointer items-center gap-1 border px-2 font-mono transition-colors"
      >
        <RefreshCw className="size-3" aria-hidden /> Refresh
      </button>
    </div>
  );
}

/**
 * DISAMBIGUATION — the honest "which did you mean?" (D37): candidate chips
 * (symbol + name + exchange) instead of a guessed brief; a click re-runs the
 * research bound to the chosen quote-routable symbol at the brief's depth.
 */
function DisambiguationView({
  brief,
  disambiguation,
}: {
  brief: ResearchBriefData;
  disambiguation: BriefDisambiguation;
}) {
  const depth = briefDepthTier(brief);
  const choose = useCallback(
    (target: string) => {
      if (!target) {
        return;
      }
      useAgentCommandStore.getState().send(researchDepthPrompt(target, depth), depth);
    },
    [depth],
  );
  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      <p className="text-charcoal-100 text-panel-title leading-snug">Which did you mean?</p>
      <p className="text-charcoal-400 text-caption leading-relaxed">
        “{disambiguation.query || brief.query}” matched more than one instrument — pick one to
        research it.
      </p>
      <ul className="flex flex-col gap-2">
        {disambiguation.candidates.map((candidate) => (
          <li key={`${candidate.symbol}-${candidate.exchange ?? ""}`}>
            <button
              type="button"
              onClick={() => choose(candidate.yahooSymbol ?? candidate.symbol)}
              className="border-charcoal-700 bg-charcoal-850 hover:border-charcoal-600 text-caption flex w-full cursor-pointer items-baseline gap-2 border px-3 py-2 text-left font-mono transition-colors"
            >
              <span className="text-charcoal-100 shrink-0 font-medium">{candidate.symbol}</span>
              <span className="text-charcoal-300 min-w-0 flex-1 truncate">{candidate.name}</span>
              {candidate.exchange ? (
                <span className="text-micro text-charcoal-500 shrink-0">{candidate.exchange}</span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- empty / no-web states -------------------------------------------------

function EmptyState() {
  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col items-center justify-start gap-3 px-8 pt-16 text-center">
      <FlaskConical className="text-charcoal-600 size-8" />
      <p className="text-charcoal-300 text-caption font-mono">Ask JARVIS to research a company</p>
      <p className="text-charcoal-500 text-micro max-w-xs font-mono leading-relaxed">
        Run a research query in the agent dock and the brief — with cited sources and a cost readout
        — lands here.
      </p>
    </div>
  );
}

// --- the panel -------------------------------------------------------------

/**
 * Brief panel — the B+A research output surface (FR-074). Renders the latest
 * research brief from `useBriefStore`: a metadata header (mode / sources / cost),
 * the markdown body with interactive `[n]` citation chips, a collapsible sources
 * tray, and a dev-only step-log tray. When no web-search backend was available
 * it says so honestly rather than faking an error or an empty result.
 */
export function BriefPanel() {
  const panel = useBriefStore((s) => s.panel);
  const brief = useBriefStore((s) => s.brief);
  // ARCHIVED rendering (D39): an archived phase, or any brief WITHOUT an
  // execution record (no record = archival by definition — pre-R10 artifacts,
  // workspace restores of older blobs).
  const archived =
    panel.phase === "archived" || (panel.phase !== "in_flight" && !!brief && !brief.execution);

  // Map a source index to its rendered <li> so a `[n]` chip can scroll it into
  // view + flash it. A ref map (not state) — purely imperative, no re-render.
  const sourceRefs = useRef(new Map<number, HTMLLIElement>());
  const [sourcesOpenNonce, setSourcesOpenNonce] = useState(0);

  // The keyless-fallback nudge is dismissible PER BRIEF: dismissal records the
  // brief's identity (createdAt), so the next published brief that fell back
  // re-shows the honest notice.
  const [nudgeDismissedFor, setNudgeDismissedFor] = useState<number | null>(null);

  // Export is Copy-markdown (Decision 7 default): `composeBriefMarkdown` is pure +
  // reliable (it includes the "## Sources" appendix) and the clipboard write needs
  // no Rust round-trip, no raster, no path to surface — it just copies, and a
  // transient "Copied" flash confirms it.
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const flashStatus = useCallback((msg: string) => {
    setExportStatus(msg);
    window.setTimeout(() => setExportStatus(null), 4500);
  }, []);

  const handleCopyMarkdown = useCallback(async () => {
    if (!brief) return;
    const md = composeBriefMarkdown(brief);
    // `navigator.clipboard` is undefined outside a secure context — the Tauri
    // webview is secure, but guard it defensively so a non-secure context flashes
    // a useful message instead of throwing.
    const clip = typeof navigator !== "undefined" ? navigator.clipboard : undefined;
    if (!clip?.writeText) {
      flashStatus("Clipboard unavailable in this context");
      return;
    }
    try {
      await clip.writeText(md);
      flashStatus("Copied");
    } catch (e) {
      flashStatus(`Copy failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [brief, flashStatus]);

  // De-duplicate the cited sources by URL before rendering the rail — a repeat
  // citation shows once. (The markdown's [n] markers point at the first.)
  const sources = useMemo(() => (brief ? dedupeSources(brief.sources) : []), [brief]);

  const registerSourceRef = useCallback((n: number, el: HTMLLIElement | null) => {
    if (el) {
      sourceRefs.current.set(n, el);
    } else {
      sourceRefs.current.delete(n);
    }
  }, []);

  const scrollToSource = useCallback((n: number) => {
    const el = sourceRefs.current.get(n);
    if (!el) {
      // The sources tray may be collapsed — force it open, then the chip's next
      // click (or the user) reaches the row. Bump the nonce so the tray remounts
      // open. (Reduced-motion-safe: `smooth` is honoured by the browser's
      // prefers-reduced-motion handling.)
      setSourcesOpenNonce((v) => v + 1);
      return;
    }
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("bg-charcoal-875");
    window.setTimeout(() => el.classList.remove("bg-charcoal-875"), 1200);
  }, []);

  // IN-FLIGHT (D39): the working skeleton — never a broken empty panel mid-run.
  if (panel.phase === "in_flight") {
    return <InFlightView run={panel} />;
  }

  if (!brief) {
    return <EmptyState />;
  }

  // DISAMBIGUATION (D37): the chooser renders INSTEAD of a researched body —
  // the two never co-exist for one run.
  if (brief.disambiguation && !brief.markdown.trim()) {
    return (
      <div className="bg-charcoal-900 flex h-full w-full flex-col overflow-y-auto">
        <DisambiguationView brief={brief} disambiguation={brief.disambiguation} />
      </div>
    );
  }

  // `noWeb` is the honest no-web state, already reconciled in briefFromInput with
  // the source count — so a brief that cited sources can never land here (the
  // symptom-#2 fix). When it DOES fire, `webRateLimited` picks the transient
  // "rate-limited, retrying" copy over the false global "no backend" claim, and
  // `bodyCites` keys the R8 honest copy: a body that visibly cites web domains
  // with ZERO captured sources must never claim "no web sources found" — the
  // truthful statement is that sources were not captured.
  const noWeb = brief.webAvailable === false;
  const webRateLimited = brief.webReason === "rate_limited";
  const bodyCites = bodyCitesWeb(brief.markdown);
  const forSymbol = brief.symbol ? ` for ${brief.symbol}` : "";
  const hasSteps = IS_DEV && Array.isArray(brief.steps) && brief.steps.length > 0;
  // Gate 2: the nudge fires ONLY on the exact keyless-fallback backend id —
  // never on searxng / research-model — and stays dismissed for THIS brief.
  const showKeylessNudge =
    brief.backend === "keyless-fallback" && nudgeDismissedFor !== brief.createdAt;

  return (
    // `@container` makes the PANEL the query container so the brief body can
    // downshift prose(16px)→body(13px) below 420px of panel width (R8 §1).
    <div className="bg-charcoal-900 @container flex h-full w-full flex-col">
      {/* Export toolbar — one "Copy markdown" button (Decision 7 default).
          `composeBriefMarkdown` is pure + reliable and already appends the
          "## Sources" appendix, so the copy needs no raster, no Rust round-trip,
          no path to surface — it just writes the markdown to the clipboard. */}
      <div className="border-charcoal-700 flex items-center justify-end gap-1 border-b px-3 py-1">
        <button
          type="button"
          title="Copy the brief as Markdown (with a Sources appendix)"
          onClick={handleCopyMarkdown}
          className="text-charcoal-400 hover:bg-charcoal-800 hover:text-charcoal-100 rounded-control text-caption flex items-center gap-1 px-2 py-1 transition-colors"
        >
          <ClipboardCopy className="size-3" /> Copy markdown
        </button>
      </div>

      {/* Transient copy status — flashes "Copied" so the user sees it landed
          (the same affordance pattern as the Notes panel). */}
      {exportStatus ? (
        <div
          className="text-charcoal-400 border-charcoal-800 bg-charcoal-925 text-micro truncate border-b px-3 py-1 font-mono"
          title={exportStatus}
        >
          {exportStatus}
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <div className="bg-charcoal-900 flex flex-col">
          <MetaHeader brief={brief} />

          {/* ARCHIVED strip (D39): provenance eyebrow + the Refresh re-run. */}
          {archived && <ArchivedBanner brief={brief} />}

          {showKeylessNudge && (
            <KeylessFallbackNudge onDismiss={() => setNudgeDismissedFor(brief.createdAt)} />
          )}

          {/* Honest no-web state: NOT an error, NOT empty — a prominent banner.
              `noWeb` is already reconciled with the source count (a sourced brief
              never reaches here — symptom #2 fix), so this fires ONLY when the run
              gathered zero sources. The copy states WHY per-symbol/per-run:
                - a TRANSIENT throttle (`webReason === "rate_limited"`) ⇒
                  "rate-limited, retrying" — NEVER the false "no backend" claim;
                - otherwise ⇒ honest "structured data only for {symbol}".
              The honest structured-only affordance is preserved; only the false /
              contradictory banner is killed. */}
          {noWeb ? (
            <div className="border-warning/40 bg-charcoal-900 m-3 flex items-start gap-2 rounded-none border px-3 py-3">
              <Globe className="text-warning mt-0.5 size-4 shrink-0" />
              <div className="flex flex-col gap-0.5">
                <p className="text-caption text-warning font-medium">
                  {webRateLimited
                    ? "Web search was rate-limited"
                    : bodyCites
                      ? "Sources were not captured for this brief"
                      : "Structured-data-only brief"}
                </p>
                <p className="text-charcoal-300 text-micro leading-relaxed">
                  {brief.note ??
                    (webRateLimited
                      ? "Web search was rate-limited for this run — retry in a moment for live web sources."
                      : bodyCites
                        ? "The brief body cites web material, but this run did not capture the sources — treat its citations as unverified."
                        : `Structured data only — no web sources found${forSymbol}.`)}
                </p>
              </div>
            </div>
          ) : brief.note ? (
            <p className="text-charcoal-400 border-charcoal-800 text-micro mx-4 mt-3 border-l-2 pl-3 leading-relaxed">
              {brief.note}
            </p>
          ) : null}

          <BriefBody brief={brief} onCite={scrollToSource} dimMetrics={archived} />
        </div>

        {sources.length > 0 ? (
          <Tray
            key={`sources-${sourcesOpenNonce}`}
            title="Sources"
            count={sources.length}
            defaultOpen={sourcesOpenNonce > 0}
          >
            <ul
              className={
                "overflow-y-auto " +
                "max-h-64" /* tokens-ok: tray scroll cap — layout, not rhythm */
              }
            >
              {sources.map((source, i) => (
                <SourceRow
                  key={`${i}-${source.url}`}
                  index={i + 1}
                  source={source}
                  registerRef={registerSourceRef}
                />
              ))}
            </ul>
          </Tray>
        ) : null}

        {hasSteps ? (
          <Tray title="Step log · dev" count={brief.steps!.length}>
            <div
              className={
                "overflow-y-auto " +
                "max-h-48" /* tokens-ok: tray scroll cap — layout, not rhythm */
              }
            >
              <StepLog steps={brief.steps!} />
            </div>
          </Tray>
        ) : null}
      </div>
    </div>
  );
}
