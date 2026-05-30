"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { validateProvider } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import { useChartSyncBus } from "@/store/chart-sync";
import { useChatHistoryStore } from "@/store/chat-history";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { usePanelContextBus } from "@/store/panel-context";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { AgentContextSnapshot, LLMProviderId, LLMStreamEvent } from "../../../types/ai";
import { captureTerminalState } from "./context-provider";
import { parseSlashCommand, SLASH_HELP_LINES } from "./slash-commands";
import { streamAgentInvocation, streamChat } from "./streaming";

/** The default agent: the terminal-aware router/concierge. Bare text routes here. */
const DEFAULT_AGENT_ID = "copilot";

/** Execute a copilot host-action tool against the live stores, and return a
 *  short human label for the tool-step chip. UI actions (chart/panel/watchlist)
 *  apply immediately; `propose_order` is NOT executed here — it routes through
 *  the §6.5 confirmation dialog, so we only surface a review note. */
function executeHostAction(name: string, input: Record<string, unknown>): string | null {
  const symbol = typeof input.symbol === "string" ? input.symbol : "";
  switch (name) {
    case "set_chart_symbol":
      if (symbol) {
        useChartSyncBus.getState().setSymbol("copilot", symbol);
        return `Loading ${symbol} into the chart`;
      }
      return null;
    case "open_panel": {
      const panel = typeof input.panel === "string" ? input.panel : "";
      if (panel) {
        useWorkspaceStore.getState().openPanel(panel);
        return `Opening ${panel}`;
      }
      return null;
    }
    case "add_to_watchlist":
      if (symbol) {
        const assetClass = input.asset_class === "crypto" ? "crypto" : "equity";
        useSymbolsStore.getState().addSymbol(symbol, assetClass);
        return `Adding ${symbol} to your watchlist`;
      }
      return null;
    case "propose_order":
      return `Prepared a ${String(input.side ?? "")} order for ${symbol || "review"} — review & confirm it in the broker panel`;
    case "get_terminal_state":
      return "Reading what you're looking at";
    case "get_portfolio":
      return "Reading your portfolio";
    default:
      return `Using ${name.replace(/_/g, " ")}`;
  }
}

