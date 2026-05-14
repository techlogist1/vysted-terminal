"use client";

import type { FunctionComponent } from "react";

import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { useModulesStore } from "@/store/modules";

/**
 * Settings panel — the per-module enable/disable list.
 *
 * Renders every registered module with a toggle that drives
 * `useModulesStore.setModuleEnabled`. Disabling a module drops its panels and
 * cmd+K commands (the registry handles that; the toggle↔palette refresh is wired
 * in `page.tsx`). The `platform` module's toggle is locked on — Settings is the
 * only way to re-enable a module, so disabling the module that hosts it would
 * be a dead end.
 *
 * Wired into the platform module as `panelComponents["settings-panel"]`.
 */
export const SettingsPanel: FunctionComponent = () => {
  // Subscribing to the whole store keeps the list live: toggling one module
  // re-renders every row (so a future "X of N enabled" summary stays correct).
  const modules = useModulesStore((state) => state.modules);
  const enabled = useModulesStore((state) => state.enabled);
  const setModuleEnabled = useModulesStore((state) => state.setModuleEnabled);

  return (
    <div className="bg-charcoal-900 h-full w-full overflow-y-auto p-6">
      <header className="mb-4">
        <h2 className="text-charcoal-100 font-serif text-xl">Modules</h2>
        <p className="text-charcoal-400 mt-1 font-mono text-xs">
          Enable or disable modules. Disabled modules contribute no panels or commands.
        </p>
      </header>
      <ul className="flex flex-col gap-1.5">
        {modules.map((module) => {
          const isPlatform = module.id === PLATFORM_MODULE_ID;
          const isEnabled = enabled[module.id] !== false;
          return (
            <li
              key={module.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-md border px-4 py-3"
            >
              <div className="flex flex-col">
                <span className="text-charcoal-100 font-mono text-sm">{module.title}</span>
                <span className="text-charcoal-400 font-mono text-xs">
                  {module.panels.length} panel{module.panels.length === 1 ? "" : "s"} ·{" "}
                  {module.commands.length} command{module.commands.length === 1 ? "" : "s"}
                  {isPlatform ? " · always on" : ""}
                </span>
              </div>
              <label className="flex items-center gap-2">
                <span className="sr-only">
                  {isEnabled ? "Disable" : "Enable"} {module.title}
                </span>
                <input
                  type="checkbox"
                  role="switch"
                  aria-label={`${module.title} enabled`}
                  checked={isEnabled}
                  disabled={isPlatform}
                  onChange={(event) => {
                    // The platform module hosts Settings itself, so it must
                    // never be disableable — guard here as well as via the
                    // `disabled` attribute.
                    if (isPlatform) {
                      return;
                    }
                    setModuleEnabled(module.id, event.target.checked);
                  }}
                  className="size-4 accent-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
                />
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

SettingsPanel.displayName = "SettingsPanel";
