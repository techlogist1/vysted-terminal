/**
 * Streaming client — SSE wrapper around the sidecar's chat / agent endpoints.
 *
 * Native ``EventSource`` only supports GET, and the chat endpoint is POST
 * (request body carries the API key + messages array). So we use ``fetch``
 * with a streaming response body and a custom SSE parser. The on-wire shape
 * matches ``data: <json>\n\n`` frames where each ``<json>`` is one
 * ``LLMStreamEvent`` discriminated-union member.
 */

import { normalizeBriefDepth } from "@/lib/brief-ingest";
import { buildSearchHeaders } from "@/lib/search-headers";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useBriefStore } from "@/store/brief";
import { useSettingsStore } from "@/store/settings";
import type {
  AgentInvocationRequest,
  LLMMessage,
  LLMProviderId,
  LLMStreamEvent,
} from "../../../types/ai";
import type { BriefStepKind, BriefStepStatus } from "../../../types/brief";

/**
 * A structured error frame (R10 D43, Team ERRORS contract): `{kind:"error",
 * message, action?, detail?, code?}`. Structurally assignable to the legacy
 * `{kind:"error", message}` union member, so every existing consumer keeps
 * working; the chat surface reads the extra fields via {@link errorFrameOf}.
 */
export interface StreamErrorFrame {
  kind: "error";
  message: string;
  /** The next step in plain language ("Top up or switch provider in Settings"). */
  action?: string;
  /** The raw provider text — shown behind a "Details" disclosure only. */
  detail?: string;
  /** Machine tag ("provider_402", "network", "auth", …). */
  code?: string;
}

/** The structured fields of an error event, or null for a legacy plain error. */
export function errorFrameOf(
  event: LLMStreamEvent,
): Pick<StreamErrorFrame, "action" | "detail" | "code"> | null {
  if (event.kind !== "error") {
    return null;
  }
  const frame = event as StreamErrorFrame;
  if (frame.action === undefined && frame.detail === undefined && frame.code === undefined) {
    return null;
  }
  return { action: frame.action, detail: frame.detail, code: frame.code };
}

/** The runtime's `research:begin {run_id} depth={depth} query={…}` engine step
 *  (Team RUNTIME contract) — the frontend keys its in-flight brief state on it. */
const RESEARCH_BEGIN_RE = /^research:begin\s+(\S+)\s+depth=(\S+)(?:\s+query=(.*))?$/;

const BRIEF_STEP_KINDS = new Set<string>([
  "plan",
  "tool",
  "search",
  "compress",
  "distill",
  "reflect",
  "synthesize",
  "engine",
]);

/**
 * Feed the brief lifecycle store from the research-step channel (R10 D39):
 * the `research:begin` engine step transitions the panel to in_flight, and
 * every subsequent step rides into the in-flight trace (the store ignores
 * steps outside a run). One chokepoint — every SSE consumer (chat, palette
 * one-shots) keeps the panel honest without re-implementing the parse.
 */
function feedBriefLifecycle(step: {
  stepKind: string;
  detail: string;
  latencyMs?: number;
  status: string;
}): void {
  const begin = step.stepKind === "engine" ? RESEARCH_BEGIN_RE.exec(step.detail.trim()) : null;
  if (begin) {
    useBriefStore.getState().beginRun({
      runId: begin[1],
      depth: normalizeBriefDepth(begin[2]),
      query: (begin[3] ?? "").trim(),
    });
    return;
  }
  useBriefStore.getState().appendRunStep({
    kind: (BRIEF_STEP_KINDS.has(step.stepKind) ? step.stepKind : "tool") as BriefStepKind,
    detail: step.detail,
    latencyMs: step.latencyMs,
    status: (step.status === "error" || step.status === "skipped"
      ? step.status
      : "ok") as BriefStepStatus,
  });
}

export interface ChatRequest {
  provider: LLMProviderId;
  model: string;
  messages: LLMMessage[];
  apiKey?: string;
  baseUrl?: string;
  options?: Record<string, unknown>;
}

