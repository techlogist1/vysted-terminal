"""OpenAI (and OpenAI-shaped) provider adapter.

Wraps ``openai.AsyncOpenAI(...).chat.completions.create(stream=True, ...)``
(openai SDK 2.36.0). The same adapter handles DeepSeek and xAI via
``base_url`` override — both speak the OpenAI chat-completions wire format
end-to-end. The dispatch lives in ``services.llm.__init__`` so the adapter
file count stays at five (per the Phase 3 plan).

The streaming chunks carry text deltas in ``choices[0].delta.content`` and
tool-call deltas in ``choices[0].delta.tool_calls`` (function-calling shape).
The final chunk's ``finish_reason`` and the optional terminal chunk's
``usage`` (set via ``stream_options={"include_usage": True}``) round out the
:class:`LLMDoneEvent` payload.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import jsonschema
import openai

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMModelOption,
    LLMThinkingEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services.errors import humanize

from .base import LLMProvider, LLMStreamEvent, is_chat_model
from .native_search import (
    openai_web_search_tool,
    openrouter_web_search_tool,
    xai_search_parameters,
)

logger = logging.getLogger(__name__)

#: Providers whose models are known to occasionally LEAK a tool call as plain
#: assistant text — a ``{"name": ..., "arguments": {...}}`` JSON block in
#: ``delta.content`` instead of the native ``tool_calls`` array. DeepSeek's
#: documented text-fall-through is the canonical case; OpenRouter routes through
#: many such models and Ollama's local models do the same. The content-leak
#: rescue (Step 2, ported from litellm's ``function_call_prompt`` round-trip as
#: original code) is GATED to this set so a chatty-but-correct OpenAI/Anthropic
#: model that merely *describes* a tool in prose never mis-fires a real call.
_CONTENT_LEAK_PROVIDERS = frozenset({"deepseek", "openrouter", "ollama"})

#: Transport retry budget for the streaming request (Step 3, ported from the
#: vercel/ai ``retry-with-exponential-backoff.ts`` pattern as original code).
#: Only RETRYABLE failures (429 / 5xx / connection) consume an attempt; a
#: deterministic 4xx (e.g. a 400 bad-request) is surfaced immediately — it is a
#: bug to fix, never a transient to retry.
_MAX_TRANSPORT_RETRIES = 2
_RETRY_BASE_DELAY = 0.5  # seconds; doubled each attempt, jittered
_RETRY_MAX_DELAY = 8.0

#: OpenRouter provider slugs Vysted never routes through. Amazon Bedrock is
#: excluded on every OpenRouter request so the terminal runs clean on OpenRouter's
#: own credits / other providers rather than a (historically unreliable, billed-
#: separately) account-level Bedrock BYOK integration. Sent as ``provider.ignore``
#: (OpenRouter-specific; only openrouter instances reach the branch that uses it).
#: A slug that no longer exists is a harmless no-op, never a routing break.
_OPENROUTER_IGNORE_PROVIDERS = ["amazon-bedrock"]

#: Reserved key the adapter stamps into a tool call's ``input`` when its
#: arguments failed JSON parse + schema validation AND a single repair round
#: could not fix them. The runtime's ``_dispatch_tool`` recognises it and
#: returns the graceful ``{"ok": False, "error": …}`` result keyed on the
#: call id, so the model self-corrects next round — NEVER a silent coerce to
#: ``{}`` (the core WS8 bug). Mirrors the existing "tool not found" convention.
INVALID_ARGS_SENTINEL = "__vysted_invalid_args__"


def _to_api_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert host messages to OpenAI chat-completions shape.

    ``role="tool"`` carries the result of a host-resolved call keyed by
    ``tool_call_id``. An assistant turn with ``metadata["tool_calls"]`` is
    reconstructed into the native ``tool_calls`` array (arguments re-serialised
    to a JSON string) so the provider associates each following tool result
    with the call that produced it.
    """
    api_messages: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "tool":
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                }
            )
            continue
        if message.role == "assistant" and message.metadata and message.metadata.get("tool_calls"):
            api_messages.append(
                {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [
                        {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("input", {})),
                            },
                        }
                        for tc in message.metadata["tool_calls"]
                    ],
                }
            )
            continue
        api_messages.append(
            {
                "role": message.role,
                "content": message.content,
                **({"tool_call_id": message.tool_call_id} if message.tool_call_id else {}),
            }
        )
    return api_messages


