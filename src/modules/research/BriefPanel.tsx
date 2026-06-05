"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FlaskConical,
  Globe,
  Telescope,
} from "lucide-react";

import type { BriefDepth, BriefSource, BriefStep, ResearchBriefData } from "../../../types/brief";
import { ProvenanceBadge, StalenessBadge } from "@/components/DataBadges";
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
      className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wide uppercase ${
        deep ? "bg-amber-600/25 text-amber-200" : "bg-charcoal-800 text-charcoal-300"
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
        className="text-charcoal-500 ml-auto shrink-0 font-mono text-[10px]"
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
      className="border-charcoal-700 text-charcoal-300 hover:text-lume ml-auto flex shrink-0 items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[10px] transition-colors hover:border-amber-500/50"
    >
      <Telescope className="size-3" /> {NEXT_DEPTH_LABEL[next]}
    </button>
  );
}

function MetaHeader({ brief }: { brief: ResearchBriefData }) {
  const tokens = brief.cost?.tokens;
  const spend = brief.cost?.spendUsd;
  return (
    <header className="border-charcoal-700 flex flex-col gap-1.5 border-b px-4 py-2.5">
      <div className="flex items-center gap-2">
        <ModeBadge mode={brief.mode} />
        {brief.symbol ? (
          <span className="font-mono text-[11px] font-medium text-amber-400">{brief.symbol}</span>
        ) : null}
        <span className="text-charcoal-500 font-mono text-[10px]">
          {brief.sourceCount} source{brief.sourceCount === 1 ? "" : "s"}
        </span>
        {typeof tokens === "number" ? (
          <span className="text-charcoal-500 font-mono text-[10px]" title={`${tokens} tokens`}>
            · {formatTokens(tokens)} tok
          </span>
        ) : null}
        {typeof spend === "number" ? (
          <span className="text-charcoal-500 font-mono text-[10px]">· {formatSpend(spend)}</span>
        ) : null}
        {/* In-place depth escalation — one research model, "go deeper" deepens the
            SAME run rather than spawning a parallel brief (FR-115). */}
        <GoDeeper brief={brief} />
      </div>
      {/* Provenance line: WHERE the brief drew from (web vs structured-data-only)
          and WHEN it was produced, so a cached/offline run is never mistaken for
          a fresh web pull. Subtle by design — it sits under the mode/cost row. */}
      <div className="flex flex-wrap items-center gap-1.5">
        <ProvenanceBadge
          provider={brief.webAvailable ? "web + structured data" : "structured data"}
        />
        {typeof brief.createdAt === "number" ? (
          <StalenessBadge freshness="eod" asOf={brief.createdAt} />
        ) : null}
      </div>
      <h2 className="text-charcoal-100 font-serif text-sm leading-snug">{brief.query}</h2>
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
      className="mt-1 size-3 shrink-0 rounded-[2px]"
    />
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
  return (
    <li
      ref={(el) => registerRef(index, el)}
      className="border-charcoal-800 flex gap-2.5 border-b px-4 py-2.5 last:border-b-0 target:bg-amber-600/5"
      data-source-index={index}
    >
      <span className="text-charcoal-500 w-4 shrink-0 pt-0.5 text-right font-mono text-[10px]">
        {index}
      </span>
      <FaviconDot domain={domain} />
      <div className="flex min-w-0 flex-col gap-1">
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="text-charcoal-100 group inline-flex items-start gap-1 text-[12px] leading-snug transition-colors hover:text-amber-300"
        >
          <span className="min-w-0">{source.title || source.url}</span>
          <ExternalLink className="text-charcoal-600 mt-0.5 size-3 shrink-0 group-hover:text-amber-400" />
        </a>
        <span className="text-charcoal-500 bg-charcoal-850 w-fit max-w-full truncate rounded-sm px-1 py-px font-mono text-[10px]">
          {domain}
        </span>
        {source.excerpt ? (
          <p className="text-charcoal-400 line-clamp-3 text-[11px] leading-relaxed">
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
          className="border-charcoal-850 flex items-center gap-2 border-b px-4 py-1.5 font-mono text-[10px] last:border-b-0"
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
        className="text-charcoal-300 hover:text-charcoal-100 flex w-full items-center gap-1.5 px-4 py-2 font-mono text-[11px] tracking-wide uppercase transition-colors"
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
    <div className="bg-charcoal-900 flex h-full w-full flex-col items-center justify-center gap-3 px-8 text-center">
      <FlaskConical className="text-charcoal-600 size-8" />
      <p className="text-charcoal-300 font-mono text-xs">Ask JARVIS to research a company</p>
      <p className="text-charcoal-500 max-w-xs font-mono text-[11px] leading-relaxed">
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
    el.classList.add("bg-amber-600/10");
    window.setTimeout(() => el.classList.remove("bg-amber-600/10"), 1200);
  }, []);

  if (!brief) {
    return <EmptyState />;
  }

  const noWeb = brief.webAvailable === false;
  const hasSteps = IS_DEV && Array.isArray(brief.steps) && brief.steps.length > 0;

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <MetaHeader brief={brief} />

      <div className="flex-1 overflow-y-auto">
        {/* Honest no-web state: NOT an error, NOT empty — a prominent banner that
            the brief is structured-data-only, with the pipeline's note. */}
        {noWeb ? (
          <div className="m-3 flex items-start gap-2.5 rounded-md border border-amber-600/40 bg-amber-600/10 px-3 py-2.5">
            <Globe className="mt-0.5 size-4 shrink-0 text-amber-300" />
            <div className="flex flex-col gap-0.5">
              <p className="text-[12px] font-medium text-amber-200">Structured-data-only brief</p>
              <p className="text-charcoal-300 text-[11px] leading-relaxed">
                {brief.note ??
                  "No web-search backend configured — this brief is built from structured data only."}
              </p>
            </div>
          </div>
        ) : brief.note ? (
          <p className="text-charcoal-400 border-charcoal-800 mx-4 mt-3 border-l-2 pl-3 text-[11px] leading-relaxed italic">
            {brief.note}
          </p>
        ) : null}

        <BriefBody brief={brief} onCite={scrollToSource} />
      </div>

      {brief.sources.length > 0 ? (
        <Tray
          key={`sources-${sourcesOpenNonce}`}
          title="Sources"
          count={brief.sources.length}
          defaultOpen={sourcesOpenNonce > 0}
        >
          <ul className="max-h-64 overflow-y-auto">
            {brief.sources.map((source, i) => (
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
  );
}