export interface StreamingHandlers {
  onEvent: (event: LLMStreamEvent) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

/**
 * Map the camelCase frontend `options` onto the wire body. `researchDepth` (the
 * composer's three-stop depth slider) crosses as snake_case `research_depth` so
 * the sidecar reads ONE spelling; every other key passes through unchanged (the
 * sidecar already consumes `history`/`deepResearchBackend`/`modelWebSearch`
 * as-is — renaming them here would silently break those contracts).
 */
function wireOptions(options?: Record<string, unknown>): Record<string, unknown> {
  if (!options) {
    return {};
  }
  const { researchDepth, ...rest } = options;
  return researchDepth === undefined ? rest : { ...rest, research_depth: researchDepth };
}

/** Stream a raw chat completion (no agent). */
export async function streamChat(payload: ChatRequest, handlers: StreamingHandlers): Promise<void> {
  const base = await getSidecarBaseUrl();
  const url = new URL("/llm/chat", base);
  const body = JSON.stringify({
    provider: payload.provider,
    model: payload.model,
    messages: payload.messages,
    api_key: payload.apiKey,
    base_url: payload.baseUrl,
    options: wireOptions(payload.options),
  });
  await consumeSseStream(url, body, handlers);
}

/** Stream an agent invocation. */
export async function streamAgentInvocation(
  agentId: string,
  payload: AgentInvocationRequest,
  handlers: StreamingHandlers,
): Promise<void> {
  const base = await getSidecarBaseUrl();
  const url = new URL(`/agents/${encodeURIComponent(agentId)}/invoke`, base);
  const body = JSON.stringify({
    prompt: payload.prompt,
    context_snapshot: payload.contextSnapshot
      ? {
          focused_source: payload.contextSnapshot.focusedSource,
          by_source: payload.contextSnapshot.bySource,
          captured_at: payload.contextSnapshot.capturedAt,
        }
      : null,
    provider: payload.provider,
    model: payload.model,
    api_key: payload.apiKey,
    // Intent axis (FR-003): the sidecar infers read-vs-mutate from the prompt via
    // classify_intent and gates a read intent to read-only tools server-side. The
    // default matches DEFAULT_AGENT_MODE ("agent") — the legacy "ask"/"edit"/"build"
    // mode vocabulary is gone (the spine collapsed to agent|delegate, S-15).
    mode: payload.mode ?? "agent",
    // Autonomy axis (ORTHOGONAL to mode): the sidecar threads this into the
    // host-action narration so the copilot tells the truth — in "auto" a non-order
    // change is ALREADY applied (past tense); in "ask" it is staged for review.
    // Orders always require confirmation regardless (§6.5).
    autonomy: payload.autonomy,
    options: wireOptions(payload.options),
  });
  await consumeSseStream(url, body, handlers);
}

async function consumeSseStream(
  url: URL,
  body: string,
  handlers: StreamingHandlers,
): Promise<void> {
  // The three-tier web-search contract (FR-080/083/084): the active tier, the
  // BYOK Exa key (keychain), and the local SearXNG URL ride the chat/agent
  // request so the sidecar dispatches web search to the right backend during a
  // research run. Undefined values are dropped (never an empty header).
  const searchHeaders = await buildSearchHeaders();
  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    // Region (FR-060): the sidecar reads this so the agent's tool calls
    // (price_data / resolve_symbol / …) route to the user's locale source.
    "X-Vysted-Region": useSettingsStore.getState().region,
  };
  for (const [key, value] of Object.entries(searchHeaders)) {
    if (value !== undefined) {
      requestHeaders[key] = value;
    }
  }
  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "POST",
      headers: requestHeaders,
      body,
      signal: handlers.signal,
    });
  } catch (err) {
    handlers.onError?.(toError(err));
    return;
  }
  if (!response.ok || !response.body) {
    const detail = await safeReadDetail(response);
    handlers.onError?.(new Error(detail ?? `sidecar returned ${response.status}`));
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      // Frames are split by a blank line (``\n\n``); incomplete trailing
      // frame stays in ``buffer`` for the next chunk.
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const frame = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        dispatchFrame(frame, handlers);
        separator = buffer.indexOf("\n\n");
      }
    }
    // Flush any trailing partial frame that has no terminator.
    if (buffer.trim()) {
      dispatchFrame(buffer, handlers);
    }
  } catch (err) {
    handlers.onError?.(toError(err));
  } finally {
    reader.releaseLock();
  }
}

