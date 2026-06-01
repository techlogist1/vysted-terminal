"use client";

import { Fragment, useCallback, useMemo, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, ExternalLink, FlaskConical, Globe } from "lucide-react";

import type { BriefSource, BriefStep, ResearchBriefData } from "../../../types/brief";
import { useBriefStore } from "@/store/brief";

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

// --- minimal safe markdown -------------------------------------------------
//
// The repo ships no markdown library and we must NOT inject raw HTML, so the
// brief body is rendered with a deliberately small, safe subset: headings,
// bullet/ordered lists, paragraphs, and inline emphasis / code / `[n]` citation
// chips. Everything is built from React nodes — there is no `dangerouslySet…`
// anywhere, so a malicious source title or body can never inject markup.

/** Split a line of inline markdown into bold / italic / code / citation / text spans. */
function renderInline(text: string, onCite: (n: number) => void): ReactNode[] {
  const nodes: ReactNode[] = [];
  // One pass over a combined token regex keeps ordering correct across the
  // different inline kinds. `[n]` citation markers get an interactive chip; the
  // rest map to plain emphasis spans.
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[(\d+)\])/g;
  let last = 0;
  let key = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(<Fragment key={key++}>{text.slice(last, match.index)}</Fragment>);
    }
    const token = match[0];
    if (match[2] !== undefined) {
      const n = Number(match[2]);
      nodes.push(
        <button
          key={key++}
          type="button"
          onClick={() => onCite(n)}
          className="mx-px inline-flex translate-y-[-1px] items-center rounded-[3px] bg-amber-600/20 px-1 align-baseline font-mono text-[10px] leading-tight text-amber-300 transition-colors hover:bg-amber-600/30 hover:text-amber-200 focus-visible:ring-1 focus-visible:ring-amber-400/60 focus-visible:outline-none"
          aria-label={`Jump to source ${n}`}
        >
          {n}
        </button>,
      );
    } else if (token.startsWith("**")) {
      nodes.push(
        <strong key={key++} className="text-lume font-semibold">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("*")) {
      nodes.push(
        <em key={key++} className="text-charcoal-200 italic">
          {token.slice(1, -1)}
        </em>,
      );
    } else {
      nodes.push(
        <code
          key={key++}
          className="bg-charcoal-800 rounded-[3px] px-1 py-px font-mono text-[12px] text-amber-200"
        >
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = pattern.lastIndex;
  }
  if (last < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  }
  return nodes;
}

/** Render a markdown string into a safe React tree (no raw HTML injection). */
function Markdown({ source, onCite }: { source: string; onCite: (n: number) => void }) {
  const blocks = useMemo(() => {
    const lines = source.replace(/\r\n/g, "\n").split("\n");
    const out: ReactNode[] = [];
    let list: { ordered: boolean; items: string[] } | null = null;
    let key = 0;

    const flushList = () => {
      if (!list) {
        return;
      }
      const current = list;
      const ListTag = current.ordered ? "ol" : "ul";
      out.push(
        <ListTag
          key={key++}
          className={`text-charcoal-200 my-2 ml-5 flex flex-col gap-1 text-[13px] leading-relaxed ${
            current.ordered ? "list-decimal" : "list-disc"
          }`}
        >
          {current.items.map((item, i) => (
            <li key={i} className="pl-1">
              {renderInline(item, onCite)}
            </li>
          ))}
        </ListTag>,
      );
      list = null;
    };

    for (const raw of lines) {
      const line = raw.trimEnd();
      const heading = /^(#{1,4})\s+(.*)$/.exec(line);
      const bullet = /^[-*]\s+(.*)$/.exec(line);
      const ordered = /^\d+\.\s+(.*)$/.exec(line);

      if (heading) {
        flushList();
        const level = heading[1].length;
        const sizes = ["text-base", "text-sm", "text-[13px]", "text-xs"];
        out.push(
          <p
            key={key++}
            className={`text-lume mt-3 mb-1 font-serif font-semibold first:mt-0 ${sizes[level - 1]}`}
          >
            {renderInline(heading[2], onCite)}
          </p>,
        );
        continue;
      }
      if (bullet) {
        if (!list || list.ordered) {
          flushList();
          list = { ordered: false, items: [] };
        }
        list.items.push(bullet[1]);
        continue;
      }
      if (ordered) {
        if (!list || !list.ordered) {
          flushList();
          list = { ordered: true, items: [] };
        }
        list.items.push(ordered[1]);
        continue;
      }
      flushList();
      if (line.trim() === "") {
        continue;
      }
      out.push(
        <p key={key++} className="text-charcoal-200 my-2 text-[13px] leading-relaxed">
          {renderInline(line, onCite)}
        </p>,
      );
    }
    flushList();
    return out;
  }, [source, onCite]);

  return <div className="font-sans">{blocks}</div>;
}

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

        <div className="px-4 pt-2 pb-4">
          <Markdown source={brief.markdown} onCite={scrollToSource} />
        </div>
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