#: A buffered tool call whose argument JSON could not be parsed/validated and
#: could not be repaired. Carries the raw args + a human reason so the caller
#: can surface a ``role="tool"`` error the model self-corrects from — NEVER a
#: silent coerce to ``{}`` (the core WS8 bug). Returned alongside the good
#: events from :func:`_drain_tool_buffers`.
class _ToolArgFailure:
    __slots__ = ("tool_call_id", "name", "raw_args", "reason")

    def __init__(self, tool_call_id: str, name: str, raw_args: str, reason: str) -> None:
        self.tool_call_id = tool_call_id
        self.name = name
        self.raw_args = raw_args
        self.reason = reason


def _drain_tool_buffers(
    buffers: dict[int, dict[str, str]],
) -> tuple[list[LLMToolUseEvent], list[_ToolArgFailure]]:
    """Drain accumulated tool-call buffers into parsed events + parse failures.

    One result per buffered call. A buffer whose concatenated argument JSON
    parses to a dict yields an :class:`LLMToolUseEvent`. A buffer whose args are
    malformed JSON (``JSONDecodeError``) or parse to a non-dict yields a
    :class:`_ToolArgFailure` instead of being silently coerced to ``{}`` — the
    caller validates/repairs the events and surfaces an error turn for the
    failures so the model self-corrects. An EMPTY args string is the valid
    "no-argument call" case and parses to ``{}`` (not a failure).

    The dict is cleared so a later flush (stream-end safety net) never re-emits.
    """
    events: list[LLMToolUseEvent] = []
    failures: list[_ToolArgFailure] = []
    for index in sorted(buffers):
        buffer = buffers[index]
        tc_id = buffer.get("id", "") or ""
        name = buffer.get("name", "") or ""
        args = buffer.get("args") or ""
        if not args:
            # No fragments streamed → a genuine zero-argument call.
            events.append(LLMToolUseEvent(tool_call_id=tc_id, name=name, input={}))
            continue
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError as exc:
            failures.append(
                _ToolArgFailure(tc_id, name, args, f"arguments were not valid JSON ({exc})")
            )
            continue
        if not isinstance(parsed, dict):
            failures.append(
                _ToolArgFailure(
                    tc_id, name, args, "arguments were valid JSON but not a JSON object"
                )
            )
            continue
        events.append(LLMToolUseEvent(tool_call_id=tc_id, name=name, input=parsed))
    buffers.clear()
    return events, failures


def _validate_tool_args(name: str, args: dict[str, Any]) -> str | None:
    """Validate ``args`` against the tool's JSON Schema; return an error or None.

    Looks up ``TOOL_SCHEMAS[name]["input_schema"]`` and runs ``jsonschema``. An
    unknown tool id is NOT a validation failure here (the runtime's graceful
    ``_dispatch_tool`` handles "tool not found") — return ``None`` so we don't
    block a call the dispatcher will report on. A schema match returns ``None``;
    a mismatch returns a short, model-readable error string.
    """
    from services.agent_tools.schemas import TOOL_SCHEMAS

    schema = TOOL_SCHEMAS.get(name, {}).get("input_schema")
    if not schema:
        return None
    try:
        jsonschema.validate(instance=args, schema=schema)
    except jsonschema.ValidationError as exc:
        # ``exc.message`` is concise; the full ``str(exc)`` dumps the whole
        # schema, which would bloat the repair prompt and the error turn.
        return exc.message
    except jsonschema.SchemaError:  # pragma: no cover — our own schemas are valid
        return None
    return None


def _balanced_json_objects(text: str) -> list[str]:
    """Yield every brace-balanced ``{...}`` substring of ``text``, outermost only.

    A leaked tool call is a ``{"name": ..., "arguments": {...}}`` block that a
    chatty model embeds in prose (``Sure, calling: {...} now.``) — possibly with
    a NESTED ``arguments`` object and possibly with OTHER ``{...}`` JSON later in
    the same message. A single regex cannot reliably bracket such a block: a
    non-greedy ``.*?\\}`` truncates at the first inner brace (the original WS8
    bug), while a greedy ``\\{.*\\}`` over-captures across a trailing JSON object.
    A brace-depth scan extracts each top-level object intact, letting
    ``json.loads`` be the real validator (mirrors the repair-path intent without
    its single-block limitation). Strings (with escapes) are tracked so a brace
    inside a quoted value never miscounts depth.
    """
    objects: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    objects.append(text[start : i + 1])
                    start = -1
    return objects


