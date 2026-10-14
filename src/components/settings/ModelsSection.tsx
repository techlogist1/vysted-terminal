"use client";

import { useEffect, useState } from "react";

import { ConfirmButton } from "@/components/ConfirmButton";
import { openExternal } from "@/components/onboarding/shared";
import { Button } from "@/components/ui/button";
import type { EngineStatus } from "@/lib/local-engine";
import { cn } from "@/lib/utils";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore } from "@/store/local-models";
import type { CatalogModel, DownloadState, InstalledModel } from "../../../types/data";

const GIB = 1024 ** 3;
const MIB = 1024 ** 2;

export function formatSize(bytes: number): string {
  if (bytes >= GIB) return `${(bytes / GIB).toFixed(1)} GB`;
  return `${Math.max(1, Math.round(bytes / MIB))} MB`;
}

const FIT_BADGE: Record<CatalogModel["fits"], { label: string; className: string }> = {
  good: { label: "Runs well here", className: "text-positive border-positive/40" },
  tight: { label: "A tight fit", className: "text-caution border-caution/40" },
  "too-big": { label: "Too big for this computer", className: "text-negative border-negative/40" },
};

const IN_FLIGHT = new Set<DownloadState["state"]>(["queued", "downloading", "verifying"]);

function errorText(error: unknown): string {
  return error instanceof Error && error.message ? error.message : "That did not go through.";
}

/** The engine status in plain words (the strip uses the same core-provided reasons). */
export function engineLine(
  status: EngineStatus,
  activeName: string | null,
): { text: string; tone: "quiet" | "good" | "warn" | "bad" } {
  switch (status.state) {
    case "starting":
      return { text: "Starting the model. This can take a minute.", tone: "quiet" };
    case "ready":
      return { text: `Running on this computer: ${activeName ?? "your model"}.`, tone: "good" };
    case "crashed":
      return {
        text: `${status.error ?? "The model stopped unexpectedly."} Trying again…`,
        tone: "warn",
      };
    case "failed":
      return { text: status.error ?? "The model could not start.", tone: "bad" };
    default:
      return { text: "No model is running right now.", tone: "quiet" };
  }
}

const TONE_CLASS = {
  quiet: "text-charcoal-400",
  good: "text-positive",
  warn: "text-caution",
  bad: "text-negative",
} as const;

function GroupLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-charcoal-500 text-micro mb-2">{children}</p>;
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="border-charcoal-700 rounded-none border">{children}</div>;
}

function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "rounded-control text-micro border px-2 py-px whitespace-nowrap",
        className ?? "text-charcoal-300 border-charcoal-600",
      )}
    >
      {children}
    </span>
  );
}

function RowError({ message }: { message: string | undefined }) {
  return message ? (
    <p className="text-negative text-caption" role="alert">
      {message}
    </p>
  ) : null;
}

/**
 * Settings → Models: add, remove and switch the models that run on this
 * computer. Pure view over `useLocalModelsStore` (the wizard writer's store)
 * and `useLocalEngineStore`; every action is a store call.
 */
