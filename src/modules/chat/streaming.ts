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
import {
  extractSidecarDetail,
  getSidecarBaseUrl,
  SIDECAR_UNREACHABLE,
  SidecarError,
  sidecarFetch,
} from "@/lib/sidecar-client";
import { useBriefStore } from "@/store/brief";
import { useSettingsStore } from "@/store/settings";
import type {
  AgentInvocationRequest,
  LLMMessage,
  LLMProviderId,
  LLMStreamEvent,
  LLMUsage,
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

/**
 * Error-frame codes that say the PROVIDER could not serve the turn at all — a
 * rejected key, no credit/quota, or an unreachable/down endpoint (the sidecar's
 * `humanize` taxonomy, `sidecar/services/errors.py`). Only these let the chat
 * fall back to the next provider in the preference order (FR-038, D-B11-7); a
 * content error (bad model id, context overflow, content filter, truncation)
 * would fail the same way anywhere, and a rate limit clears on its own.
 */
const PROVIDER_FAILURE_CODES = new Set([
  "auth",
  "provider_402",
  "insufficient_credit",
  "network",
  "ollama_not_running",
  "provider_5xx",
]);

/** True when an error frame's `code` is a provider failure (see above). */
export function isProviderFailure(code: string | undefined): boolean {
  return code !== undefined && PROVIDER_FAILURE_CODES.has(code);
}

/**
 * The extra field a `done` frame carries beside the base union member (C11,
 * R15-AGENT-082): the sidecar's estimated spend for the turn. Same
 * excess-property trick as {@link StreamErrorFrame} — the chat surface reads
 * it via {@link doneFrameOf}.
 */
interface StreamDoneFrame {
  kind: "done";
  usage?: LLMUsage;
  finishReason?: string;
  contextWindow?: number;
  /** Estimated USD spend of the whole turn, or `undefined` when the model has
   *  no price or the round reported no usage — never a fabricated zero. */
  spendUsd?: number;
}

/** The estimated spend on a `done` event, or `undefined` when absent/unpriced. */
export function doneFrameOf(event: LLMStreamEvent): number | undefined {
  if (event.kind !== "done") {
    return undefined;
  }
  return (event as unknown as StreamDoneFrame).spendUsd;
}

/** The runtime's `research:begin {run_id} depth={depth} query={…}` engine step
 *  (Team RUNTIME contract) — the frontend keys its in-flight brief state on it.
 *  The query is the model's free text and may span lines, so its tail matches
 *  any character, newlines included (R15-RESEARCH-031). */
const RESEARCH_BEGIN_RE = /^research:begin\s+(\S+)\s+depth=(\S+)(?:\s+query=([\s\S]*))?$/;

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

/**
 * Every stream call ends in exactly ONE terminal callback: the first `done` or
 * `error` event, or `onError` (sidecar not ready, network, HTTP error, a
 * malformed frame, a consumer throw, or a stream that closed without a
 * terminal frame). Later terminal frames are dropped; the call never rejects.
 */
export interface StreamingHandlers {
  onEvent: (event: LLMStreamEvent) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

/** True when a `done` finish reason says the answer was cut at the output limit
 *  (`length` on OpenAI/Groq/Ollama, `max_tokens` on Anthropic, Gemini's
 *  `FinishReason.MAX_TOKENS`) — mirrors the sidecar's `is_length_finish`. */
export function isLengthFinish(reason: string | undefined): boolean {
  const tail = reason?.split(".").pop()?.toLowerCase();
  return tail === "length" || tail === "max_tokens";
}

/** The truncation notice for an answer cut at the model's output limit. */
export const LENGTH_NOTICE =
  "The answer hit the model's output limit and was cut off. Ask me to continue for the rest.";

/** The `onError` message for a stream that closed without a `done`/`error` frame. */
export const STREAM_ENDED_EARLY = "The stream ended before the answer finished.";

/** The `onError` message when no frame arrived within the idle budget. */
export const STREAM_STALLED =
  "The provider went quiet: nothing arrived for too long, so the stream was stopped.";

/**
 * Stall watchdog budgets (R15-AGENT-025): the longest the stream may go without
 * a single byte. The agent runtime sends a heartbeat every 10 s while it waits,
 * so a longer silence means the sidecar or the connection is gone. The raw chat
 * has no heartbeat; its budget sits above the adapters' own idle timeouts (180 s
 * hosted, 300 s local), so it only catches a stream that outlived them.
 */
export const AGENT_STREAM_IDLE_MS = 45_000;
export const CHAT_STREAM_IDLE_MS = 330_000;

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
  const body = JSON.stringify({
    provider: payload.provider,
    model: payload.model,
    messages: payload.messages,
    api_key: payload.apiKey,
    base_url: payload.baseUrl,
    options: wireOptions(payload.options),
  });
  await consumeSseStream("/llm/chat", body, handlers, CHAT_STREAM_IDLE_MS);
}

/** Stream an agent invocation. */
export async function streamAgentInvocation(
  agentId: string,
  payload: AgentInvocationRequest,
  handlers: StreamingHandlers,
): Promise<void> {
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
    // host-action narration so the copilot tells the truth — in "auto" a
    // change is ALREADY applied (past tense); in "ask" it is staged for review.
    autonomy: payload.autonomy,
    options: wireOptions(payload.options),
  });
  await consumeSseStream(
    `/agents/${encodeURIComponent(agentId)}/invoke`,
    body,
    handlers,
    AGENT_STREAM_IDLE_MS,
  );
}

