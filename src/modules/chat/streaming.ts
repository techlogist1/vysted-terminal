/**
 * Streaming client — SSE wrapper around the sidecar's chat / agent endpoints.
 *
 * Native ``EventSource`` only supports GET, and the chat endpoint is POST
 * (request body carries the API key + messages array). So we use ``fetch``
 * with a streaming response body and a custom SSE parser. The on-wire shape
 * matches ``data: <json>\n\n`` frames where each ``<json>`` is one
 * ``LLMStreamEvent`` discriminated-union member.
 */

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import type {
  AgentInvocationRequest,
  LLMMessage,
  LLMProviderId,
  LLMStreamEvent,
} from "../../../types/ai";

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
    options: payload.options ?? {},
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
    options: {},
  });
  await consumeSseStream(url, body, handlers);
}

async function consumeSseStream(
  url: URL,
  body: string,
  handlers: StreamingHandlers,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
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
    return { kind: "error", message: String(payload.message ?? "unknown error") };
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
