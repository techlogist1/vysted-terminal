"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  createResearchSpace,
  deleteWorkspace,
  listWorkspaces,
  loadWorkspace,
  saveWorkspace,
} from "@/lib/workspace";
import { useChartCommandStore } from "@/store/chart-command";
import { useWorkspaceStore } from "@/store/workspace";
import { useWorkspaceDialog } from "./workspace-dialog-store";

/**
 * The workspace save/load dialog. Mounted once (in `page.tsx`); it renders only
 * when the platform module's "Save Workspace" / "Load Workspace" cmd+K commands
 * flip `useWorkspaceDialog`.
 *
 * - Save mode: a name field (pre-filled with the active workspace name) →
 *   `saveWorkspace`.
 * - Load mode: the list of saved workspaces fetched from the sidecar; pick one
 *   to `loadWorkspace`, or delete one.
 */
export function WorkspaceDialog() {
  const mode = useWorkspaceDialog((state) => state.mode);
  const close = useWorkspaceDialog((state) => state.close);
  const open = mode !== null;

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : close())}>
      <DialogContent className="border-charcoal-700 bg-charcoal-900 max-w-md">
        {mode === "save" ? (
          <SaveWorkspaceForm onDone={close} />
        ) : mode === "load" ? (
          <LoadWorkspaceList onDone={close} />
        ) : mode === "research-space" ? (
          <ResearchSpaceForm onDone={close} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

interface ModeProps {
  onDone: () => void;
}

function SaveWorkspaceForm({ onDone }: ModeProps) {
  const activeName = useWorkspaceStore((state) => state.name);
  const [name, setName] = useState(activeName);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await saveWorkspace(name);
      onDone();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the workspace.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle className="text-charcoal-100">Save Workspace</DialogTitle>
        <DialogDescription className="text-charcoal-400 text-caption font-mono">
          Saves the current panel layout and the enabled modules.
        </DialogDescription>
      </DialogHeader>
      <input
        autoFocus
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Workspace name"
        aria-label="Workspace name"
        className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-400 rounded-control text-body focus:border-charcoal-500 mt-4 h-8 w-full border px-3 font-mono outline-none"
      />
      {error ? <p className="text-negative text-caption mt-2 font-mono">{error}</p> : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone} disabled={busy}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy || name.trim() === ""}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}

function ResearchSpaceForm({ onDone }: ModeProps) {
  // Prefill with the symbol currently loaded in the chart — the most likely
  // ticker the user wants a dedicated research space for.
  const activeSymbol = useChartCommandStore((state) => state.activeSymbol);
  const [symbol, setSymbol] = useState(activeSymbol ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createResearchSpace(symbol);
      onDone();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create the research space.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle className="text-charcoal-100">New Research Space</DialogTitle>
        <DialogDescription className="text-charcoal-400 text-caption font-mono">
          Spins up a dedicated cockpit for one ticker — chart, equity overview, the research brief,
          and notes scoped to it — saved as a workspace you can return to.
        </DialogDescription>
      </DialogHeader>
      <input
        autoFocus
        value={symbol}
        onChange={(event) => setSymbol(event.target.value.toUpperCase())}
        placeholder="Ticker, e.g. NVDA or RELIANCE"
        aria-label="Research space ticker"
        className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-400 rounded-control text-body focus:border-charcoal-500 mt-4 h-8 w-full border px-3 font-mono outline-none"
      />
      {error ? <p className="text-negative text-caption mt-2 font-mono">{error}</p> : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone} disabled={busy}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy || symbol.trim() === ""}>
          {busy ? "Creating…" : "Create space"}
        </Button>
      </div>
    </form>
  );
}

function LoadWorkspaceList({ onDone }: ModeProps) {
  const [names, setNames] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchFailed, setFetchFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const openSave = useWorkspaceDialog((state) => state.openSave);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    let cancelled = false;
    setNames(null);
    setError(null);
    setFetchFailed(false);
    listWorkspaces()
      .then((result) => {
        if (!cancelled) {
          setNames(result);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(
            `Could not reach the sidecar — ${caught instanceof Error ? caught.message : "unknown error."}`,
          );
          setFetchFailed(true);
          setNames([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [retryCount]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const retryFetch = useCallback(() => setRetryCount((c) => c + 1), []);

  async function handleLoad(name: string) {
    setBusy(true);
    setError(null);
    try {
      await loadWorkspace(name);
      onDone();
    } catch (caught) {
      setError(
        `Could not reach the sidecar — ${caught instanceof Error ? caught.message : "load failed."}`,
      );
      setBusy(false);
    }
  }

  async function handleDelete(name: string) {
    setBusy(true);
    setError(null);
    try {
      await deleteWorkspace(name);
      setNames((current) => (current ?? []).filter((entry) => entry !== name));
    } catch (caught) {
      setError(
        `Could not reach the sidecar — ${caught instanceof Error ? caught.message : "delete failed."}`,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <DialogHeader>
        <DialogTitle className="text-charcoal-100">Load Workspace</DialogTitle>
        <DialogDescription className="text-charcoal-400 text-caption font-mono">
          Restores a saved panel layout and its enabled modules.
        </DialogDescription>
      </DialogHeader>
      {error ? (
        <div className="mt-3 flex items-center justify-between gap-2">
          <p className="text-negative text-caption font-mono">{error}</p>
          {fetchFailed && (
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={retryFetch}
              className="text-charcoal-400 hover:text-charcoal-200 shrink-0"
            >
              Retry
            </Button>
          )}
        </div>
      ) : null}
      <div
        className={
          "mt-4 flex max-h-72 flex-col gap-2 overflow-y-auto" /* tokens-ok: workspace-list scroll cap — layout */
        }
      >
        {names === null ? (
          <p className="text-charcoal-400 text-caption py-4 text-center font-mono">Loading…</p>
        ) : names.length === 0 && !fetchFailed ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <p className="text-charcoal-400 text-caption font-mono">
              No saved workspaces yet. Save your current layout first.
            </p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                onDone();
                openSave();
              }}
              className="text-charcoal-400 hover:text-charcoal-200 text-caption font-mono"
            >
              Save current workspace
            </Button>
          </div>
        ) : (
          names.map((name) => (
            <div
              key={name}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-none border px-3 py-2"
            >
              <button
                type="button"
                onClick={() => handleLoad(name)}
                disabled={busy}
                className="text-charcoal-100 text-body flex-1 text-left font-mono disabled:opacity-50"
              >
                {name}
              </button>
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={() => handleDelete(name)}
                disabled={busy}
                className="text-charcoal-400 hover:text-negative"
              >
                Delete
              </Button>
            </div>
          ))
        )}
      </div>
      <div className="mt-4 flex justify-end">
        <Button type="button" variant="ghost" onClick={onDone} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
