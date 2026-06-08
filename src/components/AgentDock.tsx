"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import { ChatSidebar } from "@/modules/chat/ChatSidebar";
import { cn } from "@/lib/utils";
import { tween } from "@/lib/motion";
import { AGENT_DOCK_MAX_WIDTH, AGENT_DOCK_MIN_WIDTH, useAgentDockStore } from "@/store/agent-dock";
import { matchesEvent, useKeybindingsStore } from "@/store/keybindings";

/**
 * The agent's primary-column shell (FR-001) — the agent surface as a dominant,
 * resizable left column beside the dockview cockpit (passed as `children`), not
 * a bolted-on sidebar. A drag handle resizes it; closing it FULLY hides the
 * column (no leftover rail — Cursor-parity) and hands the whole cockpit back,
 * reopened from the header "Agent" button or the agent.toggle shortcut (⌘B).
 */
export function AgentDock({ children }: { children: React.ReactNode }) {
  const collapsed = useAgentDockStore((state) => state.collapsed);
  const width = useAgentDockStore((state) => state.width);
  const setWidth = useAgentDockStore((state) => state.setWidth);
  const toggleCollapsed = useAgentDockStore((state) => state.toggleCollapsed);

  const draggingRef = useRef(false);
  // `dragging` (state) mirrors draggingRef so the width transition can switch to
  // instant during a drag; the ref keeps the pointermove handler closure-stable.
  const [dragging, setDragging] = useState(false);
  const reduceMotion = useReducedMotion();

  const onPointerMove = useCallback(
    (event: PointerEvent) => {
      if (!draggingRef.current) {
        return;
      }
      // The dock is the left column; its left edge is the viewport left.
      setWidth(event.clientX);
    },
    [setWidth],
  );

  const stopDrag = useCallback(() => {
    draggingRef.current = false;
    setDragging(false);
    document.body.style.removeProperty("cursor");
    document.body.style.removeProperty("user-select");
  }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDrag);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDrag);
    };
  }, [onPointerMove, stopDrag]);

  const startDrag = useCallback(() => {
    draggingRef.current = true;
    setDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  // Data-driven toggle shortcut (⌘B by default) — mirrors the command palette's
  // keybinding dispatch. Lives here on the always-mounted wrapper so it works
  // whether the dock is open or fully closed.
  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      const combo = useKeybindingsStore.getState().bindingFor("agent.toggle");
      if (combo && matchesEvent(combo, event)) {
        event.preventDefault();
        toggleCollapsed();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggleCollapsed]);

  // The dock collapses/expands by animating its width; during an interactive
  // drag-resize the transition is instant so the handle tracks the pointer
  // (animating width per drag-pixel would feel laggy). The cockpit (children)
  // always renders and reflows to fill as the dock slides.
  const dockTransition = dragging || reduceMotion ? { duration: 0 } : tween(0.26);

  return (
    <div className="flex h-full min-h-0 w-full">
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.aside
            key="agent-dock"
            aria-label="Agent"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={dockTransition}
            style={{ minWidth: 0, maxWidth: AGENT_DOCK_MAX_WIDTH, overflow: "hidden" }}
            className="bg-charcoal-900 h-full shrink-0 border-r border-r-[color:var(--hairline-strong)]"
          >
            {/* Inner fixed-width track: the content holds full width while the
                outer width animates, so the dock REVEALS/clips rather than
                squishing its contents during the slide. */}
            <div
              style={{ width, minWidth: AGENT_DOCK_MIN_WIDTH, maxWidth: AGENT_DOCK_MAX_WIDTH }}
              className="h-full"
            >
              <ChatSidebar />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
      {!collapsed && (
        <div
          role="separator"
          aria-label="Resize agent column"
          aria-orientation="vertical"
          onPointerDown={startDrag}
          className={cn(
            // Widen the hit-target to ~12px via a transparent before-pseudo; the
            // visible tint stays 2px. The splitter is painted the panel surface
            // (charcoal-900) so the dock↔cockpit gutter is one continuous field
            // with no dark seam falling through to the charcoal-950 root.
            "bg-charcoal-900 relative w-3 shrink-0 cursor-col-resize",
            "before:absolute before:inset-y-0 before:left-1/2 before:w-0.5 before:-translate-x-1/2",
            "before:bg-charcoal-700/0 before:hover:bg-charcoal-500/60 before:transition-colors",
            dragging && "before:bg-charcoal-400/80",
          )}
        />
      )}
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
