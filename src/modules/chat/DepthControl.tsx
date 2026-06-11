"use client";

import { useId, useState } from "react";
import { motion, useReducedMotion, type Transition } from "framer-motion";

import { DUR, EASE_DETENT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { RESEARCH_DEPTHS, RESEARCH_DEPTH_LABEL, type ResearchDepth } from "@/store/research-depth";

/**
 * Research-depth heat tokens (R9 law §4) — the ONE designed color family
 * beyond the accent. The composer's send fill, the stop morph, and the depth
 * selector's active stop all key to the SAME token per stop, so escalation
 * reads as heat in one tonal family: white → peach → ember.
 */
export const DEPTH_TOKEN: Record<ResearchDepth, string> = {
  normal: "var(--color-depth-normal)",
  deep: "var(--color-depth-deep)",
  ultra: "var(--color-depth-ultra)",
};

/** The next stop in the cycle (the icons-step click affordance): N → D → U → N. */
export function nextResearchDepth(depth: ResearchDepth): ResearchDepth {
  const index = RESEARCH_DEPTHS.indexOf(depth);
  return RESEARCH_DEPTHS[(index + 1) % RESEARCH_DEPTHS.length];
}

/** The thumb's slide — 180ms on the shared easing (law §5: elements that start
 *  and end on screen ride --ease-shared). */
const THUMB_TRANSITION: Transition = { duration: DUR.base, ease: EASE_DETENT };

/** The gentle live pulse on the active stop while a research run works at it. */
const PULSE_TRANSITION: Transition = { duration: 1.8, ease: "easeInOut", repeat: Infinity };

/**
 * The composer's research-depth selector (R9 Track C) — one compact segmented
 * pill, left of the model text. At rest only the ACTIVE stop label shows
 * ("Deep"), carrying its depth heat token; on hover/focus the pill expands to
 * all three stops with an animated thumb that slides under the active one
 * (180ms shared easing; reduced motion collapses every morph to an instant
 * swap). While a research run is LIVE at this depth the active label pulses
 * gently, revalued to the token. The R8 dotted rail + dot artifact is dead.
 *
 * At the ladder's icons step (`expandable={false}`) the pill renders the
 * active stop only and a click CYCLES Normal → Deep → Ultra — every stop
 * stays reachable down to the 280px dock floor.
 */
export function DepthControl({
  depth,
  onChange,
  liveDepth,
  expandable,
}: {
  depth: ResearchDepth;
  onChange: (depth: ResearchDepth) => void;
  /** The depth a LIVE research run was sent at, or null when nothing is live. */
  liveDepth: ResearchDepth | null;
  /** False at the narrow ladder step: active-stop-only, click cycles. */
  expandable: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const thumbId = useId();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const live = liveDepth !== null && liveDepth === depth;

  if (!expandable) {
    const next = nextResearchDepth(depth);
    return (
      <button
        type="button"
        aria-label={`Research depth: ${RESEARCH_DEPTH_LABEL[depth]} — switch to ${RESEARCH_DEPTH_LABEL[next]}`}
        title={`Research depth — ${RESEARCH_DEPTH_LABEL[depth]} (click to cycle Normal → Deep → Ultra)`}
        onClick={() => onChange(next)}
        className="text-caption flex h-7 shrink-0 cursor-pointer items-center px-2 font-mono"
      >
        <DepthLabel depth={depth} active live={live} reduceMotion={!!reduceMotion} />
      </button>
    );
  }

  const expanded = hovered || focused;

  return (
    <div
      role="radiogroup"
      aria-label="Research depth"
      title={`Research depth for the next run — Normal / Deep / Ultra (now: ${RESEARCH_DEPTH_LABEL[depth]})`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        // Collapse only when focus leaves the whole pill, not when it moves
        // between stops.
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setFocused(false);
        }
      }}
      className={cn(
        "rounded-control flex h-7 shrink-0 items-center font-mono transition-colors",
        expanded && "bg-charcoal-875",
      )}
    >
      {RESEARCH_DEPTHS.map((stop) => {
        const active = stop === depth;
        const hidden = !expanded && !active;
        return (
          <button
            key={stop}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={`${RESEARCH_DEPTH_LABEL[stop]} research depth`}
            aria-hidden={hidden || undefined}
            tabIndex={hidden ? -1 : 0}
            title={`${RESEARCH_DEPTH_LABEL[stop]} research depth`}
            onClick={() => onChange(stop)}
            className={cn(
              "text-caption relative h-7 cursor-pointer items-center overflow-hidden whitespace-nowrap",
              // The morph: inactive stops collapse to zero width at rest and
              // open on hover/focus. Width+padding ride the shared 180ms CSS
              // transition; reduced motion gets the duration-0 collapse below.
              hidden ? "flex w-0 px-0" : "flex w-auto px-2",
              !reduceMotion && "ease-shared transition-all duration-180",
            )}
          >
            {active && (
              <motion.span
                aria-hidden
                layoutId={`depth-thumb-${thumbId}`}
                transition={reduceMotion ? { duration: 0 } : THUMB_TRANSITION}
                className="bg-charcoal-800 rounded-control absolute inset-0"
              />
            )}
            <DepthLabel
              depth={stop}
              active={active}
              live={active && live}
              reduceMotion={!!reduceMotion}
            />
          </button>
        );
      })}
    </div>
  );
}

/** One stop label — active carries its depth heat token; live adds the pulse. */
function DepthLabel({
  depth,
  active,
  live,
  reduceMotion,
}: {
  depth: ResearchDepth;
  active: boolean;
  live: boolean;
  reduceMotion: boolean;
}) {
  return (
    <motion.span
      animate={live && !reduceMotion ? { opacity: [1, 0.5, 1] } : { opacity: 1 }}
      transition={live && !reduceMotion ? PULSE_TRANSITION : { duration: 0 }}
      style={active ? { color: DEPTH_TOKEN[depth] } : undefined}
      className={cn(
        "relative z-10 transition-colors",
        !active && "text-charcoal-500 hover:text-charcoal-200",
      )}
    >
      {RESEARCH_DEPTH_LABEL[depth]}
    </motion.span>
  );
}
