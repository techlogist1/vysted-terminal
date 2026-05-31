"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { isHostActionMutation } from "@/lib/host-actions";
import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { validateProvider } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { useAgentModeStore } from "@/store/agent-mode";
import { useAgentRunsStore } from "@/store/agent-runs";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import { useChatHistoryStore } from "@/store/chat-history";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { usePanelContextBus } from "@/store/panel-context";
import { useProposedChangesStore } from "@/store/proposed-changes";
import { useProviderKeysStore } from "@/store/provider-keys";
import type { AgentContextSnapshot, LLMProviderId, LLMStreamEvent } from "../../../types/ai";
import { type AgentMode, AGENT_MODES, agentModeMeta } from "../../../types/agent-modes";
import { AgentHud } from "./AgentHud";
import { AgentsRail } from "./AgentsRail";
import { captureTerminalState } from "./context-provider";
import { ModeBar } from "./ModeBar";
import { ProposedChangesReview } from "./ProposedChangesReview";
import { parseSlashCommand, SLASH_HELP_LINES } from "./slash-commands";
import { streamAgentInvocation, streamChat } from "./streaming";

/** The default agent: the terminal-aware router/concierge. Bare text routes here. */
const DEFAULT_AGENT_ID = "copilot";

/** A short chip label for a READ tool (read tools already ran server-side, so we
 *  only narrate them — mutations are intercepted into the diff gate, not here). */
function readToolLabel(name: string): string {
  switch (name) {
    case "get_terminal_state":
      return "Reading what you're looking at";
    case "get_portfolio":
      return "Reading your portfolio";
    default:
      return `Using ${name.replace(/_/g, " ")}`;
  }
}

/**
 * Vysted agent surface — the four-mode spine (Ask / Edit / Build / Delegate),
 * the persona roster, the provider/model HUD, the agents rail, the streaming
 * transcript, and the diff/accept trust gate. Promoted from a dockview panel to
 * the shell's primary column (FR-001): its actions open + arrange the cockpit,
 * and every agent-proposed mutation is staged as a reviewable diff (FR-010) —
 * nothing lands before the user accepts. Orders route through the §6.5 dialog
 * (FR-011); the AI never reaches placement.
 *
 * Slash commands are parsed in `slash-commands.ts`; the composer dispatches to
 * `streamChat` (raw chat) or `streamAgentInvocation` (agent) and pipes events
 * into `useChatHistoryStore`. API keys are read from the OS keychain on demand —
 * never cached on the frontend after the request.
 */
