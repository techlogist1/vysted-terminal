"use client";

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, X } from "lucide-react";

import { tween } from "@/lib/motion";
import { useKeylessReadiness } from "@/lib/provider-validation";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelForProvider } from "@/store/model-selection";
import { useOnboardingStore } from "@/store/onboarding";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * First-run onboarding banner (Phase 9.5 / Track C).
 *
 * Makes "where do I put my AI key" obvious: shown only when NO model is
 * reachable — no key-requiring provider has a key AND the default lane is not a
 * keyless model that is ready (R15-UI-019: a working local-model user is never
 * told to set one up). One-click jump to Settings → AI Providers. Its dismissal
 * is durable (the onboarding store keeps it beside the "seen" marker). Renders
 * nothing until the keychain probe and the default lane's probe have answered,
 * so it never flashes before state is known.
 */
export function OnboardingBanner() {
  const probed = useProviderKeysStore((s) => s.probed);
  const hasAnyKey = useProviderKeysStore((s) => s.hasAnyKey());
  const refresh = useProviderKeysStore((s) => s.refresh);
  const dismissed = useOnboardingStore((s) => s.bannerDismissed);
  const refreshBanner = useOnboardingStore((s) => s.refreshBanner);
  const dismissBanner = useOnboardingStore((s) => s.dismissBanner);
  const openPanel = useWorkspaceStore((s) => s.openPanel);
  const defaultProvider = useLLMProvidersStore((s) => s.defaultProviderId);
  const keyless = useLLMProvidersStore(
    (s) => s.providers.find((p) => p.id === defaultProvider)?.requiresKey === false,
  );
  const model = useModelForProvider(defaultProvider);
  const readiness = useKeylessReadiness(defaultProvider, model, keyless && !hasAnyKey);

  useEffect(() => {
    void refresh();
    void refreshBanner();
  }, [refresh, refreshBanner]);

  // A keyless default must have ANSWERED "not ready"; a keyed default with no
  // key anywhere is not ready by definition.
  const defaultLaneNotReady = keyless ? readiness !== null && !readiness.ok : true;
  const showBanner = probed && dismissed === false && !hasAnyKey && defaultLaneNotReady;

  return (
    <AnimatePresence initial={false}>
      {showBanner && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          style={{ overflow: "hidden" }}
          transition={tween(0.28)}
        >
          <div
            role="status"
            className="bg-charcoal-925 border-charcoal-600/20 flex shrink-0 items-center gap-3 border-b px-4 py-2"
          >
            <Sparkles className="text-charcoal-300 size-4 shrink-0" aria-hidden="true" />
            <p className="text-charcoal-200 text-caption min-w-0 flex-1 font-mono leading-snug">
              Add a cloud provider key — or run a local model (Ollama) — to unlock the assistant,
              agents, and research tools. Keys stay in your OS keychain — market data and web
              searches still go to public providers.
            </p>
            <button
              type="button"
              onClick={() => openPanel("settings")}
              className="rounded-control text-caption border-charcoal-600/40 bg-charcoal-700/10 text-charcoal-300 hover:bg-charcoal-700/20 shrink-0 border px-3 py-1 font-mono"
            >
              Set up a provider →
            </button>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => void dismissBanner()}
              className="text-charcoal-500 hover:text-charcoal-200 rounded-control shrink-0 p-1"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
