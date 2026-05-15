/**
 * Vysted Terminal — AI provider, agent, and streaming protocol types.
 *
 * Defines the wire-level contract for Phase 3's AI layer:
 *
 * - The seven BYOK LLM providers and their model identifiers.
 * - The streaming event protocol that the sidecar emits over SSE (`text/
 *   event-stream`) and the frontend re-assembles into a chat conversation.
 * - The agent-invocation envelope that carries a focused panel's context
 *   alongside the user prompt so the agent reasons over real terminal state
 *   rather than abstract questions.
 *
 * This file is foundation-tier — Teammate A (provider adapters + chat
 * sidebar), Teammate B (MCP server's `invoke_agent` tool), and Teammate C
 * (Custom Agent Builder UI) all import from here. Changes that would break
 * any of those callers are coordinated at the foundation level, not
 * unilaterally.
 *
 * Agent CONFIG shape lives separately on the locked plugin contract
 * (`types/plugin.ts` → `AgentSpec`) — this file complements it with the
 * runtime types around invocation + streaming.
 */

// ---------------------------------------------------------------------------
// Providers + models
// ---------------------------------------------------------------------------

/** The seven BYOK providers Phase 3 ships. */
export type LLMProviderId =
  | "anthropic"
  | "openai"
  | "gemini"
  | "groq"
  | "ollama"
  | "deepseek"
  | "xai";

/**
 * A free-form model identifier (e.g. `"claude-opus-4-7"`, `"gpt-4.1-mini"`,
 * `"llama3.1:70b"`). The host does not enumerate models — providers expose
 * their own catalogs via `POST /llm/models` (sidecar) and the agent builder
 * UI surfaces them as a dropdown. Strings keep the contract open to model
 * releases that ship between Vysted versions.
 */
export type LLMModelId = string;

/** Per-provider summary surfaced in settings + agent builder. */
export interface LLMProviderInfo {
  id: LLMProviderId;
  /** Display name shown in the UI. */
  label: string;
  /** Whether this provider is BYOK (`true` for all except `ollama`). */
  requiresKey: boolean;
  /** Default endpoint URL — most providers are fixed; Ollama defaults to localhost. */
  defaultBaseUrl?: string;
}

// ---------------------------------------------------------------------------
// Chat messages
// ---------------------------------------------------------------------------

/** The four roles in a chat conversation; mirrors the OpenAI/Anthropic shape. */
export type LLMRole = "system" | "user" | "assistant" | "tool";

/**
 * One message in a chat conversation. `tool_call_id` is set on messages with
 * `role: "tool"` to associate a tool result with its originating tool-use
 * block in the prior assistant message.
 */
export interface LLMMessage {
  role: LLMRole;
  content: string;
  /** Stable id of the tool-use block this message responds to (role `"tool"` only). */
  tool_call_id?: string;
  /** Free-form metadata (model id, provider id, timing); not echoed back to the provider. */
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Streaming protocol
// ---------------------------------------------------------------------------

/**
 * One event in a streaming chat response. The sidecar emits these over SSE;
 * `text/event-stream` lines decode to JSON objects of this shape. Discriminated
 * union on `kind` so the frontend can dispatch each event narrowly.
 */
export type LLMStreamEvent =
  | { kind: "delta"; text: string }
  | { kind: "tool_use"; toolCallId: string; name: string; input: Record<string, unknown> }
  | { kind: "thinking"; text: string }
  | { kind: "done"; usage?: LLMUsage; finishReason?: string }
  | { kind: "error"; message: string };

/** Token usage reported on `done`. Optional — some providers omit usage on stream. */
export interface LLMUsage {
  inputTokens: number;
  outputTokens: number;
  /** Anthropic-style cache hits, when reported by the provider. */
  cacheReadInputTokens?: number;
  cacheCreationInputTokens?: number;
}

// ---------------------------------------------------------------------------
// Agent invocation
// ---------------------------------------------------------------------------

/**
 * Snapshot of the focused panel's state at agent-invocation time. Agents
 * read this to ground their reasoning in actual terminal state (e.g. Buffett
 * sees that the chart is on AAPL daily with RSI active when asked "is this
 * cheap?"). Built by `usePanelContext` (`src/store/panel-context.ts`).
 */
export interface AgentContextSnapshot {
  /** Which panel was focused when the agent was invoked. */
  focusedSource: string | null;
  /** Free-form per-panel state, keyed by `source` (see `PanelContextEvent.source`). */
  bySource: Record<string, unknown>;
  /** Epoch milliseconds when this snapshot was captured. */
  capturedAt: number;
}

/** Request envelope for `POST /agents/{agent_id}/invoke`. */
export interface AgentInvocationRequest {
  /** User prompt. */
  prompt: string;
  /** Panel context to attach to the system prompt (optional). */
  contextSnapshot?: AgentContextSnapshot;
  /** Provider override (otherwise the agent's `defaultProvider` wins). */
  provider?: LLMProviderId;
  /** Model override (otherwise the agent's recommended model wins). */
  model?: LLMModelId;
  /**
   * BYOK API key for the resolved provider. Frontend reads this from the OS
   * keychain via `src/lib/keychain.ts` and passes it per-request; the sidecar
   * never persists it.
   */
  apiKey?: string;
}

/** Unary result of an agent invocation — for callers that don't stream (e.g. MCP tools). */
export interface AgentInvocationResult {
  ok: boolean;
  /** Full aggregated assistant text. */
  content: string;
  /** Token usage reported by the provider. */
  usage?: LLMUsage;
  /** Agent id that produced the result. */
  agentId: string;
  /** Human-readable error message if `ok` is false. */
  error?: string;
}
