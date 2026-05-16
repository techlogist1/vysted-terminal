/**
 * Tradesa V2 wrapper — settings / onboarding dialog.
 *
 * First-launch entry point: the user enters their Tradesa V2 Supabase
 * project URL + service-role key, and the dialog persists both via the
 * OS keychain (Tauri Rust `keychain_set`). On submit the dialog triggers
 * a connection re-probe so the panels switch out of the `unauthenticated`
 * UX immediately.
 *
 * The service-role key is the bot's Supabase project's privileged key.
 * Vysted only ever uses it READ-ONLY (every sidecar route is GET; no
 * provider method writes; `supportsControlPlane=false`). The dialog
 * warns the user in plain language about the privilege scope.
 *
 * No localStorage / sessionStorage — values live in the OS keychain
 * (Windows Credential Manager / macOS Keychain / libsecret) so they
 * survive across launches without browser storage.
 */

"use client";

import { useEffect, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { setSecret } from "@/lib/keychain";

import { TRADESA_KEYCHAIN_ACCOUNTS, readCredentials } from "../connection";
import { useTradesaStore } from "../store";

export interface TradesaSettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

export function TradesaSettingsDialog({ open, onClose }: TradesaSettingsDialogProps) {
  const [url, setUrl] = useState("");
  const [key, setKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConnection = useTradesaStore((s) => s.refreshConnection);

  // Hydrate the form with the existing creds (if any) when the dialog
  // opens — the user is probably editing, not starting fresh.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      try {
        const creds = await readCredentials();
        if (!cancelled && creds) {
          setUrl(creds.url);
          setKey(creds.key);
        }
      } catch {
        /* swallow — missing creds is the empty-form initial state */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const trimmedUrl = url.trim();
    const trimmedKey = key.trim();

    if (!trimmedUrl) {
      setError("Supabase URL is required.");
      return;
    }
    if (!/^https?:\/\//i.test(trimmedUrl)) {
      setError("Supabase URL must start with https://.");
      return;
    }
    if (!trimmedKey) {
      setError("Service-role key is required.");
      return;
    }

    setSubmitting(true);
    try {
      await setSecret(TRADESA_KEYCHAIN_ACCOUNTS.supabaseUrl, trimmedUrl);
      await setSecret(TRADESA_KEYCHAIN_ACCOUNTS.supabaseServiceRoleKey, trimmedKey);
      await refreshConnection();
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to save credentials: ${message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="tradesa-settings-dialog-title"
      data-testid="tradesa-settings-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="w-full max-w-lg rounded-lg border border-zinc-800 bg-zinc-950 p-6 text-zinc-100 shadow-2xl">
        <h2 id="tradesa-settings-dialog-title" className="text-lg font-semibold">
          Tradesa V2 — Connect your bot
        </h2>
        <p className="mt-1 text-sm text-zinc-400">
          Vysted Terminal reads your Tradesa V2 bot&apos;s state from its Supabase
          project. Credentials live in the OS keychain — never in browser
          storage.
        </p>

        <form className="mt-4 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">
              Tradesa V2 Supabase URL
            </span>
            <input
              type="url"
              required
              autoComplete="off"
              spellCheck={false}
              placeholder="https://xxxx.supabase.co"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              data-testid="tradesa-settings-url"
              className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">
              Service-Role Key
            </span>
            <div className="flex">
              <input
                type={showKey ? "text" : "password"}
                required
                autoComplete="off"
                spellCheck={false}
                placeholder="eyJ…"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                data-testid="tradesa-settings-key"
                className="flex-1 rounded-l-md border border-r-0 border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              />
              <button
                type="button"
                aria-label={showKey ? "Hide service-role key" : "Show service-role key"}
                onClick={() => setShowKey((v) => !v)}
                data-testid="tradesa-settings-show-toggle"
                className="inline-flex items-center justify-center rounded-r-md border border-zinc-700 bg-zinc-800 px-3 text-zinc-300 transition-colors hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </label>

          <div className="rounded-md border border-amber-900/50 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">
            Your service-role key has full read+write power on your Tradesa V2
            Supabase project. Vysted Terminal uses it read-only. Keep it on
            this machine only — don&apos;t share via screen-share or chat.
          </div>

          {error && (
            <div
              role="alert"
              data-testid="tradesa-settings-error"
              className="rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-200"
            >
              {error}
            </div>
          )}

          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-md border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm text-zinc-200 transition-colors hover:bg-zinc-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              data-testid="tradesa-settings-submit"
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Saving…" : "Save & Connect"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Imperative opener — panels call this from their "Open Settings" CTA
 * via the shell's component-local state. The slash-command path is
 * deferred to v0.6.6 (lead owns `index.ts`).
 *
 * Kept exported so future glue (or a teammate-level callback registry)
 * can wire it up without expanding the lead-owned files.
 */
export function openSettingsDialog(setter: (open: boolean) => void): void {
  setter(true);
}

export default TradesaSettingsDialog;
