"use client";

import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Shared empty-state surface (R4 design §8) — a *composed* placeholder, never a
 * dead grey void. Centered in its panel: a quiet icon, a headline, one calm hint
 * line, and an optional single ghost/outline CTA. Replaces the bare
 * `<p class="text-charcoal-400">No …</p>` stubs and naked spinners-as-empty that
 * read as "abandoned" panels.
 *
 * Tiers (design §4 — hierarchy via weight/opacity, never color):
 *  - icon    → tertiary (`charcoal-500`), ~24px, stroke 1.5
 *  - headline→ secondary-bright (`charcoal-200`), weight 510, `text-panel-title`
 *  - hint    → tertiary (`charcoal-500`), `text-caption`
 *  - cta     → a single quiet button; amber `outline` only when it is a primary
 *              action, otherwise a calm `ghost`.
 */
export function EmptyState({
  icon: Icon,
  headline,
  hint,
  cta,
  className,
}: {
  /** The lucide icon for this surface (sized + tinted by the component). */
  icon: LucideIcon;
  /** The short, intentional headline (e.g. "No ratings history"). */
  headline: string;
  /** One calm supporting line — what the surface is / what to do next. */
  hint?: string;
  /** Optional single call-to-action. `primary` lifts it to the amber outline. */
  cta?: { label: string; onClick: () => void; primary?: boolean };
  className?: string;
}) {
  return (
    <div
      data-testid="empty-state"
      className={cn(
        "flex h-full w-full flex-col items-center justify-center gap-3 px-6 py-8 text-center",
        className,
      )}
    >
      <Icon
        aria-hidden
        strokeWidth={1.5}
        className="text-charcoal-500 size-6"
        data-testid="empty-state-icon"
      />
      <div className="flex flex-col items-center gap-1">
        {/* `text-panel-title` already carries the 510 label weight (design §4/§7). */}
        <p data-testid="empty-state-headline" className="text-charcoal-200 text-panel-title">
          {headline}
        </p>
        {hint && (
          <p data-testid="empty-state-hint" className="text-charcoal-500 text-caption max-w-xs">
            {hint}
          </p>
        )}
      </div>
      {cta && (
        <Button
          type="button"
          size="sm"
          variant={cta.primary ? "outline" : "ghost"}
          onClick={cta.onClick}
          data-testid="empty-state-cta"
          className={cn("mt-1", cta.primary && "border-amber-500/60 text-amber-300")}
        >
          {cta.label}
        </Button>
      )}
    </div>
  );
}