export function ChatSidebar() {
  const messages = useChatHistoryStore((state) => state.messages);
  const appendUser = useChatHistoryStore((state) => state.appendUserMessage);
  const beginAssistant = useChatHistoryStore((state) => state.beginAssistantMessage);
  const appendDelta = useChatHistoryStore((state) => state.appendAssistantDelta);
  const appendToolStep = useChatHistoryStore((state) => state.appendToolStep);
  const finalize = useChatHistoryStore((state) => state.finalizeAssistantMessage);
  const fail = useChatHistoryStore((state) => state.failAssistantMessage);
  const clearHistory = useChatHistoryStore((state) => state.clear);
  const streaming = useChatHistoryStore((state) => state.streamingMessageId !== null);

  const firstPartyAgents = useAgentsStore(selectFirstPartyAgents);
  const customAgents = useAgentsStore(selectCustomAgents);
  const refreshAgents = useAgentsStore((state) => state.refresh);

  const providers = useLLMProvidersStore((state) => state.providers);
  const defaultProviderId = useLLMProvidersStore((state) => state.defaultProviderId);
  const setDefaultProviderId = useLLMProvidersStore((state) => state.setDefaultProviderId);
  const refreshProviders = useLLMProvidersStore((state) => state.refresh);

  const keyStatuses = useProviderKeysStore((state) => state.status);
  const refreshKeys = useProviderKeysStore((state) => state.refresh);

  const mode = useAgentModeStore((state) => state.mode);
  const setMode = useAgentModeStore((state) => state.setMode);

  const setModelOverride = useModelSelectionStore((state) => state.setModel);

  const pendingChangeCount = useProposedChangesStore(
    (state) => state.changes.filter((c) => c.status === "pending").length,
  );
  const acceptAllChanges = useProposedChangesStore((state) => state.acceptAll);
  const rejectAllChanges = useProposedChangesStore((state) => state.rejectAll);
  const enqueueChange = useProposedChangesStore((state) => state.enqueue);

  const startRun = useAgentRunsStore((state) => state.startRun);
  const endRun = useAgentRunsStore((state) => state.endRun);
  const updateRun = useAgentRunsStore((state) => state.updateRun);

  // Subscribe to the three primitive bus slices independently — each is a
  // stable reference, so subscribers do not re-render on unrelated updates.
  const lastEventBySource = usePanelContextBus((state) => state.lastEventBySource);
  const focusedSource = usePanelContextBus((state) => state.focusedSource);
  const updatedAt = usePanelContextBus((state) => state.updatedAt);
  const contextSnapshot = useMemo(
    () => ({ lastEventBySource, focusedSource, updatedAt }),
    [lastEventBySource, focusedSource, updatedAt],
  );

  const [activeAgentId, setActiveAgentId] = useState<string | null>(DEFAULT_AGENT_ID);
  // Explicit provider override (HUD pick); null = use the active agent's default.
  const [providerOverride, setProviderOverride] = useState<LLMProviderId | null>(null);
  const [composer, setComposer] = useState("");
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [keyDialogProvider, setKeyDialogProvider] = useState<LLMProviderId | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void refreshAgents();
    void refreshProviders();
    void refreshKeys();
  }, [refreshAgents, refreshProviders, refreshKeys]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const activeAgent = useMemo(() => {
    if (!activeAgentId) {
      return null;
    }
    return (
      firstPartyAgents.find((a) => a.id === activeAgentId) ??
      customAgents.find((a) => a.id === activeAgentId) ??
      null
    );
  }, [activeAgentId, firstPartyAgents, customAgents]);

  // The effective provider/model for the next send (FR-004): an explicit HUD
  // override wins, else the active agent's default, else the session default.
  const effectiveProvider = useMemo<LLMProviderId>(() => {
    return (
      providerOverride ??
      (activeAgent?.defaultProvider as LLMProviderId | undefined) ??
      defaultProviderId
    );
  }, [providerOverride, activeAgent, defaultProviderId]);
  const effectiveModel = useModelSelectionStore((state) => state.modelFor(effectiveProvider));
  const providerInfo = providers.find((p) => p.id === effectiveProvider);
  const providerRequiresKey = providerInfo?.requiresKey ?? true;
  const providerConfigured =
    !providerRequiresKey || keyStatuses[effectiveProvider] === "configured";

  const contextBadge = useMemo(() => describeContext(contextSnapshot), [contextSnapshot]);

  const agentNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const a of [...firstPartyAgents, ...customAgents]) {
      map[a.id] = a.name;
    }
    return map;
  }, [firstPartyAgents, customAgents]);

  // Global hotkeys for the agent surface: ⌥1–⌥4 switch mode (FR-003); when
  // changes are pending, ⌘↵ accepts all and ⌘⌫ rejects all (FR-010 keyboard).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.altKey && !event.metaKey && !event.ctrlKey) {
        const found = AGENT_MODES.find((m) => event.code === `Digit${m.hotkeyDigit}`);
        if (found) {
          event.preventDefault();
          setMode(found.id);
          return;
        }
      }
      // Bulk accept/reject (⌘↵ / ⌘⌫) — but NOT while the user is typing in a
      // field: ⌘⌫ is the macOS "delete to line start" the composer needs.
      const el = event.target as HTMLElement | null;
      const typing =
        !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
      if ((event.metaKey || event.ctrlKey) && pendingChangeCount > 0 && !typing) {
        if (event.key === "Enter") {
          event.preventDefault();
          void acceptAllChanges();
        } else if (event.key === "Backspace") {
          event.preventDefault();
          rejectAllChanges();
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setMode, pendingChangeCount, acceptAllChanges, rejectAllChanges]);

  const handleSend = useCallback(
    async (rawInput: string) => {
      const result = parseSlashCommand(rawInput);
      if (result.kind === "error") {
        setStatusLine(result.message);
        return;
      }
      if (result.kind === "help") {
        setStatusLine(SLASH_HELP_LINES.join("\n"));
        return;
      }
      if (result.kind === "clear") {
        clearHistory();
        setStatusLine(null);
        return;
      }
      if (result.kind === "provider") {
        const match = providers.find((p) => p.id === result.providerId);
        if (!match) {
          setStatusLine(`unknown provider: ${result.providerId}`);
          return;
        }
        setDefaultProviderId(match.id);
        setProviderOverride(match.id);
        setStatusLine(`default provider → ${match.label}`);
        return;
      }
      if (result.kind === "key-set") {
        const match = providers.find((p) => p.id === result.providerId);
        if (!match) {
          setStatusLine(`unknown provider: ${result.providerId}`);
          return;
        }
        setKeyDialogProvider(match.id);
        return;
      }

      setStatusLine(null);
      const prompt = result.prompt;
      const agentForCall =
        result.kind === "agent"
          ? result.agentId
          : result.kind === "raw" && activeAgentId
            ? activeAgentId
            : null;

      const history = useChatHistoryStore
        .getState()
        .messages.filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      appendUser(prompt);

      // Resolve the effective provider/model (FR-004): HUD override → the called
      // agent's default → session default. The key is resolved for THAT provider.
      const agentSpec = agentForCall
        ? (firstPartyAgents.find((a) => a.id === agentForCall) ??
          customAgents.find((a) => a.id === agentForCall) ??
          null)
        : null;
      const provider =
        providerOverride ??
        (agentSpec?.defaultProvider as LLMProviderId | undefined) ??
        defaultProviderId;
      const model = useModelSelectionStore.getState().modelFor(provider);
      const providerMeta = providers.find((p) => p.id === provider);
      const requiresKey = providerMeta?.requiresKey ?? true;
      const providerLabel = providerMeta?.label ?? provider;
      let apiKey: string | null = null;
      if (requiresKey) {
        apiKey = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider));
        if (!apiKey) {
          setStatusLine(
            `No API key for ${providerLabel}. Add one in Settings → AI Providers (or /key set ${provider}).`,
          );
          return;
        }
      } else if (!(await validateProvider(provider))) {
        setStatusLine(
          `${providerLabel} isn't reachable. Start it (run \`ollama serve\` and pull the model) ` +
            "or switch to a cloud provider in Settings → AI Providers.",
        );
        return;
      }

      const assistantId = beginAssistant({
        agentId: agentForCall ?? undefined,
        providerId: provider,
      });
      const agentName = agentForCall
        ? (agentNameById[agentForCall] ?? agentForCall)
        : "Direct chat";

      // Track the run in the agents rail (FR-027 / US3 AS3) with a cancel that
      // aborts the stream. P3 deepens this into durable, budget-guarded runs.
      const controller = new AbortController();
      const runId = startRun({
        agentId: agentForCall,
        agentName,
        mode,
        abort: () => controller.abort(),
      });

      const handlers = makeHandlers({
        onDelta: (text) => appendDelta(assistantId, text),
        onError: (message) => {
          if (controller.signal.aborted) {
            finalize(assistantId, null);
            endRun(runId, "cancelled");
          } else {
            fail(assistantId, message);
            endRun(runId, "error", message);
          }
        },
        onDone: (usage) => {
          finalize(assistantId, usage);
          endRun(runId, "done");
          if (usage) {
            updateRun(runId, { tokens: usage.inputTokens + usage.outputTokens });
          }
        },
        onToolUse: (name, input, toolCallId) => {
          if (isHostActionMutation(name)) {
            // FR-010 — stage the mutation as a reviewable diff instead of
            // applying it. One agent turn = one batch (assistantId).
            const id = enqueueChange({
              toolCallId,
              name,
              input,
              batchId: assistantId,
              agentId: agentForCall ?? undefined,
              agentName,
            });
            const change = useProposedChangesStore.getState().changes.find((c) => c.id === id);
            appendToolStep(assistantId, `Proposed: ${change?.title ?? name} — review below`);
          } else {
            appendToolStep(assistantId, readToolLabel(name));
          }
        },
      });

      if (agentForCall) {
        const terminalState = captureTerminalState();
        const snapshot: AgentContextSnapshot = {
          focusedSource: terminalState.focusedPanel,
          bySource: { __terminal__: terminalState as unknown as Record<string, unknown> },
          capturedAt: terminalState.capturedAt,
        };
        await streamAgentInvocation(
          agentForCall,
          {
            prompt,
            contextSnapshot: snapshot,
            provider,
            model,
            mode,
            apiKey: apiKey ?? undefined,
            options: { history },
          },
          { ...handlers, signal: controller.signal },
        );
      } else {
        await streamChat(
          {
            provider,
            model,
            messages: [{ role: "user", content: prompt }],
            apiKey: apiKey ?? undefined,
          },
          { ...handlers, signal: controller.signal },
        );
      }
    },
    [
      activeAgentId,
      appendDelta,
      appendToolStep,
      appendUser,
      agentNameById,
      beginAssistant,
      clearHistory,
      customAgents,
      defaultProviderId,
      endRun,
      enqueueChange,
      fail,
      finalize,
      firstPartyAgents,
      mode,
      providerOverride,
      providers,
      setDefaultProviderId,
      startRun,
      updateRun,
    ],
  );

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <header className="border-charcoal-700 flex items-center gap-2 border-b px-3 py-2">
        <Sparkles className="text-amber-400" size={14} aria-hidden />
        <span className="text-charcoal-200 font-mono text-xs font-medium">Agent</span>
      </header>
      <ModeBar mode={mode} onChange={setMode} />
      <RosterStrip
        firstParty={firstPartyAgents}
        custom={customAgents}
        activeAgentId={activeAgentId}
        onChange={(id) => {
          setActiveAgentId(id);
          setProviderOverride(null);
        }}
      />
      <AgentHud
        providers={providers}
        provider={effectiveProvider}
        model={effectiveModel}
        providerConfigured={providerConfigured}
        onProviderChange={(p) => setProviderOverride(p)}
        onModelChange={(m) => setModelOverride(effectiveProvider, m)}
      />
      <AgentsRail />
      <ContextBadge text={contextBadge} />
      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        aria-label="Chat transcript"
        className="flex-1 overflow-y-auto px-3 py-3"
      >
        {messages.length === 0 ? (
          <EmptyState activeAgentName={activeAgent?.name ?? null} mode={mode} />
        ) : (
          <ul className="flex flex-col gap-3">
            {messages.map((message) => (
              <li
                key={message.id}
                className={cn(
                  "rounded-md border px-3 py-2 font-mono text-xs",
                  message.role === "user"
                    ? "border-charcoal-700 bg-charcoal-800 text-charcoal-100"
                    : "text-charcoal-100 border-amber-900/30 bg-amber-950/15",
                )}
              >
                <div className="text-charcoal-400 mb-1 text-[0.6rem] tracking-wide uppercase">
                  {message.role === "user"
                    ? "You"
                    : message.agentId
                      ? (agentNameById[message.agentId] ?? message.agentId)
                      : "Assistant"}
                </div>
                {message.toolSteps && message.toolSteps.length > 0 && (
                  <ul className="mb-1.5 flex flex-col gap-0.5">
                    {message.toolSteps.map((step, i) => (
                      <li
                        key={i}
                        className="text-charcoal-400 flex items-center gap-1 text-[0.6rem]"
                      >
                        <span className="text-amber-400">→</span> {step}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="whitespace-pre-wrap">
                  {message.content}
                  {message.pending && (
                    <span className="text-charcoal-400 animate-pulse" aria-hidden>
                      ▋
                    </span>
                  )}
                </div>
                {message.error && (
                  <div className="text-negative mt-1 text-[0.65rem]">{message.error}</div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      <ProposedChangesReview />
      {statusLine && (
        <div className="border-charcoal-700 text-charcoal-300 border-t px-3 py-1 font-mono text-[0.65rem] whitespace-pre-line">
          {statusLine}
        </div>
      )}
      <Composer
        value={composer}
        onChange={setComposer}
        onSend={(text) => {
          setComposer("");
          void handleSend(text);
        }}
        // Delegate runs are background (US3 AS3): keep the composer live so the
        // user can keep working the cockpit while the run streams in the rail.
        disabled={streaming && mode !== "delegate"}
        mode={mode}
      />
      <KeyEntryDialog
        open={keyDialogProvider !== null}
        providerId={keyDialogProvider}
        onOpenChange={(open) => {
          if (!open) {
            setKeyDialogProvider(null);
            void refreshKeys();
          }
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

interface AgentPickerProps {
  firstParty: readonly { id: string; name: string }[];
  custom: readonly { id: string; name: string }[];
  activeAgentId: string | null;
  onChange: (id: string | null) => void;
}

/** A visible, clickable roster of personas — no memorized ids. The copilot
 *  router is pinned first as the default; clicking a chip switches the lens. */
function RosterStrip({ firstParty, custom, activeAgentId, onChange }: AgentPickerProps) {
  const ordered = [...firstParty].sort((a, b) =>
    a.id === DEFAULT_AGENT_ID ? -1 : b.id === DEFAULT_AGENT_ID ? 1 : 0,
  );
  const all = [...ordered, ...custom];
  if (all.length === 0) {
    return null;
  }
  return (
    <div
      aria-label="Persona roster"
      className="border-charcoal-700 flex items-center gap-1 overflow-x-auto border-b px-2 py-1.5"
    >
      {all.map((agent) => {
        const active = agent.id === activeAgentId;
        return (
          <button
            key={agent.id}
            type="button"
            onClick={() => onChange(agent.id)}
            aria-pressed={active}
            title={agent.name}
            className={cn(
              "shrink-0 rounded-full border px-2.5 py-1 font-mono text-[0.65rem] whitespace-nowrap transition-colors",
              active
                ? "border-amber-500 bg-amber-500/15 text-amber-300"
                : "border-charcoal-700 text-charcoal-400 hover:text-charcoal-100 hover:border-charcoal-600",
            )}
          >
            {agent.name}
          </button>
        );
      })}
    </div>
  );
}

function ContextBadge({ text }: { text: string }) {
  return (
    <div
      aria-label="Panel context"
      className="border-charcoal-700 text-charcoal-300 border-b px-3 py-1 font-mono text-[0.6rem] tracking-wide uppercase"
    >
      {text}
    </div>
  );
}

function EmptyState({
  activeAgentName,
  mode,
}: {
  activeAgentName: string | null;
  mode: AgentMode;
}) {
  const meta = agentModeMeta(mode);
  return (
    <div className="text-charcoal-400 flex h-full flex-col items-center justify-center gap-2 px-6 text-center font-mono text-xs">
      <Sparkles className="text-amber-400/70" size={20} aria-hidden />
      <p>
        Ask me anything about what you&rsquo;re looking at — your portfolio, a chart, a screen. I
        read the terminal and can drive it.
      </p>
      <p className="text-charcoal-500">
        Mode: <span className="text-charcoal-300">{meta.label}</span> — {meta.consequence}
      </p>
      {activeAgentName && (
        <p className="text-charcoal-500">
          Lens: <span className="text-charcoal-300">{activeAgentName}</span>
        </p>
      )}
    </div>
  );
}

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (text: string) => void;
  disabled: boolean;
  mode: AgentMode;
}

function Composer({ value, onChange, onSend, disabled, mode }: ComposerProps) {
  const meta = agentModeMeta(mode);
  return (
    <form
      className="border-charcoal-700 flex items-center gap-2 border-t p-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) {
          onSend(value);
        }
      }}
    >
      <input
        aria-label="Chat input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={`${meta.label} — ${meta.hint}`}
        disabled={disabled}
        className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 h-8 flex-1 rounded-md px-2 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
      />
      <Button
        type="submit"
        size="icon-sm"
        variant="outline"
        aria-label="Send message"
        disabled={disabled || value.trim().length === 0}
      >
        <Send />
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface InternalHandlers {
  onDelta: (text: string) => void;
  onError: (message: string) => void;
  onDone: (usage: { inputTokens: number; outputTokens: number } | null) => void;
  onToolUse: (name: string, input: Record<string, unknown>, toolCallId: string) => void;
}

function makeHandlers(internal: InternalHandlers): {
  onEvent: (event: LLMStreamEvent) => void;
  onError: (err: Error) => void;
} {
  return {
    onEvent: (event) => {
      if (event.kind === "delta") {
        internal.onDelta(event.text);
      } else if (event.kind === "tool_use") {
        internal.onToolUse(
          event.name,
          (event.input as Record<string, unknown>) ?? {},
          event.toolCallId,
        );
      } else if (event.kind === "error") {
        internal.onError(event.message);
      } else if (event.kind === "done") {
        internal.onDone(
          event.usage
            ? { inputTokens: event.usage.inputTokens, outputTokens: event.usage.outputTokens }
            : null,
        );
      }
    },
    onError: (err) => internal.onError(err.message),
  };
}

/** Render the panel-context badge text from the snapshot. */
function describeContext(snapshot: {
  focusedSource: string | null;
  lastEventBySource: Record<string, { payload: unknown }>;
}): string {
  if (!snapshot.focusedSource) {
    const count = Object.keys(snapshot.lastEventBySource).length;
    return count === 0
      ? "Context: none"
      : `Context: ${count} panel${count === 1 ? "" : "s"} active`;
  }
  const focused = snapshot.lastEventBySource[snapshot.focusedSource];
  if (!focused) {
    return `Context: ${snapshot.focusedSource}`;
  }
  const payload = focused.payload;
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (typeof obj.symbol === "string") {
      const tf = typeof obj.timeframe === "string" ? `, ${obj.timeframe}` : "";
      return `Context: ${snapshot.focusedSource} (${obj.symbol}${tf})`;
    }
    if (typeof obj.ticker === "string") {
      return `Context: ${snapshot.focusedSource} (${obj.ticker})`;
    }
  }
  return `Context: ${snapshot.focusedSource}`;
}
