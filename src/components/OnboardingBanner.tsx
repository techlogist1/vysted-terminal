"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, X } from "lucide-react";

import { tween } from "@/lib/motion";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * First-run onboarding banner (Phase 9.5 / Track C).
 *
 * Makes "where do I put my AI key" obvious: shown whenever no key-requiring LLM
 * provider has a key in the keychain, with a one-click jump to Settings → AI
 * Providers. It is driven by real key state (not a one-shot flag), so it
 * disappears the moment a key is saved and reappears only if every key is
 * removed. Dismissible for the session. No-op (renders null) until the first
 * keychain probe completes, so it never flashes before state is known.
 */
export function OnboardingBanner() {
  const probed = useProviderKeysStore((s) => s.probed);
  const hasAnyKey = useProviderKeysStore((s) => s.hasAnyKey());
  const refresh = useProviderKeysStore((s) => s.refresh);
  const openPanel = useWorkspaceStore((s) => s.openPanel);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const showBanner = probed && !hasAnyKey && !dismissed;

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
              agents, and research tools. Keys stay in your OS keychain; nothing leaves this
              machine.
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
              onClick={() => setDismissed(true)}
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
