"use client";

import { useCallback, useEffect, useRef } from "react";
import { PanelLeftOpen } from "lucide-react";

import { ChatSidebar } from "@/modules/chat/ChatSidebar";
import { cn } from "@/lib/utils";
import { AGENT_DOCK_MAX_WIDTH, AGENT_DOCK_MIN_WIDTH, useAgentDockStore } from "@/store/agent-dock";

/**
 * The agent's primary-column shell (FR-001) — the agent surface as a dominant,
 * resizable left column beside the dockview cockpit (passed as `children`), not
 * a bolted-on sidebar. A drag handle resizes it; the collapse control hands the
 * full cockpit back. On the P1 (existing) skin; P2 reskins this shell.
 */
export function AgentDock({ children }: { children: React.ReactNode }) {
  const collapsed = useAgentDockStore((state) => state.collapsed);
  const width = useAgentDockStore((state) => state.width);
  const setWidth = useAgentDockStore((state) => state.setWidth);
  const setCollapsed = useAgentDockStore((state) => state.setCollapsed);

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

  if (collapsed) {
    return (
      <div className="flex h-full min-h-0 w-full">
        <button
          type="button"
          aria-label="Show agent"
          title="Show agent"
          onClick={() => setCollapsed(false)}
          className="border-charcoal-700 bg-charcoal-925 text-charcoal-400 flex w-7 shrink-0 items-center justify-center border-r hover:text-amber-300"
        >
          <PanelLeftOpen size={14} aria-hidden />
        </button>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    );
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
          "bg-charcoal-700/0 w-1 shrink-0 cursor-col-resize transition-colors hover:bg-amber-500/40",
        )}
      />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
