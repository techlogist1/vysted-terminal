"use client";

import {
  type KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { launchDelegateRun } from "@/lib/delegate-runs";
import { isHostActionMutation } from "@/lib/host-actions";
import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { tween } from "@/lib/motion";
import { validateProvider } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useAgentModeStore } from "@/store/agent-mode";
import { type AgentRunBudget, useAgentRunsStore } from "@/store/agent-runs";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import {
  type AgentPlanView,
  type ResearchStepView,
  useChatHistoryStore,
} from "@/store/chat-history";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelCatalog, useModelCatalogStore } from "@/store/model-catalog";
import { useModelSelectionStore } from "@/store/model-selection";
import { usePanelContextBus } from "@/store/panel-context";
import { useProposedChangesStore } from "@/store/proposed-changes";
import { useOnboardingStore } from "@/store/onboarding";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useSettingsStore } from "@/store/settings";
import type { Region } from "@/lib/region";
import type { AgentContextSnapshot, LLMProviderId, LLMStreamEvent } from "../../../types/ai";
import { type AgentMode, AGENT_MODES, agentModeMeta } from "../../../types/agent-modes";
import { AgentHud } from "./AgentHud";
import { AgentsRail } from "./AgentsRail";
import { BudgetConfig, DEFAULT_DELEGATE_BUDGET } from "./BudgetConfig";
import { captureTerminalState } from "./context-provider";
import { applyMentionPrefixes, type MentionDef, matchMention, resolveMention } from "./mentions";
import { MentionPicker } from "./MentionPicker";
import { ModeBar } from "./ModeBar";
import { PlanView } from "./PlanView";
import { ProposedChangesReview } from "./ProposedChangesReview";
import { ResearchActivity } from "./ResearchActivity";
import {
  parseSlashCommand,
  parseSlashInvocation,
  type SlashAction,
  type SlashCommandDef,
  SLASH_HELP_LINES,
  matchSlash,
} from "./slash-commands";
import { SlashCommandPicker } from "./SlashCommandPicker";
import { streamAgentInvocation, streamChat } from "./streaming";

/**
 * Autonomy switcher (Claude-Code-style) — `ask` keeps every change in the diff
 * gate; `auto` applies UI/layout/chart/watchlist changes without a per-action
 * confirmation. Orders are NEVER auto-applied in either mode (enforced in
 * `proposed-changes`, not here). Sits beside the model HUD as the agent's
 * confirmation-friction axis (orthogonal to the four intent modes).
 */
function AutonomyToggle() {
  const autonomy = useAgentAutonomyStore((state) => state.autonomy);
  const setAutonomy = useAgentAutonomyStore((state) => state.setAutonomy);
  return (
    <div className="border-charcoal-700 text-charcoal-400 flex items-center gap-2 border-b px-3 py-1 font-mono text-[0.6rem]">
      <span className="tracking-wide uppercase">Autonomy</span>
      <div
        role="radiogroup"
        aria-label="Agent autonomy"
        className="border-charcoal-700 flex overflow-hidden rounded border"
      >
        {(["ask", "auto"] as const).map((level) => (
          <button
            key={level}
            type="button"
            role="radio"
            aria-checked={autonomy === level}
            onClick={() => setAutonomy(level)}
            className={cn(
              "px-2 py-0.5 uppercase transition-colors",
              autonomy === level
                ? "text-charcoal-950 bg-amber-400"
                : "text-charcoal-400 hover:text-lume",
            )}
          >
            {level}
          </button>
        ))}
      </div>
      <span
        className="text-charcoal-500 truncate"
        title={
          autonomy === "auto"
            ? "Auto-apply: UI / layout / chart / watchlist changes apply without a per-action confirmation. Orders ALWAYS route through the confirm-before-place dialog."
            : "Ask: every proposed change waits for your accept in the diff gate."
        }
      >
        {autonomy === "auto" ? "auto-applies UI · orders always ask" : "review every change"}
      </span>
    </div>
  );
}

