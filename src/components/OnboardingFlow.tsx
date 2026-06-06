"use client";

/**
 * First-run onboarding (Track 2) — the headline.
 *
 * A beautiful, no-sign-in first-run flow that EDUCATES and OFFERS two paths,
 * making the tradeoffs legible:
 *   - Path A (most power): paste one OpenRouter key — the recommended one-key
 *     broker for every model — guided, with rough cost shown.
 *   - Path B (private & free): set up a local model that runs entirely on this
 *     machine, fit-scored to the detected hardware, with clean Ollama-install
 *     guidance and a live download progress bar (never a frozen wait).
 *
 * The terminal WORKS KEYLESS IMMEDIATELY (keyless data + DuckDuckGo search +
 * local research), so this flow is an UPGRADE, not a gate — it is dismissible
 * ("I'll explore first") and shows exactly once (durable keychain marker via
 * {@link useOnboardingStore}). It renders AFTER the §6.5 first-launch TOS
 * (sequenced on `firstLaunchTosAcked`) so two blocking surfaces never stack.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  Check,
  Cpu,
  Download,
  ExternalLink,
  KeyRound,
  Loader2,
  Lock,
  Sparkles,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import {
  type LocalModelRecommendation,
  type OllamaStatus,
  type PullProgress,
  fetchLocalModelRecommendation,
  fetchOllamaStatus,
  pullOllamaModel,
  verdictMeta,
} from "@/lib/hardware-fit";
import { KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { tween } from "@/lib/motion";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { autosaveLayout } from "@/lib/workspace";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useOnboardingStore } from "@/store/onboarding";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useSafetyStore } from "@/store/safety";

type Step = "welcome" | "cloud" | "local" | "done";

/** The fast agentic default activated when an OpenRouter key is added (Track 1). */
const OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-v4-flash";
const OPENROUTER_KEYS_URL = "https://openrouter.ai/keys";
const OLLAMA_DOWNLOAD_URL = "https://ollama.com/download";

async function openExternal(url: string): Promise<void> {
  try {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(url);
  } catch {
    // Non-Tauri / blocked — silently no-op (the URL is also shown as text).
  }
}

async function validateKey(provider: string, apiKey: string): Promise<boolean> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL("/llm/keys/validate", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: apiKey }),
    });
    if (!resp.ok) {
      return false;
    }
    const body = (await resp.json()) as { ok: boolean };
    return Boolean(body.ok);
  } catch {
    return false;
  }
}

function formatBytes(n: number | null | undefined): string {
  if (!n || n <= 0) {
    return "";
  }
  const gb = n / 1024 ** 3;
  if (gb >= 1) {
    return `${gb.toFixed(1)} GB`;
  }
  return `${Math.round(n / 1024 ** 2)} MB`;
}