def _rescue_content_leaked_tool_call(text: str, known_tool_ids: set[str]) -> LLMToolUseEvent | None:
    """Recover a tool call a model emitted as plain text (Step 2).

    Some models (DeepSeek's documented text-fall-through; many OpenRouter-routed
    and Ollama-local models) answer a tool-capable turn by writing a
    ``{"name": ..., "arguments": {...}}`` JSON block into ``delta.content``
    instead of using the native ``tool_calls`` array. When the accumulated
    assistant text contains such a block whose ``name`` matches a KNOWN tool id,
    parse it into a :class:`LLMToolUseEvent` so the round still drives the loop.

    Returns ``None`` when no valid leaked call is found (the common case — the
    text is a genuine final answer). The CALLER gates this on the provider id so
    a chatty OpenAI/Anthropic model never has a real call mis-fired from prose.
    Ported as original code from the round-trip pattern litellm uses to coax a
    function call out of a text-only response (no litellm import).
    """
    if not text or not known_tool_ids:
        return None
    # First try the whole text as a single JSON object, then scan for an
    # embedded block (models often wrap the call in prose or a code fence).
    # The embedded scan uses a brace-depth pass (``_balanced_json_objects``) so a
    # leaked block with a NESTED ``arguments`` object is captured WHOLE and a
    # trailing JSON object later in the prose does not get swept in — a
    # non-greedy regex truncated the former, a greedy regex over-captured the
    # latter. ``json.loads`` is the real validator.
    candidates: list[str] = []
    stripped = text.strip()
    if stripped.startswith("```"):
        # Strip a ```json … ``` fence if present.
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped).strip()
    candidates.append(stripped)
    candidates.extend(_balanced_json_objects(text))
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("name")
        args = obj.get("arguments")
        if not isinstance(name, str) or name not in known_tool_ids:
            continue
        # ``arguments`` may itself be a JSON string (the OpenAI tool-call shape)
        # or an inline object. Normalise to a dict; a non-dict/unparseable args
        # block is treated as a zero-argument call so the dispatcher still runs.
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        leaked_id = obj.get("id")
        return LLMToolUseEvent(
            tool_call_id=str(leaked_id) if isinstance(leaked_id, str) and leaked_id else "leaked-0",
            name=name,
            input=args,
        )
    return None


def _http_date_delay(raw: str) -> float | None:
    """Seconds until an HTTP-date ``Retry-After`` (RFC 7231), or ``None`` if it
    is unparseable. A past date yields a non-positive delay (caller treats <0 as
    "retry now" via the backoff fallback)."""
    try:
        when = parsedate_to_datetime(raw.strip())
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # a naive HTTP-date is UTC by spec
        when = when.replace(tzinfo=UTC)
    return (when - datetime.now(UTC)).total_seconds()


def _retry_after_seconds(exc: openai.APIError) -> float | None:
    """Honour a ``Retry-After`` header on a rate-limit/5xx response, if present.

    RFC 7231 allows both an integer-seconds form (the common API form) and an
    HTTP-date form (some 429/503 responses use it); both are parsed. Returns the
    instructed wait in seconds (capped at ``_RETRY_MAX_DELAY``) or ``None`` to
    fall back to exponential backoff.
    """
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(str(raw).strip())
    except (TypeError, ValueError):
        # Not an integer-seconds value — try the HTTP-date form before giving up.
        seconds = _http_date_delay(str(raw))
        if seconds is None:
            return None
    if seconds < 0:
        return None
    return min(seconds, _RETRY_MAX_DELAY)


def _is_retryable_transport_error(exc: BaseException) -> bool:
    """True only for transient transport failures worth retrying (Step 3).

    Retry: rate limits (429), server errors (5xx), and connection failures.
    NEVER retry a deterministic 4xx that is not 429 (a 400 bad-request is a bug
    to surface, not a transient) — those carry a ``status_code`` < 500 and != 429
    and fall through to ``False``.
    """
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIConnectionError):
        # Covers APITimeoutError (a subclass) too — both are transient transport.
        return True
    if isinstance(exc, openai.APIStatusError):
        status = getattr(exc, "status_code", None)
        if status is not None:
            return status >= 500
    if isinstance(exc, openai.InternalServerError):  # pragma: no cover — 5xx subclass
        return True
    return False


