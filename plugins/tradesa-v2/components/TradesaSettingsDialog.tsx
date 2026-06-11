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

import { Button } from "@/components/ui/button";
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
      <div className="border-charcoal-700 bg-charcoal-950 text-charcoal-100 rounded-control w-full max-w-lg border p-6">
        <h2 id="tradesa-settings-dialog-title" className="text-section">
          Tradesa V2 — Connect your bot
        </h2>
        <p className="text-charcoal-400 text-body mt-1">
          Vysted Terminal reads your Tradesa V2 bot&apos;s state from its Supabase project.
          Credentials live in the OS keychain — never in browser storage.
        </p>

        <form className="mt-4 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-caption font-medium tracking-wide uppercase">
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
              className="border-charcoal-700 bg-charcoal-900 text-charcoal-100 placeholder:text-charcoal-600 rounded-control text-body focus:border-charcoal-500 focus-visible:ring-charcoal-500 h-8 border px-3 focus:outline-none focus-visible:ring-1"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-caption font-medium tracking-wide uppercase">
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
                className="border-charcoal-700 bg-charcoal-900 text-charcoal-100 placeholder:text-charcoal-600 rounded-l-control text-caption focus:border-charcoal-500 focus-visible:ring-charcoal-500 h-8 flex-1 border border-r-0 px-3 font-mono focus:outline-none focus-visible:ring-1"
              />
              <button
                type="button"
                aria-label={showKey ? "Hide service-role key" : "Show service-role key"}
                onClick={() => setShowKey((v) => !v)}
                data-testid="tradesa-settings-show-toggle"
                className="border-charcoal-700 bg-charcoal-800 text-charcoal-300 hover:bg-charcoal-700 rounded-r-control focus-visible:ring-charcoal-500 inline-flex h-8 items-center justify-center border px-3 transition-colors focus:outline-none focus-visible:ring-1"
              >
                {/* 14px icon — R9 §3 rung for the h-8 control. */}
                {showKey ? (
                  <EyeOff className={"size-3.5" /* tokens-ok: 14px icon — R9 §3 rung */} />
                ) : (
                  <Eye className={"size-3.5" /* tokens-ok: 14px icon — R9 §3 rung */} />
                )}
              </button>
            </div>
          </label>

          <div className="border-warning/40 bg-warning/10 text-warning text-caption rounded-none border px-3 py-2">
            Your service-role key has full read+write power on your Tradesa V2 Supabase project.
            Vysted Terminal uses it read-only. Keep it on this machine only — don&apos;t share via
            screen-share or chat.
          </div>

          {error && (
            <div
              role="alert"
              data-testid="tradesa-settings-error"
              className="border-negative/40 bg-negative/10 text-negative text-caption rounded-none border px-3 py-2"
            >
              {error}
            </div>
          )}

          {/* Form rung (R9 §3): actions join the sibling h-8 inputs; the shared
              primitive supplies the monochrome primary, no shadow, 1px ring. */}
          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} data-testid="tradesa-settings-submit">
              {submitting ? "Saving…" : "Save & Connect"}
            </Button>
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
