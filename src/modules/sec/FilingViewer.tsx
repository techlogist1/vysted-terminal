"use client";

/**
 * FilingViewer — renders a parsed SEC filing.
 *
 * Layout: section navigation rail on the left, the selected section's
 * body on the right. Top-right "View original on EDGAR" link opens the
 * canonical EDGAR URL in the user's default browser via the Tauri shell
 * (`@tauri-apps/plugin-shell`).
 */

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { openEdgarUrl, useSecStore } from "@/store/sec";

import type { FilingDetail } from "../../../types/sec";

interface FilingViewerProps {
  accession: string | null;
  identifier: string | null;
  onClose: () => void;
}

export function FilingViewer({ accession, identifier, onClose }: FilingViewerProps) {
  const loadFilingDetail = useSecStore((s) => s.loadFilingDetail);
  const detailMap = useSecStore((s) => s.filingDetailByAccession);
  const status = useSecStore((s) => s.filingDetailStatus);
  const error = useSecStore((s) => s.filingDetailError);

  useEffect(() => {
    if (accession && identifier && !detailMap[accession]) {
      void loadFilingDetail(accession, identifier);
    }
  }, [accession, identifier, detailMap, loadFilingDetail]);

  const detail: FilingDetail | null = accession ? (detailMap[accession] ?? null) : null;
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);

  const activeSection = useMemo(() => {
    if (!detail) return null;
    if (activeSectionId) {
      const match = detail.sections.find((s) => s.id === activeSectionId);
      if (match) return match;
    }
    return detail.sections[0] ?? null;
  }, [detail, activeSectionId]);

  if (!accession) {
    return (
      <div className="text-charcoal-400 flex h-full items-center justify-center text-sm">
        Select a filing to view its sections.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col" data-testid="filing-viewer">
      <header className="border-charcoal-700 flex items-center gap-2 border-b px-3 py-2">
        <Button size="xs" variant="ghost" onClick={onClose} data-testid="filing-viewer-close">
          ← Back
        </Button>
        <span className="text-charcoal-100 text-sm font-semibold">
          {detail?.filing.form_type ?? ""}
        </span>
        <span
          className="text-charcoal-400 max-w-[16ch] truncate text-xs"
          title={detail?.filing.company_name ?? ""}
        >
          {detail?.filing.company_name ?? ""}
        </span>
        {detail?.filing.filed_date && (
          <span className="text-charcoal-500 text-xs">· filed {detail.filing.filed_date}</span>
        )}
        <span className="text-charcoal-500 ml-auto font-mono text-[10px]">{accession}</span>
        {detail?.filing.edgar_url && (
          <Button
            size="xs"
            variant="outline"
            onClick={() => void openEdgarUrl(detail.filing.edgar_url)}
            data-testid="filing-viewer-edgar-link"
          >
            View original on EDGAR ↗
          </Button>
        )}
      </header>

      {error && !detail && (
        <div className="flex min-h-0 flex-1">
          <div className="w-56 shrink-0" />
          <article
            className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center"
            data-testid="filing-viewer-error"
          >
            <p className="text-negative font-mono text-xs">Could not load this filing.</p>
            <p className="text-charcoal-500 font-mono text-[10px]">{error}</p>
            <div className="flex gap-2">
              <Button
                size="xs"
                variant="ghost"
                className="text-amber-300 hover:text-amber-200"
                onClick={() =>
                  accession && identifier && void loadFilingDetail(accession, identifier)
                }
              >
                Retry
              </Button>
              <Button size="xs" variant="ghost" onClick={onClose}>
                ← Back to list
              </Button>
            </div>
          </article>
        </div>
      )}
      {error && detail && (
        <div
          className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2"
          data-testid="filing-viewer-error"
        >
          <span className="text-negative font-mono text-[11px]">{error}</span>
          <Button
            size="xs"
            variant="ghost"
            className="text-amber-300 hover:text-amber-200"
            onClick={() => accession && identifier && void loadFilingDetail(accession, identifier)}
          >
            Retry
          </Button>
        </div>
      )}
      {status === "loading" && !detail && !error && (
        <div className="flex min-h-0 flex-1">
          {/* Section nav skeleton */}
          <div className="border-charcoal-700 w-56 shrink-0 overflow-y-auto border-r px-3 py-2">
            {[70, 50, 80, 60, 45, 65, 55].map((w, i) => (
              <div
                key={i}
                className="bg-charcoal-700 mb-2 h-3 animate-pulse rounded"
                style={{ width: `${w}%` }}
              />
            ))}
          </div>
          {/* Article skeleton */}
          <div className="flex-1 overflow-y-auto px-4 py-3">
            <div className="bg-charcoal-700 mb-4 h-4 w-1/3 animate-pulse rounded" />
            {[100, 90, 75, 95, 60, 85, 70, 80, 50, 65].map((w, i) => (
              <div
                key={i}
                className="bg-charcoal-800 mb-2 h-3 animate-pulse rounded"
                style={{ width: `${w}%` }}
              />
            ))}
          </div>
        </div>
      )}

      {detail && (
        <div className="flex min-h-0 flex-1">
          <nav
            className="border-charcoal-700 w-56 shrink-0 overflow-y-auto border-r"
            data-testid="filing-viewer-section-nav"
          >
            <ul>
              {detail.sections.map((section) => (
                <li key={section.id}>
                  <button
                    type="button"
                    onClick={() => setActiveSectionId(section.id)}
                    className={cn(
                      "hover:bg-charcoal-800 w-full px-3 py-1.5 text-left text-[11px]",
                      (activeSectionId ?? detail.sections[0]?.id) === section.id
                        ? "bg-charcoal-800 text-charcoal-100 border-l-2 border-l-amber-400"
                        : "text-charcoal-300",
                    )}
                    data-testid={`filing-section-${section.id}`}
                  >
                    <span className="block truncate">{section.title}</span>
                    <span className="text-charcoal-500 text-[10px]">
                      {section.word_count} words
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <article className="flex-1 overflow-y-auto px-4 py-3" data-testid="filing-viewer-body">
            {activeSection ? (
              <>
                <h3 className="text-charcoal-100 mb-2 text-sm font-semibold">
                  {activeSection.title}
                </h3>
                <pre className="text-charcoal-200 max-w-full text-[12px] leading-relaxed whitespace-pre-wrap">
                  {activeSection.text}
                </pre>
              </>
            ) : (
              <p className="text-charcoal-400 text-sm">No section selected.</p>
            )}
          </article>
        </div>
      )}
    </div>
  );
}