async function consumeSseStream(
  path: string,
  body: string,
  handlers: StreamingHandlers,
  idleMs: number,
): Promise<void> {
  let settled = false;
  const fail = (err: unknown): void => {
    if (!settled) {
      settled = true;
      handlers.onError?.(toError(err));
    }
  };
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  // Stall watchdog (R15-AGENT-025): re-armed on every chunk; on silence it ends
  // the stream with STREAM_STALLED (the transcript's Retry row) and drops the
  // connection so the server-side run stops too.
  let stalled = false;
  let stallTimer: ReturnType<typeof setTimeout> | undefined;
  const armWatchdog = (): void => {
    clearTimeout(stallTimer);
    stallTimer = setTimeout(() => {
      stalled = true;
      fail(new Error(STREAM_STALLED));
      void reader?.cancel().catch(() => undefined);
    }, idleMs);
  };
  const onEvent = (event: LLMStreamEvent): void => {
    if (stalled) {
      return;
    }
    const terminal = event.kind === "done" || event.kind === "error";
    if (terminal && settled) {
      return;
    }
    settled ||= terminal;
    // A runtime notice (C9) is transcript copy, never a step of a brief run.
    if (event.kind === "research_step" && event.stepKind !== "notice") {
      feedBriefLifecycle(event);
    }
    handlers.onEvent(event);
  };
  armWatchdog();
  try {
    // Inside the try: a sidecar that is not ready rejects here, and that must
    // reach onError like any other failure (R15-AGENT-029).
    const url = new URL(path, await getSidecarBaseUrl());
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
    const response = await sidecarFetch(url.toString(), {
      method: "POST",
      headers: requestHeaders,
      body,
      signal: handlers.signal,
    });
    if (stalled) {
      await response.body?.cancel().catch(() => undefined);
      return;
    }
    if (!response.ok || !response.body) {
      // The same humanizing as the REST client: a FastAPI `detail` (a string,
      // or a 422 field-error array) — never the raw JSON body (R15-UI-012).
      const fallback = `sidecar returned ${response.status}`;
      const parsed: unknown = await response.json().catch(() => null);
      throw new SidecarError(response.status, extractSidecarDetail(parsed, fallback));
    }
    reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    for (;;) {
      // The engine dying mid-stream rejects the read like a refused fetch does.
      const { done, value } = await reader.read().catch((err: unknown) => {
        throw handlers.signal?.aborted ? err : new SidecarError(0, SIDECAR_UNREACHABLE);
      });
      if (done || stalled) {
        break;
      }
      armWatchdog();
      buffer += decoder.decode(value, { stream: true });
      // Frames are split by a blank line (``\n\n``); incomplete trailing
      // frame stays in ``buffer`` for the next chunk.
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const frame = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        dispatchFrame(frame, onEvent);
        separator = buffer.indexOf("\n\n");
      }
    }
    // Flush any trailing partial frame that has no terminator.
    if (buffer.trim()) {
      dispatchFrame(buffer, onEvent);
    }
  } catch (err) {
    fail(err);
    // Stop the server-side run too: nothing reads a settled message's frames.
    await reader?.cancel().catch(() => undefined);
  } finally {
    clearTimeout(stallTimer);
    reader?.releaseLock();
  }
  fail(new Error(STREAM_ENDED_EARLY));
}

