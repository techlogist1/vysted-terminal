"use client";

/**
 * BrokerConnectPanel — Phase 5 broker-connect surface.
 *
 * Lists all 7 broker adapters + ccxt sub-exchanges in two groups. Each row
 * surfaces:
 *
 *   - Status badge (disconnected / connecting / connected / error)
 *   - Mode badge (paper / live / read-only)
 *   - Connect button → credentials dialog (uses keychain
 *     `broker:<id>:<field>` namespace)
 *   - Per-broker first-connect disclaimer dialog (BLUEPRINT §6.5 #8)
 *   - Kite static-IP banner (embedded `<KiteStaticIpBanner>` — Teammate I)
 *     when the broker is `kite` and `requiresStaticIp` is true.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { BrokerFirstConnectDialog } from "@/modules/safety/DisclaimerFlow";
import { useBrokersStore } from "@/store/brokers";
import { useSafetyStore } from "@/store/safety";

import type { BrokerId, BrokerMode, BrokerState } from "../../../types/broker";

import { KiteStaticIpBanner } from "./kite-static-ip-banner";

const BROKER_CREDENTIAL_FIELDS: Record<BrokerId, Array<{ key: string; label: string }>> = {
  dhan: [
    { key: "client_id", label: "Client ID" },
    { key: "access_token", label: "Access Token" },
  ],
  angelone: [
    { key: "api_key", label: "API Key" },
    { key: "client_code", label: "Client Code" },
    { key: "pin", label: "PIN" },
    { key: "totp_secret", label: "TOTP Secret" },
  ],
  kite: [
    { key: "api_key", label: "API Key" },
    { key: "api_secret", label: "API Secret" },
    { key: "access_token", label: "Access Token" },
    { key: "static_ip", label: "Static IP (SEBI rule)" },
  ],
  alpaca: [
    { key: "api_key", label: "API Key" },
    { key: "api_secret", label: "API Secret" },
  ],
  ib: [
    { key: "host", label: "Gateway Host" },
    { key: "port", label: "Gateway Port" },
    { key: "client_id", label: "Client ID" },
  ],
  oanda: [
    { key: "api_token", label: "API Token" },
    { key: "account_id", label: "Account ID" },
  ],
  "ccxt-bybit": [
    { key: "api_key", label: "API Key" },
    { key: "api_secret", label: "API Secret" },
  ],
  "ccxt-binance": [
    { key: "api_key", label: "API Key" },
    { key: "api_secret", label: "API Secret" },
  ],
  "ccxt-kraken": [
    { key: "api_key", label: "API Key" },
    { key: "api_secret", label: "API Secret" },
  ],
  "ccxt-coinbase": [
    { key: "api_key", label: "API Key" },
    { key: "api_secret", label: "API Secret" },
  ],
};

function brokerLabel(broker: BrokerId): string {
  switch (broker) {
    case "dhan":
      return "Dhan";
    case "angelone":
      return "Angel One";
    case "kite":
      return "Zerodha Kite";
    case "alpaca":
      return "Alpaca";
    case "ib":
      return "Interactive Brokers";
    case "oanda":
      return "OANDA";
    case "ccxt-bybit":
      return "Bybit (ccxt)";
    case "ccxt-binance":
      return "Binance (ccxt)";
    case "ccxt-kraken":
      return "Kraken (ccxt)";
    case "ccxt-coinbase":
      return "Coinbase (ccxt)";
  }
}

export function BrokerConnectPanel() {
  const refresh = useSafetyStore((s) => s.refreshFirstLaunchAck);
  const firstLaunchTosAcked = useSafetyStore((s) => s.firstLaunchTosAcked);
  const refreshBrokers = useBrokersStore((s) => s.refresh);
  const byId = useBrokersStore((s) => s.byId);
  const status = useBrokersStore((s) => s.status);

  useEffect(() => {
    void refresh();
    void refreshBrokers();
  }, [refresh, refreshBrokers]);

  const { primary, crypto } = useMemo(() => {
    const all = Object.values(byId).filter(
      (s): s is NonNullable<typeof s> => s !== undefined,
    );
    return {
      primary: all.filter((s) => !s.broker.startsWith("ccxt-")),
      crypto: all.filter((s) => s.broker.startsWith("ccxt-")),
    };
  }, [byId]);

  return (
    <div
      data-testid="broker-connect-panel"
      className="flex h-full w-full flex-col bg-charcoal-900 font-mono text-xs text-charcoal-100"
    >
      <header className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
        <h2 className="text-charcoal-100 text-sm tracking-wide uppercase">Broker Connections</h2>
        <span className="text-charcoal-500 text-[10px]">
          {primary.length + crypto.length} brokers
        </span>
      </header>

      {!firstLaunchTosAcked && (
        <div className="m-3 rounded-md border border-amber-500/60 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">
          Accept the Terms of Service to connect a broker.
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-3 py-2">
        <section>
          <h3 className="text-charcoal-400 mb-1 text-[10px] uppercase">Brokers</h3>
          {primary.length === 0 && (
            <p className="text-charcoal-500 px-1 py-2">
              {status === "loading" ? "Loading…" : "No brokers reported by sidecar."}
            </p>
          )}
          <ul>
            {primary.map((state) => (
              <BrokerRow key={state.broker} state={state} disabled={!firstLaunchTosAcked} />
            ))}
          </ul>
        </section>

        {crypto.length > 0 && (
          <section className="mt-4">
            <h3 className="text-charcoal-400 mb-1 text-[10px] uppercase">Crypto (ccxt)</h3>
            <ul>
              {crypto.map((state) => (
                <BrokerRow key={state.broker} state={state} disabled={!firstLaunchTosAcked} />
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

interface BrokerRowProps {
  state: BrokerState;
  disabled: boolean;
}

function BrokerRow({ state, disabled }: BrokerRowProps) {
  const [credentialsOpen, setCredentialsOpen] = useState(false);
  const [firstConnectOpen, setFirstConnectOpen] = useState(false);
  const [sidecarBaseUrl, setSidecarBaseUrl] = useState<string | null>(null);
  const brokerFirstConnectAcked = useSafetyStore(
    (s) => s.brokerFirstConnectAcked[state.broker] === true,
  );
  const refreshFirstConnectAck = useSafetyStore((s) => s.refreshBrokerFirstConnectAck);
  const connect = useBrokersStore((s) => s.connect);
  const setMode = useBrokersStore((s) => s.setMode);
  const setReadOnly = useBrokersStore((s) => s.setReadOnly);

  useEffect(() => {
    void refreshFirstConnectAck(state.broker);
  }, [state.broker, refreshFirstConnectAck]);

  // Resolve the sidecar base url once for the KiteStaticIpBanner.
  useEffect(() => {
    if (state.broker !== "kite") {
      return;
    }
    void (async () => {
      try {
        const base = await getSidecarBaseUrl();
        setSidecarBaseUrl(base);
      } catch {
        // Tauri not available in test env — banner just skips.
      }
    })();
  }, [state.broker]);

  const handleConnectClick = useCallback(() => {
    if (!brokerFirstConnectAcked) {
      setFirstConnectOpen(true);
      return;
    }
    setCredentialsOpen(true);
  }, [brokerFirstConnectAcked]);

  const handleFirstConnectAccept = useCallback(() => {
    setFirstConnectOpen(false);
    setCredentialsOpen(true);
  }, []);

  const handleModeToggle = useCallback(async () => {
    const next: BrokerMode = state.mode === "paper" ? "live" : "paper";
    await setMode(state.broker, next);
  }, [setMode, state.broker, state.mode]);

  const handleReadOnlyToggle = useCallback(async () => {
    await setReadOnly(state.broker, !state.readOnly);
  }, [setReadOnly, state.broker, state.readOnly]);

  return (
    <li
      data-testid={`broker-row-${state.broker}`}
      className="border-charcoal-800 flex items-center justify-between gap-2 border-b py-2"
    >
      <div className="flex flex-1 flex-col gap-0.5">
        <span className="text-charcoal-100 text-sm">{brokerLabel(state.broker)}</span>
        <div className="flex flex-wrap gap-1">
          <StatusBadge status={state.status} />
          <ModeBadge mode={state.mode} />
          {state.readOnly && <ReadOnlyBadge />}
          {state.error !== undefined && (
            <span className="text-red-400">err: {state.error}</span>
          )}
        </div>
        {state.broker === "kite" && state.mode === "live" && sidecarBaseUrl !== null && (
          <div className="mt-1">
            <KiteStaticIpBanner sidecarBaseUrl={sidecarBaseUrl} configuredIp={null} />
          </div>
        )}
      </div>
      <div className="flex gap-1">
        {state.status === "connected" ? (
          <>
            <Button size="xs" variant="ghost" onClick={handleModeToggle}>
              {state.mode === "paper" ? "Go live" : "Go paper"}
            </Button>
            <Button size="xs" variant="ghost" onClick={handleReadOnlyToggle}>
              {state.readOnly ? "Allow writes" : "Read-only"}
            </Button>
          </>
        ) : (
          <Button
            size="xs"
            variant="outline"
            onClick={handleConnectClick}
            disabled={disabled || state.status === "connecting"}
            data-testid={`connect-${state.broker}`}
          >
            {state.status === "connecting" ? "Connecting…" : "Connect"}
          </Button>
        )}
      </div>

      <BrokerFirstConnectDialog
        broker={state.broker}
        open={firstConnectOpen}
        onAccept={handleFirstConnectAccept}
        onCancel={() => setFirstConnectOpen(false)}
      />
      <CredentialsDialog
        broker={state.broker}
        open={credentialsOpen}
        onClose={() => setCredentialsOpen(false)}
        onSubmit={async (credentials) => {
          for (const [key, value] of Object.entries(credentials)) {
            await setSecret(KEYCHAIN_NAMESPACES.broker(state.broker, key), value);
          }
          await connect(state.broker, credentials);
          setCredentialsOpen(false);
        }}
      />
    </li>
  );
}

function StatusBadge({ status }: { status: BrokerState["status"] }) {
  const color = {
    disconnected: "bg-charcoal-700 text-charcoal-300",
    connecting: "bg-amber-800/40 text-amber-200",
    connected: "bg-emerald-800/40 text-emerald-200",
    error: "bg-red-800/40 text-red-200",
  }[status];
  return (
    <span
      data-testid="broker-status-badge"
      className={cn("rounded px-1.5 py-[1px] text-[10px] uppercase", color)}
    >
      {status}
    </span>
  );
}

function ModeBadge({ mode }: { mode: BrokerMode }) {
  return (
    <span
      data-testid="broker-mode-badge"
      className={cn(
        "rounded px-1.5 py-[1px] text-[10px] uppercase",
        mode === "paper"
          ? "bg-sky-800/40 text-sky-200"
          : "bg-red-800/40 text-red-200",
      )}
    >
      {mode}
    </span>
  );
}

function ReadOnlyBadge() {
  return (
    <span
      data-testid="broker-readonly-badge"
      className="rounded bg-amber-800/40 px-1.5 py-[1px] text-[10px] uppercase text-amber-200"
    >
      read-only
    </span>
  );
}

interface CredentialsDialogProps {
  broker: BrokerId;
  open: boolean;
  onClose: () => void;
  onSubmit: (credentials: Record<string, string>) => Promise<void>;
}

function CredentialsDialog({ broker, open, onClose, onSubmit }: CredentialsDialogProps) {
  const fields = useMemo(() => BROKER_CREDENTIAL_FIELDS[broker], [broker]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await onSubmit(values);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Connect failed");
      } finally {
        setBusy(false);
      }
    },
    [onSubmit, values],
  );

  if (!open) {
    return null;
  }

  return (
    <Dialog
      open
      onOpenChange={(value) => {
        if (!value) {
          onClose();
        }
      }}
    >
      <DialogContent data-testid={`credentials-dialog-${broker}`}>
        <DialogHeader>
          <DialogTitle>Connect {brokerLabel(broker)}</DialogTitle>
          <DialogDescription>
            Credentials are stored in the OS keychain under{" "}
            <code>broker:{broker}:&lt;field&gt;</code>.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          {fields.map((field) => (
            <label key={field.key} className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground text-[10px] uppercase">{field.label}</span>
              <input
                type={
                  field.key.includes("token") ||
                  field.key.includes("secret") ||
                  field.key === "pin"
                    ? "password"
                    : "text"
                }
                value={values[field.key] ?? ""}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                }
                className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
                data-testid={`cred-${broker}-${field.key}`}
              />
            </label>
          ))}
          {error !== null && <p className="text-xs text-red-400">{error}</p>}
          <DialogFooter>
            <Button variant="ghost" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Connecting…" : "Connect"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