function dispatchFrame(frame: string, handlers: StreamingHandlers): void {
  // SSE frames have multiple fields; we only care about ``data:`` lines.
  const dataLines = frame
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  if (dataLines.length === 0) {
    return;
  }
  const payload = dataLines.join("\n");
  try {
    const parsed = JSON.parse(payload) as Record<string, unknown> & { kind?: unknown };
    const event = normalizeEvent(parsed);
    if (event) {
      handlers.onEvent(event);
    }
  } catch (err) {
    handlers.onError?.(new Error(`unparseable SSE frame: ${(err as Error).message}`));
  }
}

/** Map snake_case sidecar fields to the camelCase TS shape. */
function normalizeEvent(payload: Record<string, unknown>): LLMStreamEvent | null {
  const kind = payload.kind;
  if (kind === "delta") {
    return { kind: "delta", text: String(payload.text ?? "") };
  }
  if (kind === "thinking") {
    return { kind: "thinking", text: String(payload.text ?? "") };
  }
  if (kind === "tool_use") {
    return {
      kind: "tool_use",
      toolCallId: String(payload.tool_call_id ?? ""),
      name: String(payload.name ?? ""),
      input: (payload.input as Record<string, unknown>) ?? {},
    };
  }
  if (kind === "research_step") {
    const step = {
      kind: "research_step" as const,
      toolCallId: String(payload.tool_call_id ?? ""),
      tool: String(payload.tool ?? ""),
      stepKind: String(payload.step_kind ?? "tool"),
      detail: String(payload.detail ?? ""),
      latencyMs: typeof payload.latency_ms === "number" ? payload.latency_ms : undefined,
      status: String(payload.status ?? "ok"),
      index: Number(payload.index ?? 0),
    };
    // One chokepoint: the brief panel's lifecycle (in_flight begin + live
    // steps) is fed here so EVERY stream consumer keeps the panel honest.
    feedBriefLifecycle(step);
    return step;
  }
  if (kind === "agent_plan") {
    const rawSteps = Array.isArray(payload.steps) ? payload.steps : [];
    return {
      kind: "agent_plan",
      goal: String(payload.goal ?? ""),
      steps: rawSteps.map((s) => {
        const step = (s ?? {}) as Record<string, unknown>;
        return {
          action: String(step.action ?? ""),
          args:
            step.args && typeof step.args === "object"
              ? (step.args as Record<string, unknown>)
              : {},
          rationale: String(step.rationale ?? ""),
          staged: step.staged === true,
        };
      }),
      note: typeof payload.note === "string" ? payload.note : undefined,
    };
  }
  if (kind === "done") {
    const rawUsage = payload.usage as
      | { input_tokens?: number; output_tokens?: number }
      | null
      | undefined;
    const usage = rawUsage
      ? {
          inputTokens: Number(rawUsage.input_tokens ?? 0),
          outputTokens: Number(rawUsage.output_tokens ?? 0),
        }
      : undefined;
    return {
      kind: "done",
      usage,
      finishReason: typeof payload.finish_reason === "string" ? payload.finish_reason : undefined,
    };
  }
  if (kind === "error") {
    // Structured frames (R10 D43) carry action/detail/code; a legacy frame's
    // bare message passes through untouched. Typed as StreamErrorFrame so the
    // extra fields survive the union without widening the frozen contract.
    const frame: StreamErrorFrame = {
      kind: "error",
      message: String(payload.message ?? "unknown error"),
      ...(typeof payload.action === "string" && payload.action
        ? { action: payload.action }
        : {}),
      ...(typeof payload.detail === "string" && payload.detail
        ? { detail: payload.detail }
        : {}),
      ...(typeof payload.code === "string" && payload.code ? { code: payload.code } : {}),
    };
    return frame;
  }
  return null;
}

async function safeReadDetail(response: Response): Promise<string | null> {
  try {
    const text = await response.text();
    return text.slice(0, 500);
  } catch {
    return null;
  }
}

function toError(err: unknown): Error {
  return err instanceof Error ? err : new Error(String(err));
}
