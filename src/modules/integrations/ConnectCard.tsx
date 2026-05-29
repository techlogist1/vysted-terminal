"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  exchangeAndConnectKite,
  openKiteLogin,
  extractRequestToken,
} from "@/lib/integrations/kite-connect";
import type { IntegrationSpec } from "@/lib/integrations/types";
import { KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import type { BrokerId } from "../../../types/broker";
import { useBrokersStore } from "@/store/brokers";

/**
 * One dialog renders ANY integration from its spec — fields + authFlow drive
 * everything. Kite takes the two-step loopback-OAuth path (save key/secret →
 * browser login → paste request_token → exchange); static-token /
 * interactive-session brokers write their fields to the keychain and connect.
 */
export function ConnectCard({
  spec,
  open,
  onOpenChange,
}: {
  spec: IntegrationSpec | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const connectBroker = useBrokersStore((s) => s.connect);
  const [values, setValues] = useState<Record<string, string>>({});
  const [requestToken, setRequestToken] = useState("");
  const [step, setStep] = useState<"fields" | "awaiting-token">("fields");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  if (!spec) {
    return null;
  }

  function reset() {
    setValues({});
    setRequestToken("");
    setStep("fields");
    setError(null);
    setDone(null);
    setBusy(false);
  }

  async function persistFields(s: IntegrationSpec): Promise<boolean> {
    for (const field of s.fields) {
      const value = (values[field.key] ?? "").trim();
      if (field.required && !value) {
        setError(`${field.label} is required.`);
        return false;
      }
      if (value) {
        await setSecret(KEYCHAIN_NAMESPACES.broker(s.id, field.key), value);
      }
    }
    return true;
  }

  async function handleStaticConnect(s: IntegrationSpec) {
    setBusy(true);
    setError(null);
    try {
      if (!(await persistFields(s))) {
        return;
      }
      const credentials: Record<string, string> = {};
      for (const field of s.fields) {
        const value = (values[field.key] ?? "").trim();
        if (value) {
          credentials[field.key] = value;
        }
      }
      await connectBroker(s.id as BrokerId, credentials);
      setDone(`Connected ${s.label}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleKiteBeginLogin(s: IntegrationSpec) {
    setBusy(true);
    setError(null);
    try {
      // Persist key/secret/static_ip; only the access_token is minted later.
      if (!(await persistFields(s))) {
        return;
      }
      await openKiteLogin((values.api_key ?? "").trim());
      setStep("awaiting-token");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open the Kite login.");
    } finally {
      setBusy(false);
    }
  }

  async function handleKiteComplete() {
    const token = extractRequestToken(requestToken);
    if (!token) {
      setError("Paste the redirect URL (or the request_token) from the Kite login.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await exchangeAndConnectKite(token);
      setDone(`Connected Zerodha${result.userId ? ` (${result.userId})` : ""}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kite login exchange failed.");
    } finally {
      setBusy(false);
    }
  }

  const isKite = spec.authFlow === "loopback-oauth";

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          reset();
        }
        onOpenChange(next);
      }}
    >
      <DialogContent className="bg-charcoal-900 max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-charcoal-100 font-serif">{spec.label}</DialogTitle>
          <DialogDescription className="text-charcoal-400 font-mono text-xs">
            {spec.description}
          </DialogDescription>
        </DialogHeader>

        {spec.instructions && (
          <p className="text-charcoal-400 border-charcoal-700 bg-charcoal-850 rounded-md border p-3 font-mono text-[0.7rem] whitespace-pre-line">
            {spec.instructions}
          </p>
        )}
        {spec.dailyExpiry && (
          <p className="font-mono text-[0.7rem] text-amber-400">
            Session resets daily at {spec.dailyExpiry.boundaryLabel}. {spec.dailyExpiry.note}
          </p>
        )}

        {step === "fields" && (
          <div className="flex flex-col gap-2">
            {spec.fields.map((field) => (
              <label key={field.key} className="flex flex-col gap-1">
                <span className="text-charcoal-300 font-mono text-[0.7rem]">
                  {field.label}
                  {field.required ? "" : " (optional)"}
                </span>
                <input
                  type={field.type === "password" ? "password" : "text"}
                  value={values[field.key] ?? ""}
                  placeholder={field.placeholder}
                  onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                  className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 h-8 rounded-md border px-2 font-mono text-xs outline-none focus:border-amber-400"
                />
                {field.help && (
                  <span className="text-charcoal-500 font-mono text-[0.65rem]">{field.help}</span>
                )}
              </label>
            ))}
          </div>
        )}

        {step === "awaiting-token" && (
          <div className="flex flex-col gap-2">
            <p className="text-charcoal-300 font-mono text-[0.7rem]">
              Logged in? Paste the page URL you landed on (or the{" "}
              <span className="text-charcoal-100">request_token</span> from it):
            </p>
            <input
              value={requestToken}
              onChange={(e) => setRequestToken(e.target.value)}
              placeholder="http://127.0.0.1:43117/kite/callback?request_token=…"
              className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 h-8 rounded-md border px-2 font-mono text-xs outline-none focus:border-amber-400"
            />
          </div>
        )}

        {error && <p className="text-negative font-mono text-xs">{error}</p>}
        {done && <p className="text-positive font-mono text-xs">{done}</p>}

        <div className="flex items-center justify-between gap-2">
          {spec.website ? (
            <a
              href={spec.website}
              target="_blank"
              rel="noreferrer"
              className="text-charcoal-400 flex items-center gap-1 font-mono text-[0.7rem] hover:text-amber-400"
            >
              Get your key <ExternalLink className="size-3" />
            </a>
          ) : (
            <span />
          )}
          {done ? (
            <Button size="sm" variant="outline" onClick={() => onOpenChange(false)}>
              Done
            </Button>
          ) : isKite ? (
            step === "fields" ? (
              <Button size="sm" disabled={busy} onClick={() => void handleKiteBeginLogin(spec)}>
                Connect with Zerodha
              </Button>
            ) : (
              <Button size="sm" disabled={busy} onClick={() => void handleKiteComplete()}>
                Complete connection
              </Button>
            )
          ) : (
            <Button size="sm" disabled={busy} onClick={() => void handleStaticConnect(spec)}>
              Connect
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
