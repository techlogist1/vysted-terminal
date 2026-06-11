"use client";

import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Cpu, RefreshCw } from "lucide-react";

import { formatModelLabel } from "@/components/StatusChrome";
import { buildModelGroups, modelOptionLabel } from "@/lib/model-options";
import { cn } from "@/lib/utils";
import { KNOWN_MODELS_BY_PROVIDER } from "@/store/model-selection";

import type { LLMModelOption, LLMProviderId, LLMProviderInfo } from "../../../types/ai";

/**
 * The composer's inline model control (R9 Track C — Claude's "Fable 5 High"
 * pattern): the model name in its designed short form as QUIET TEXT beside the
 * send button — charcoal-400, hover lume, no pill chrome. Clicking opens the
 * provider · model popover (capability pips, refresh, no-key affordance). At
 * the ladder's icons step the text collapses to a 14px icon + tooltip; the
 * popover stays identical, so nothing falls out of reach at any width.
 */

/** Anchored popover — raised surface, hairline border, opens ABOVE the row. */
function Popover({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      role="listbox"
      aria-label={label}
      className={cn(
        "border-charcoal-700 bg-charcoal-875 rounded-control absolute right-0 bottom-full z-30 mb-1 flex w-64 flex-col overflow-y-auto border py-1",
        "max-h-[min(20rem,50vh)]" /* tokens-ok: viewport scroll cap — layout, not rhythm */,
      )}
    >
      {children}
    </div>
  );
}

function PopoverHeader({ children }: { children: ReactNode }) {
  return (
    <div className="text-micro text-charcoal-500 flex items-center gap-2 px-3 py-1 tracking-wide uppercase">
      {children}
    </div>
  );
}

function PopoverRow({
  active,
  onSelect,
  label,
  hint,
}: {
  active: boolean;
  onSelect: () => void;
  label: string;
  hint?: string;
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={active}
      onClick={onSelect}
      className={cn(
        "text-caption flex w-full flex-col items-start px-3 py-1 text-left font-mono transition-colors",
        active
          ? "bg-charcoal-850 text-lume"
          : "text-charcoal-300 hover:bg-charcoal-850 hover:text-charcoal-100",
      )}
    >
      <span className="w-full truncate">{label}</span>
      {hint && <span className="text-micro text-charcoal-500 w-full truncate">{hint}</span>}
    </button>
  );
}

export interface ModelControlProps {
  providers: LLMProviderInfo[];
  provider: LLMProviderId;
  model: string;
  providerConfigured: boolean;
  modelOptions?: LLMModelOption[];
  catalogNote?: string | null;
  catalogLoading?: boolean;
  onProviderChange: (provider: LLMProviderId) => void;
  onModelChange: (model: string) => void;
  onKeyRequired?: (provider: LLMProviderId) => void;
  onRefreshModels?: () => void;
  /** Collapse-ladder density: designed full text, two-word text, or icon. */
  density: "full" | "short" | "icon";
}

export function ModelControl({
  providers,
  provider,
  model,
  providerConfigured,
  modelOptions,
  catalogNote,
  catalogLoading,
  onProviderChange,
  onModelChange,
  onKeyRequired,
  onRefreshModels,
  density,
}: ModelControlProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  // Click-outside or Escape dismisses (the house popover idiom).
  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: PointerEvent) {
      const el = rootRef.current;
      if (el && event.target instanceof Node && !el.contains(event.target)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const providerInfo = providers.find((p) => p.id === provider);
  const providerLabel = providerInfo?.label ?? provider;
  // Live catalog when present; otherwise the config-driven known list (and the
  // static map as the last resort before the sidecar is reached).
  const fallbackKnown =
    providerInfo?.knownModels && providerInfo.knownModels.length > 0
      ? providerInfo.knownModels
      : (KNOWN_MODELS_BY_PROVIDER[provider] ?? []);
  const baseOptions: LLMModelOption[] =
    modelOptions && modelOptions.length > 0
      ? modelOptions
      : fallbackKnown.map((id) => ({ id, label: id }));
  const { groups, selectedIsNoTools } = buildModelGroups(baseOptions, model);

  // The control shows the DESIGNED short form (formatter, never CSS mid-word
  // truncation); the tooltip and popover rows carry the exact ids. The SHORT
  // density drops trailing variant words ("DeepSeek V4 Flash" → "DeepSeek V4").
  const fullLabel = formatModelLabel(model);
  const text = density === "short" ? fullLabel.split(" ").slice(0, 2).join(" ") : fullLabel;
  const title = catalogNote ?? `${providerLabel} · ${model}`;

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        type="button"
        aria-label={`Model — ${providerLabel} · ${model}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={title}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "text-caption flex h-7 cursor-pointer items-center gap-1 px-1 font-mono transition-colors",
          open ? "text-lume" : "text-charcoal-400 hover:text-lume",
        )}
      >
        {density === "icon" ? (
          <Cpu
            aria-hidden
            className="size-3.5 shrink-0" /* tokens-ok: law §3 — 14px icon inside an h-7 control */
          />
        ) : (
          <span className="whitespace-nowrap">{text}</span>
        )}
        {selectedIsNoTools && (
          <span
            className="text-warning shrink-0"
            title="This model has no tool-calling — agent host-actions will fail. Pick a tool-capable model."
          >
            ⚠
          </span>
        )}
        {!providerConfigured && density !== "icon" && (
          <span className="text-warning shrink-0" title="No BYOK key configured">
            no key
          </span>
        )}
      </button>
      {open && (
        <Popover label="Provider and model">
          <PopoverHeader>
            <span className="min-w-0 flex-1 truncate">Provider</span>
            {onRefreshModels && (
              <button
                type="button"
                onClick={onRefreshModels}
                title={catalogNote ?? "Refresh model list"}
                aria-label="Refresh model list"
                className="text-charcoal-500 hover:text-charcoal-200 rounded-control shrink-0 cursor-pointer transition-colors"
              >
                <RefreshCw className={cn("size-3", catalogLoading && "animate-spin")} />
              </button>
            )}
          </PopoverHeader>
          {providers.map((p) => (
            <PopoverRow
              key={p.id}
              active={p.id === provider}
              label={p.label}
              onSelect={() => onProviderChange(p.id)}
            />
          ))}
          {!providerConfigured && (
            <button
              type="button"
              onClick={() => {
                onKeyRequired?.(provider);
                setOpen(false);
              }}
              className="text-warning text-caption hover:text-charcoal-100 w-full cursor-pointer px-3 py-1 text-left font-mono transition-colors"
              title="No BYOK key configured for this provider — click to add"
            >
              no key for {providerLabel} — add one
            </button>
          )}
          <PopoverHeader>Model</PopoverHeader>
          {groups.map((group, index) => (
            <Fragment key={group.label ?? `flat-${index}`}>
              {group.label && <PopoverHeader>{group.label}</PopoverHeader>}
              {group.options.map((option) => (
                <PopoverRow
                  key={option.id}
                  active={option.id === model}
                  label={modelOptionLabel(option)}
                  onSelect={() => {
                    onModelChange(option.id);
                    setOpen(false);
                  }}
                />
              ))}
            </Fragment>
          ))}
          {selectedIsNoTools && (
            <div className="text-warning text-micro px-3 py-1">
              ⚠ no tools — agent host-actions will fail on this model
            </div>
          )}
        </Popover>
      )}
    </div>
  );
}