export function OnboardingFlow() {
  const tosAcked = useSafetyStore((s) => s.firstLaunchTosAcked);
  const seen = useOnboardingStore((s) => s.seen);
  const forceOpen = useOnboardingStore((s) => s.forceOpen);
  const refresh = useOnboardingStore((s) => s.refresh);
  const markSeen = useOnboardingStore((s) => s.markSeen);
  const closeForce = useOnboardingStore((s) => s.close);

  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("welcome");
  const [chosen, setChosen] = useState<"cloud" | "local" | null>(null);

  // Probe the durable "seen" marker once on mount.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Open once the TOS is acked AND this is a genuine first run (or a CTA forced
  // it). `seen === null` means "not probed yet" → wait. Local `open` decouples the
  // overlay lifetime from `seen`, so reaching the success step (which persists the
  // marker) doesn't yank the overlay before the user clicks through.
  const shouldOpen = tosAcked && (seen === false || forceOpen);
  /* eslint-disable react-hooks/set-state-in-effect */
  // Latching the local `open` from the derived gate is the intended sync (open
  // the overlay once the condition turns true); it fires only on the transition.
  useEffect(() => {
    if (shouldOpen) {
      setOpen(true);
    }
  }, [shouldOpen]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const finish = useCallback(
    async (choice: string) => {
      // Await the durable keychain write BEFORE tearing down, so a force-quit
      // immediately after dismiss can't lose the "seen" marker (it would re-show
      // once otherwise). The write is a fast IPC round-trip — imperceptible.
      await markSeen(choice);
      setOpen(false);
      closeForce();
    },
    [markSeen, closeForce],
  );

  // Any non-completion exit (skip / escape / outside-click) marks it seen so the
  // upgrade isn't re-nagged; the keyless chat CTA can always re-open it.
  const handleDismiss = useCallback(() => void finish("skip"), [finish]);

  if (!open) {
    return null;
  }

  return (
    <Dialog open onOpenChange={(value) => (value ? undefined : handleDismiss())}>
      <DialogContent
        data-testid="onboarding-flow"
        showCloseButton={false}
        // Don't let an incidental outside-pointer (e.g. the workspace-restore
        // opening a panel during boot) or a stray Escape dismiss the headline
        // before the user reads it — it only closes via its explicit buttons
        // (Skip / Add key / Set up local / Start exploring). Mirrors the §6.5 TOS.
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
        className="border-charcoal-700 bg-charcoal-950 max-w-2xl gap-0 overflow-hidden p-0"
      >
        <DialogTitle className="sr-only">Welcome to Vysted</DialogTitle>
        <DialogDescription className="sr-only">
          Set up Vysted: connect a cloud model with one key, or run a local model — or explore
          first; the terminal already works with no key.
        </DialogDescription>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={tween(0.22)}
          >
            {step === "welcome" && (
              <WelcomeStep
                onCloud={() => {
                  setChosen("cloud");
                  setStep("cloud");
                }}
                onLocal={() => {
                  setChosen("local");
                  setStep("local");
                }}
                onSkip={handleDismiss}
              />
            )}
            {step === "cloud" && (
              <CloudStep onBack={() => setStep("welcome")} onDone={() => setStep("done")} />
            )}
            {step === "local" && (
              <LocalStep
                onBack={() => setStep("welcome")}
                onCloud={() => {
                  setChosen("cloud");
                  setStep("cloud");
                }}
                onDone={() => setStep("done")}
              />
            )}
            {step === "done" && (
              <DoneStep
                choice={chosen}
                onMarkSeen={() => void markSeen(chosen ?? "seen")}
                onClose={() => void finish(chosen ?? "seen")}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  );
}

// --- Step: Welcome ----------------------------------------------------------

function WelcomeStep({
  onCloud,
  onLocal,
  onSkip,
}: {
  onCloud: () => void;
  onLocal: () => void;
  onSkip: () => void;
}) {
  return (
    <div className="flex flex-col gap-4 px-6 py-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2 rounded bg-amber-400" />
          <span className="hud-label leading-none">Welcome</span>
        </div>
        <h2 className="text-lume text-overview leading-tight font-semibold">
          An agent-native finance terminal
        </h2>
        <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
          Local-first, bring-your-own-keys, your machine. Nothing leaves this computer except the
          model calls you authorize.
        </p>
      </div>

      <div className="border-positive/25 bg-positive/5 flex items-start gap-3 rounded-none border px-4 py-3">
        <Check className="text-positive mt-1 size-4 shrink-0" aria-hidden="true" />
        <p className="text-charcoal-200 text-caption font-mono leading-relaxed">
          <span className="text-positive font-medium">It already works — no key, no account.</span>{" "}
          Live quotes, charts, news, screeners and web research run right now. Pick a path below to
          turn on the AI agent, or explore first.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <PathCard
          icon={<Zap className="size-4 text-amber-400" aria-hidden="true" />}
          title="Connect a model"
          tag="most power"
          body="Paste one OpenRouter key to unlock every top model (Claude, GPT, Gemini, DeepSeek, Kimi…) for the agent and deep research. Pay-as-you-go — a research run costs cents."
          cta="Add a key"
          onClick={onCloud}
          primary
        />
        <PathCard
          icon={<Lock className="size-4 text-amber-400" aria-hidden="true" />}
          title="Run it locally"
          tag="private & free"
          body="No key, no cost, fully private — set up a model that runs entirely on your machine. Slower and less powerful than the cloud, but it's yours and offline."
          cta="Set up local AI"
          onClick={onLocal}
        />
      </div>

      <div className="flex items-center justify-between pt-1">
        <button
          type="button"
          onClick={onSkip}
          className="text-charcoal-400 hover:text-charcoal-200 text-caption font-mono transition-colors"
        >
          Skip — I&apos;ll explore first →
        </button>
        <span className="text-charcoal-500 text-caption font-mono">
          You can change this anytime in Settings
        </span>
      </div>
    </div>
  );
}

function PathCard({
  icon,
  title,
  tag,
  body,
  cta,
  onClick,
  primary = false,
}: {
  icon: React.ReactNode;
  title: string;
  tag: string;
  body: string;
  cta: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-none border p-4 transition-colors",
        primary ? "border-amber-500/40 bg-amber-500/[0.04]" : "border-charcoal-700 bg-charcoal-900",
      )}
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-charcoal-100 text-body font-mono font-medium">{title}</span>
        <span className="text-micro text-charcoal-500 ml-auto font-mono">{tag}</span>
      </div>
      <p className="text-charcoal-400 text-caption min-h-[5.5rem] font-mono leading-relaxed">
        {body}
      </p>
      <Button
        size="sm"
        variant={primary ? "default" : "outline"}
        onClick={onClick}
        className="mt-auto w-full"
      >
        {cta} →
      </Button>
    </div>
  );
}

// --- Step: Cloud (OpenRouter key) -------------------------------------------

function CloudStep({ onBack, onDone }: { onBack: () => void; onDone: () => void }) {
  const refreshOne = useProviderKeysStore((s) => s.refreshOne);
  const [key, setKey] = useState("");
  const [status, setStatus] = useState<"idle" | "validating" | "invalid" | "error">("idle");

  async function save() {
    if (!key.trim()) {
      return;
    }
    setStatus("validating");
    const ok = await validateKey("openrouter", key.trim());
    if (!ok) {
      setStatus("invalid");
      return;
    }
    try {
      await setSecret(KEYCHAIN_NAMESPACES.llmProvider("openrouter"), key.trim());
      await refreshOne("openrouter");
      useLLMProvidersStore.getState().setDefaultProviderId("openrouter");
      useModelSelectionStore.getState().setModel("openrouter", OPENROUTER_DEFAULT_MODEL);
      void autosaveLayout();
      onDone();
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="flex flex-col gap-4 px-6 py-6">
      <StepHeader
        icon={<KeyRound className="size-4 text-amber-400" aria-hidden="true" />}
        title="Connect OpenRouter"
        onBack={onBack}
      />
      <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
        <span className="text-charcoal-100">OpenRouter is one key for every model</span> — Claude,
        GPT, Gemini, DeepSeek, Kimi and more. Create a key, add a few dollars of credit, and the
        agent + deep research light up. A typical research run costs only a few cents.
      </p>

      <button
        type="button"
        onClick={() => void openExternal(OPENROUTER_KEYS_URL)}
        className="border-charcoal-700 bg-charcoal-900 text-charcoal-200 rounded-control text-caption flex items-center gap-2 border px-3 py-2 font-mono transition-colors hover:border-amber-500/40 hover:text-amber-300"
      >
        <ExternalLink className="size-3.5" aria-hidden="true" />
        Get a key — openrouter.ai/keys
      </button>

      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <input
          type="password"
          value={key}
          autoFocus
          onChange={(e) => {
            setKey(e.target.value);
            if (status !== "idle") {
              setStatus("idle");
            }
          }}
          placeholder="sk-or-..."
          aria-label="OpenRouter API key"
          className="border-charcoal-700 bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 rounded-control text-body h-8 border px-3 font-mono outline-none focus:border-amber-400"
        />
        {status === "invalid" && (
          <p className="text-negative text-caption font-mono">
            That key wasn&apos;t accepted by OpenRouter. Check it and try again.
          </p>
        )}
        {status === "error" && (
          <p className="text-negative text-caption font-mono">
            Couldn&apos;t save the key — check your OS keychain permissions.
          </p>
        )}
        <div className="flex items-center justify-between pt-1">
          <span className="text-charcoal-500 text-caption font-mono">
            Stored in your OS keychain — never written to disk by Vysted.
          </span>
          <Button type="submit" size="sm" disabled={status === "validating" || !key.trim()}>
            {status === "validating" ? (
              <>
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> Validating…
              </>
            ) : (
              "Save & continue →"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

// --- Step: Local (Ollama) ---------------------------------------------------

function LocalStep({
  onBack,
  onCloud,
  onDone,
}: {
  onBack: () => void;
  onCloud: () => void;
  onDone: () => void;
}) {
  const [rec, setRec] = useState<LocalModelRecommendation | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [pulling, setPulling] = useState(false);
  const [progress, setProgress] = useState<PullProgress | null>(null);
  const [pullError, setPullError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    // Reset transient pull state so a re-check (daemon down→up) can't show a stale
    // "Download failed" message next to a freshly-healthy daemon.
    setPullError(null);
    setProgress(null);
    const [recResult, statusResult] = await Promise.all([
      fetchLocalModelRecommendation(),
      fetchOllamaStatus(),
    ]);
    setRec(recResult);
    setOllama(statusResult);
    setLoading(false);
  }, []);

  /* eslint-disable react-hooks/set-state-in-effect */
  // Load the hardware fit + Ollama status when the local step mounts; `load`
  // owns its own loading/data state transitions.
  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const model = rec?.recommended?.name ?? null;
  const installed = Boolean(model && ollama?.models.includes(model));

  function activate(modelName: string) {
    useLLMProvidersStore.getState().setDefaultProviderId("ollama");
    useModelSelectionStore.getState().setModel("ollama", modelName);
    void autosaveLayout();
    onDone();
  }

  async function pull(modelName: string) {
    setPulling(true);
    setPullError(null);
    setProgress({ status: "starting" });
    const controller = new AbortController();
    abortRef.current = controller;
    const result = await pullOllamaModel(modelName, {
      signal: controller.signal,
      onProgress: (p) => setProgress(p),
    });
    setPulling(false);
    if (!result.ok) {
      setPullError(result.error ?? "download failed");
      return;
    }
    activate(modelName);
  }

  return (
    <div className="flex flex-col gap-4 px-6 py-6">
      <StepHeader
        icon={<Cpu className="size-4 text-amber-400" aria-hidden="true" />}
        title="Run a local model"
        onBack={onBack}
      />

      {loading && (
        <div className="text-charcoal-400 text-caption flex items-center gap-2 py-6 font-mono">
          <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> Detecting your hardware…
        </div>
      )}

      {!loading && rec && (
        <>
          <div className="border-charcoal-700 bg-charcoal-900 flex items-center gap-3 rounded-none border px-4 py-3">
            <Cpu className="text-charcoal-400 size-4 shrink-0" aria-hidden="true" />
            <p className="text-charcoal-300 text-caption font-mono">
              <span className="text-charcoal-100">{rec.device.chip}</span> · {rec.device.ramGib} GB
              RAM · {rec.device.isAppleSilicon ? "Apple Silicon" : rec.device.arch}
            </p>
          </div>

          {!model && (
            <div className="border-warning/30 bg-warning/5 flex flex-col gap-2 rounded-none border px-4 py-3">
              <p className="text-charcoal-200 text-caption font-mono leading-relaxed">
                Your machine is tight on memory for a capable local model. The one-key cloud path
                will feel much better here — and the terminal already works keyless meanwhile.
              </p>
              <Button size="sm" variant="outline" onClick={onCloud} className="self-start">
                Use the cloud key instead →
              </Button>
            </div>
          )}

          {model && (
            <div className="flex flex-col gap-3">
              <div className="border-charcoal-700 bg-charcoal-900 flex items-center justify-between rounded-none border px-4 py-3">
                <div className="flex flex-col gap-1">
                  <span className="text-charcoal-100 text-body font-mono">{model}</span>
                  <span
                    className={cn(
                      "text-caption font-mono",
                      verdictMeta(rec.recommended!.verdict).className,
                    )}
                  >
                    {verdictMeta(rec.recommended!.verdict).label}
                    {rec.recommended!.demandGib ? ` · ~${rec.recommended!.demandGib} GB` : ""}
                  </span>
                </div>
                <span className="text-charcoal-500 text-caption max-w-[14rem] text-right font-mono leading-snug">
                  {rec.recommended!.reason}
                </span>
              </div>

              {/* State machine: not-installed daemon → install guidance; running
                  + present → use; running + absent → download with progress. */}
              {ollama && !ollama.running && (
                <div className="border-charcoal-700 bg-charcoal-900 flex flex-col gap-3 rounded-none border px-4 py-3">
                  <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
                    Local models run through <span className="text-charcoal-100">Ollama</span>, a
                    free open-source runner. Install it, start it, then come back:
                  </p>
                  <button
                    type="button"
                    onClick={() => void openExternal(OLLAMA_DOWNLOAD_URL)}
                    className="border-charcoal-700 bg-charcoal-800 text-charcoal-200 rounded-control text-caption flex items-center gap-2 self-start border px-3 py-2 font-mono transition-colors hover:border-amber-500/40 hover:text-amber-300"
                  >
                    <ExternalLink className="size-3.5" aria-hidden="true" />
                    Download Ollama — ollama.com/download
                  </button>
                  <code className="text-charcoal-400 bg-charcoal-950 border-charcoal-800 text-caption rounded-control border px-2 py-1 font-mono">
                    or: brew install ollama
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void load()}
                    className="self-start"
                  >
                    I&apos;ve installed it — re-check →
                  </Button>
                </div>
              )}

              {ollama && ollama.running && installed && (
                <Button size="sm" onClick={() => activate(model)} className="self-start">
                  <Check className="size-3.5" aria-hidden="true" /> Use {model}
                </Button>
              )}

              {ollama && ollama.running && !installed && !pulling && (
                <Button size="sm" onClick={() => void pull(model)} className="self-start">
                  <Download className="size-3.5" aria-hidden="true" /> Download &amp; use {model}
                </Button>
              )}

              {pulling && progress && (
                <div className="flex flex-col gap-2">
                  <div className="bg-charcoal-800 rounded-control h-2 w-full overflow-hidden">
                    <div
                      className="rounded-control h-full bg-amber-400 transition-all"
                      style={{
                        width:
                          progress.total && progress.completed
                            ? `${Math.min(100, Math.round((progress.completed / progress.total) * 100))}%`
                            : "8%",
                      }}
                    />
                  </div>
                  <p className="text-charcoal-400 text-caption font-mono">
                    {progress.status}
                    {progress.total && progress.completed
                      ? ` · ${formatBytes(progress.completed)} / ${formatBytes(progress.total)}`
                      : "…"}
                  </p>
                </div>
              )}

              {pullError && (
                <p className="text-negative text-caption font-mono">Download failed: {pullError}</p>
              )}
            </div>
          )}
        </>
      )}

      {!loading && !rec && (
        <p className="text-charcoal-400 text-caption font-mono">
          Couldn&apos;t reach the local engine to check your hardware. The cloud key path works
          regardless, and the terminal is usable keyless meanwhile.
        </p>
      )}
    </div>
  );
}

// --- Step: Done -------------------------------------------------------------

function DoneStep({
  choice,
  onMarkSeen,
  onClose,
}: {
  choice: "cloud" | "local" | null;
  onMarkSeen: () => void;
  onClose: () => void;
}) {
  // Persist the marker ONCE as soon as the success screen renders, so closing the
  // app from here still counts as completed. A `fired` ref guards against the
  // re-render that markSeen triggers (seen false→true) re-running the effect.
  const fired = useRef(false);
  useEffect(() => {
    if (!fired.current) {
      fired.current = true;
      onMarkSeen();
    }
  }, [onMarkSeen]);

  return (
    <div className="flex flex-col items-center gap-4 px-6 py-8 text-center">
      <div className="border-positive/30 bg-positive/10 flex size-12 items-center justify-center rounded-full border">
        <Check className="text-positive size-6" aria-hidden="true" />
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="text-lume text-section font-semibold">You&apos;re set</h2>
        <p className="text-charcoal-300 text-caption max-w-sm font-mono leading-relaxed">
          {choice === "cloud"
            ? "OpenRouter is connected — the agent and deep research are live. Ask the agent to “research NVDA” to see a visual brief land in the cockpit."
            : choice === "local"
              ? "Your local model is set — the agent runs privately on your machine. Ask it to “research NVDA” to see a visual brief land in the cockpit."
              : "You're exploring keyless — data, charts, news and web research all work. Add a model anytime from Settings to turn on the agent."}
        </p>
      </div>
      <Button size="sm" onClick={onClose} className="mt-1">
        <Sparkles className="size-3.5" aria-hidden="true" /> Start exploring
      </Button>
    </div>
  );
}

// --- shared -----------------------------------------------------------------

function StepHeader({
  icon,
  title,
  onBack,
}: {
  icon: React.ReactNode;
  title: string;
  onBack: () => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onBack}
        aria-label="Back"
        className="text-charcoal-400 hover:text-charcoal-100 rounded-control -ml-1 p-1 transition-colors"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
      </button>
      {icon}
      <h2 className="text-charcoal-100 text-section font-semibold">{title}</h2>
    </div>
  );
}
