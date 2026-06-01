"use client";

import { useCallback, useEffect, useRef } from "react";

import { ChatSidebar } from "@/modules/chat/ChatSidebar";
import { cn } from "@/lib/utils";
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

  if (collapsed) {
    // Fully closed — no leftover rail. The cockpit takes the full width; reopen
    // from the header "Agent" button or the agent.toggle shortcut (⌘B).
    return <div className="h-full min-h-0 w-full">{children}</div>;
  }

  return (
    <div className="flex h-full min-h-0 w-full">
      <aside
        aria-label="Agent"
        style={{
          width,
          minWidth: AGENT_DOCK_MIN_WIDTH,
          maxWidth: AGENT_DOCK_MAX_WIDTH,
        }}
        className="border-charcoal-700 h-full shrink-0 border-r"
      >
        <ChatSidebar />
      </aside>
      <div
        role="separator"
        aria-label="Resize agent column"
        aria-orientation="vertical"
        onPointerDown={startDrag}
        className={cn(
          // Widen the hit-target to ~12px via a transparent before-pseudo;
          // the visible tint stays 2px. This fixes the 4px dead-zone on the
          // drag handle that made it feel broken.
          "relative w-3 shrink-0 cursor-col-resize",
          "before:absolute before:inset-y-0 before:left-1/2 before:w-0.5 before:-translate-x-1/2",
          "before:bg-charcoal-700/0 before:transition-colors before:hover:bg-amber-500/40",
        )}
      />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
