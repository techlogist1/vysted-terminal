"use client";

import { AnimatePresence, motion } from "framer-motion";

import { SPRING_PILL, tween } from "@/lib/motion";
import { cn } from "@/lib/utils";

import { AGENT_MODES, agentModeMeta, type AgentMode } from "../../../types/agent-modes";

/**
 * The four-mode spine selector (FR-003) — Ask / Edit panel / Build / Delegate as
 * explicit, always-visible intents on stable hotkeys (⌥1–⌥4). The active mode's
 * consequence is surfaced at the point of use so agent-centrality is usable, not
 * a trap (US3). The ⌥1–⌥4 keydown handling lives in the parent agent surface so
 * the hotkeys work regardless of focus.
 */
export function ModeBar({
  mode,
  onChange,
}: {
  mode: AgentMode;
  onChange: (mode: AgentMode) => void;
}) {
  const meta = agentModeMeta(mode);
  return (
    <div className="border-charcoal-700 border-b">
      <div role="tablist" aria-label="Agent mode" className="flex items-center gap-1 px-2 pt-1.5">
        {AGENT_MODES.map((m) => {
          const active = m.id === mode;
          // Shorten "Edit panel" → "Edit" to prevent 4 tabs crowding at 320px min-dock.
          const displayLabel = m.label === "Edit panel" ? "Edit" : m.label;
          return (
            <button
              key={m.id}
              role="tab"
              type="button"
              aria-selected={active}
              title={`${m.hint} (${m.hotkeyLabel})`}
              onClick={() => onChange(m.id)}
              className={cn(
                "relative flex items-center gap-1.5 rounded-t-md px-2.5 py-1 font-mono text-[0.7rem] transition-colors",
                active
                  ? // -mb-px makes the active-tab bottom flush-connect with the border-b below,
                    // eliminating the 1px gap that made the active tab look detached.
                    "-mb-px text-amber-300"
                  : "text-charcoal-400 hover:text-charcoal-100",
              )}
            >
              {active && (
                <motion.span
                  layoutId="mode-active-pill"
                  className="bg-charcoal-800 border-charcoal-700 absolute inset-0 -z-10 rounded-t-md border border-b-transparent"
                  transition={SPRING_PILL}
                />
              )}
              {displayLabel}
              <kbd className="border-charcoal-700 text-charcoal-500 rounded border px-1 text-[0.55rem]">
                {m.hotkeyLabel}
              </kbd>
            </button>
          );
        })}
      </div>
      <AnimatePresence mode="wait">
        <motion.p
          key={mode}
          className="text-charcoal-400 px-3 py-1 font-mono text-[0.6rem]"
          aria-live="polite"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={tween(0.12)}
        >
          <span className={meta.mutates ? "text-amber-400/80" : "text-positive/80"} aria-hidden>
            ●
          </span>{" "}
          {meta.consequence}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
