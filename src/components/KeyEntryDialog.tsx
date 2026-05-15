"use client";

import { useEffect, useState } from "react";
import { KeyRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useLLMProvidersStore } from "@/store/llm-providers";
import type { LLMProviderId } from "../../types/ai";

/**
 * BYOK key entry dialog.
 *
 * Opens for a specific provider (passed via ``providerId``). Validates the
 * key against the sidecar's ``POST /llm/keys/validate`` endpoint before
 * writing it to the OS keychain via :func:`setSecret`. The key is never
 * cached on the frontend after dialog close — every subsequent invocation
 * reads it back through :func:`getSecret` on demand.
 */
export interface KeyEntryDialogProps {
  open: boolean;
  providerId: LLMProviderId | null;
  onOpenChange: (open: boolean) => void;
  onSaved?: (providerId: LLMProviderId) => void;
}

interface ValidationResponse {
  ok: boolean;
  detail?: string | null;
}

type Status = "idle" | "validating" | "valid" | "invalid" | "save-error";

export function KeyEntryDialog({ open, providerId, onOpenChange, onSaved }: KeyEntryDialogProps) {
  const providers = useLLMProvidersStore((state) => state.providers);
  const [key, setKey] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    // Reset on close so the next time the dialog opens it starts blank — no
    // residual key value in component state between sessions. The setState
    // calls only fire on a transition (when ``open`` flips to ``false``),
    // not on every render, so there is no cascade risk in practice.
    if (!open) {
      setKey("");
      setStatus("idle");
      setErrorDetail(null);
    }
  }, [open]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const provider = providers.find((p) => p.id === providerId) ?? null;

  async function handleSave() {
    if (!providerId) {
      return;
    }
    setStatus("validating");
    setErrorDetail(null);
    try {
      // Validate via the sidecar — cheap probe against the provider's
      // models endpoint. ``POST /llm/keys/validate`` returns ok/detail.
      const validation = await postValidate(providerId, key);
      if (!validation.ok) {
        setStatus("invalid");
        setErrorDetail(validation.detail ?? "Key was not accepted by the provider.");
        return;
      }
      await setSecret(KEYCHAIN_NAMESPACES.llmProvider(providerId), key);
      setStatus("valid");
      onSaved?.(providerId);
      // Close after a short pause so the user sees the success state.
      setTimeout(() => onOpenChange(false), 500);
    } catch (err) {
      setStatus("save-error");
      setErrorDetail(err instanceof Error ? err.message : "Failed to save key.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-charcoal-700 bg-charcoal-900 max-w-md gap-0 p-0 shadow-2xl">
        <DialogHeader className="border-charcoal-700 border-b px-5 py-3">
          <DialogTitle className="text-charcoal-200 flex items-center gap-2 font-mono text-sm font-medium">
            <KeyRound className="size-3.5 text-amber-400" aria-hidden="true" />
            {provider ? `${provider.label} API key` : "Provider API key"}
          </DialogTitle>
          <DialogDescription className="text-charcoal-400 mt-1 font-mono text-xs">
            Stored in the OS keychain; never written to disk by Vysted.
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-3 px-5 py-4"
          onSubmit={(event) => {
            event.preventDefault();
            void handleSave();
          }}
        >
          <input
            type="password"
            value={key}
            autoFocus
            onChange={(event) => setKey(event.target.value)}
            placeholder={provider?.requiresKey === false ? "(no key required)" : "sk-..."}
            disabled={!provider || provider.requiresKey === false}
            aria-label="API key"
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 h-9 rounded-md px-3 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
          />
          {status === "invalid" && (
            <p className="text-negative font-mono text-xs">{errorDetail ?? "Invalid key."}</p>
          )}
          {status === "save-error" && (
            <p className="text-negative font-mono text-xs">{errorDetail}</p>
          )}
          {status === "valid" && <p className="text-positive font-mono text-xs">Saved.</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={status === "validating"}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={status === "validating" || !key || provider?.requiresKey === false}
            >
              {status === "validating" ? "Validating…" : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

async function postValidate(provider: LLMProviderId, apiKey: string): Promise<ValidationResponse> {
  const base = await getSidecarBaseUrl();
  const url = new URL("/llm/keys/validate", base);
  const response = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
  if (!response.ok) {
    return { ok: false, detail: `sidecar returned ${response.status}` };
  }
  // Mirror the sidecar wire shape.
  const body = (await response.json()) as { ok: boolean; detail?: string | null };
  return { ok: body.ok, detail: body.detail ?? null };
}