/** The default agent: the terminal-aware router/concierge. Bare text routes here. */
const DEFAULT_AGENT_ID = "copilot";

/**
 * First-party "generic" agents that carry NO deliberate provider preference. The
 * agent JSON schema *requires* a `defaultProvider`, so the generic concierge
 * (`copilot`) ships a boilerplate one (`ollama`) — but it must NOT shadow the
 * user's chosen/persisted default provider (that was the persistence bug: a saved
 * "DeepSeek as default" was masked forever by copilot's pin). Persona agents
 * (Buffett, researcher, …) keep their deliberate pin; only these defer. */
const GENERIC_AGENT_IDS = new Set<string>([DEFAULT_AGENT_ID]);

/** The agent's *deliberate* provider preference, or undefined for a generic agent
 *  (whose boilerplate pin must defer to the user's persisted default). */
function agentProviderPreference(
  agent: { id: string; defaultProvider?: string } | null | undefined,
): LLMProviderId | undefined {
  if (!agent || GENERIC_AGENT_IDS.has(agent.id)) {
    return undefined;
  }
  return agent.defaultProvider as LLMProviderId | undefined;
}

/** A short lead for the collapsed "short chat" view (Track 3): the first couple
 *  of sentences, hard-capped to ~220 chars at a word boundary — so even a verbose
 *  bulleted summary collapses to a glance, with the rest behind the toggle. */
function firstSentences(text: string, max = 2, maxChars = 220): string {
  const trimmed = text.trim();
  const parts = trimmed.split(/(?<=[.!?])\s+/);
  let out = parts.length <= max ? trimmed : parts.slice(0, max).join(" ").trim();
  if (out.length > maxChars) {
    out =
      out
        .slice(0, maxChars)
        .replace(/\s+\S*$/, "")
        .trim() + "…";
  }
  return out;
}

/**
 * Assistant reply body. When this turn published a research brief (Track 3), the
 * depth lives in the rendered brief — so a long reply collapses to its first
 * couple of sentences with a "show full analysis" toggle, killing the wall of
 * markdown the chat used to dump. Streaming (pending) and short replies always
 * render in full.
 */
