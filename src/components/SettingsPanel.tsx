"use client";

import { type FunctionComponent, useEffect, useState } from "react";
import { Check, KeyRound, Layers, Plug, Settings2, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { deleteSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { HOST_VERSION } from "@/lib/plugin-bootstrap";
import {
  deleteWorkspace,
  listWorkspaces,
  loadWorkspace,
  saveWorkspace,
  WorkspaceError,
} from "@/lib/workspace";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModulesStore } from "@/store/modules";
import { useProviderKeysStore } from "@/store/provider-keys";
import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";
import type { LLMProviderId } from "../../types/ai";

/**
 * Settings — the discoverable control surface (Phase 9.5 / Track C).
 *
 * Four sections:
 *  - AI Providers (BYOK): the "where do I put my key" surface. Every provider
 *    shows its key status from the OS keychain with add / update / remove, plus
 *    a default-provider picker. This is what first-run onboarding points to.
 *  - Layouts: save / restore / delete named cockpits + reset to the default.
 *  - Modules: enable / disable registered modules.
 *  - About: the open / local-first / BYOK positioning + version.
 *
 * Opened from the toolbar gear, the `platform.open-settings` command, or the
 * onboarding banner. Wired into the platform module as
 * `panelComponents["settings-panel"]`.
 */
export const SettingsPanel: FunctionComponent = () => {
  return (
    <div className="bg-charcoal-900 h-full w-full overflow-y-auto">
      <div className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
        <header>
          <h1 className="text-charcoal-100 flex items-center gap-2 font-serif text-2xl">
            <Settings2 className="size-5 text-amber-400" aria-hidden="true" />
            Settings
          </h1>
          <p className="text-charcoal-400 mt-1 font-mono text-xs">
            Local-first &amp; bring-your-own-keys. Nothing leaves this machine except calls you make
            to providers you configure.
          </p>
        </header>
        <ProvidersSection />
        <LayoutsSection />
        <ModulesSection />
        <AboutSection />
      </div>
    </div>
  );
};

SettingsPanel.displayName = "SettingsPanel";

// ---------------------------------------------------------------------------
// AI Providers (BYOK)
// ---------------------------------------------------------------------------

function ProvidersSection() {
  const providers = useLLMProvidersStore((s) => s.providers);
  const defaultProviderId = useLLMProvidersStore((s) => s.defaultProviderId);
  const setDefaultProviderId = useLLMProvidersStore((s) => s.setDefaultProviderId);
  const status = useProviderKeysStore((s) => s.status);
  const refresh = useProviderKeysStore((s) => s.refresh);
  const refreshOne = useProviderKeysStore((s) => s.refreshOne);

  const [dialogProvider, setDialogProvider] = useState<LLMProviderId | null>(null);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleRemove(id: LLMProviderId) {
    await deleteSecret(KEYCHAIN_NAMESPACES.llmProvider(id));
    await refreshOne(id);
  }

  return (
    <section aria-labelledby="settings-providers">
      <SectionHeader
        id="settings-providers"
        icon={<Plug className="size-4 text-amber-400" aria-hidden="true" />}
        title="AI Providers"
        hint="Paste an API key to enable an AI provider. Keys are stored in your OS keychain — never on disk or sent anywhere but the provider you call."
      />
      <ul className="flex flex-col gap-1.5">
        {providers.map((provider) => {
          const keyState = status[provider.id] ?? "missing";
          const configured = keyState === "configured";
          const isDefault = defaultProviderId === provider.id;
          const needsKey = provider.requiresKey;
          return (
            <li
              key={provider.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-md border px-4 py-3"
            >
              <div className="flex min-w-0 flex-col">
                <span className="text-charcoal-100 flex items-center gap-2 font-mono text-sm">
                  {provider.label}
                  {isDefault && (
                    <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-amber-400 uppercase">
                      default
                    </span>
                  )}
                </span>
                <span className="mt-0.5 flex items-center gap-1.5 font-mono text-xs">
                  {!needsKey ? (
                    <span className="text-charcoal-400">No key required (local)</span>
                  ) : configured ? (
                    <span className="text-positive flex items-center gap-1">
                      <Check className="size-3" aria-hidden="true" /> Key configured
                    </span>
                  ) : (
                    <span className="text-charcoal-400">No key yet</span>
                  )}
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                {(configured || !needsKey) && !isDefault && (
                  <button
                    type="button"
                    onClick={() => setDefaultProviderId(provider.id)}
                    className="text-charcoal-400 hover:text-charcoal-100 font-mono text-[11px] uppercase"
                  >
                    Set default
                  </button>
                )}
                {needsKey && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setDialogProvider(provider.id)}
                    >
                      <KeyRound className="size-3" aria-hidden="true" />
                      {configured ? "Update key" : "Add key"}
                    </Button>
                    {configured && (
                      <button
                        type="button"
                        aria-label={`Remove ${provider.label} key`}
                        onClick={() => void handleRemove(provider.id)}
                        className="text-charcoal-400 rounded p-1.5 hover:text-red-400"
                      >
                        <Trash2 className="size-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      <KeyEntryDialog
        open={dialogProvider !== null}
        providerId={dialogProvider}
        onOpenChange={(next) => {
          if (!next) setDialogProvider(null);
        }}
        onSaved={(id) => void refreshOne(id)}
      />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Layouts
// ---------------------------------------------------------------------------

function LayoutsSection() {
  const [names, setNames] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState("");
  const activeName = useWorkspaceStore((s) => s.name);
  const resetLayout = useWorkspaceStore((s) => s.resetToDefaultLayout);

  async function reload() {
    try {
      const all = await listWorkspaces();
      setNames(all.filter((n) => !isReservedLayoutName(n)).sort());
      setError(null);
    } catch (caught) {
      setError(caught instanceof WorkspaceError ? caught.message : "Could not list layouts.");
      setNames([]);
    }
  }

  useEffect(() => {
    // `reload` only sets state after the awaited listWorkspaces() resolves —
    // never synchronously within the effect — so the cascading-render concern
    // the rule guards against does not apply (same pattern as PortfolioPanel).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, []);

  async function withBusy(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (caught) {
      setError(caught instanceof WorkspaceError ? caught.message : "Layout operation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="settings-layouts">
      <SectionHeader
        id="settings-layouts"
        icon={<Layers className="size-4 text-amber-400" aria-hidden="true" />}
        title="Layouts"
        hint="Drag tabs to dock, split, or rearrange any panel into your own cockpit, then save it. Your last layout is restored automatically on launch."
      />
      <form
        className="mb-2 flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const name = newName.trim();
          if (!name) return;
          void withBusy(async () => {
            await saveWorkspace(name);
            setNewName("");
            await reload();
          });
        }}
      >
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Save current layout as…"
          aria-label="New layout name"
          className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-400 h-8 flex-1 rounded-md border px-3 font-mono text-xs outline-none focus:border-amber-400"
        />
        <Button type="submit" size="sm" variant="outline" disabled={busy || newName.trim() === ""}>
          Save
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => void resetLayout()}>
          Reset to default
        </Button>
      </form>
      {error && <p className="mb-2 font-mono text-xs text-red-400">{error}</p>}
      {names === null ? (
        <p className="text-charcoal-400 font-mono text-xs">Loading layouts…</p>
      ) : names.length === 0 ? (
        <p className="text-charcoal-400 font-mono text-xs">
          No saved layouts yet — arrange your panels and save above.
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {names.map((name) => (
            <li
              key={name}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-md border px-3 py-2"
            >
              <span className="text-charcoal-100 truncate font-mono text-xs">
                {name}
                {name === activeName && (
                  <span className="text-charcoal-500 ml-2 text-[10px] uppercase">active</span>
                )}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => void withBusy(() => loadWorkspace(name))}
                  className="text-charcoal-300 font-mono text-[11px] uppercase hover:text-amber-400"
                >
                  Load
                </button>
                <button
                  type="button"
                  aria-label={`Delete layout ${name}`}
                  onClick={() =>
                    void withBusy(async () => {
                      await deleteWorkspace(name);
                      await reload();
                    })
                  }
                  className="text-charcoal-400 rounded p-1 hover:text-red-400"
                >
                  <X className="size-3.5" aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="text-charcoal-500 mt-2 font-mono text-[10px]">
        Autosave slot: {AUTOSAVE_LAYOUT_NAME} (hidden; restored on launch)
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

function ModulesSection() {
  const modules = useModulesStore((state) => state.modules);
  const enabled = useModulesStore((state) => state.enabled);
  const setModuleEnabled = useModulesStore((state) => state.setModuleEnabled);

  return (
    <section aria-labelledby="settings-modules">
      <SectionHeader
        id="settings-modules"
        icon={<Layers className="size-4 text-amber-400" aria-hidden="true" />}
        title="Modules"
        hint="Disabled modules contribute no panels or ⌘K commands."
      />
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
                    if (isPlatform) return;
                    setModuleEnabled(module.id, event.target.checked);
                  }}
                  className="size-4 accent-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
                />
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// About
// ---------------------------------------------------------------------------

function AboutSection() {
  return (
    <section aria-labelledby="settings-about" className="pb-4">
      <SectionHeader
        id="settings-about"
        icon={<Settings2 className="size-4 text-amber-400" aria-hidden="true" />}
        title="About"
      />
      <div className="border-charcoal-700 bg-charcoal-850 text-charcoal-300 flex flex-col gap-1.5 rounded-md border px-4 py-3 font-mono text-xs">
        <p>
          Vysted Terminal <span className="text-charcoal-500">v{HOST_VERSION}</span> — an
          open-source, AI-native finance terminal.
        </p>
        <p className="text-charcoal-400">
          Plugin architecture · local-first · bring-your-own-keys. Your data, your keys, your
          machine — extend it like an IDE.
        </p>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function SectionHeader({
  id,
  icon,
  title,
  hint,
}: {
  id: string;
  icon: React.ReactNode;
  title: string;
  hint?: string;
}) {
  return (
    <header className="mb-3">
      <h2 id={id} className="text-charcoal-100 flex items-center gap-2 font-serif text-lg">
        {icon}
        {title}
      </h2>
      {hint && <p className="text-charcoal-400 mt-1 font-mono text-xs">{hint}</p>}
    </header>
  );
}
