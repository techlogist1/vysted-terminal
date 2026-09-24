"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Undo2, X } from "lucide-react";

import { tween } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useProposedChangesStore } from "@/store/proposed-changes";

import type { ProposedChange } from "../../../types/proposed-change";

/**
 * The diff/accept trust gate UI (FR-010, US4). Agent-proposed cockpit mutations
 * are staged here as old→new diffs; nothing applies until the user accepts.
 * Per-item Accept/Reject plus bulk Accept all / Reject all. Bulk is also keyboard
 * driven from the agent surface (⌘↵ accept all, ⌘⌫ reject all). An applied data
 * write stays listed for the session with Undo, which restores its pre-image.
 */
export function ProposedChangesReview() {
  const changes = useProposedChangesStore((state) => state.changes);
  const accept = useProposedChangesStore((state) => state.accept);
  const reject = useProposedChangesStore((state) => state.reject);
  const acceptAll = useProposedChangesStore((state) => state.acceptAll);
  const rejectAll = useProposedChangesStore((state) => state.rejectAll);
  const undo = useProposedChangesStore((state) => state.undo);

  const pending = useMemo(() => changes.filter((c) => c.status === "pending"), [changes]);
  const undoable = useMemo(
    () => changes.filter((c) => c.status === "accepted" && c.preImage),
    [changes],
  );

  return (
    <AnimatePresence initial={false}>
      {(pending.length > 0 || undoable.length > 0) && (
        <motion.section
          aria-label="Proposed changes"
          className="border-charcoal-700 bg-charcoal-925 border-t px-3 py-2"
          initial={{ opacity: 0, y: 12, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: 8, height: 0 }}
          style={{ overflow: "hidden" }}
          transition={tween(0.24)}
        >
          {pending.length > 0 && (
            <header className="flex items-center justify-between gap-2">
              <span className="text-charcoal-200 text-micro tracking-wide uppercase">
                {pending.length} proposed change{pending.length === 1 ? "" : "s"} — review before
                they apply
              </span>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={() => void acceptAll()}
                  className="border-positive/40 text-positive hover:bg-positive/10 text-micro rounded-control border px-2 py-0.5"
                  title="Accept all (⌘↵)"
                >
                  Accept all
                </button>
                <button
                  type="button"
                  onClick={() => rejectAll()}
                  className="border-charcoal-700 text-charcoal-400 hover:text-negative text-micro rounded-control border px-2 py-0.5"
                  title="Reject all (⌘⌫)"
                >
                  Reject all
                </button>
              </div>
            </header>
          )}
          {/* The scroll cap + overflow-y-auto prevents the diff list from pushing
              the composer off-screen when many changes are staged at once. */}
          <ul
            className={cn(
              "mt-2 flex flex-col gap-2 overflow-y-auto",
              "max-h-48" /* tokens-ok: diff-list scroll cap — layout, not rhythm */,
            )}
          >
            <AnimatePresence initial={false}>
              {pending.map((change) => (
                <ProposedChangeCard
                  key={change.id}
                  change={change}
                  onAccept={() => void accept(change.id)}
                  onReject={() => reject(change.id)}
                />
              ))}
              {undoable.map((change) => (
                <AppliedChangeRow key={change.id} change={change} onUndo={() => undo(change.id)} />
              ))}
            </AnimatePresence>
          </ul>
        </motion.section>
      )}
    </AnimatePresence>
  );
}

/** An applied data write, kept for the session so it can be undone. */
function AppliedChangeRow({ change, onUndo }: { change: ProposedChange; onUndo: () => void }) {
  return (
    <motion.li
      layout
      data-kind={change.kind}
      className="border-charcoal-800 rounded-none border px-2 py-1.5"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 8, height: 0, marginBottom: 0 }}
      transition={tween(0.2)}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-charcoal-300 text-micro">Applied: {change.title}</div>
          {change.detail && (
            <div className="text-negative text-micro mt-0.5">
              Couldn&rsquo;t undo: {change.detail}
            </div>
          )}
        </div>
        <button
          type="button"
          aria-label={`Undo: ${change.title}`}
          onClick={onUndo}
          className="border-charcoal-700 text-charcoal-300 hover:text-charcoal-100 text-micro rounded-control flex shrink-0 items-center gap-1 border px-2 py-0.5"
        >
          <Undo2 size={12} aria-hidden />
          Undo
        </button>
      </div>
    </motion.li>
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
    <motion.li
      layout
      data-kind={change.kind}
      className="border-charcoal-700 bg-charcoal-900 rounded-none border px-2 py-2"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 8, height: 0, marginBottom: 0 }}
      transition={tween(0.2)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-charcoal-100 text-micro">{change.title}</div>
          <div className="text-micro mt-0.5 overflow-hidden leading-relaxed">
            <span className="text-negative/80 block break-all">− {change.before}</span>
            <span className="text-positive/90 block break-all">+ {change.after}</span>
          </div>
          {change.detail && (
            <div className="text-negative text-micro mt-0.5">
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
              "border-positive/40 text-positive hover:bg-positive/10 rounded-control border p-1",
            )}
          >
            <Check size={12} aria-hidden />
          </button>
          <button
            type="button"
            aria-label={`Reject: ${change.title}`}
            onClick={onReject}
            className="border-charcoal-700 text-charcoal-400 hover:text-negative hover:border-negative/40 rounded-control border p-1"
          >
            <X size={12} aria-hidden />
          </button>
        </div>
      </div>
    </motion.li>
  );
}