/** Parse one frame and hand its event to `onEvent`. Only the parse is guarded:
 *  a throw from the consumer propagates with its own message instead of being
 *  relabelled a malformed frame (R15-CODE-PLATFORM-037). */
function dispatchFrame(frame: string, onEvent: (event: LLMStreamEvent) => void): void {
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
  let event: LLMStreamEvent | null;
  try {
    event = normalizeEvent(JSON.parse(payload) as Record<string, unknown> & { kind?: unknown });
  } catch (err) {
    throw new Error(`unparseable SSE frame: ${(err as Error).message}`);
  }
  if (event) {
    onEvent(event);
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
  if (kind === "heartbeat") {
    return { kind: "heartbeat" };
  }
  if (kind === "tool_use") {
    return {
      kind: "tool_use",
      toolCallId: String(payload.tool_call_id ?? ""),
      name: String(payload.name ?? ""),
      input: (payload.input as Record<string, unknown>) ?? {},
    };
  }
  if (kind === "tool_result") {
    return {
      kind: "tool_result",
      toolCallId: String(payload.tool_call_id ?? ""),
      name: String(payload.name ?? ""),
      ok: payload.ok === true,
      ...(typeof payload.error === "string" ? { error: payload.error } : {}),
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
      | { input_tokens?: number; output_tokens?: number; served_model?: unknown }
      | null
      | undefined;
    const usage = rawUsage
      ? {
          inputTokens: Number(rawUsage.input_tokens ?? 0),
          outputTokens: Number(rawUsage.output_tokens ?? 0),
          ...(typeof rawUsage.served_model === "string" && rawUsage.served_model
            ? { servedModel: rawUsage.served_model }
            : {}),
        }
      : undefined;
    // Typed as a variable (not returned as a literal) so the extra
    // `spendUsd` field (C11, R15-AGENT-082) skips the excess-property check —
    // same trick as the error frame below. Read via {@link doneFrameOf}.
    const doneFrame: StreamDoneFrame = {
      kind: "done",
      usage,
      finishReason: typeof payload.finish_reason === "string" ? payload.finish_reason : undefined,
      contextWindow:
        typeof payload.context_window === "number" ? payload.context_window : undefined,
      spendUsd: typeof payload.spend_usd === "number" ? payload.spend_usd : undefined,
    };
    return doneFrame;
  }
  if (kind === "error") {
    // Structured frames (R10 D43) carry action/detail/code; a legacy frame's
    // bare message passes through untouched. Typed as StreamErrorFrame so the
    // extra fields survive the union without widening the frozen contract.
    const frame: StreamErrorFrame = {
      kind: "error",
      message: String(payload.message ?? "unknown error"),
      ...(typeof payload.action === "string" && payload.action ? { action: payload.action } : {}),
      ...(typeof payload.detail === "string" && payload.detail ? { detail: payload.detail } : {}),
      ...(typeof payload.code === "string" && payload.code ? { code: payload.code } : {}),
    };
    return frame;
  }
  return null;
}

function toError(err: unknown): Error {
  return err instanceof Error ? err : new Error(String(err));
}
