"use client";

import type { FunctionComponent } from "react";

/**
 * Factory for a placeholder panel body. The Phase 1.A-2 scaffold wires every
 * module's panel to one of these; each Phase 1.B teammate then replaces the
 * `panelComponents` entry in their own module file with the real panel
 * component. Until then the panel renders this stub so the dockview layout, the
 * registry, and cmd+K are all exercised end-to-end.
 */
export function createPlaceholderPanel(title: string): FunctionComponent {
  function PlaceholderPanel() {
    return (
      <div className="bg-charcoal-900 flex h-full w-full flex-col items-center justify-center gap-2 p-8">
        <p className="text-charcoal-100 font-serif text-xl">{title}</p>
        <p className="text-charcoal-400 font-mono text-xs">Arrives in Phase 1.B</p>
      </div>
    );
  }
  PlaceholderPanel.displayName = `PlaceholderPanel(${title})`;
  return PlaceholderPanel;
}
