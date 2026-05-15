"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { cn } from "@/lib/utils";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import { useChatHistoryStore } from "@/store/chat-history";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { usePanelContextBus } from "@/store/panel-context";
import type { AgentContextSnapshot, LLMProviderId, LLMStreamEvent } from "../../../types/ai";
import { parseSlashCommand, SLASH_HELP_LINES } from "./slash-commands";
import { streamAgentInvocation, streamChat } from "./streaming";

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

  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
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

      appendUser(prompt);

      const providerId = (
        agentForCall
          ? // Use the agent's default provider; the runtime resolves it.
            undefined
          : defaultProviderId
      ) as LLMProviderId | undefined;

      // Read the API key on-demand from the OS keychain.
      const provider = providerId ?? defaultProviderId;
      const requiresKey = providers.find((p) => p.id === provider)?.requiresKey ?? true;
      let apiKey: string | null = null;
      if (requiresKey) {
        apiKey = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider));
        if (!apiKey) {
          setStatusLine(`no API key set for ${provider}; run /key set ${provider}`);
          return;
        }
      }

      const assistantId = beginAssistant({
        agentId: agentForCall ?? undefined,
        providerId: provider,
      });

      const handlers = makeHandlers(assistantId, {
        onDelta: (text) => appendDelta(assistantId, text),
        onError: (message) => fail(assistantId, message),
        onDone: (usage) => finalize(assistantId, usage),
      });

      if (agentForCall) {
        const snapshot: AgentContextSnapshot = {
          focusedSource: contextSnapshot.focusedSource,
          bySource: Object.fromEntries(
            Object.entries(contextSnapshot.lastEventBySource).map(([source, event]) => [
              source,
              event.payload,
            ]),
          ),
          capturedAt: contextSnapshot.updatedAt,
        };
        await streamAgentInvocation(
          agentForCall,
          {
            prompt,
            contextSnapshot: snapshot,
            apiKey: apiKey ?? undefined,
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
      appendUser,
      beginAssistant,
      clearHistory,
      contextSnapshot,
      defaultProviderId,
      fail,
      finalize,
      providers,
      setDefaultProviderId,
    ],
  );

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <header className="border-charcoal-700 flex items-center justify-between gap-2 border-b px-3 py-2">
        <div className="flex items-center gap-2">
          <Sparkles className="text-amber-400" size={14} aria-hidden />
          <span className="text-charcoal-200 font-mono text-xs font-medium">AI Assistant</span>
        </div>
        <AgentPicker
          firstParty={firstPartyAgents}
          custom={customAgents}
          activeAgentId={activeAgentId}
          onChange={setActiveAgentId}
        />
      </header>
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
                  {message.role === "user" ? "You" : (message.agentId ?? "Assistant")}
                </div>
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

function AgentPicker({ firstParty, custom, activeAgentId, onChange }: AgentPickerProps) {
  return (
    <select
      aria-label="Agent picker"
      value={activeAgentId ?? ""}
      onChange={(event) => onChange(event.target.value || null)}
      className="bg-charcoal-800 text-charcoal-200 h-6 max-w-[60%] truncate rounded-md px-2 font-mono text-[0.65rem] outline-none focus:ring-1 focus:ring-amber-400"
    >
      <option value="">No agent (raw chat)</option>
      {firstParty.length > 0 && (
        <optgroup label="First-party agents">
          {firstParty.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </optgroup>
      )}
      {custom.length > 0 && (
        <optgroup label="Custom agents">
          {custom.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </optgroup>
      )}
    </select>
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
      {activeAgentName ? (
        <p>
          Ready — invoke <span className="text-charcoal-200">{activeAgentName}</span> with a prompt,
          or switch agents in the header dropdown.
        </p>
      ) : (
        <p>
          Type <span className="text-charcoal-200">/ask</span> for a raw chat,{" "}
          <span className="text-charcoal-200">/agent &lt;id&gt;</span> to invoke a specific agent,
          or <span className="text-charcoal-200">/help</span> for the full slash-command list.
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
        placeholder="/ask a question, /agent buffett <prompt>, /help"
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
      return "llama3.1:8b";
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
}

function makeHandlers(
  _assistantId: string,
  internal: InternalHandlers,
): { onEvent: (event: LLMStreamEvent) => void; onError: (err: Error) => void } {
  return {
    onEvent: (event) => {
      if (event.kind === "delta") {
        internal.onDelta(event.text);
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
