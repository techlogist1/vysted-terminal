"use client";

/**
 * Workflow save dialog — captures the workflow name and (optional)
 * description before the panel POSTs to `/workflow/save`.
 *
 * Lives as a controlled modal so the parent panel owns the open/close
 * state and the in-flight feedback. No localStorage — workflow data
 * round-trips through the sidecar exclusively (CLAUDE.md
 * sidecar-owned-persistence convention).
 *
 * The body is split into a separate `WorkflowSaveDialogBody` component
 * so the parent can pass the initial form values via React's
 * `key`-based remount idiom — this avoids the React-19
 * `set-state-in-effect` anti-pattern (no effect re-seeds local state
 * when the parent re-opens with different defaults; the parent just
 * remounts the body with a fresh `key`).
 */

import { useState } from "react";

import { Button } from "@/components/ui/button";

export interface SaveDialogValue {
  name: string;
  description: string;
}

interface WorkflowSaveDialogProps {
  open: boolean;
  initialValue: SaveDialogValue;
  /** When `true`, the title and primary button reflect update semantics. */
  mode: "create" | "update";
  saving: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (value: SaveDialogValue) => void;
}

export function WorkflowSaveDialog(props: WorkflowSaveDialogProps) {
  if (!props.open) {
    return null;
  }
  // Re-key the body whenever the dialog is re-opened so the inner
  // useState seeds from the current `initialValue` without an effect.
  const remountKey = `${props.initialValue.name}::${props.initialValue.description}`;
  return <WorkflowSaveDialogBody key={remountKey} {...props} />;
}

function WorkflowSaveDialogBody({
  initialValue,
  mode,
  saving,
  error,
  onClose,
  onSubmit,
}: WorkflowSaveDialogProps) {
  const [name, setName] = useState(initialValue.name);
  const [description, setDescription] = useState(initialValue.description);

  const canSubmit = name.trim().length > 0 && !saving;

  return (
    <div
      data-testid="workflow-save-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workflow-save-dialog-title"
      className="bg-charcoal-950/60 fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!canSubmit) return;
          onSubmit({ name: name.trim(), description: description.trim() });
        }}
        className="bg-charcoal-900 border-charcoal-700 flex w-[420px] flex-col gap-3 rounded-md border p-4"
      >
        <header className="flex items-baseline justify-between">
          <h2
            id="workflow-save-dialog-title"
            className="text-charcoal-100 font-mono text-sm tracking-wide uppercase"
          >
            {mode === "create" ? "Save workflow" : "Update workflow"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-charcoal-400 font-mono text-sm hover:text-amber-400"
          >
            ×
          </button>
        </header>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[10px] uppercase">Name</span>
          <input
            aria-label="Workflow name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Research: AAPL daily"
            autoFocus
            className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[10px] uppercase">
            Description (optional)
          </span>
          <textarea
            aria-label="Workflow description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Fetch quote + history; compute RSI; run researcher; log."
            rows={3}
            className="bg-charcoal-800 text-charcoal-100 min-h-[3rem] resize-y rounded-md p-2 font-mono text-xs leading-relaxed outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        {error !== null && error !== undefined && (
          <p className="text-negative font-mono text-[10px]">{error}</p>
        )}
        <div className="flex items-center justify-end gap-2 pt-1">
          <Button type="button" size="sm" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" variant="outline" disabled={!canSubmit}>
            {saving ? "Saving…" : mode === "create" ? "Save" : "Update"}
          </Button>
        </div>
      </form>
    </div>
  );
}