export function ModelsSection() {
  const hardware = useLocalModelsStore((s) => s.hardware);
  const catalog = useLocalModelsStore((s) => s.catalog);
  const installed = useLocalModelsStore((s) => s.installed);
  const ollama = useLocalModelsStore((s) => s.ollama);
  const downloads = useLocalModelsStore((s) => s.downloads);
  const activeModelId = useLocalModelsStore((s) => s.activeModelId);
  const loadError = useLocalModelsStore((s) => s.loadError);
  const engine = useLocalEngineStore((s) => s.status);

  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [paused, setPaused] = useState<Record<string, boolean>>({});

  useEffect(() => {
    void useLocalModelsStore.getState().refresh();
  }, []);

  async function run(id: string, action: () => Promise<unknown>) {
    setBusy(id);
    setErrors((e) => ({ ...e, [id]: "" }));
    try {
      await action();
    } catch (error) {
      setErrors((e) => ({ ...e, [id]: errorText(error) }));
    } finally {
      setBusy(null);
    }
  }

  const store = useLocalModelsStore.getState;
  const nameOf = (id: string) =>
    catalog?.models.find((m) => m.id === id)?.name ??
    installed.find((m) => m.id === id)?.name ??
    id;
  const isActive = (m: InstalledModel) =>
    activeModelId !== null ? activeModelId === m.id : m.active;
  const installedIds = new Set(installed.map((m) => m.id));
  const activeName = activeModelId ? nameOf(activeModelId) : null;
  const line = engineLine(engine, activeName);

  const pending = Object.values(downloads).filter(
    (d) =>
      d.state !== "done" &&
      !(d.state === "cancelled" && d.receivedBytes === 0) &&
      !installedIds.has(d.id),
  );
  const pendingIds = new Set(pending.map((d) => d.id));
  const models = [...(catalog?.models ?? [])].sort(
    (a, b) => Number(b.id === catalog?.recommendedId) - Number(a.id === catalog?.recommendedId),
  );

  return (
    <div className="flex flex-col gap-6">
      {loadError !== null && (
        <p
          className="text-negative text-caption"
          aria-live="polite"
          data-testid="models-load-error"
        >
          {loadError}
        </p>
      )}

      <div>
        <GroupLabel>This computer</GroupLabel>
        <Card>
          <p className="text-charcoal-300 text-caption px-4 py-3" data-testid="models-computer">
            {hardware
              ? `${formatSize(hardware.totalRamBytes)} of memory (${formatSize(hardware.availableRamBytes)} free) · ${formatSize(hardware.freeDiskBytes)} of free disk space`
              : "Checking this computer…"}
          </p>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <p
          className={cn("text-caption min-w-0 flex-1", TONE_CLASS[line.tone])}
          aria-live="polite"
          data-testid="models-engine-line"
        >
          {line.text}
        </p>
        {engine.state === "failed" && activeModelId && (
          <Button
            size="sm"
            variant="outline"
            disabled={busy !== null}
            onClick={() => void run(activeModelId, () => store().activate(activeModelId))}
          >
            Try again
          </Button>
        )}
      </div>

      {ollama.running && (
        <p className="text-charcoal-400 text-caption">
          Ollama is running — its models are listed too. Vysted never needs Ollama.
        </p>
      )}

      <div>
        <GroupLabel>On this computer</GroupLabel>
        <Card>
          {installed.length === 0 ? (
            <p className="text-charcoal-400 text-caption px-4 py-3">
              No models yet. Pick one below to download.
            </p>
          ) : (
            <ul className="divide-charcoal-800 divide-y">
              {installed.map((m) => {
                const fromOllama = m.id.startsWith("ollama:");
                const active = isActive(m);
                return (
                  <li
                    key={m.id}
                    className="flex flex-col gap-2 px-4 py-3"
                    data-testid={`installed-${m.id}`}
                  >
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                        <span className="text-charcoal-100 text-body truncate">{m.name}</span>
                        {fromOllama && <Badge>from Ollama</Badge>}
                        {active && (
                          <Badge className="text-positive border-positive/40">In use</Badge>
                        )}
                        <span className="text-charcoal-500 text-caption">
                          {formatSize(m.sizeBytes)}
                        </span>
                      </div>
                      {active ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy !== null}
                          onClick={() => void run(m.id, () => store().deactivate())}
                        >
                          Turn off
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy !== null}
                          onClick={() => void run(m.id, () => store().activate(m.id))}
                        >
                          Use this
                        </Button>
                      )}
                      {fromOllama ? (
                        <span className="text-charcoal-500 text-caption">Remove it in Ollama</span>
                      ) : (
                        <ConfirmButton
                          size="sm"
                          variant="ghost"
                          disabled={busy !== null}
                          armedLabel={active ? "Stop and remove?" : "Remove for good?"}
                          aria-label={`Remove ${m.name}`}
                          onConfirm={() => void run(m.id, () => store().remove(m.id))}
                        >
                          Remove
                        </ConfirmButton>
                      )}
                    </div>
                    <RowError message={errors[m.id]} />
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>

      {pending.length > 0 && (
        <div>
          <GroupLabel>Downloading</GroupLabel>
          <Card>
            <ul className="divide-charcoal-800 divide-y">
              {pending.map((d) => (
                <DownloadRow
                  key={d.id}
                  d={d}
                  name={nameOf(d.id)}
                  heldByUser={paused[d.id] === true}
                  busy={busy !== null}
                  error={errors[d.id]}
                  onPause={() => {
                    setPaused((p) => ({ ...p, [d.id]: true }));
                    void run(d.id, () => store().cancel(d.id));
                  }}
                  onCancel={() => {
                    setPaused((p) => ({ ...p, [d.id]: false }));
                    void run(d.id, () => store().cancel(d.id));
                  }}
                  onResume={() => {
                    setPaused((p) => ({ ...p, [d.id]: false }));
                    void run(d.id, () => store().download(d.id));
                  }}
                  onDiscard={() => void run(d.id, () => store().cancel(d.id, true))}
                />
              ))}
            </ul>
          </Card>
        </div>
      )}

      <div>
        <GroupLabel>Add a model</GroupLabel>
        <Card>
          {models.length === 0 ? (
            <p className="text-charcoal-400 text-caption px-4 py-3">
              {catalog === null ? "Loading the list…" : "No models to show."}
            </p>
          ) : (
            <ul className="divide-charcoal-800 divide-y">
              {models.map((m) => {
                const fit = FIT_BADGE[m.fits];
                const have = installedIds.has(m.id);
                const loading = pendingIds.has(m.id);
                return (
                  <li
                    key={m.id}
                    className="flex flex-col gap-2 px-4 py-3"
                    data-testid={`catalog-${m.id}`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-charcoal-100 text-body">{m.name}</span>
                      {m.id === catalog?.recommendedId && (
                        <Badge className="text-lume border-lume/40">Recommended for you</Badge>
                      )}
                      <Badge className={fit.className}>{fit.label}</Badge>
                    </div>
                    <p className="text-charcoal-300 text-caption">{m.purpose}</p>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                      <p className="text-charcoal-400 text-caption min-w-0 flex-1">
                        {formatSize(m.sizeBytes)} download · needs {formatSize(m.diskNeededBytes)}{" "}
                        of free disk space · Licence:{" "}
                        <a
                          href={m.licence.url}
                          onClick={(e) => {
                            e.preventDefault();
                            void openExternal(m.licence.url);
                          }}
                          className="text-charcoal-200 underline underline-offset-2"
                        >
                          {m.licence.name}
                        </a>
                      </p>
                      {have ? (
                        <span className="text-charcoal-500 text-caption">
                          Already on this computer
                        </span>
                      ) : loading ? (
                        <span className="text-charcoal-500 text-caption">
                          Downloading — see above
                        </span>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy !== null}
                          aria-label={`Download ${m.name}`}
                          onClick={() => void run(m.id, () => store().download(m.id))}
                        >
                          Download
                        </Button>
                      )}
                    </div>
                    <RowError message={errors[m.id]} />
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

function DownloadRow({
  d,
  name,
  heldByUser,
  busy,
  error,
  onPause,
  onCancel,
  onResume,
  onDiscard,
}: {
  d: DownloadState;
  name: string;
  heldByUser: boolean;
  busy: boolean;
  error: string | undefined;
  onPause: () => void;
  onCancel: () => void;
  onResume: () => void;
  onDiscard: () => void;
}) {
  const active = IN_FLIGHT.has(d.state);
  const pct =
    d.totalBytes > 0 ? Math.min(100, Math.floor((d.receivedBytes / d.totalBytes) * 100)) : 0;
  let status: string;
  if (d.state === "verifying") status = "Checking the file…";
  else if (d.state === "queued") status = "Waiting to start…";
  else if (d.state === "downloading") {
    status = `${formatSize(d.receivedBytes)} of ${formatSize(d.totalBytes)}${
      d.bytesPerSec ? ` · ${formatSize(d.bytesPerSec)}/s` : ""
    }`;
  } else if (d.state === "failed") status = d.error ?? "The download failed.";
  else if (d.state === "cancelled") {
    status = heldByUser ? "Paused" : "Cancelled. The part already downloaded is kept.";
  } else {
    status = d.error ?? "Paused";
  }
  const canResume =
    d.state === "paused" || d.state === "cancelled" || (d.state === "failed" && d.retryable);

  return (
    <li className="flex flex-col gap-2 px-4 py-3" data-testid={`download-${d.id}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-charcoal-100 text-body min-w-0 flex-1 truncate">{name}</span>
        {active && (
          <>
            <Button
              size="sm"
              variant="outline"
              disabled={busy || d.state === "verifying"}
              onClick={onPause}
            >
              Pause
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={busy || d.state === "verifying"}
              onClick={onCancel}
            >
              Cancel
            </Button>
          </>
        )}
        {canResume && (
          <>
            <Button size="sm" variant="outline" disabled={busy} onClick={onResume}>
              Resume
            </Button>
            <ConfirmButton
              size="sm"
              variant="ghost"
              disabled={busy}
              armedLabel="Delete the partial file?"
              aria-label={`Discard ${name}`}
              onConfirm={onDiscard}
            >
              Discard
            </ConfirmButton>
          </>
        )}
      </div>
      <div
        role="progressbar"
        aria-label={`Download of ${name}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        className="bg-charcoal-850 h-1 w-full"
      >
        <div className="bg-charcoal-200 h-full" style={{ width: `${pct}%` }} />
      </div>
      <p
        className={cn("text-caption", d.state === "failed" ? "text-negative" : "text-charcoal-400")}
      >
        {pct}% · {status}
      </p>
      <RowError message={error} />
    </li>
  );
}
