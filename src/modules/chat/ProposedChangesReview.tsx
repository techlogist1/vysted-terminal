"use client";

import { useMemo } from "react";
import { Check, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { useProposedChangesStore } from "@/store/proposed-changes";

import type { ProposedChange } from "../../../types/proposed-change";

/**
 * The diff/accept trust gate UI (FR-010, US4). Agent-proposed cockpit mutations
 * are staged here as old→new diffs; nothing applies until the user accepts.
 * Per-item Accept/Reject plus bulk Accept all / Reject all. Bulk is also keyboard
 * driven from the agent surface (⌘↵ accept all, ⌘⌫ reject all). For orders the
 * Accept opens the §6.5 confirm-before-place dialog — never a direct placement.
 */
export function ProposedChangesReview() {
  const changes = useProposedChangesStore((state) => state.changes);
  const accept = useProposedChangesStore((state) => state.accept);
  const reject = useProposedChangesStore((state) => state.reject);
  const acceptAll = useProposedChangesStore((state) => state.acceptAll);
  const rejectAll = useProposedChangesStore((state) => state.rejectAll);

  const pending = useMemo(() => changes.filter((c) => c.status === "pending"), [changes]);
  if (pending.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Proposed changes"
      className="border-charcoal-700 bg-charcoal-925 border-t px-3 py-2"
    >
      <header className="flex items-center justify-between gap-2">
        <span className="text-charcoal-200 font-mono text-[0.65rem] tracking-wide uppercase">
          {pending.length} proposed change{pending.length === 1 ? "" : "s"} — review before they
          apply
        </span>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={() => void acceptAll()}
            className="border-positive/40 text-positive hover:bg-positive/10 rounded border px-2 py-0.5 font-mono text-[0.6rem]"
            title="Accept all (⌘↵)"
          >
            Accept all
          </button>
          <button
            type="button"
            onClick={() => rejectAll()}
            className="border-charcoal-700 text-charcoal-400 hover:text-negative rounded border px-2 py-0.5 font-mono text-[0.6rem]"
            title="Reject all (⌘⌫)"
          >
            Reject all
          </button>
        </div>
      </header>
      <ul className="mt-1.5 flex flex-col gap-1.5">
        {pending.map((change) => (
          <ProposedChangeCard
            key={change.id}
            change={change}
            onAccept={() => void accept(change.id)}
            onReject={() => reject(change.id)}
          />
        ))}
      </ul>
    </section>
  );
}

function ProposedChangeCard({
  change,
  onAccept,
  onReject,
}: {
  change: ProposedChange;
  onAccept: () => void;
  onReject: () => void;
}) {
  return (
    <li
      data-kind={change.kind}
      className="border-charcoal-700 bg-charcoal-900 rounded-md border px-2.5 py-1.5"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-charcoal-100 font-mono text-[0.7rem]">{change.title}</div>
          <div className="mt-0.5 font-mono text-[0.6rem] leading-relaxed">
            <span className="text-negative/80">− {change.before}</span>
            <br />
            <span className="text-positive/90">+ {change.after}</span>
          </div>
          {change.kind === "order" && (
            <div className="text-warning mt-0.5 font-mono text-[0.55rem]">
              Accept opens the confirm-before-place dialog — nothing is placed automatically.
            </div>
          )}
          {change.detail && (
            <div className="text-negative mt-0.5 font-mono text-[0.55rem]">
              Couldn&rsquo;t apply: {change.detail} — try again.
            </div>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            aria-label={`Accept: ${change.title}`}
            onClick={onAccept}
            className={cn(
              "border-positive/40 text-positive hover:bg-positive/10 rounded border p-1",
            )}
          >
            <Check size={12} aria-hidden />
          </button>
          <button
            type="button"
            aria-label={`Reject: ${change.title}`}
            onClick={onReject}
            className="border-charcoal-700 text-charcoal-400 hover:text-negative hover:border-negative/40 rounded border p-1"
          >
            <X size={12} aria-hidden />
          </button>
        </div>
      </div>
    </li>
  );
}
