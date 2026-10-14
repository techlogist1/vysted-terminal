"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Download, X } from "lucide-react";

import { tween } from "@/lib/motion";
import {
  checkForUpdate,
  hasActiveModelDownload,
  installUpdate,
  type UpdateInfo,
  type UpdateProgress,
} from "@/lib/updater";

export const FIRST_CHECK_MS = 15_000;
export const RECHECK_MS = 6 * 60 * 60 * 1000;
export const DOWNLOAD_POLL_MS = 5_000;

function progressLabel(p: UpdateProgress | null): string {
  if (!p) return "Preparing update…";
  if (p.total)
    return `Downloading update… ${Math.min(100, Math.round((p.downloaded / p.total) * 100))}%`;
  return `Downloading update… ${(p.downloaded / 1_048_576).toFixed(1)} MB`;
}

/**
 * Self-update strip (R16). Checks 15 s after boot and every 6 h; quiet when there
 * is nothing (offline, no release, 404). Never interrupts a model download: while
 * one is active the install waits and starts on its own once it ends.
 */
export function UpdatePrompt() {
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [notesOpen, setNotesOpen] = useState(false);
  const [downloadActive, setDownloadActive] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [progress, setProgress] = useState<UpdateProgress | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const check = () =>
      void checkForUpdate().then((next) => {
        if (next.available) setInfo(next);
      });
    const first = setTimeout(check, FIRST_CHECK_MS);
    const every = setInterval(check, RECHECK_MS);
    return () => {
      clearTimeout(first);
      clearInterval(every);
    };
  }, []);

  const install = useCallback(() => {
    setWaiting(false);
    setFailed(false);
    setInstalling(true);
    setProgress(null);
    installUpdate(setProgress).catch(() => {
      setInstalling(false);
      setFailed(true);
    });
  }, []);

  const visible = info !== null;
  useEffect(() => {
    if (!visible || installing) return;
    let alive = true;
    const poll = () =>
      void hasActiveModelDownload().then((active) => {
        if (!alive) return;
        setDownloadActive(active);
        if (waiting && !active) install();
      });
    poll();
    const id = setInterval(poll, DOWNLOAD_POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [visible, installing, waiting, install]);

  const onPrimary = () => (downloadActive ? setWaiting(true) : install());
  const later = () => {
    setInfo(null);
    setWaiting(false);
    setNotesOpen(false);
  };

  return (
    <AnimatePresence initial={false}>
      {info && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          style={{ overflow: "hidden" }}
          transition={tween(0.28)}
        >
          <div
            role="status"
            aria-label="App update"
            className="bg-charcoal-925 border-charcoal-600/20 shrink-0 border-b px-4 py-2"
          >
            <div className="flex items-center gap-3">
              <Download className="text-charcoal-300 size-4 shrink-0" aria-hidden="true" />
              <p className="text-charcoal-200 text-caption min-w-0 flex-1 font-mono leading-snug">
                {installing
                  ? progressLabel(progress)
                  : failed
                    ? "The update could not be installed. Check your connection and try again."
                    : `Vysted Terminal ${info.version ?? ""} is available.`}
              </p>
              {info.notes && !installing && (
                <button
                  type="button"
                  aria-expanded={notesOpen}
                  onClick={() => setNotesOpen((o) => !o)}
                  className="text-charcoal-400 hover:text-charcoal-200 text-caption rounded-control flex shrink-0 items-center gap-1 font-mono"
                >
                  What&apos;s new
                  <ChevronDown
                    className={`size-3.5 transition-transform ${notesOpen ? "rotate-180" : ""}`}
                    aria-hidden="true"
                  />
                </button>
              )}
              {!installing && (
                <>
                  <button
                    type="button"
                    disabled={waiting}
                    onClick={onPrimary}
                    className="rounded-control text-caption border-charcoal-600/40 bg-charcoal-700/10 text-charcoal-300 hover:bg-charcoal-700/20 shrink-0 border px-3 py-1 font-mono disabled:opacity-60"
                  >
                    {waiting
                      ? "Updating after the download finishes…"
                      : downloadActive
                        ? "Update after the download finishes"
                        : "Restart to update"}
                  </button>
                  <button
                    type="button"
                    onClick={later}
                    className="text-charcoal-500 hover:text-charcoal-200 text-caption rounded-control flex shrink-0 items-center gap-1 px-1 py-1 font-mono"
                  >
                    Later
                    <X className="size-3.5" aria-hidden="true" />
                  </button>
                </>
              )}
            </div>
            {installing && (
              <div className="bg-charcoal-800 mt-2 h-0.5 overflow-hidden rounded-full">
                <div
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={
                    progress?.total
                      ? Math.round((progress.downloaded / progress.total) * 100)
                      : undefined
                  }
                  className="h-full bg-amber-500 transition-[width]"
                  style={{
                    width: progress?.total
                      ? `${Math.min(100, (progress.downloaded / progress.total) * 100)}%`
                      : "100%",
                  }}
                />
              </div>
            )}
            {notesOpen && info.notes && !installing && (
              <p className="text-charcoal-400 text-caption mt-2 max-h-40 overflow-y-auto font-mono leading-snug whitespace-pre-wrap">
                {info.notes}
              </p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
