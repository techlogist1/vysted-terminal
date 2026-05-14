"use client";

import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { deleteWorkspace, listWorkspaces, loadWorkspace, saveWorkspace } from "@/lib/workspace";
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
        <DialogTitle className="text-charcoal-100 font-serif">Save Workspace</DialogTitle>
        <DialogDescription className="text-charcoal-400 font-mono text-xs">
          Saves the current panel layout and the enabled modules.
        </DialogDescription>
      </DialogHeader>
      <input
        autoFocus
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Workspace name"
        aria-label="Workspace name"
        className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-400 mt-4 w-full rounded-md border px-3 py-2 font-mono text-sm outline-none focus:border-amber-400"
      />
      {error ? <p className="mt-2 font-mono text-xs text-red-400">{error}</p> : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onDone} disabled={busy}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={busy || name.trim() === ""}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}

function LoadWorkspaceList({ onDone }: ModeProps) {
  const [names, setNames] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listWorkspaces()
      .then((result) => {
        if (!cancelled) {
          setNames(result);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Could not list workspaces.");
          setNames([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLoad(name: string) {
    setBusy(true);
    setError(null);
    try {
      await loadWorkspace(name);
      onDone();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the workspace.");
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
      setError(caught instanceof Error ? caught.message : "Could not delete the workspace.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <DialogHeader>
        <DialogTitle className="text-charcoal-100 font-serif">Load Workspace</DialogTitle>
        <DialogDescription className="text-charcoal-400 font-mono text-xs">
          Restores a saved panel layout and its enabled modules.
        </DialogDescription>
      </DialogHeader>
      {error ? <p className="mt-3 font-mono text-xs text-red-400">{error}</p> : null}
      <div className="mt-4 flex max-h-72 flex-col gap-1.5 overflow-y-auto">
        {names === null ? (
          <p className="text-charcoal-400 py-4 text-center font-mono text-xs">Loading…</p>
        ) : names.length === 0 ? (
          <p className="text-charcoal-400 py-4 text-center font-mono text-xs">
            No saved workspaces yet.
          </p>
        ) : (
          names.map((name) => (
            <div
              key={name}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-md border px-3 py-2"
            >
              <button
                type="button"
                onClick={() => handleLoad(name)}
                disabled={busy}
                className="text-charcoal-100 flex-1 text-left font-mono text-sm disabled:opacity-50"
              >
                {name}
              </button>
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={() => handleDelete(name)}
                disabled={busy}
                className="text-charcoal-400 hover:text-red-400"
              >
                Delete
              </Button>
            </div>
          ))
        )}
      </div>
      <div className="mt-4 flex justify-end">
        <Button type="button" variant="ghost" size="sm" onClick={onDone} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
