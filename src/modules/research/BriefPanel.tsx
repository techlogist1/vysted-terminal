"use client";

import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FileText,
  FlaskConical,
  Globe,
  Printer,
  Telescope,
} from "lucide-react";

import type {
  BriefDepth,
  BriefSource,
  BriefSourceType,
  BriefStep,
  ResearchBriefData,
} from "../../../types/brief";
import { ProvenanceBadge, StalenessBadge } from "@/components/DataBadges";
import {
  briefSlug,
  composeBriefMarkdown,
  dedupeSources,
  deriveSourceType,
} from "@/lib/brief-ingest";
import { saveTextArtifact, savePdfArtifact } from "@/lib/export-artifact";
import { sendToAgent } from "@/store/agent-command";
import { useBriefStore } from "@/store/brief";
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

/** Compact a token / spend number to a terse readout (e.g. "12.4k", "$0.03"). */
function formatTokens(tokens: number): string {
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(tokens >= 10000 ? 0 : 1)}k`;
  }
  return String(tokens);
}

function formatSpend(usd: number): string {
  return usd >= 1 ? `$${usd.toFixed(2)}` : `$${usd.toFixed(usd >= 0.01 ? 2 : 4)}`;
}

// The brief BODY is now rendered as a typed-block document (metric cards, tables,
// prose with live ticker chips + citation chips) by `BriefBody` in `brief-blocks`
// — deterministically derived from the brief, never a wall of raw markdown.

// --- metadata header -------------------------------------------------------

function ModeBadge({ mode }: { mode: ResearchBriefData["mode"] }) {
  const deep = mode === "DEEP";
  return (
    <span
      className={`rounded-control text-micro px-1.5 py-0.5 font-mono font-medium tracking-wide uppercase ${
        deep ? "bg-charcoal-850 text-charcoal-300" : "bg-charcoal-800 text-charcoal-300"
      }`}
      title={deep ? "Deep research run" : "Fast research run"}
    >
      {mode}
    </span>
  );
}

// --- "Go deeper" — in-place depth escalation (FR-115 / SC-028) -------------

/** The depth tier a brief reached, derived from the explicit `depth` field with
 *  a fallback to the mode badge for older briefs that predate the field. */
function briefDepth(brief: ResearchBriefData): BriefDepth {
  if (brief.depth === "quick" || brief.depth === "deep" || brief.depth === "heavy") {
    return brief.depth;
  }
  return brief.mode === "DEEP" ? "deep" : "quick";
}

/** The next tier "Go deeper" escalates to, or `null` at the deepest tier. */
function nextDepth(depth: BriefDepth): Exclude<BriefDepth, "quick"> | null {
  if (depth === "quick") {
    return "deep";
  }
  if (depth === "deep") {
    return "heavy";
  }
  return null;
}

const NEXT_DEPTH_LABEL: Record<Exclude<BriefDepth, "quick">, string> = {
  deep: "Go deeper",
  heavy: "Go all out",
};

/**
 * "Go deeper" — escalates the SAME research query to the next depth tier IN
 * PLACE (FR-115). It does NOT spawn a parallel brief: it routes a depth-tagged
 * re-run of the same query through the agent (the single send path via the
 * agent-command bus), and the new run's auto-published brief REPLACES this one
 * in the store. Hidden at the deepest (`heavy`) tier — there's nowhere deeper.
 */
function GoDeeper({ brief }: { brief: ResearchBriefData }) {
  const current = briefDepth(brief);
  const next = nextDepth(current);
  if (!next) {
    return (
      <span
        className="text-charcoal-500 text-micro ml-auto shrink-0 font-mono"
        title="This is the deepest research tier."
      >
        deepest
      </span>
    );
  }
  const subject = brief.symbol || brief.query;
  // A natural-language ask the agent maps to research(subject, depth=next). The
  // explicit tier word ("go deeper"/"go all out") matches the agent's prompt
  // guidance so it escalates rather than re-running the same tier.
  const verb = next === "heavy" ? "go all out" : "go deeper";
  const onGoDeeper = () => sendToAgent(`research ${subject} — ${verb}`);
  return (
    <button
      type="button"
      onClick={onGoDeeper}
      title={`Re-run this research at the ${next} tier, in place`}
      className="border-charcoal-700 text-charcoal-300 hover:text-lume rounded-control text-micro hover:border-charcoal-500/50 ml-auto flex shrink-0 items-center gap-1 border px-2 py-0.5 font-mono transition-colors"
    >
      <Telescope className="size-3" /> {NEXT_DEPTH_LABEL[next]}
    </button>
  );
}

function MetaHeader({ brief }: { brief: ResearchBriefData }) {
  const tokens = brief.cost?.tokens;
  const spend = brief.cost?.spendUsd;
  return (
    <header className="border-charcoal-700 flex flex-col gap-1.5 border-b px-4 py-3">
      <div className="flex items-center gap-2">
        <ModeBadge mode={brief.mode} />
        {brief.symbol ? (
          <span className="text-micro text-charcoal-100 font-mono font-medium">{brief.symbol}</span>
        ) : null}
        <span className="text-charcoal-500 text-micro font-mono">
          {brief.sourceCount} source{brief.sourceCount === 1 ? "" : "s"}
        </span>
        {typeof tokens === "number" ? (
          <span className="text-charcoal-500 text-micro font-mono" title={`${tokens} tokens`}>
            · {formatTokens(tokens)} tok
          </span>
        ) : null}
        {typeof spend === "number" ? (
          <span className="text-charcoal-500 text-micro font-mono">· {formatSpend(spend)}</span>
        ) : null}
        {/* In-place depth escalation — one research model, "go deeper" deepens the
            SAME run rather than spawning a parallel brief (FR-115). */}
        <GoDeeper brief={brief} />
      </div>
      {/* Provenance line: WHERE the brief drew from (web vs structured-data-only)
          and WHEN it was produced, so a cached/offline run is never mistaken for
          a fresh web pull. Subtle by design — it sits under the mode/cost row.
          NB: this badge keys off REAL web sources (http(s) URLs), NOT the
          reconciled `webAvailable` flag — that flag is true whenever ANY source
          (incl. synthetic `vysted://` structured-provenance legs) was cited, so
          using it here would falsely claim "web" for a structured-only run. */}
      <div className="flex flex-wrap items-center gap-1.5">
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
    // eslint-disable-next-line @next/next/no-img-element
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
    <span className="border-charcoal-700 text-charcoal-400 bg-charcoal-850 rounded-control text-micro shrink-0 border px-1.5 py-0.5 font-mono tracking-wide uppercase">
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
        <div className="flex flex-wrap items-center gap-1.5">
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
          className="border-charcoal-850 text-micro flex items-center gap-2 border-b px-4 py-1.5 font-mono last:border-b-0"
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
        className="text-charcoal-300 hover:text-charcoal-100 text-micro flex w-full items-center gap-1.5 px-4 py-2 font-mono tracking-wide uppercase transition-colors"
      >
        {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
        {title}
        {typeof count === "number" ? (
          <span className="text-charcoal-500 normal-case">({count})</span>
        ) : null}
      </button>
      {open ? <div>{children}</div> : null}
    </section>
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
  const brief = useBriefStore((s) => s.brief);

  // Map a source index to its rendered <li> so a `[n]` chip can scroll it into
  // view + flash it. A ref map (not state) — purely imperative, no re-render.
  const sourceRefs = useRef(new Map<number, HTMLLIElement>());
  const [sourcesOpenNonce, setSourcesOpenNonce] = useState(0);

  // The rendered brief body — the PDF/PNG raster target (the WKWebView blocks
  // browser downloads, so every export writes a real file via the Rust atomic
  // commands; a transient status line confirms the saved path).
  const briefBodyRef = useRef<HTMLDivElement>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const flashStatus = useCallback((msg: string) => {
    setExportStatus(msg);
    window.setTimeout(() => setExportStatus(null), 4500);
  }, []);

  const handleExportMd = useCallback(async () => {
    if (!brief) return;
    try {
      const md = composeBriefMarkdown(brief);
      const r = await saveTextArtifact("research", `${briefSlug(brief)}.md`, md);
      flashStatus(r.path ? `Saved ${r.path}` : "Downloaded .md");
    } catch (e) {
      flashStatus(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [brief, flashStatus]);

  const handleExportPdf = useCallback(async () => {
    const el = briefBodyRef.current;
    if (!brief || !el) return;
    try {
      const r = await savePdfArtifact("research", `${briefSlug(brief)}.pdf`, el);
      flashStatus(r.path ? `Saved ${r.path}` : "Downloaded .pdf");
    } catch (e) {
      flashStatus(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
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

  if (!brief) {
    return <EmptyState />;
  }

  // `noWeb` is the honest no-web state, already reconciled in briefFromInput with
  // the source count — so a brief that cited sources can never land here (the
  // symptom-#2 fix). When it DOES fire, `webRateLimited` picks the transient
  // "rate-limited, retrying" copy over the false global "no backend" claim.
  const noWeb = brief.webAvailable === false;
  const webRateLimited = brief.webReason === "rate_limited";
  const forSymbol = brief.symbol ? ` for ${brief.symbol}` : "";
  const hasSteps = IS_DEV && Array.isArray(brief.steps) && brief.steps.length > 0;

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      {/* Export toolbar — MD composes the brief + a Sources appendix; PDF
          rasterises the rendered body. Both write a real file via the Rust
          atomic-write commands (the WKWebView blocks browser downloads). */}
      <div className="border-charcoal-700 flex items-center justify-end gap-1 border-b px-3 py-1.5">
        <button
          type="button"
          title="Export Markdown"
          onClick={handleExportMd}
          className="text-charcoal-400 hover:bg-charcoal-800 hover:text-charcoal-100 rounded-control text-caption flex items-center gap-1.5 px-2 py-1 transition-colors"
        >
          <FileText className="size-3.5" /> MD
        </button>
        <button
          type="button"
          title="Export PDF"
          onClick={handleExportPdf}
          className="text-charcoal-400 hover:bg-charcoal-800 hover:text-charcoal-100 rounded-control text-caption flex items-center gap-1.5 px-2 py-1 transition-colors"
        >
          <Printer className="size-3.5" /> PDF
        </button>
      </div>

      {/* Transient export status — confirms the saved path so the user sees it
          landed (the same affordance pattern as the Notes panel). */}
      {exportStatus ? (
        <div
          className="text-charcoal-400 border-charcoal-800 bg-charcoal-925 text-micro truncate border-b px-3 py-1.5 font-mono"
          title={exportStatus}
        >
          {exportStatus}
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {/* The export raster target — the meta header + the brief body. */}
        <div ref={briefBodyRef} className="bg-charcoal-900 flex flex-col">
          <MetaHeader brief={brief} />

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
                  {webRateLimited ? "Web search was rate-limited" : "Structured-data-only brief"}
                </p>
                <p className="text-charcoal-300 text-micro leading-relaxed">
                  {brief.note ??
                    (webRateLimited
                      ? "Web search was rate-limited for this run — retry in a moment for live web sources."
                      : `Structured data only — no web sources found${forSymbol}.`)}
                </p>
              </div>
            </div>
          ) : brief.note ? (
            <p className="text-charcoal-400 border-charcoal-800 text-micro mx-4 mt-3 border-l-2 pl-3 leading-relaxed">
              {brief.note}
            </p>
          ) : null}

          <BriefBody brief={brief} onCite={scrollToSource} />
        </div>

        {sources.length > 0 ? (
          <Tray
            key={`sources-${sourcesOpenNonce}`}
            title="Sources"
            count={sources.length}
            defaultOpen={sourcesOpenNonce > 0}
          >
            <ul className="max-h-64 overflow-y-auto">
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
            <div className="max-h-48 overflow-y-auto">
              <StepLog steps={brief.steps!} />
            </div>
          </Tray>
        ) : null}
      </div>
    </div>
  );
}
