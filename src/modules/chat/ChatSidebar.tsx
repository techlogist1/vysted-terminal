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
import { ArrowUp, Plus, Sparkles, Square } from "lucide-react";

import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { launchDelegateRun } from "@/lib/delegate-runs";
import { isHostActionMutation } from "@/lib/host-actions";
import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { completeIncomplete, hasIncompleteCodeFence } from "@/lib/markdown-stream";
import { tween } from "@/lib/motion";
import { validateProvider } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useAgentCommandStore } from "@/store/agent-command";
import { useChatPendingStore } from "@/store/chat-pending";
import { type ResearchDepth, useResearchDepthStore } from "@/store/research-depth";
import { useAgentModeStore } from "@/store/agent-mode";
import { useAgentSpacesStore } from "@/store/agent-spaces";
import { type AgentRunBudget, useAgentRunsStore } from "@/store/agent-runs";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import {
  type AgentPlanView,
  type ChatMessage,
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
import { useSymbolsStore } from "@/store/symbols";
import { MarkdownBody } from "@/modules/research/brief-blocks";
import type { Region } from "@/lib/region";
import type { AgentContextSnapshot, LLMProviderId, LLMStreamEvent } from "../../../types/ai";
import { type AgentMode, AGENT_MODES, agentModeMeta } from "../../../types/agent-modes";
import { AgentsRail } from "./AgentsRail";
import { BudgetConfig, DEFAULT_DELEGATE_BUDGET } from "./BudgetConfig";
import { ComposerMetaRow } from "./ComposerMetaRow";
import { captureTerminalState } from "./context-provider";
import { applyMentionPrefixes, type MentionDef, matchMention, resolveMention } from "./mentions";
import { MentionPicker } from "./MentionPicker";
import { PlanView } from "./PlanView";
import { ProposedChangesReview } from "./ProposedChangesReview";
import { formatElapsed, ResearchActivity } from "./ResearchActivity";
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
import { SuggestionChips } from "./SuggestionChips";

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

/** Title-case fallback for an agent id the roster hasn't resolved yet — the lens
 *  chip must NEVER show a raw id ("warren" → "Warren", "portfolio_advisor" →
 *  "Portfolio Advisor"). The roster display name always wins when present. */
function humanizeAgentId(id: string): string {
  return id
    .split(/[_-]+/)
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
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

/** Stable no-op cite handler — chat has no source rail, so [n] chips render inert.
 *  A module-level reference keeps MarkdownBody's `ctx` useMemo from recomputing on
 *  every render (a fresh `() => {}` would defeat it). */
const NOOP_CITE = () => {};

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
  // The chat's known-ticker set is the user's watchlist (precision over recall:
  // a chip fires only on $CASHTAG or one of these symbols, never a bare word).
  const watchlist = useSymbolsStore((s) => s.entries);
  const chatKnownSet = useMemo(
    () => new Set(watchlist.map((e) => e.symbol.toUpperCase())),
    [watchlist],
  );

  const isLong = content.trim().length > 200;
  const collapsible = Boolean(briefPublished) && !pending && isLong;
  const collapsed = collapsible && !expanded;
  const shown = collapsed ? firstSentences(content) : content;

  // While streaming, repair the trailing in-flight token so the live markdown
  // doesn't flicker between broken/fixed on every delta. The pulsing caret is
  // suppressed inside an open code fence (where it would render as literal text).
  const source = pending ? completeIncomplete(shown) : shown;
  const caret = pending && !hasIncompleteCodeFence(shown);

  return (
    <div className="flex flex-col gap-3">
      <MarkdownBody source={source} known={chatKnownSet} onCite={NOOP_CITE} />
      {caret && (
        <span className="text-charcoal-400 -mt-3 animate-pulse" aria-hidden>
          ▋
        </span>
      )}
      {collapsible && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-charcoal-400 text-caption hover:text-charcoal-100 -mt-2 self-start align-baseline underline transition-colors"
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
 * The step trace for one assistant turn — language first, telemetry behind a
 * disclosure (R7 Track C). WHILE STREAMING the live activity renders as before
 * (visible plan → animated research trace → tool-step lines: the one place the
 * peach accent belongs) so the work is visibly underway. Once the run finishes
 * the whole trace collapses into ONE quiet line above the prose —
 * `▸ Worked for 12s · 7 steps` — that expands on demand to the full
 * ResearchActivity-style detail. Expanded state is per-message; the default is
 * collapsed, so the transcript reads as prose, not telemetry.
 */
function ActivityTrace({ message }: { message: ChatMessage }) {
  const [expanded, setExpanded] = useState(false);
  const researchSteps = message.researchSteps ?? [];
  const toolSteps = message.toolSteps ?? [];
  const stepCount = researchSteps.length + toolSteps.length;
  if (stepCount === 0 && !message.plan) {
    return null;
  }

  const detail = (active: boolean) => (
    <>
      {message.plan && <PlanView plan={message.plan} active={active} />}
      {researchSteps.length > 0 && (
        <ResearchActivity
          steps={researchSteps}
          active={active}
          startedAt={message.researchStartedAt}
        />
      )}
      {toolSteps.length > 0 && (
        <ul className="mb-1.5 flex flex-col gap-0.5">
          {toolSteps.map((step, i) => (
            <li key={i} className="text-charcoal-400 text-caption flex items-center gap-1">
              <span className="text-charcoal-500">→</span> {step}
            </li>
          ))}
        </ul>
      )}
    </>
  );

  if (message.pending) {
    return detail(true);
  }

  // Honest duration: the sum of measured step latencies (the same number the
  // expanded trace footer shows) — never a fabricated wall-clock guess.
  const totalLatency = researchSteps.reduce((sum, s) => sum + (s.latencyMs ?? 0), 0);
  const label =
    stepCount > 0
      ? `Worked${totalLatency > 0 ? ` for ${formatElapsed(totalLatency)}` : ""} · ${stepCount} step${stepCount === 1 ? "" : "s"}`
      : "Planned";

  return (
    <div className="mb-1.5">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        aria-label={`${expanded ? "Collapse" : "Expand"} step trace — ${label}`}
        className="text-charcoal-500 text-micro hover:text-charcoal-300 flex items-center gap-1.5 transition-colors"
      >
        <span aria-hidden>{expanded ? "▾" : "▸"}</span>
        <span className="tabular-nums">{label}</span>
      </button>
      {expanded && <div className="mt-1.5">{detail(false)}</div>}
    </div>
  );
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
  const stopMessage = useChatHistoryStore((state) => state.stopAssistantMessage);
  const fail = useChatHistoryStore((state) => state.failAssistantMessage);
  const clearHistory = useChatHistoryStore((state) => state.clear);
  const streaming = useChatHistoryStore((state) => state.streamingMessageId !== null);
  // A research run is LIVE when the streaming message has research steps — the
  // ONE place the peach accent belongs (the depth slider's live stop).
  const researchLive = useChatHistoryStore((state) => {
    if (!state.streamingMessageId) {
      return false;
    }
    const live = state.messages.find((m) => m.id === state.streamingMessageId);
    return !!live && (live.researchSteps?.length ?? 0) > 0;
  });

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
  // Clean composer: Mode / Lens / Provider+Model / Autonomy are ALL inline and
  // always visible (no disclosure gear — the Round-2 "hide the stack" anti-pattern
  // is gone). There is no "Deep Research" toggle: research is ONE model and depth
  // is the agent's call + the brief's "Go deeper" escalation (FR-115 / SC-028).
  // Multiple agent spaces (chat threads/pages) — switching swaps the transcript.
  const spaces = useAgentSpacesStore((s) => s.spaces);
  const activeSpaceId = useAgentSpacesStore((s) => s.activeId);
  const newSpace = useAgentSpacesStore((s) => s.newSpace);
  const switchSpace = useAgentSpacesStore((s) => s.switchTo);
  const closeSpace = useAgentSpacesStore((s) => s.closeSpace);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  // Tracks the last successfully dispatched prompt so the Retry button can re-send.
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);
  // The in-flight stream's AbortController, lifted to a ref so the composer's
  // stop square can reach it (R7 Track C).
  const abortRef = useRef<AbortController | null>(null);
  // Three-stop research depth (the meta-row slider) + the depth the LIVE run
  // was sent at — the slider accents its active stop only while that run lives.
  const researchDepth = useResearchDepthStore((s) => s.depth);
  const setResearchDepth = useResearchDepthStore((s) => s.setDepth);
  const [lastSentDepth, setLastSentDepth] = useState<ResearchDepth | null>(null);

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

      // Auto-title the space from its first prompt (Perplexity-style) so the space
      // tabs read as real threads, not "Chat 1/2/3". Read via getState to avoid
      // adding a dep to this memoised handler.
      if (useChatHistoryStore.getState().messages.length === 0) {
        const cleaned = prompt.replace(/^\/\S+\s*/, "").trim();
        const title = cleaned.length > 28 ? `${cleaned.slice(0, 28).trim()}…` : cleaned;
        if (title) {
          useAgentSpacesStore.getState().renameActive(title);
        }
      }
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
      // /deep routes to the chosen backend without depending on the model. Read at
      // call time.
      const deepResearchBackend = useSettingsStore.getState().deepResearchBackend;
      // WS5: thread the RESOLVED model's native-search capability so the sidecar can
      // gate OpenRouter per-MODEL (the live catalog lives here on the frontend —
      // keyless-first, no extra network on the sidecar hot path). The five
      // provider-level native providers ignore this hint; non-OpenRouter models
      // simply leave it undefined.
      const modelWebSearch =
        useModelCatalogStore.getState().byProvider[provider]?.models.find((m) => m.id === model)
          ?.webSearch ?? undefined;
      // The meta-row depth slider (R7): read at call time, threaded into the
      // invocation options (streaming.ts puts it on the wire as snake_case
      // `research_depth`). Remember what THIS send carried so the slider can
      // accent its live stop honestly.
      const depthForSend = useResearchDepthStore.getState().depth;
      setLastSentDepth(depthForSend);
      const deepResearchOptions = {
        deepResearchBackend,
        researchDepth: depthForSend,
        ...(modelWebSearch ? { modelWebSearch } : {}),
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
          // Carry only the non-secret backend choice + per-model search capability
          // into a DURABLE run (its state is persisted; secrets stay off disk).
          options: { history, ...deepResearchOptions },
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
      // aborts the stream. The controller is lifted to `abortRef` so the
      // composer's stop square aborts the SAME in-flight run.
      const controller = new AbortController();
      abortRef.current = controller;
      const runId = startRun({
        agentId: agentForCall,
        agentName,
        mode,
        abort: () => controller.abort(),
      });

      const handlers = makeHandlers({
        onDelta: (text) => appendDelta(assistantId, text),
        onError: (message) => {
          if (abortRef.current === controller) {
            abortRef.current = null;
          }
          if (controller.signal.aborted) {
            // User-stopped (the composer's stop square / rail cancel): the
            // partial message stands, quietly marked "stopped" — not an error.
            stopMessage(assistantId);
            endRun(runId, "cancelled");
          } else {
            fail(assistantId, message);
            endRun(runId, "error", message);
          }
        },
        onDone: (usage) => {
          if (abortRef.current === controller) {
            abortRef.current = null;
          }
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
              // phantom), ASK queued it for the diff gate below. ORDERS are EXEMPT
              // from auto-apply (§6.5; proposed-changes excludes kind === "order"),
              // so an order always stages — never narrate it as "Applied", in any
              // mode, or the transcript would lie about an unconfirmed order.
              const auto =
                useAgentAutonomyStore.getState().autonomy === "auto" && change?.kind !== "order";
              const title = change?.title ?? name;
              appendToolStep(
                assistantId,
                auto ? `Applied: ${title}` : `Proposed: ${title} — review below`,
              );
            }
          } else if (name === "research") {
            // Track A: the live ResearchActivity surface (fed by onResearchStep)
            // replaces the generic "Using …" one-liner for the research tool, so the
            // animated step trace isn't shadowed by a static label. (ONE research
            // tool now — depth is internal, so this single name covers every tier.)
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
            // Autonomy rides the request so the sidecar narrates host-actions
            // truthfully (auto = applied/past-tense, ask = staged for review).
            // Orders always need confirmation regardless (§6.5).
            autonomy: useAgentAutonomyStore.getState().autonomy,
            apiKey: apiKey ?? undefined,
            options: { history, ...deepResearchOptions },
          },
          { ...handlers, signal: controller.signal },
        );
      } else {
        // FR-116 / coherence: the raw-chat path must preserve conversation context
        // too, so a mid-conversation MODEL SWAP doesn't reset the thread. `history`
        // (the last-10 user/assistant turns, captured above BEFORE appendUser, so it
        // excludes the current prompt) is prepended; previously this path sent only
        // the single current turn and silently dropped everything before it.
        await streamChat(
          {
            provider,
            model,
            messages: [...history, { role: "user", content: prompt }],
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
      stopMessage,
      firstPartyAgents,
      mode,
      providerOverride,
      providers,
      setDefaultProviderId,
      setLastPrompt,
      setLastSentDepth,
      startRun,
      updateRun,
    ],
  );

  // Agent-command channel (FR-115): a non-chat module — the brief panel's "Go
  // deeper" affordance, a first-run "try this" chip — pushes a prompt here, and
  // we route it through the SAME `handleSend` (one send path: provider/model/
  // history/gate). Track the consumed `seq` so a repeat (clicking "Go deeper"
  // twice) re-fires. While a stream is in flight we DON'T consume the seq — the
  // effect re-runs when `streaming` flips to false and dispatches then, so a
  // "Go deeper" click queued mid-run escalates the moment the current run ends
  // (no interleaving, and no synchronous setState in the effect body).
  const lastAgentCmdSeq = useRef(0);
  const agentCommand = useAgentCommandStore((s) => s.command);
  useEffect(() => {
    if (!agentCommand || agentCommand.seq === lastAgentCmdSeq.current || streaming) {
      return;
    }
    lastAgentCmdSeq.current = agentCommand.seq;
    void handleSend(agentCommand.prompt);
  }, [agentCommand, streaming, handleSend]);

  // Drain the FIFO prompt queue (R7 Track C): prompts typed while a stream was
  // in flight (and the palette's one-shot "Ask AI" handoff) send IN ORDER, one
  // at a time, through the SAME handleSend the moment nothing is streaming.
  // `handleSend` resolves only when its stream finishes, so awaiting it serial-
  // izes the drain; the ref guards the effect re-running mid-drain (each send
  // flips `streaming`, re-firing this effect).
  const queueLength = useChatPendingStore((s) => s.queue.length);
  const drainingRef = useRef(false);
  useEffect(() => {
    if (streaming || drainingRef.current || queueLength === 0) {
      return;
    }
    drainingRef.current = true;
    void (async () => {
      try {
        for (;;) {
          // Re-check between sends — another path (agent-command) may have
          // started a stream while we awaited.
          if (useChatHistoryStore.getState().streamingMessageId !== null) {
            break;
          }
          const next = useChatPendingStore.getState().consumePrompt();
          if (next === null) {
            break;
          }
          if (next.trim()) {
            await handleSend(next);
          }
        }
      } finally {
        drainingRef.current = false;
      }
    })();
  }, [streaming, queueLength, handleSend]);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      {/* Agent spaces — multiple chat threads/pages (Perplexity/Cursor). Switching
          archives the live transcript and restores the target's. */}
      <div className="border-charcoal-700 flex items-center gap-1 overflow-x-auto border-b px-2 py-1">
        {spaces.map((s) => {
          const active = s.id === activeSpaceId;
          return (
            <div
              key={s.id}
              className={cn(
                "text-caption rounded-control flex shrink-0 items-center font-mono",
                active ? "bg-charcoal-800 text-charcoal-100" : "text-charcoal-400",
              )}
            >
              <button
                type="button"
                onClick={() => switchSpace(s.id)}
                className={cn("max-w-[10rem] truncate px-2 py-1 transition-colors", {
                  "hover:text-lume": !active,
                })}
                title={s.title}
              >
                {s.title}
              </button>
              {spaces.length > 1 && (
                <button
                  type="button"
                  onClick={() => closeSpace(s.id)}
                  aria-label={`Close ${s.title}`}
                  className="text-charcoal-500 hover:text-negative px-1 py-1 transition-colors"
                >
                  ×
                </button>
              )}
            </div>
          );
        })}
        <button
          type="button"
          onClick={newSpace}
          aria-label="New chat space"
          title="New chat space"
          className="text-charcoal-400 rounded-control hover:text-charcoal-100 shrink-0 px-2 py-1 transition-colors"
        >
          <Plus className="size-3" />
        </button>
      </div>
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
          <ul className="flex flex-col gap-2">
            {messages.map((message) => (
              <motion.li
                key={message.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={tween(0.18)}
                className={cn(
                  "text-body rounded-none border px-3 py-1.5 font-mono",
                  message.role === "user"
                    ? "border-charcoal-700 bg-charcoal-800 text-charcoal-100"
                    : "border-charcoal-700 bg-charcoal-875 text-charcoal-100",
                )}
              >
                <div className="text-charcoal-400 text-micro mb-1">
                  {message.role === "user"
                    ? "You"
                    : message.agentId
                      ? (agentNameById[message.agentId] ?? message.agentId)
                      : "Assistant"}
                </div>
                <ActivityTrace message={message} />
                <MessageBody
                  content={message.content}
                  pending={message.pending}
                  briefPublished={message.briefPublished}
                />
                {message.stopped && (
                  <div className="text-charcoal-500 text-caption mt-1">stopped</div>
                )}
                {message.error && (
                  <div className="text-caption mt-1 flex items-center gap-2">
                    <span className="text-negative">Something went wrong — {message.error}</span>
                    {lastPrompt && (
                      <button
                        type="button"
                        onClick={() => {
                          void handleSend(lastPrompt);
                        }}
                        className="text-charcoal-300 hover:text-lume shrink-0 underline transition-colors"
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
            className="border-charcoal-700 text-charcoal-300 text-caption border-t px-3 py-1 font-mono whitespace-pre-line"
          >
            {statusLine}
          </motion.div>
        )}
      </AnimatePresence>
      {/* ── Composer dock — ONE unit (R7 Track C, Cursor-grade): queued-prompt
          chips → the bordered auto-growing field with send/stop INSIDE → one
          quiet 24px meta row (mode · lens · depth ··· autonomy · model) whose
          chips open anchored popovers. The standing select rows are gone. ── */}
      <div className="border-charcoal-700 border-t">
        {/* Delegate-only: the BudgetGuard ceiling for the durable background run. */}
        {mode === "delegate" && (
          <BudgetConfig budget={delegateBudget} onChange={setDelegateBudget} />
        )}
        <QueuedPrompts />
        <Composer
          value={composer}
          onChange={setComposer}
          onSend={(text) => {
            setComposer("");
            // While a stream is in flight the prompt queues (visible chips
            // above the field) and drains in order when the stream ends; the
            // input itself is sent verbatim — depth rides `options`, never
            // prepended prose.
            if (useChatHistoryStore.getState().streamingMessageId !== null) {
              useChatPendingStore.getState().queuePrompt(text);
            } else {
              void handleSend(text);
            }
          }}
          onStop={() => abortRef.current?.abort()}
          streaming={streaming}
          mode={mode}
          region={region}
        />
        <ComposerMetaRow
          mode={mode}
          onModeChange={setMode}
          lensLabel={activeAgent?.name ?? humanizeAgentId(activeAgentId ?? DEFAULT_AGENT_ID)}
          firstParty={firstPartyAgents}
          custom={customAgents}
          activeAgentId={activeAgentId ?? DEFAULT_AGENT_ID}
          onLensChange={(id) => {
            setActiveAgentId(id);
            setProviderOverride(null);
          }}
          depth={researchDepth}
          onDepthChange={setResearchDepth}
          liveDepth={researchLive ? lastSentDepth : null}
          providers={providers}
          provider={effectiveProvider}
          model={effectiveModel}
          providerConfigured={providerConfigured}
          modelOptions={modelCatalog?.models}
          catalogNote={modelCatalog?.note}
          catalogLoading={modelCatalog?.loading}
          onProviderChange={(p) => {
            // The pick wins this session AND becomes the persisted default
            // (rides the page.tsx autosave), so it survives a relaunch.
            setProviderOverride(p);
            setDefaultProviderId(p);
          }}
          onModelChange={(m) => setModelOverride(effectiveProvider, m)}
          onKeyRequired={(p) => setKeyDialogProvider(p)}
          onRefreshModels={refreshModelCatalog}
        />
      </div>
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

/** The visible FIFO of prompts queued while a stream is in flight — quiet,
 *  removable chips directly above the composer field. Renders nothing when the
 *  queue is empty; the drain order is the chip order (oldest first). */
function QueuedPrompts() {
  const queue = useChatPendingStore((s) => s.queue);
  const removePrompt = useChatPendingStore((s) => s.removePrompt);
  if (queue.length === 0) {
    return null;
  }
  return (
    <ul aria-label="Queued prompts" className="flex flex-wrap gap-1 px-3 pt-2">
      {queue.map((prompt, index) => (
        <li
          key={`${index}-${prompt}`}
          className="border-charcoal-700 bg-charcoal-850 text-micro text-charcoal-400 rounded-control flex h-6 max-w-[14rem] items-center gap-1 border px-2 font-mono"
        >
          <span className="truncate" title={prompt}>
            {prompt}
          </span>
          <button
            type="button"
            aria-label={`Remove queued prompt: ${prompt}`}
            onClick={() => removePrompt(index)}
            className="text-charcoal-500 hover:text-charcoal-200 shrink-0 transition-colors"
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  );
}

function ContextBadge({ text }: { text: string }) {
  return (
    <div
      aria-label="Panel context"
      className="border-charcoal-700 text-charcoal-300 text-caption border-b px-3 py-1.5 font-mono tracking-wide uppercase"
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
  // Hero empty state (§13): FILL the dock column — a centered identity block, then
  // a distributed suggestion set occupying the remaining height. No `justify-center`
  // floating a small block in a tall column (the R4 dead-void failure). The identity
  // block sits in the upper-middle (`mt-auto`/`mb-auto` distribute the slack), and the
  // chips anchor toward the composer so the column reads intentional top-to-bottom.
  return (
    <div className="flex h-full flex-col gap-6 px-6 py-8 text-center">
      <div className="mt-auto flex flex-col items-center gap-3">
        <Sparkles className="text-charcoal-500 size-6" strokeWidth={1.5} aria-hidden />
        <div className="flex max-w-xs flex-col items-center gap-1">
          <p className="text-charcoal-200 text-panel-title">
            Ask anything about what you&rsquo;re viewing
          </p>
          <p className="text-charcoal-500 text-caption">
            I read the terminal — your portfolio, a chart, a screen — and can drive it.
          </p>
        </div>
      </div>
      <div className="mb-auto flex flex-col items-center gap-3">
        <p className="text-charcoal-500 text-micro tracking-wide uppercase">Try this</p>
        <SuggestionChips />
        <p className="text-charcoal-500 text-caption max-w-xs">
          Mode <span className="text-charcoal-300">{meta.label}</span>
          {activeAgentName && (
            <>
              {" · "}lens <span className="text-charcoal-300">{activeAgentName}</span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  /** Submit the text — the parent sends it, or queues it while streaming. */
  onSend: (text: string) => void;
  /** Abort the in-flight stream (the send square morphs into stop). */
  onStop: () => void;
  /** True while a foreground stream is live — Enter queues, the button stops. */
  streaming: boolean;
  mode: AgentMode;
  region: Region;
}

/** Max field height before the textarea scrolls — ~6 lines of text-body
 *  (13px × 1.5 ≈ 19.5px each) plus the field's vertical padding. */
const COMPOSER_MAX_HEIGHT_PX = 144;

/**
 * The chat composer — ONE bordered unit (R7 Track C): an auto-growing textarea
 * (one line min, ~6 lines max) with the send/stop square pinned INSIDE the
 * field's bottom-right. While a stream is live the square morphs into STOP and
 * Enter queues the typed prompt instead of sending (the visible FIFO above the
 * field); Shift+Enter inserts a newline. The inline `/`-command and `@`-mention
 * pickers (FR-100/101, SC-023) are unchanged: keyboard-first, ↑/↓ moves, ↵/⇥
 * accepts, Esc dismisses; `matchSlash` fires only while typing the leading
 * command name, `matchMention` on the `@` token under the caret. Mention
 * resolution stays async + locale-aware, race-guarded by a sequence token.
 */
function Composer({ value, onChange, onSend, onStop, streaming, mode, region }: ComposerProps) {
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
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

  function syncCaret(el: HTMLTextAreaElement) {
    setCaret(el.selectionStart ?? el.value.length);
  }

  // Auto-grow: one-line baseline, expands with content, capped at ~6 lines
  // (then the textarea scrolls). Height math runs off the real scrollHeight so
  // wrapped lines count too.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) {
      return;
    }
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, COMPOSER_MAX_HEIGHT_PX)}px`;
  }, [value]);

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

  function onKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
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
    // No picker open: submit on Enter EXPLICITLY (a textarea never form-submits
    // on Enter). While a stream is live the parent QUEUES the prompt instead of
    // sending — typing stays enabled throughout. Shift+Enter inserts a newline.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (value.trim()) {
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
        className="px-3 pt-2 pb-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (value.trim()) {
            onSend(value);
          }
        }}
      >
        {/* ONE bordered unit (§14): the auto-growing textarea with the send/stop
            square pinned INSIDE the field's bottom-right. Minimal, monochrome —
            the peach accent is reserved for live agent activity, never the send. */}
        <div className="bg-charcoal-850 border-charcoal-700 focus-within:border-charcoal-600 rounded-control relative border transition-colors">
          <textarea
            ref={inputRef}
            rows={1}
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
            placeholder={
              streaming
                ? "Queue the next prompt…"
                : mode === "delegate"
                  ? "Delegate a task…"
                  : "Ask anything…"
            }
            autoComplete="off"
            spellCheck={false}
            className="text-charcoal-100 placeholder:text-charcoal-500 text-body block w-full resize-none bg-transparent py-2 pr-10 pl-3 font-mono outline-none"
          />
          {streaming ? (
            <button
              type="button"
              aria-label="Stop the in-flight run"
              title="Stop — the partial answer stands"
              onClick={onStop}
              className="rounded-control bg-charcoal-200 text-charcoal-950 hover:bg-lume absolute right-2 bottom-2 flex size-6 shrink-0 items-center justify-center transition-colors"
            >
              <Square className="size-2.5" fill="currentColor" strokeWidth={0} />
            </button>
          ) : (
            <button
              type="submit"
              aria-label="Send message"
              disabled={value.trim().length === 0}
              className={cn(
                "rounded-control absolute right-2 bottom-2 flex size-6 shrink-0 items-center justify-center transition-colors",
                value.trim().length > 0
                  ? "bg-charcoal-200 text-charcoal-950 hover:bg-lume"
                  : "text-charcoal-600",
              )}
            >
              <ArrowUp className="size-3.5" strokeWidth={2.25} />
            </button>
          )}
        </div>
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
