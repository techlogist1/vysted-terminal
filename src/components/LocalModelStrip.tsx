"use client";

import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Check, Download, Loader2, X } from "lucide-react";

import { askAgent } from "@/components/onboarding/example";
import { downloadPercent, formatBytes, isActiveDownload, timeLeft } from "@/lib/local-models";
import { tween } from "@/lib/motion";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore } from "@/store/local-models";
import { useOnboardingStore } from "@/store/onboarding";
import type { DownloadState } from "../../types/data";

interface Action {
  label: string;
  onClick: () => void;
  primary?: boolean;
}

interface Line {
  key: string;
  icon: ReactNode;
  text: string;
  actions: Action[];
  progress?: number;
  tone?: "warn";
}

/** A download the user can pick back up: paused, failed, or stopped part-way. */
function isStalled(d: DownloadState): boolean {
  return (
    d.state === "paused" || d.state === "failed" || (d.state === "cancelled" && d.receivedBytes > 0)
  );
}

const spin = <Loader2 className="text-charcoal-300 size-4 shrink-0 animate-spin" aria-hidden />;
const warn = <AlertCircle className="text-caution size-4 shrink-0" aria-hidden />;

/**
 * The one-line on-computer model strip under the header (R16): download
 * progress, a paused/failed download, the model starting, or the model failing
 * — each with its next step. Hidden when nothing is happening.
 */
export function LocalModelStrip() {
  const engine = useLocalEngineStore((s) => s.status);
  const downloads = useLocalModelsStore((s) => s.downloads);
  const catalog = useLocalModelsStore((s) => s.catalog);
  const installed = useLocalModelsStore((s) => s.installed);
  const activeModelId = useLocalModelsStore((s) => s.activeModelId);
  const waitingQuestion = useOnboardingStore((s) => s.waitingQuestion);

  const nameOf = (id: string | null) =>
    (id &&
      (catalog?.models.find((m) => m.id === id)?.name ??
        installed.find((m) => m.id === id)?.name)) ||
    "the model";
  const models = useLocalModelsStore.getState;
  const openWizard = useOnboardingStore.getState().open;
  const quiet = (p: Promise<unknown>) => void p.catch(() => undefined);
  const retryEngine = () => {
    const id = activeModelId ?? engine.modelId;
    if (id) quiet(models().activate(id));
  };

  const list = Object.values(downloads);
  const active = list.find(isActiveDownload);
  const stalled = list.find(isStalled);
  let line: Line | null = null;

  if (engine.state === "failed") {
    line = {
      key: "failed",
      icon: warn,
      tone: "warn",
      text: `The on-computer model couldn't start. ${engine.error ?? ""}`.trim(),
      actions: [
        { label: "Try again", onClick: retryEngine, primary: true },
        { label: "Use a smaller model", onClick: () => openWizard("local") },
        { label: "Use my own key", onClick: () => openWizard("key") },
      ],
    };
  } else if (engine.state === "crashed") {
    line = {
      key: "crashed",
      icon: spin,
      text: "The on-computer model stopped unexpectedly — restarting it…",
      actions: [],
    };
  } else if (engine.state === "starting") {
    line = { key: "starting", icon: spin, text: "Starting the on-computer model…", actions: [] };
  } else if (active) {
    const pct = downloadPercent(active);
    const name = nameOf(active.id);
    const text =
      active.state === "verifying"
        ? `Checking ${name}… almost done`
        : active.state === "queued"
          ? `Starting the download of ${name}…`
          : [
              `Downloading ${name} — ${pct}%`,
              active.bytesPerSec ? `${formatBytes(active.bytesPerSec)}/s` : null,
              timeLeft(active),
            ]
              .filter(Boolean)
              .join(" · ");
    line = {
      key: "downloading",
      icon: <Download className="text-charcoal-300 size-4 shrink-0" aria-hidden />,
      text,
      progress: pct,
      actions:
        active.state === "verifying"
          ? []
          : [{ label: "Pause", onClick: () => quiet(models().cancel(active.id)) }],
    };
  } else if (stalled) {
    const pct = downloadPercent(stalled);
    const failed = stalled.state === "failed";
    const reason = stalled.error ? ` ${stalled.error.replace(/\.$/, "")}.` : "";
    line = {
      key: "stalled",
      icon: warn,
      tone: "warn",
      progress: failed ? undefined : pct,
      text: failed
        ? `The download of ${nameOf(stalled.id)} stopped.${reason}`
        : `The download of ${nameOf(stalled.id)} is paused at ${pct}%.${stalled.state === "paused" ? reason : ""}`,
      actions: [
        {
          label: failed ? "Try again" : "Resume",
          onClick: () => quiet(models().download(stalled.id)),
          primary: true,
        },
        { label: "Use my own key", onClick: () => openWizard("key") },
        { label: "Cancel download", onClick: () => quiet(models().cancel(stalled.id, true)) },
      ],
    };
  } else if (engine.state === "ready" && waitingQuestion) {
    line = {
      key: "ready",
      icon: <Check className="text-positive size-4 shrink-0" aria-hidden />,
      text: "Your on-computer model is ready.",
      actions: [
        {
          label: `Ask: “${waitingQuestion}”`,
          primary: true,
          onClick: () => {
            useOnboardingStore.getState().setWaitingQuestion(null);
            askAgent(waitingQuestion);
          },
        },
      ],
    };
  }

  return (
    <AnimatePresence initial={false}>
      {line && (
        <motion.div
          key="local-model-strip"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          style={{ overflow: "hidden" }}
          transition={tween(0.28)}
        >
          <div
            role="status"
            aria-label="On-computer model"
            data-state={line.key}
            className="bg-charcoal-925 border-charcoal-600/20 shrink-0 border-b px-4 py-2"
          >
            <div className="flex items-center gap-3">
              {line.icon}
              <p
                className={`text-caption min-w-0 flex-1 truncate font-mono leading-snug ${line.tone === "warn" ? "text-charcoal-100" : "text-charcoal-200"}`}
                title={line.text}
              >
                {line.text}
              </p>
              {line.actions.map((a) => (
                <button
                  key={a.label}
                  type="button"
                  onClick={a.onClick}
                  className={
                    a.primary
                      ? "rounded-control text-caption border-charcoal-600/40 bg-charcoal-700/10 text-charcoal-200 hover:bg-charcoal-700/20 shrink-0 border px-3 py-1 font-mono"
                      : "text-charcoal-400 hover:text-charcoal-200 text-caption rounded-control shrink-0 px-1 py-1 font-mono"
                  }
                >
                  {a.label}
                </button>
              ))}
              {line.key === "ready" && (
                <button
                  type="button"
                  aria-label="Dismiss"
                  onClick={() => useOnboardingStore.getState().setWaitingQuestion(null)}
                  className="text-charcoal-500 hover:text-charcoal-200 rounded-control shrink-0 p-1"
                >
                  <X className="size-3" aria-hidden />
                </button>
              )}
            </div>
            {line.progress !== undefined && (
              <div className="bg-charcoal-800 mt-2 h-0.5 overflow-hidden rounded-full">
                <div
                  role="progressbar"
                  aria-label="Download progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={line.progress}
                  className="h-full bg-amber-500 transition-[width]"
                  style={{ width: `${line.progress}%` }}
                />
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