/**
 * Vysted chat sidebar — agent picker, streaming response area, slash-command
 * composer.
 *
 * The sidebar reads:
 *  - First-party + custom agents from :func:`useAgentsStore`.
 *  - The seven BYOK providers from :func:`useLLMProvidersStore`.
 *  - The aggregated panel context (chart symbol, watchlist, equity, …) from
 *    :func:`selectSnapshot`.
 *
 * Slash commands are parsed in ``slash-commands.ts``; the composer dispatches
 * to ``streamChat`` (raw chat) or ``streamAgentInvocation`` (agent) and pipes
 * the resulting events into :func:`useChatHistoryStore`. API keys are read
 * from the OS keychain on demand via :func:`getSecret` — never cached on the
 * frontend after the request.
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

  // Subscribe to the three primitive bus slices independently — each is a
  // stable reference, so subscribers do not re-render on unrelated updates.
  // Aggregating into one object via a fresh `selectSnapshot` would re-mint
  // the object on every store change and infinite-loop `useSyncExternalStore`
  // (CLAUDE.md Phase-2 gotcha).
  const lastEventBySource = usePanelContextBus((state) => state.lastEventBySource);
  const focusedSource = usePanelContextBus((state) => state.focusedSource);
  const updatedAt = usePanelContextBus((state) => state.updatedAt);
  const contextSnapshot = useMemo(
    () => ({ lastEventBySource, focusedSource, updatedAt }),
    [lastEventBySource, focusedSource, updatedAt],
  );

  // Default to the copilot router — bare text "just works" with tools + context.
  const [activeAgentId, setActiveAgentId] = useState<string | null>(DEFAULT_AGENT_ID);
  const [composer, setComposer] = useState("");
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [keyDialogProvider, setKeyDialogProvider] = useState<LLMProviderId | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Fetch agents + providers once on mount. Failures are silent — the static
  // catalogs in the stores are the fallback.
  useEffect(() => {
    void refreshAgents();
    void refreshProviders();
  }, [refreshAgents, refreshProviders]);

  // Autoscroll to the newest message whenever the conversation grows.
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

  const contextBadge = useMemo(() => describeContext(contextSnapshot), [contextSnapshot]);

  // Map agent id -> display name for the transcript identity header.
  const agentNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const a of [...firstPartyAgents, ...customAgents]) {
      map[a.id] = a.name;
    }
    return map;
  }, [firstPartyAgents, customAgents]);

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
        // Best-effort: accept any of the seven known provider ids.
        const match = providers.find((p) => p.id === result.providerId);
        if (!match) {
          setStatusLine(`unknown provider: ${result.providerId}`);
          return;
        }
        setDefaultProviderId(match.id);
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
      const prompt = result.kind === "raw" ? result.prompt : result.prompt;
      const agentForCall =
        result.kind === "agent"
          ? result.agentId
          : result.kind === "raw" && activeAgentId
            ? activeAgentId
            : null;

      // Recent-turn history (captured BEFORE the new user message) so the
      // copilot holds a thread — last ~10 user/assistant turns.
      const history = useChatHistoryStore
        .getState()
        .messages.filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      appendUser(prompt);

      // Resolve which provider's keychain key we need. On the agent path use
      // the AGENT's default provider (BYOK fix — previously used the UI default,
      // which sent the wrong key when they differed); else the session default.
      const agentSpec = agentForCall
        ? (firstPartyAgents.find((a) => a.id === agentForCall) ??
          customAgents.find((a) => a.id === agentForCall) ??
          null)
        : null;
      const provider = (agentSpec?.defaultProvider ?? defaultProviderId) as LLMProviderId;
      const providerInfo = providers.find((p) => p.id === provider);
      const requiresKey = providerInfo?.requiresKey ?? true;
      const providerLabel = providerInfo?.label ?? provider;
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
        // Keyless provider (e.g. Ollama) — gate the call on the local daemon
        // actually being reachable, so a missing or stopped local model surfaces
        // a clear onboarding message instead of failing the call silently (the
        // ratified "offer both, never silently default to an absent local model"
        // rule from US1 / FR-032).
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

      const handlers = makeHandlers(assistantId, {
        onDelta: (text) => appendDelta(assistantId, text),
        onError: (message) => fail(assistantId, message),
        onDone: (usage) => finalize(assistantId, usage),
        onToolUse: (name, input) => {
          // Render a step chip AND drive the terminal for host-action tools.
          const label = executeHostAction(name, input);
          if (label) {
            appendToolStep(assistantId, label);
          }
        },
      });

      if (agentForCall) {
        // Structured "what the user is looking at" snapshot — the sidecar
        // renders a terse preamble + the get_terminal_state tool reads it.
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
            apiKey: apiKey ?? undefined,
            options: { history },
          },
          handlers,
        );
      } else {
        await streamChat(
          {
            provider,
            model: defaultModelFor(provider),
            messages: [{ role: "user", content: prompt }],
            apiKey: apiKey ?? undefined,
          },
          handlers,
        );
      }
    },
    [
      activeAgentId,
      appendDelta,
      appendToolStep,
      appendUser,
      beginAssistant,
      clearHistory,
      customAgents,
      defaultProviderId,
      fail,
      finalize,
      firstPartyAgents,
      providers,
      setDefaultProviderId,
    ],
  );

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <header className="border-charcoal-700 flex items-center gap-2 border-b px-3 py-2">
        <Sparkles className="text-amber-400" size={14} aria-hidden />
        <span className="text-charcoal-200 font-mono text-xs font-medium">Copilot</span>
      </header>
      <RosterStrip
        firstParty={firstPartyAgents}
        custom={customAgents}
        activeAgentId={activeAgentId}
        onChange={setActiveAgentId}
      />
      <ContextBadge text={contextBadge} />
      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        aria-label="Chat transcript"
        className="flex-1 overflow-y-auto px-3 py-3"
      >
        {messages.length === 0 ? (
          <EmptyState activeAgentName={activeAgent?.name ?? null} />
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
        disabled={streaming}
      />
      <KeyEntryDialog
        open={keyDialogProvider !== null}
        providerId={keyDialogProvider}
        onOpenChange={(open) => !open && setKeyDialogProvider(null)}
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

function EmptyState({ activeAgentName }: { activeAgentName: string | null }) {
  return (
    <div className="text-charcoal-400 flex h-full flex-col items-center justify-center gap-2 px-6 text-center font-mono text-xs">
      <Sparkles className="text-amber-400/70" size={20} aria-hidden />
      <p>
        Ask me anything about what you&rsquo;re looking at — your portfolio, a chart, a screen. I
        read the terminal and can drive it.
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
}

function Composer({ value, onChange, onSend, disabled }: ComposerProps) {
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
        placeholder="Ask anything — your portfolio, a chart, a screen…"
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

function defaultModelFor(provider: LLMProviderId): string {
  switch (provider) {
    case "anthropic":
      return "claude-opus-4-7";
    case "openai":
      return "gpt-4.1-mini";
    case "gemini":
      return "gemini-2.5-pro";
    case "groq":
      return "llama-3.3-70b-versatile";
    case "ollama":
      return "qwen2.5:7b";
    case "deepseek":
      return "deepseek-chat";
    case "xai":
      return "grok-2-latest";
  }
}

interface InternalHandlers {
  onDelta: (text: string) => void;
  onError: (message: string) => void;
  onDone: (usage: { inputTokens: number; outputTokens: number } | null) => void;
  onToolUse: (name: string, input: Record<string, unknown>) => void;
}

function makeHandlers(
  _assistantId: string,
  internal: InternalHandlers,
): { onEvent: (event: LLMStreamEvent) => void; onError: (err: Error) => void } {
  return {
    onEvent: (event) => {
      if (event.kind === "delta") {
        internal.onDelta(event.text);
      } else if (event.kind === "tool_use") {
        internal.onToolUse(event.name, (event.input as Record<string, unknown>) ?? {});
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
  // Walk one level deep into a payload object to pull the most useful field.
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
