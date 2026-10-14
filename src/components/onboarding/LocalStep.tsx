import { useEffect, useState } from "react";
import { Check, Cpu, Download, ExternalLink, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fetchLocalModelRecommendation } from "@/lib/hardware-fit";
import {
  LocalModelsError,
  downloadPercent,
  formatBytes,
  isActiveDownload,
  timeLeft,
} from "@/lib/local-models";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/app";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore, WARMING_UP } from "@/store/local-models";
import type { CatalogModel, LocalModelFit } from "../../../types/data";
import { LinkButton, Notice, StepHeader, Waiting, offline, openExternal } from "./shared";

const RETRY_MS = 5_000;

const FIT: Record<LocalModelFit, { label: string; className: string }> = {
  good: { label: "Runs well here", className: "text-positive border-positive/30" },
  tight: { label: "Tight fit here", className: "text-caution border-caution/30" },
  "too-big": { label: "Too big for this computer", className: "text-negative border-negative/30" },
};

/** The model list, with the licence shown before the download button. */
export function LocalStep({
  onBack,
  onContinue,
  onUseKey,
  onSkip,
}: {
  onBack?: () => void;
  /** Leave the step; `modelId` is the model being set up. */
  onContinue: (modelId: string) => void;
  onUseKey: () => void;
  onSkip: () => void;
}) {
  const catalog = useLocalModelsStore((s) => s.catalog);
  const hardware = useLocalModelsStore((s) => s.hardware);
  const installed = useLocalModelsStore((s) => s.installed);
  const downloads = useLocalModelsStore((s) => s.downloads);
  const loadError = useLocalModelsStore((s) => s.loadError);
  const sidecarStatus = useAppStore((s) => s.sidecarStatus);
  const engine = useLocalEngineStore((s) => s.status);
  const [picked, setPicked] = useState<string | null>(null);
  const [diskError, setDiskError] = useState<LocalModelsError | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [estimated, setEstimated] = useState(false);

  // Load quietly, and keep trying while the data engine is still starting.
  useEffect(() => {
    if (catalog) return;
    void useLocalModelsStore.getState().refresh();
    const id = setInterval(() => void useLocalModelsStore.getState().refresh(), RETRY_MS);
    return () => clearInterval(id);
  }, [catalog]);

  useEffect(() => {
    let alive = true;
    void fetchLocalModelRecommendation()
      .then((rec) => alive && setEstimated(Boolean(rec?.device.estimated)))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  if (!catalog) {
    const warming = !loadError || loadError === WARMING_UP || sidecarStatus !== "connected";
    return (
      <div className="flex flex-col gap-4 px-6 py-6">
        <StepHeader
          icon={<Cpu className="text-charcoal-300 size-4" />}
          title="On this computer"
          onBack={onBack}
        />
        {warming ? (
          <Waiting>{WARMING_UP}</Waiting>
        ) : (
          <Notice
            tone="error"
            actions={
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void useLocalModelsStore.getState().refresh()}
                >
                  Try again
                </Button>
                <LinkButton onClick={onUseKey}>Use my own key</LinkButton>
                <LinkButton onClick={onSkip}>Skip for now</LinkButton>
              </>
            }
          >
            Couldn&apos;t load the list of models. {loadError}
          </Notice>
        )}
      </div>
    );
  }

  const selectedId = picked ?? catalog.recommendedId ?? catalog.models[0]?.id ?? null;
  const model = catalog.models.find((m) => m.id === selectedId) ?? null;
  const dl = model ? downloads[model.id] : undefined;
  const stalled = Boolean(
    dl &&
    (dl.state === "failed" ||
      dl.state === "paused" ||
      (dl.state === "cancelled" && dl.receivedBytes > 0)),
  );
  const isInstalled = model ? installed.some((m) => m.id === model.id) : false;
  const extras = installed.filter((m) => !catalog.models.some((c) => c.id === m.id));
  const freeDisk = hardware?.freeDiskBytes ?? null;
  const shortOnDisk = Boolean(
    model && !isInstalled && !dl && freeDisk !== null && freeDisk < model.diskNeededBytes,
  );
  const lowRam = Boolean(
    model &&
    (catalog.tier === "under-8gb" ||
      model.fits === "tight" ||
      (hardware && hardware.availableRamBytes < model.minRamBytes)),
  );
  const smaller = model ? smallerThan(catalog.models, model, freeDisk) : null;

  const select = (id: string) => {
    setPicked(id);
    setDiskError(null);
    setStartError(null);
  };

  async function download(m: CatalogModel) {
    setBusy(true);
    setDiskError(null);
    setStartError(null);
    try {
      await useLocalModelsStore.getState().download(m.id);
    } catch (error) {
      if (error instanceof LocalModelsError && error.kind === "disk") {
        setDiskError(error);
      } else if (offline()) {
        setStartError("No internet connection.");
      } else {
        setStartError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      setBusy(false);
    }
  }

  async function use(id: string) {
    setBusy(true);
    setStartError(null);
    try {
      const status = await useLocalModelsStore.getState().activate(id);
      // A failed start shows its own notice with the next steps.
      if (status.state !== "failed") onContinue(id);
    } catch (error) {
      setStartError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  const keyOrSkip = (
    <>
      <LinkButton onClick={onUseKey}>Use my own key</LinkButton>
      <LinkButton onClick={onSkip}>Skip for now</LinkButton>
    </>
  );

  return (
    <div className="flex flex-col gap-4 px-6 py-6">
      <StepHeader
        icon={<Cpu className="text-charcoal-300 size-4" />}
        title="On this computer"
        onBack={onBack}
      />
      <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
        Pick a model to download. It runs on this computer — no key and no cost. {catalog.reason}
      </p>
      {hardware && (
        <p className="text-charcoal-400 text-caption flex flex-wrap items-center gap-x-2 font-mono">
          This computer: {formatBytes(hardware.totalRamBytes)} RAM ·{" "}
          {formatBytes(hardware.freeDiskBytes)} free space
          {estimated && (
            <span
              className="border-charcoal-700 text-charcoal-400 rounded-control border px-1 py-0.5"
              title="The memory size could not be measured — the fit labels are a best guess."
            >
              estimated
            </span>
          )}
        </p>
      )}

      <div
        role="radiogroup"
        aria-label="Models"
        className="flex max-h-64 flex-col gap-2 overflow-y-auto" /* tokens-ok: model-list scroll cap — layout */
      >
        {catalog.models.map((m) => {
          const selected = m.id === selectedId;
          const fit = FIT[m.fits];
          return (
            <div
              key={m.id}
              role="radio"
              aria-checked={selected}
              tabIndex={0}
              onClick={() => select(m.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  select(m.id);
                }
              }}
              className={cn(
                "flex cursor-pointer flex-col gap-1 rounded-none border px-4 py-3 transition-colors",
                selected
                  ? "border-charcoal-400/60 bg-charcoal-700/[0.06]"
                  : "border-charcoal-700 bg-charcoal-900 hover:border-charcoal-500/40",
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-charcoal-100 text-body font-mono">{m.name}</span>
                {m.id === catalog.recommendedId && (
                  <span className="text-micro font-mono text-amber-300">Recommended</span>
                )}
                <span
                  className={cn("text-micro ml-auto border px-2 py-0.5 font-mono", fit.className)}
                >
                  {fit.label}
                </span>
              </div>
              <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
                {m.purpose}
              </p>
              <p className="text-charcoal-500 text-caption flex flex-wrap items-center gap-x-3 font-mono">
                <span>{formatBytes(m.sizeBytes)} download</span>
                <span>needs {formatBytes(m.diskNeededBytes)} free</span>
                <a
                  href={m.licence.url}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    void openExternal(m.licence.url);
                  }}
                  className="hover:text-charcoal-200 inline-flex items-center gap-1 underline underline-offset-2"
                >
                  Licence: {m.licence.name}
                  <ExternalLink className="size-3" aria-hidden="true" />
                </a>
              </p>
            </div>
          );
        })}
      </div>

      {extras.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-caption font-mono">Already on this computer</span>
          {extras.map((m) => (
            <div key={m.id} className="flex items-center gap-2">
              <span className="text-charcoal-200 text-caption flex-1 font-mono">{m.name}</span>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => void use(m.id)}>
                Use this one
              </Button>
            </div>
          ))}
        </div>
      )}

      {model && lowRam && (
        <Notice
          tone="warn"
          testId="low-ram"
          actions={<LinkButton onClick={onUseKey}>Use my own key instead</LinkButton>}
        >
          This computer is short on free memory for {model.name}. Closing your web browser and other
          apps before you ask a question will help. Or use your own key — then the thinking happens
          online, not on this computer.
        </Notice>
      )}

      {model && (diskError || shortOnDisk) && (
        <Notice
          tone="error"
          testId="disk-short"
          actions={
            <>
              {smaller && (
                <Button size="sm" variant="outline" onClick={() => select(smaller.id)}>
                  Pick {smaller.name} ({formatBytes(smaller.diskNeededBytes)})
                </Button>
              )}
              {keyOrSkip}
            </>
          }
        >
          Not enough space on this computer. {model.name} needs{" "}
          {formatBytes(diskError?.neededBytes ?? model.diskNeededBytes)} free and there is{" "}
          {formatBytes(diskError?.freeBytes ?? freeDisk ?? 0)}. Free up space or pick a smaller
          model.
        </Notice>
      )}

      {model && dl && isActiveDownload(dl) && (
        <Notice
          testId="download-active"
          actions={
            <Button size="sm" onClick={() => onContinue(model.id)}>
              Continue →
            </Button>
          }
        >
          <span className="flex flex-col gap-2">
            <span>
              {dl.state === "verifying"
                ? "Checking the model file…"
                : `Downloading — ${downloadPercent(dl)}%${timeLeft(dl) ? ` · ${timeLeft(dl)}` : ""}`}
            </span>
            <span className="bg-charcoal-800 block h-0.5 overflow-hidden rounded-full">
              <span
                className="block h-full bg-amber-500"
                style={{ width: `${downloadPercent(dl)}%` }}
              />
            </span>
            <span className="text-charcoal-400">
              We&apos;ll finish in the background — you can keep going. The bar at the top shows
              progress.
            </span>
          </span>
        </Notice>
      )}

      {model && dl && stalled && (
        <Notice
          tone="error"
          testId="download-stopped"
          actions={
            <>
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => void download(model)}
              >
                {dl.state === "failed" ? "Try again" : "Resume"}
              </Button>
              {keyOrSkip}
            </>
          }
        >
          {dl.state === "failed"
            ? "The download stopped."
            : `The download is paused at ${downloadPercent(dl)}%.`}{" "}
          {dl.error ?? ""}
        </Notice>
      )}

      {startError && (
        <Notice tone="error" testId="start-error" actions={keyOrSkip}>
          {startError}
        </Notice>
      )}

      {model && isInstalled && engine.state === "failed" && engine.modelId === model.id && (
        <Notice
          tone="error"
          testId="engine-failed"
          actions={
            <>
              <Button size="sm" variant="outline" onClick={() => void use(model.id)}>
                Try again
              </Button>
              {smaller && (
                <LinkButton onClick={() => select(smaller.id)}>Use a smaller model</LinkButton>
              )}
              <LinkButton onClick={onUseKey}>Use my own key</LinkButton>
            </>
          }
        >
          The model couldn&apos;t start. {engine.error ?? ""}
        </Notice>
      )}

      <div className="flex items-center justify-between gap-3 pt-1">
        <LinkButton onClick={onSkip}>Skip for now</LinkButton>
        {model && isInstalled ? (
          <Button size="sm" disabled={busy} onClick={() => void use(model.id)}>
            {busy ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
            ) : (
              <Check aria-hidden="true" />
            )}
            Use {model.name}
          </Button>
        ) : model && !(dl && (isActiveDownload(dl) || stalled)) ? (
          <Button
            size="sm"
            disabled={busy || model.fits === "too-big" || shortOnDisk}
            onClick={() => void download(model)}
          >
            {busy ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
            ) : (
              <Download aria-hidden="true" />
            )}
            Download {model.name} ({formatBytes(model.sizeBytes)})
          </Button>
        ) : null}
      </div>
      {model?.fits === "too-big" && (
        <p className="text-charcoal-400 text-caption font-mono">
          {model.name} is too big for this computer — pick a smaller one.
        </p>
      )}
    </div>
  );
}

/** The largest model smaller than `model` that fits the free space and is not too big. */
function smallerThan(
  models: CatalogModel[],
  model: CatalogModel,
  freeDisk: number | null,
): CatalogModel | null {
  return (
    models
      .filter(
        (m) =>
          m.diskNeededBytes < model.diskNeededBytes &&
          m.fits !== "too-big" &&
          (freeDisk === null || m.diskNeededBytes <= freeDisk),
      )
      .sort((a, b) => b.diskNeededBytes - a.diskNeededBytes)[0] ?? null
  );
}