function MessageBody({
  content,
  pending,
  briefPublished,
}: {
  content: string;
  pending?: boolean;
  briefPublished?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const isLong = content.trim().length > 200;
  const collapsible = Boolean(briefPublished) && !pending && isLong;
  const collapsed = collapsible && !expanded;
  const shown = collapsed ? firstSentences(content) : content;
  return (
    <div className="whitespace-pre-wrap">
      {shown}
      {pending && (
        <span className="text-charcoal-400 animate-pulse" aria-hidden>
          ▋
        </span>
      )}
      {collapsible && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-charcoal-400 ml-1.5 align-baseline text-[0.65rem] underline transition-colors hover:text-amber-300"
        >
          {collapsed ? "show full analysis" : "show less"}
        </button>
      )}
    </div>
  );
}

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
  const appendResearchStep = useChatHistoryStore((state) => state.appendResearchStep);
  const setPlan = useChatHistoryStore((state) => state.setPlan);
  const markBriefPublished = useChatHistoryStore((state) => state.markBriefPublished);
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

  // Active session region — routes `@TICKER` resolution locale-first (NSE for IN).
  const region = useSettingsStore((state) => state.region);

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
  const [delegateBudget, setDelegateBudget] = useState<AgentRunBudget>(DEFAULT_DELEGATE_BUDGET);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  // Tracks the last successfully dispatched prompt so the Retry button can re-send.
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);

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
  // override wins, else the active agent's *deliberate* provider preference (a
  // generic concierge has none — see GENERIC_AGENT_IDS), else the user's
  // persisted default provider.
  const effectiveProvider = useMemo<LLMProviderId>(() => {
    return providerOverride ?? agentProviderPreference(activeAgent) ?? defaultProviderId;
  }, [providerOverride, activeAgent, defaultProviderId]);
  const effectiveModel = useModelSelectionStore((state) => state.modelFor(effectiveProvider));
  // Live model catalog for the active provider — auto-fetched, TTL-cached.
  const { entry: modelCatalog, refresh: refreshModelCatalog } = useModelCatalog(effectiveProvider);
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

  // Stage a curated-slash action through the SAME diff/accept gate the agent uses
  // (FR-100): in AUTO it auto-applies (orders excluded — but no slash action is an
  // order), in ASK it queues for review. Returns nothing; surfaces the proposal in
  // the status line so an ASK-mode user knows to confirm it below.
  const enqueueSlashChange = useCallback(
    (name: string, input: Record<string, unknown>) => {
      const stamp = Date.now();
      const id = enqueueChange({
        toolCallId: `slash-${name}-${stamp}`,
        name,
        input,
        batchId: `slash-${stamp}`,
        agentName: "Slash command",
      });
      const change = useProposedChangesStore.getState().changes.find((c) => c.id === id);
      const applied = useAgentAutonomyStore.getState().autonomy === "auto";
      // In AUTO the change auto-applied (it's already gone from `changes`) → a brief
      // past-tense confirmation. In ASK the ProposedChangesReview panel below is the
      // single source of truth for what's pending — we DON'T set a second
      // "review below" status line that lingers after the change is resolved (the
      // phantom "proposed in the permission bar" bug). Clear any prior line either way.
      setStatusLine(applied ? `Applied: ${change?.title ?? name}` : null);
    },
    [enqueueChange],
  );

  // `/export` — download the current conversation as a markdown transcript. A pure
  // frontend action (no cockpit mutation), so it does not ride the gate.
  const exportConversation = useCallback(() => {
    const msgs = useChatHistoryStore.getState().messages;
    if (msgs.length === 0) {
      setStatusLine("Nothing to export yet — start a conversation first.");
      return;
    }
    const body = msgs
      .map((m) => {
        const who =
          m.role === "user"
            ? "You"
            : m.agentId
              ? (agentNameById[m.agentId] ?? m.agentId)
              : "Assistant";
        return `**${who}:**\n\n${m.content}`;
      })
      .join("\n\n---\n\n");
    const blob = new Blob([`# Vysted conversation\n\n${body}\n`], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "vysted-conversation.md";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setStatusLine(`Exported ${msgs.length} message${msgs.length === 1 ? "" : "s"} to markdown.`);
  }, [agentNameById]);

  // Route a curated-slash ACTION (FR-100). UI/layout/chart/watchlist actions ride
  // the gate via `enqueueSlashChange`; `clear`/`export` are local conveniences.
  const dispatchSlashAction = useCallback(
    (action: SlashAction, args: string) => {
      setStatusLine(null);
      switch (action) {
        case "clear":
          clearHistory();
          return;
        case "export":
          exportConversation();
          return;
        case "chart": {
          const [symbol, timeframe] = args.trim().split(/\s+/);
          if (!symbol) {
            setStatusLine("usage: /chart <ticker> [timeframe]");
            return;
          }
          enqueueSlashChange("set_chart_symbol", {
            symbol: symbol.toUpperCase(),
            ...(timeframe ? { timeframe } : {}),
          });
          return;
        }
        case "watch": {
          const symbol = args.trim().split(/\s+/)[0];
          if (!symbol) {
            setStatusLine("usage: /watch <ticker>");
            return;
          }
          enqueueSlashChange("add_to_watchlist", { symbol: symbol.toUpperCase() });
          return;
        }
        case "portfolio":
          enqueueSlashChange("open_panel", { panel: "portfolio" });
          return;
        case "sources":
          // The sources tray lives in the BriefPanel — opening it surfaces the
          // citations behind the latest answer.
          enqueueSlashChange("open_panel", { panel: "brief" });
          return;
        case "layout": {
          // A named template (research-cockpit / compare / macro-scan / single-focus)
          // or, absent an arg, the flagship research cockpit.
          const pattern = args.trim() || "research-cockpit";
          enqueueSlashChange("arrange_layout", { pattern });
          return;
        }
        case "screener":
          // `screener` is a prompt-kind command in the registry — it never reaches
          // here as an action (kept exhaustive for the union).
          return;
      }
    },
    [clearHistory, enqueueSlashChange, exportConversation],
  );

  const handleSend = useCallback(
    async (rawInput: string) => {
      // Curated slash registry (FR-100) takes precedence over the legacy verbs.
      // An ACTION dispatches through the gate and returns; a PROMPT composes its
      // template and routes as raw agent text — we DON'T re-run the legacy parser
      // on the composed string (it may itself start with "/", e.g. `/deep …`).
      const invocation = parseSlashInvocation(rawInput);
      let result: ReturnType<typeof parseSlashCommand>;
      if (invocation) {
        if (invocation.cmd.dispatch.kind === "action") {
          dispatchSlashAction(invocation.cmd.dispatch.action, invocation.args);
          return;
        }
        result = { kind: "raw", prompt: invocation.cmd.dispatch.template(invocation.args) };
      } else {
        result = parseSlashCommand(rawInput);
      }
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
      // `@analyst` / `@quant` mentions reroute the turn via a prompt prefix
      // ("[Act as a fundamental analyst] …") without switching the active agent
      // (FR-101); surface/scope/instrument mentions are left in place for the
      // context layer. No agent mention → the prompt is returned untouched.
      const prompt = applyMentionPrefixes(result.prompt);
      setLastPrompt(prompt);
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
      // agent's *deliberate* provider preference (a generic concierge has none) →
      // the user's persisted default. The key is resolved for THAT provider.
      const agentSpec = agentForCall
        ? (firstPartyAgents.find((a) => a.id === agentForCall) ??
          customAgents.find((a) => a.id === agentForCall) ??
          null)
        : null;
      const provider = providerOverride ?? agentProviderPreference(agentSpec) ?? defaultProviderId;
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
        // The keyless default (local Ollama) isn't set up yet — this is the
        // zero-setup first impression. Open the guided setup (add a key or run a
        // local model) rather than dead-ending; the data tools work meanwhile.
        setStatusLine(
          "No AI model is set up yet — opening setup. (Quotes, charts, news and web " +
            "research already work without one.)",
        );
        useOnboardingStore.getState().open();
        return;
      }

      // Thread the user's deep-research engine selection (Track 5) to the agent so
      // /deep routes to the chosen backend without depending on the model; for
      // Tongyi, forward the BYOK OpenRouter key (per-request, never persisted) so
      // it works regardless of the active provider. Read at call time.
      const deepResearchBackend = useSettingsStore.getState().deepResearchBackend;
      let deepResearchKey: string | undefined;
      if (deepResearchBackend === "tongyi") {
        try {
          deepResearchKey =
            (await getSecret(KEYCHAIN_NAMESPACES.llmProvider("openrouter"))) ?? undefined;
        } catch {
          deepResearchKey = undefined;
        }
      }
      const deepResearchOptions = {
        deepResearchBackend,
        ...(deepResearchKey ? { deepResearchKey } : {}),
      };

      // Delegate launches a DURABLE, budget-guarded background run (US9) instead
      // of a foreground stream — it survives this turn and appears in the agents
      // rail with live cost-so-far; its proposed changes still ride the diff gate.
      if (mode === "delegate" && agentForCall) {
        const terminalState = captureTerminalState();
        const snapshot: AgentContextSnapshot = {
          focusedSource: terminalState.focusedPanel,
          bySource: { __terminal__: terminalState as unknown as Record<string, unknown> },
          capturedAt: terminalState.capturedAt,
        };
        const noteId = beginAssistant({ agentId: agentForCall, providerId: provider });
        appendDelta(
          noteId,
          "Delegated to a background run — track its cost + status in the agents rail above. " +
            "It works autonomously under your budget; any changes it proposes still need your review.",
        );
        finalize(noteId, null);
        void launchDelegateRun({
          agentId: agentForCall,
          agentName: agentNameById[agentForCall] ?? agentForCall,
          prompt,
          contextSnapshot: snapshot,
          provider,
          model,
          apiKey: apiKey ?? undefined,
          budget: delegateBudget,
          // Carry only the non-secret backend choice into a DURABLE run — never
          // the OpenRouter key (a delegate run's state is persisted; secrets stay
          // off disk). A delegate Tongyi run reuses the key only if the active
          // provider is already OpenRouter.
          options: { history, deepResearchBackend },
        });
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
          if (usage) {
            updateRun(runId, {
              cost: { tokens: usage.inputTokens + usage.outputTokens, spendUsd: 0, steps: 0 },
            });
          }
          endRun(runId, "done");
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
            // Track 3: a brief published this turn (model-issued OR the runtime's
            // synthetic auto-publish) means the depth lives in the rendered brief
            // — collapse the chat essay to a short pointer.
            if (name === "publish_brief") {
              markBriefPublished(assistantId);
            } else {
              // Reflect the ACTUAL autonomy: AUTO auto-applied (no "review below"
              // phantom), ASK queued it for the diff gate below.
              const auto = useAgentAutonomyStore.getState().autonomy === "auto";
              const title = change?.title ?? name;
              appendToolStep(
                assistantId,
                auto ? `Applied: ${title}` : `Proposed: ${title} — review below`,
              );
            }
          } else if (name === "deep_research" || name === "research") {
            // Track A: the live ResearchActivity surface (fed by onResearchStep)
            // replaces the generic "Using …" one-liner for research tools, so the
            // animated step trace isn't shadowed by a static label.
          } else {
            appendToolStep(assistantId, readToolLabel(name));
          }
        },
        onResearchStep: (step) => appendResearchStep(assistantId, step),
        // Track 6 #2: surface the plan up front (visible plan-then-execute). It is
        // ADVISORY — the loop below still drives execution and stages each
        // host-action through the existing gate, so we don't pre-stage here (that
        // would double-apply). The plan just shows what's coming.
        onPlan: (plan) => setPlan(assistantId, plan),
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
            options: { history, ...deepResearchOptions },
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
      appendResearchStep,
      setPlan,
      markBriefPublished,
      appendUser,
      agentNameById,
      beginAssistant,
      clearHistory,
      customAgents,
      defaultProviderId,
      delegateBudget,
      dispatchSlashAction,
      endRun,
      enqueueChange,
      fail,
      finalize,
      firstPartyAgents,
      mode,
      providerOverride,
      providers,
      setDefaultProviderId,
      setLastPrompt,
      startRun,
      updateRun,
    ],
  );

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
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
        modelOptions={modelCatalog?.models}
        catalogNote={modelCatalog?.note}
        catalogLoading={modelCatalog?.loading}
        onProviderChange={(p) => {
          // The HUD pick wins this session AND becomes the persisted default
          // (setDefaultProviderId rides the page.tsx autosave subscription), so a
          // provider chosen in the prominent HUD survives a relaunch — not just
          // the one set in Settings.
          setProviderOverride(p);
          setDefaultProviderId(p);
        }}
        onModelChange={(m) => setModelOverride(effectiveProvider, m)}
        onKeyRequired={(p) => setKeyDialogProvider(p)}
        onRefreshModels={refreshModelCatalog}
      />
      <AutonomyToggle />
      <AnimatePresence initial={false}>
        {mode === "delegate" && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ overflow: "hidden" }}
            transition={tween(0.2)}
          >
            <BudgetConfig budget={delegateBudget} onChange={setDelegateBudget} />
          </motion.div>
        )}
      </AnimatePresence>
      <AgentsRail
        onForeground={(run) => {
          const id = beginAssistant({ agentId: run.agentId ?? undefined });
          appendDelta(
            id,
            `Delegate run "${run.agentName}" — ${run.status}` +
              (run.cost ? `, ${run.cost.tokens.toLocaleString()} tokens` : "") +
              (run.detail ? `. ${run.detail}` : "."),
          );
          finalize(id, null);
        }}
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
          <EmptyState activeAgentName={activeAgent?.name ?? null} mode={mode} />
        ) : (
          <ul className="flex flex-col gap-3">
            {messages.map((message) => (
              <motion.li
                key={message.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={tween(0.18)}
                className={cn(
                  "rounded-md border px-3 py-2 font-mono text-xs",
                  message.role === "user"
                    ? "border-charcoal-700 bg-charcoal-800 text-charcoal-100"
                    : "text-charcoal-100 border-amber-600/30 bg-amber-500/10",
                )}
              >
                <div className="text-charcoal-400 mb-1 text-[0.6rem] tracking-wide uppercase">
                  {message.role === "user"
                    ? "You"
                    : message.agentId
                      ? (agentNameById[message.agentId] ?? message.agentId)
                      : "Assistant"}
                </div>
                {message.plan && <PlanView plan={message.plan} active={!!message.pending} />}
                {message.researchSteps && message.researchSteps.length > 0 && (
                  <ResearchActivity
                    steps={message.researchSteps}
                    active={!!message.pending}
                    startedAt={message.researchStartedAt}
                  />
                )}
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
                <MessageBody
                  content={message.content}
                  pending={message.pending}
                  briefPublished={message.briefPublished}
                />
                {message.error && (
                  <div className="mt-1 flex items-center gap-2 text-[0.65rem]">
                    <span className="text-negative">Something went wrong — {message.error}</span>
                    {lastPrompt && (
                      <button
                        type="button"
                        onClick={() => {
                          void handleSend(lastPrompt);
                        }}
                        className="shrink-0 text-amber-400 underline transition-colors hover:text-amber-300"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                )}
              </motion.li>
            ))}
          </ul>
        )}
      </div>
      <ProposedChangesReview />
      <AnimatePresence initial={false}>
        {statusLine && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ overflow: "hidden" }}
            transition={tween(0.16)}
            className="border-charcoal-700 text-charcoal-300 border-t px-3 py-1 font-mono text-[0.65rem] whitespace-pre-line"
          >
            {statusLine}
          </motion.div>
        )}
      </AnimatePresence>
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
        region={region}
      />
      <KeyEntryDialog
        open={keyDialogProvider !== null}
        providerId={keyDialogProvider}
        onOpenChange={(open) => {
          if (!open) {
            const justConfigured = keyDialogProvider;
            setKeyDialogProvider(null);
            void refreshKeys();
            // A freshly-saved key re-narrows the live catalog (e.g. OpenRouter
            // /models/user) — force a refetch for that provider.
            if (justConfigured) {
              void useModelCatalogStore.getState().fetchCatalog(justConfigured, { force: true });
            }
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

/** The active persona ("lens") — one compact picker rather than a 13-chip strip
 *  that scrolls and clips mid-name. The copilot router is pinned first as the
 *  default; the full roster (12 investor personas + any custom agents) lives one
 *  click away in the dropdown. Matches the AgentHud native-select pattern so the
 *  whole HUD reads as one quiet, keyboard-driven control surface. */
function RosterStrip({ firstParty, custom, activeAgentId, onChange }: AgentPickerProps) {
  const ordered = [...firstParty].sort((a, b) =>
    a.id === DEFAULT_AGENT_ID ? -1 : b.id === DEFAULT_AGENT_ID ? 1 : 0,
  );
  if (ordered.length === 0 && custom.length === 0) {
    return null;
  }
  return (
    <div
      aria-label="Persona roster"
      className="border-charcoal-700 text-charcoal-400 flex items-center gap-1.5 border-b px-3 py-1.5 font-mono text-[0.6rem]"
    >
      <span className="shrink-0 tracking-wide uppercase">Lens</span>
      <select
        aria-label="Active persona"
        value={activeAgentId ?? DEFAULT_AGENT_ID}
        onChange={(event) => onChange(event.target.value)}
        className="bg-charcoal-800 text-charcoal-200 border-charcoal-700 min-w-0 flex-1 truncate rounded border px-1.5 py-1 font-mono text-[0.7rem] outline-none focus:ring-1 focus:ring-amber-400"
      >
        <optgroup label="First-party">
          {ordered.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </optgroup>
        {custom.length > 0 && (
          <optgroup label="Custom">
            {custom.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </optgroup>
        )}
      </select>
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
  region: Region;
}

/**
 * The chat composer with inline `/`-command and `@`-mention pickers (FR-100/101,
 * SC-023). Both pickers are keyboard-first: ``/`` or ``@`` opens the relevant
 * list, ↑/↓ moves the highlight, ↵ or ⇥ accepts, Esc dismisses. A `/cmd @entity`
 * composition works because the two matchers key off different parse states —
 * `matchSlash` fires only while typing the leading command name (no space yet),
 * `matchMention` fires on the `@` token under the caret anywhere in the line. The
 * pickers themselves are presentational; this owns the open/active/resolve state
 * and the text splicing. Mention resolution is async + locale-aware (`/resolve`),
 * race-guarded by a sequence token so a slow lookup never overwrites a newer one.
 */
function Composer({ value, onChange, onSend, disabled, mode, region }: ComposerProps) {
  const meta = agentModeMeta(mode);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [caret, setCaret] = useState(0);
  // The composer value at the moment Esc was pressed — keeps the picker dismissed
  // until the text changes again (so Esc closes without losing what was typed).
  const [dismissedAt, setDismissedAt] = useState<string | null>(null);
  // Resolved `@`-mentions, keyed by the `region:query` they were fetched for so a
  // render whose query has moved on simply ignores them (no effect-driven clear).
  const [resolved, setResolved] = useState<{ key: string; matches: MentionDef[] }>({
    key: "",
    matches: [],
  });
  // The highlighted row, tied to the picker identity it was set against; when the
  // identity changes the derived `activeIndex` falls back to the top.
  const [active, setActive] = useState<{ index: number; sig: string }>({ index: 0, sig: "" });
  const resolveSeq = useRef(0);

  const slash = matchSlash(value);
  const mention = matchMention(value, caret);
  const suppressed = dismissedAt !== null && dismissedAt === value;
  const showSlash = slash.open && slash.matches.length > 0 && !suppressed;
  const showMention = mention.open && !showSlash && !suppressed;

  // Resolve `@` mentions when the query (or region) changes — static matches plus
  // live instruments from `/resolve`. Only the async `.then` sets state (a stale
  // resolve is dropped by the seq token); a closed/changed picker is handled by
  // the render-time key guard below, so there is no synchronous effect setState.
  useEffect(() => {
    if (!showMention) {
      return;
    }
    const key = `${region}:${mention.query}`;
    const seq = (resolveSeq.current += 1);
    void resolveMention(mention.query, region).then((matches) => {
      if (seq === resolveSeq.current) {
        setResolved({ key, matches });
      }
    });
  }, [showMention, mention.query, region]);

  const mentionKey = `${region}:${mention.query}`;
  const mentionMatches = showMention && resolved.key === mentionKey ? resolved.matches : [];
  const items: (SlashCommandDef | MentionDef)[] = showSlash ? slash.matches : mentionMatches;
  const pickerOpen = (showSlash || showMention) && items.length > 0;

  // The highlight resets to the top whenever the picker identity (which list +
  // query + length) changes; arrow keys move it within that identity. Derived, so
  // there's no cascading setState-in-effect.
  const pickerSig = showSlash
    ? `s:${slash.query}:${slash.matches.length}`
    : showMention
      ? `m:${mention.query}:${mentionMatches.length}`
      : "";
  const activeIndex = active.sig === pickerSig ? active.index : 0;

  function moveActive(delta: number) {
    if (items.length === 0) {
      return;
    }
    const nextIndex = (activeIndex + delta + items.length) % items.length;
    setActive({ index: nextIndex, sig: pickerSig });
  }

  function syncCaret(el: HTMLInputElement) {
    setCaret(el.selectionStart ?? el.value.length);
  }

  function pickSlash(cmd: SlashCommandDef) {
    // Insert `/trigger ` — the trailing space closes the slash picker (matchSlash
    // needs a space-free name) and positions the caret for arguments.
    const next = `/${cmd.trigger} `;
    onChange(next);
    setDismissedAt(null);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(next.length, next.length);
        syncCaret(el);
      }
    });
  }

  function pickMention(m: MentionDef) {
    // Replace the `@token` ending at the caret with the picked token + a space.
    const pos = Math.max(0, Math.min(caret, value.length));
    const before = value.slice(0, pos);
    const after = value.slice(pos);
    const tokenStart = before.search(/@\S*$/);
    const start = tokenStart < 0 ? before.length : tokenStart;
    const next = `${before.slice(0, start)}${m.token} ${after}`;
    const newCaret = start + m.token.length + 1;
    onChange(next);
    setDismissedAt(null);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(newCaret, newCaret);
        syncCaret(el);
      }
    });
  }

  function acceptActive() {
    const item = items[activeIndex] ?? items[0];
    if (!item) {
      return;
    }
    if (showSlash) {
      pickSlash(item as SlashCommandDef);
    } else {
      pickMention(item as MentionDef);
    }
  }

  function onKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (pickerOpen) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        moveActive(1);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        moveActive(-1);
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        acceptActive();
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setDismissedAt(value);
        return;
      }
      return;
    }
    // No picker open: submit on Enter EXPLICITLY. Don't rely on the form's default
    // Enter-submit — with a React-controlled input + the picker state machine it
    // was unreliable (the enter-to-send bug). Shift+Enter is reserved (no submit)
    // for a future multi-line composer.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim()) {
        onSend(value);
      }
    }
  }

  return (
    <div className="relative">
      {pickerOpen && (
        <div className="absolute right-0 bottom-full left-0 mb-1 max-h-[min(18rem,45vh)] overflow-y-auto px-2">
          {showSlash ? (
            <SlashCommandPicker
              matches={slash.matches}
              activeIndex={activeIndex}
              onPick={pickSlash}
            />
          ) : (
            <MentionPicker
              matches={mentionMatches}
              activeIndex={activeIndex}
              onPick={pickMention}
            />
          )}
        </div>
      )}
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
          ref={inputRef}
          aria-label="Chat input"
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            setDismissedAt(null);
            syncCaret(event.target);
          }}
          onKeyDown={onKeyDown}
          onKeyUp={(event) => syncCaret(event.currentTarget)}
          onClick={(event) => syncCaret(event.currentTarget)}
          onSelect={(event) => syncCaret(event.currentTarget)}
          placeholder={`${meta.label} — ${meta.hint}`}
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
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
    </div>
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
  onResearchStep: (step: ResearchStepView) => void;
  onPlan: (plan: AgentPlanView) => void;
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
      } else if (event.kind === "research_step") {
        internal.onResearchStep({
          stepKind: event.stepKind,
          detail: event.detail,
          latencyMs: event.latencyMs,
          status: event.status,
          index: event.index,
        });
      } else if (event.kind === "agent_plan") {
        internal.onPlan({ goal: event.goal, steps: event.steps, note: event.note });
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