class OpenAIProvider(LLMProvider):
    """OpenAI chat-completions adapter; also serves DeepSeek and xAI.

    ``provider_id`` is informational — it lets DeepSeek/xAI adapter instances
    surface the right error provenance without changing the wire shape.
    """

    def __init__(self, base_url: str | None = None, provider_id: str = "openai") -> None:
        self._base_url = base_url
        self._provider_id = provider_id

    def _client(self, api_key: str | None) -> openai.AsyncOpenAI:
        # OpenRouter takes optional attribution headers (leaderboard/analytics
        # only; safe to send). They identify the app, carry no secret.
        default_headers: dict[str, str] | None = None
        if self._provider_id == "openrouter":
            default_headers = {
                "HTTP-Referer": "https://vysted.app",
                "X-Title": "Vysted Terminal",
            }
        # ``max_retries=0`` makes the ADAPTER the single retry authority. The SDK
        # defaults to ``openai.DEFAULT_MAX_RETRIES`` (== 2) and would otherwise
        # retry 429/5xx/connection internally BEFORE ever raising to
        # :meth:`_create_with_retry`, double-counting the budget (~3 adapter
        # attempts × 3 SDK requests ≈ 9 underlying HTTP calls with stacked
        # sleeps). With the SDK loop off, ``_create_with_retry`` (which honours a
        # ``Retry-After`` header and never retries a deterministic 4xx) is the one
        # place transport retries are decided.
        return openai.AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            default_headers=default_headers,
            max_retries=0,
        )

    async def _create_with_retry(
        self, client: openai.AsyncOpenAI, request_kwargs: dict[str, Any]
    ) -> Any:
        """Open the streaming completion with header-aware exponential backoff.

        Retries ONLY transient transport failures (429 / 5xx / connection) up to
        :data:`_MAX_TRANSPORT_RETRIES` times, honouring a ``Retry-After`` header
        when the server sends one. A single 429 no longer kills the stream. A
        deterministic 4xx (e.g. a 400) is NOT retried — it re-raises immediately
        so the bug surfaces. Ported as original code from the vercel/ai
        ``retry-with-exponential-backoff`` pattern (no vercel-ai import).
        """
        attempt = 0
        while True:
            try:
                return await client.chat.completions.create(**request_kwargs)
            except Exception as exc:  # noqa: BLE001 — classify then re-raise/retry
                if attempt >= _MAX_TRANSPORT_RETRIES or not _is_retryable_transport_error(exc):
                    raise
                delay = None
                if isinstance(exc, openai.APIError):
                    delay = _retry_after_seconds(exc)
                if delay is None:
                    # Exponential backoff with full jitter, capped.
                    delay = min(_RETRY_BASE_DELAY * (2**attempt), _RETRY_MAX_DELAY)
                    delay = random.uniform(0, delay)
                logger.debug(
                    "%s transport retry %d/%d after %.2fs (%s)",
                    self._provider_id,
                    attempt + 1,
                    _MAX_TRANSPORT_RETRIES,
                    delay,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
                attempt += 1

    async def _resolve_tool_events(
        self,
        events: list[LLMToolUseEvent],
        failures: list[_ToolArgFailure],
        *,
        model: str,
        api_key: str | None,
    ) -> list[LLMToolUseEvent]:
        """Validate each parsed call's args; repair-once or surface an error turn.

        Step 1 of WS8 (ported from the vercel/ai ``parse-tool-call`` pattern as
        original code, no vercel-ai import):

        * A successfully-parsed call is validated against its tool's JSON Schema.
          On a schema MISS, run EXACTLY ONE repair round via
          :func:`oneshot.complete` (it rides the per-request BYOK creds) giving
          the model the schema + the validation error + the raw args, then
          re-validate the repaired args.
        * A call whose args could not even be parsed (``_ToolArgFailure``) gets
          the same one repair round, re-parsed + re-validated.
        * If repair STILL fails, the call's ``input`` is stamped with
          :data:`INVALID_ARGS_SENTINEL` carrying the reason. The runtime's
          ``_dispatch_tool`` turns that into a ``role="tool"`` ``{"ok": False,
          "error": …}`` result keyed on the call id — so the model self-corrects
          next round. NEVER a silent coerce to ``{}`` (the core WS8 bug).
        """
        from services.agent_tools.schemas import TOOL_SCHEMAS

        resolved: list[LLMToolUseEvent] = []

        # 1) Parsed calls that fail schema validation → one repair round.
        for event in events:
            error = _validate_tool_args(event.name, event.input)
            if error is None:
                resolved.append(event)
                continue
            schema = TOOL_SCHEMAS.get(event.name, {}).get("input_schema")
            repaired = await self._repair_tool_args(
                tool_name=event.name,
                raw_args=json.dumps(event.input),
                error=error,
                schema=schema,
                model=model,
                api_key=api_key,
            )
            if repaired is not None:
                resolved.append(
                    LLMToolUseEvent(
                        tool_call_id=event.tool_call_id, name=event.name, input=repaired
                    )
                )
            else:
                resolved.append(
                    LLMToolUseEvent(
                        tool_call_id=event.tool_call_id,
                        name=event.name,
                        input={
                            INVALID_ARGS_SENTINEL: (
                                f"invalid arguments for {event.name}: {error}; "
                                "call again with valid args"
                            )
                        },
                    )
                )

        # 2) Calls whose args never parsed → one repair round, re-parsed.
        for failure in failures:
            schema = TOOL_SCHEMAS.get(failure.name, {}).get("input_schema")
            repaired = await self._repair_tool_args(
                tool_name=failure.name,
                raw_args=failure.raw_args,
                error=failure.reason,
                schema=schema,
                model=model,
                api_key=api_key,
            )
            if repaired is not None:
                resolved.append(
                    LLMToolUseEvent(
                        tool_call_id=failure.tool_call_id, name=failure.name, input=repaired
                    )
                )
            else:
                resolved.append(
                    LLMToolUseEvent(
                        tool_call_id=failure.tool_call_id,
                        name=failure.name,
                        input={
                            INVALID_ARGS_SENTINEL: (
                                f"invalid arguments for {failure.name}: {failure.reason}; "
                                "call again with valid args"
                            )
                        },
                    )
                )
        return resolved

    async def _repair_tool_args(
        self,
        *,
        tool_name: str,
        raw_args: str,
        error: str,
        schema: dict[str, Any] | None,
        model: str,
        api_key: str | None,
    ) -> dict[str, Any] | None:
        """Run ONE repair round; return valid args dict or ``None`` on failure.

        Reuses :func:`services.llm.oneshot.complete` (rides the per-request BYOK
        creds) to ask the SAME model to re-emit ONLY a valid JSON arguments
        object for ``tool_name`` given the schema + the validation error + its
        own raw args. The reply is parsed, schema-re-validated, and returned —
        ``None`` if it still cannot be parsed or still fails validation (the
        caller then surfaces an error turn). No network on the test path: the
        ``oneshot.complete`` call is mocked.
        """
        if not schema:
            return None
        from services.llm import oneshot

        prompt = (
            "A previous tool call to the function "
            f"`{tool_name}` had invalid arguments.\n\n"
            f"JSON Schema for the arguments:\n{json.dumps(schema)}\n\n"
            f"The arguments you sent:\n{raw_args}\n\n"
            f"The validation error:\n{error}\n\n"
            "Reply with ONLY a single valid JSON object for the arguments — no "
            "prose, no code fence, no explanation. It must satisfy the schema."
        )
        try:
            reply = await oneshot.complete(
                self._provider_id,
                model,
                api_key,
                [{"role": "user", "content": prompt}],
            )
        except Exception:  # noqa: BLE001 — a failed repair is a non-fatal miss
            logger.debug("tool-arg repair call failed for %s", tool_name, exc_info=True)
            return None
        if not reply:
            return None
        candidate = reply.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```[a-zA-Z]*\n?", "", candidate)
            candidate = re.sub(r"\n?```$", "", candidate).strip()
        # The model may wrap the object in prose; extract the first {...} block.
        if not candidate.startswith("{"):
            match = re.search(r"\{.*\}", candidate, re.DOTALL)
            if match:
                candidate = match.group(0)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        if _validate_tool_args(tool_name, parsed) is not None:
            return None
        return parsed

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        tool_ids = kwargs.pop("tool_ids", None)
        web_search = bool(kwargs.pop("web_search", False))
        # ``web_search_max_uses`` is Anthropic-only; pop it so it never reaches
        # the OpenAI/xAI SDK (the runtime caps these providers loop-side).
        kwargs.pop("web_search_max_uses", None)
        client = self._client(api_key)
        api_messages = _to_api_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools: list[dict[str, Any]] = []
        if tool_ids:
            from services.agent_tools.schemas import openai_tools

            tools.extend(openai_tools(tool_ids))
        # Native server-side web search (FR-081), opt-in via ``web_search``.
        # OpenAI takes a ``{"type": "web_search"}`` tools entry; OpenRouter (WS5)
        # takes its own ``{"type": "openrouter:web_search"}`` tools entry to ride
        # the upstream model's native search; xAI (dispatched through this adapter
        # via the x.ai base_url) speaks Live Search through a top-level
        # ``search_parameters`` block instead of a tool — gate on the provider id.
        # DeepSeek has no native search, so it is left untouched (graceful no-op;
        # the runtime falls back to a BYOK search plugin).
        if web_search:
            if self._provider_id == "xai":
                request_kwargs["extra_body"] = {
                    **request_kwargs.get("extra_body", {}),
                    "search_parameters": xai_search_parameters(),
                }
            elif self._provider_id == "openrouter":
                tools.append(openrouter_web_search_tool())
            elif self._provider_id == "openai":
                tools.append(openai_web_search_tool())
        if tools:
            request_kwargs["tools"] = tools
        # OpenRouter cheapest-capable routing (FINDINGS §2.2): pick the cheapest
        # PROVIDER of the chosen model, and — when we send tools — refuse a
        # provider that would silently drop them (so multi-round tool use never
        # breaks). Sent as ``extra_body.provider`` (OpenRouter-specific; ignored
        # by vanilla OpenAI, but only openrouter instances reach this branch).
        if self._provider_id == "openrouter":
            or_provider: dict[str, Any] = {
                "sort": "price",
                "ignore": list(_OPENROUTER_IGNORE_PROVIDERS),
            }
            if tools:
                or_provider["require_parameters"] = True
            request_kwargs["extra_body"] = {
                **request_kwargs.get("extra_body", {}),
                "provider": or_provider,
            }
        request_kwargs.update(kwargs)
        # Known tool ids for the content-leak rescue (Step 2). Resolved from the
        # SAME filtered set the schemas were built from so a leaked block is only
        # rescued for a tool the model was actually offered.
        known_tool_ids: set[str] = set()
        if tool_ids:
            from services.agent_tools.schemas import TOOL_SCHEMAS

            known_tool_ids = {tid for tid in tool_ids if tid in TOOL_SCHEMAS}
        try:
            stream = await self._create_with_retry(client, request_kwargs)
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            # Function-call streaming sends the id/name once and the arguments
            # JSON in fragments across many chunks, keyed by the tool_call
            # index. Accumulate per index, then emit ONE tool_use event per
            # call with the parsed arguments dict when the round finishes.
            tool_buffers: dict[int, dict[str, str]] = {}
            # Accumulate assistant text for the content-leak rescue (Step 2):
            # a round that finishes with no native tool buffers may still carry
            # a leaked ``{"name", "arguments"}`` block in the text.
            content_parts: list[str] = []
            # Accumulate DeepSeek-reasoner ``reasoning_content`` (Step 4): the
            # reasoner streams its chain-of-thought in a SEPARATE delta field;
            # surface it as a thinking event so the runtime can echo it on the
            # reconstructed tool-use turn for a well-formed multi-round reasoner.
            emitted_tool_events = False
            async for chunk in stream:
                # Some providers (DeepSeek, occasionally OpenAI) emit a
                # terminal chunk with no choices but populated usage. Guard
                # both branches independently.
                choices = getattr(chunk, "choices", None) or []
                for choice in choices:
                    delta = getattr(choice, "delta", None)
                    if delta is not None:
                        reasoning = getattr(delta, "reasoning_content", None) or getattr(
                            delta, "reasoning", None
                        )
                        if reasoning:
                            yield LLMThinkingEvent(text=reasoning)
                        content = getattr(delta, "content", None)
                        if content:
                            content_parts.append(content)
                            yield LLMDeltaEvent(text=content)
                        tool_calls = getattr(delta, "tool_calls", None) or []
                        for tool_call in tool_calls:
                            index = getattr(tool_call, "index", 0) or 0
                            buffer = tool_buffers.setdefault(
                                index, {"id": "", "name": "", "args": ""}
                            )
                            tc_id = getattr(tool_call, "id", None)
                            if tc_id:
                                buffer["id"] = tc_id
                            function = getattr(tool_call, "function", None)
                            if function is not None:
                                name = getattr(function, "name", None)
                                if name:
                                    buffer["name"] = name
                                args_raw = getattr(function, "arguments", None)
                                if args_raw:
                                    buffer["args"] += args_raw
                    reason = getattr(choice, "finish_reason", None)
                    if reason:
                        finish_reason = reason
                    if reason == "tool_calls":
                        events, failures = _drain_tool_buffers(tool_buffers)
                        for event in await self._resolve_tool_events(
                            events, failures, model=model, api_key=api_key
                        ):
                            emitted_tool_events = True
                            yield event
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    usage = LLMUsage(
                        input_tokens=getattr(chunk_usage, "prompt_tokens", 0) or 0,
                        output_tokens=getattr(chunk_usage, "completion_tokens", 0) or 0,
                    )
            # Stream ended with buffers still pending (no explicit
            # ``tool_calls`` finish_reason from this provider) — flush them so
            # the call is never dropped.
            if tool_buffers:
                events, failures = _drain_tool_buffers(tool_buffers)
                for event in await self._resolve_tool_events(
                    events, failures, model=model, api_key=api_key
                ):
                    emitted_tool_events = True
                    yield event
            # Content-leak rescue (Step 2): if the round produced NO tool calls
            # at all and did NOT finish via ``tool_calls``, but the accumulated
            # text carries a leaked ``{"name", "arguments"}`` block matching a
            # known tool, recover it. GATED to providers whose models do this
            # (DeepSeek / OpenRouter / Ollama) so a chatty-but-correct
            # OpenAI/Anthropic answer never mis-fires a tool the user did not
            # intend.
            if (
                not emitted_tool_events
                and finish_reason != "tool_calls"
                and self._provider_id in _CONTENT_LEAK_PROVIDERS
                and known_tool_ids
            ):
                rescued = _rescue_content_leaked_tool_call("".join(content_parts), known_tool_ids)
                if rescued is not None:
                    for event in await self._resolve_tool_events(
                        [rescued], [], model=model, api_key=api_key
                    ):
                        yield event
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except openai.OpenAIError as exc:  # pragma: no cover — network path
            _h = humanize(self._provider_id, exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )
        except Exception as exc:  # pragma: no cover — defensive
            _h = humanize(self._provider_id, exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )

    async def validate_key(self, api_key: str | None = None) -> bool:
        """Probe ``/v1/models`` — works for OpenAI, DeepSeek, and xAI alike."""
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            await client.models.list()
            return True
        except openai.AuthenticationError:
            return False
        except openai.PermissionDeniedError:
            return False
        except openai.OpenAIError:
            raise

    async def list_models(self, api_key: str | None = None) -> list[LLMModelOption]:
        """Live model catalog.

        OpenRouter gets the rich treatment (user-scoped + tool-capability) via
        :func:`openrouter_catalog.fetch_openrouter_catalog`. The plain
        OpenAI-shaped providers (OpenAI, DeepSeek, xAI) surface what
        ``/v1/models`` returns, filtered down to chat models — their catalog API
        does not expose per-model tool-calling, so ``supports_tools`` stays
        ``None`` (unknown, not "no").
        """
        if self._provider_id == "openrouter":
            from .openrouter_catalog import fetch_openrouter_catalog

            return await fetch_openrouter_catalog(api_key, self._base_url)
        if not api_key:
            return []
        try:
            client = self._client(api_key)
            page = await client.models.list()
        except openai.AuthenticationError:
            return []
        except openai.PermissionDeniedError:
            return []
        options = [
            LLMModelOption(id=str(model.id), label=str(model.id))
            for model in (getattr(page, "data", None) or [])
            if getattr(model, "id", None) and is_chat_model(str(model.id))
        ]
        options.sort(key=lambda opt: opt.id.lower())
        return options
