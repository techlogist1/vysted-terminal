"use client";

import { Fragment, type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";

import { buildModelGroups, modelOptionLabel } from "@/lib/model-options";
import { cn } from "@/lib/utils";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { KNOWN_MODELS_BY_PROVIDER } from "@/store/model-selection";
import { RESEARCH_DEPTHS, RESEARCH_DEPTH_LABEL, type ResearchDepth } from "@/store/research-depth";

import type { LLMModelOption, LLMProviderId, LLMProviderInfo } from "../../../types/ai";
import { type AgentMode, AGENT_MODES } from "../../../types/agent-modes";

/**
 * The composer's ONE quiet 24px meta row (R7 Track C) — every standing select
 * row the old composer stacked above the field collapses into compact chips:
 *
 *   [mode chip] [lens chip] [depth slider] ··· [autonomy] [model chip]
 *
 * Mode / lens / model chips each open a SINGLE anchored popover (raised
 * surface + hairline border, one open at a time) holding the options the old
 * `<select>` rows carried — including the model catalog's capability pips
 * (`· no tools`, `· ⌕`) and the refresh affordance. The lens chip ALWAYS
 * shows the agent's display name, never a raw id. The depth slider is the
 * three-stop dotted rail; its active stop carries the peach accent ONLY while
 * a research run is live at that depth (live agent activity is the one accent
 * role), otherwise text-bright. Autonomy stays the law's 24px segmented
 * ASK/AUTO toggle. Everything here is `text-micro`, tertiary at rest.
 */

type PopoverKey = "mode" | "lens" | "model";

/** Shared 24px chip — quiet tertiary text that brightens on hover/open. */
function MetaChip({
  label,
  open,
  onClick,
  title,
  children,
}: {
  label: string;
  open: boolean;
  onClick: () => void;
  title?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-haspopup="listbox"
      aria-expanded={open}
      title={title ?? label}
      onClick={onClick}
      className={cn(
        "rounded-control text-micro flex h-6 min-w-0 shrink items-center gap-1 px-1 font-mono tracking-wide uppercase transition-colors",
        open ? "bg-charcoal-875 text-charcoal-200" : "text-charcoal-500 hover:text-charcoal-300",
      )}
    >
      {children}
    </button>
  );
}

/** The anchored popover — raised surface, hairline border, opens ABOVE the row. */
function Popover({
  align,
  label,
  children,
}: {
  align: "left" | "right";
  label: string;
  children: ReactNode;
}) {
  return (
    <div
      role="listbox"
      aria-label={label}
      className={cn(
        "border-charcoal-700 bg-charcoal-875 rounded-control absolute bottom-full z-30 mb-1 flex max-h-[min(20rem,50vh)] w-64 flex-col overflow-y-auto border py-1",
        align === "right" ? "right-0" : "left-0",
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

/**
 * The three-stop depth slider — three dots on a thin dotted rail. The ACTIVE
 * stop's dot + label read text-bright at rest and take the accent ONLY while a
 * research run is live at that depth (`liveDepth`).
 */
function DepthSlider({
  depth,
  onChange,
  liveDepth,
}: {
  depth: ResearchDepth;
  onChange: (depth: ResearchDepth) => void;
  liveDepth: ResearchDepth | null;
}) {
  const live = liveDepth !== null && liveDepth === depth;
  return (
    <div
      role="radiogroup"
      aria-label="Research depth"
      title="Research depth for the next run — Normal / Deep / Ultra"
      className="flex h-6 shrink-0 items-center px-1"
    >
      {RESEARCH_DEPTHS.map((stop, i) => {
        const active = stop === depth;
        return (
          <Fragment key={stop}>
            {i > 0 && (
              <span aria-hidden className="border-charcoal-600 w-3 border-t border-dotted" />
            )}
            <button
              type="button"
              role="radio"
              aria-checked={active}
              aria-label={`${RESEARCH_DEPTH_LABEL[stop]} research depth`}
              title={RESEARCH_DEPTH_LABEL[stop]}
              onClick={() => onChange(stop)}
              className="group flex h-6 items-center justify-center px-0.5"
            >
              <span
                aria-hidden
                className={cn(
                  "size-1.5 rounded-full transition-colors",
                  active && live
                    ? "bg-amber-400"
                    : active
                      ? "bg-lume"
                      : "bg-charcoal-600 group-hover:bg-charcoal-400",
                )}
              />
            </button>
          </Fragment>
        );
      })}
      <span
        className={cn(
          "text-micro ml-1 tracking-wide uppercase",
          live ? "text-amber-400" : "text-lume",
        )}
      >
        {RESEARCH_DEPTH_LABEL[depth]}
      </span>
    </div>
  );
}

/** The law's 24px segmented ASK/AUTO toggle — one bordered unit, divided. */
function AutonomySegments() {
  const autonomy = useAgentAutonomyStore((state) => state.autonomy);
  const setAutonomy = useAgentAutonomyStore((state) => state.setAutonomy);
  return (
    <div
      role="radiogroup"
      aria-label="Agent autonomy"
      title={
        autonomy === "auto"
          ? "Auto-apply: UI / layout / chart / watchlist changes apply without a per-action confirmation. Orders ALWAYS route through the confirm-before-place dialog."
          : "Ask: every proposed change waits for your accept in the diff gate."
      }
      className="border-charcoal-700 divide-charcoal-700 rounded-control flex h-6 shrink-0 items-stretch divide-x overflow-hidden border font-mono"
    >
      {(["ask", "auto"] as const).map((level) => (
        <button
          key={level}
          type="button"
          role="radio"
          aria-checked={autonomy === level}
          onClick={() => setAutonomy(level)}
          className={cn(
            "text-micro flex items-center px-2 tracking-wide uppercase transition-colors",
            autonomy === level
              ? "bg-charcoal-875 text-lume"
              : "text-charcoal-500 hover:text-charcoal-300",
          )}
        >
          {level}
        </button>
      ))}
    </div>
  );
}

export interface ComposerMetaRowProps {
  mode: AgentMode;
  onModeChange: (mode: AgentMode) => void;
  /** The lens chip text — ALWAYS a display name, never a raw agent id. */
  lensLabel: string;
  firstParty: readonly { id: string; name: string }[];
  custom: readonly { id: string; name: string }[];
  activeAgentId: string;
  onLensChange: (id: string) => void;
  depth: ResearchDepth;
  onDepthChange: (depth: ResearchDepth) => void;
  /** The depth a LIVE research run was sent at, or null when nothing is live. */
  liveDepth: ResearchDepth | null;
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
}

export function ComposerMetaRow({
  mode,
  onModeChange,
  lensLabel,
  firstParty,
  custom,
  activeAgentId,
  onLensChange,
  depth,
  onDepthChange,
  liveDepth,
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
}: ComposerMetaRowProps) {
  const [open, setOpen] = useState<PopoverKey | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const toggle = useCallback(
    (key: PopoverKey) => setOpen((current) => (current === key ? null : key)),
    [],
  );

  // One popover at a time; click-outside or Escape dismisses.
  useEffect(() => {
    if (open === null) {
      return;
    }
    function onPointerDown(event: PointerEvent) {
      const el = containerRef.current;
      if (el && event.target instanceof Node && !el.contains(event.target)) {
        setOpen(null);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(null);
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
  // static map as the last resort before the sidecar is reached) — the same
  // fallback ladder the old AgentHud used.
  const fallbackKnown =
    providerInfo?.knownModels && providerInfo.knownModels.length > 0
      ? providerInfo.knownModels
      : (KNOWN_MODELS_BY_PROVIDER[provider] ?? []);
  const baseOptions: LLMModelOption[] =
    modelOptions && modelOptions.length > 0
      ? modelOptions
      : fallbackKnown.map((id) => ({ id, label: id }));
  const { groups, selectedIsNoTools } = buildModelGroups(baseOptions, model);

  const ordered = [...firstParty].sort((a, b) =>
    a.id === "copilot" ? -1 : b.id === "copilot" ? 1 : 0,
  );
  const activeMode = AGENT_MODES.find((m) => m.id === mode);

  return (
    <div ref={containerRef} className="mb-2 flex h-6 items-center gap-1 px-3 font-mono">
      {/* Mode chip → Agent | Delegate popover */}
      <div className="relative shrink-0">
        <MetaChip
          label={`Agent mode — ${activeMode?.label ?? mode}`}
          title={activeMode?.hint}
          open={open === "mode"}
          onClick={() => toggle("mode")}
        >
          <span className="truncate">{activeMode?.label ?? mode}</span>
        </MetaChip>
        {open === "mode" && (
          <Popover align="left" label="Agent mode">
            {AGENT_MODES.map((m) => (
              <PopoverRow
                key={m.id}
                active={m.id === mode}
                label={`${m.label} (${m.hotkeyLabel})`}
                hint={m.hint}
                onSelect={() => {
                  onModeChange(m.id);
                  setOpen(null);
                }}
              />
            ))}
          </Popover>
        )}
      </div>

      {/* Lens chip → persona roster popover. ALWAYS the display name. */}
      <div className="relative min-w-0 shrink">
        <MetaChip
          label={`Active lens — ${lensLabel}`}
          title={`Lens: ${lensLabel}`}
          open={open === "lens"}
          onClick={() => toggle("lens")}
        >
          <span className="max-w-[9rem] truncate">{lensLabel}</span>
        </MetaChip>
        {open === "lens" && (
          <Popover align="left" label="Active lens">
            <PopoverHeader>First-party</PopoverHeader>
            {ordered.map((agent) => (
              <PopoverRow
                key={agent.id}
                active={agent.id === activeAgentId}
                label={agent.name}
                onSelect={() => {
                  onLensChange(agent.id);
                  setOpen(null);
                }}
              />
            ))}
            {custom.length > 0 && (
              <>
                <PopoverHeader>Custom</PopoverHeader>
                {custom.map((agent) => (
                  <PopoverRow
                    key={agent.id}
                    active={agent.id === activeAgentId}
                    label={agent.name}
                    onSelect={() => {
                      onLensChange(agent.id);
                      setOpen(null);
                    }}
                  />
                ))}
              </>
            )}
          </Popover>
        )}
      </div>

      <DepthSlider depth={depth} onChange={onDepthChange} liveDepth={liveDepth} />

      <div className="min-w-0 flex-1" />

      <AutonomySegments />

      {/* Model chip → provider · model popover (capability pips + refresh). */}
      <div className="relative min-w-0 shrink-0">
        <MetaChip
          label={`Model — ${providerLabel} · ${model}`}
          title={catalogNote ?? `${providerLabel} · ${model}`}
          open={open === "model"}
          onClick={() => toggle("model")}
        >
          <span className="max-w-[13rem] truncate normal-case">
            {providerLabel} · {model}
          </span>
          {selectedIsNoTools && (
            <span
              className="text-warning shrink-0 normal-case"
              title="This model has no tool-calling — agent host-actions will fail. Pick a tool-capable model."
            >
              ⚠
            </span>
          )}
          {!providerConfigured && (
            <span className="text-warning shrink-0" title="No BYOK key configured">
              no key
            </span>
          )}
        </MetaChip>
        {open === "model" && (
          <Popover align="right" label="Provider and model">
            <PopoverHeader>
              <span className="min-w-0 flex-1 truncate">Provider</span>
              {onRefreshModels && (
                <button
                  type="button"
                  onClick={onRefreshModels}
                  title={catalogNote ?? "Refresh model list"}
                  aria-label="Refresh model list"
                  className="text-charcoal-500 hover:text-charcoal-200 rounded-control shrink-0 transition-colors"
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
                  setOpen(null);
                }}
                className="text-warning text-caption hover:text-charcoal-100 w-full px-3 py-1 text-left font-mono transition-colors"
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
                      setOpen(null);
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
    </div>
  );
}
