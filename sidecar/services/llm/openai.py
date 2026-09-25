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
    LLMToolUseEvent,
    LLMUsage,
)
from services.errors import humanize, says_invalid_key

#: The sentinel lives in ``base`` (every adapter stamps it); re-exported here
#: for the runtime's existing ``from services.llm.openai import`` path.
from .base import (
    INVALID_ARGS_SENTINEL,
    LLMProvider,
    LLMStreamEvent,
    client_timeout,
    is_chat_model,
)
from .native_search import (
    openai_native_search_supported,
    openai_shaped_search_count,
    openai_web_search_options,
    openrouter_web_search_tool,
)
from .reasoning_split import ReasoningSplitter
from .tool_call_rescue import LeakHold, rescue_leaked_tool_call

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


#: Tool-arg repairs per provider round, and the wall-clock cap on each one
#: (R15-AGENT-048): five bad calls used to cost five serial, untimed completions
#: whose usage was never counted. Calls past the cap get the error turn at once.
_MAX_REPAIRS_PER_ROUND = 2
_REPAIR_TIMEOUT_S = 30.0
#: JSON-Schema keywords: a repair reply keyed by these (and not by the tool's own
#: property names) is the schema echoed back, not filled-in args (R15-LEAD-014).
_SCHEMA_KEYWORDS = frozenset(
    {"type", "properties", "required", "additionalProperties", "$schema", "description"}
)


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


def _is_reasoning_effort_tool_conflict(exc: BaseException) -> bool:
    """True for the gpt-5.x "function tools + reasoning_effort" 400.

    OpenAI's reasoning models refuse function tools on ``/v1/chat/completions``
    unless reasoning is off: *"Function tools with reasoning_effort are not
    supported for <model> in /v1/chat/completions. To use function tools, use
    /v1/responses or set reasoning_effort to 'none'."* We never send the
    parameter — the model's own default trips it — so the repair is to send it
    explicitly as ``"none"`` and retry once. Matched on the message rather than a
    model-name list so a future reasoning model needs no code change.
    """
    return (
        isinstance(exc, openai.APIStatusError)
        and getattr(exc, "status_code", None) == 400
        and "reasoning_effort" in str(exc)
    )


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
            timeout=client_timeout(),
        )

    async def _create_with_retry(
        self, client: openai.AsyncOpenAI, request_kwargs: dict[str, Any]
    ) -> Any:
        """Open the streaming completion with header-aware exponential backoff.

        Retries ONLY transient transport failures (429 / 5xx / connection) up to
        :data:`_MAX_TRANSPORT_RETRIES` times, honouring a ``Retry-After`` header
        when the server sends one. A single 429 no longer kills the stream. A
        deterministic 4xx (e.g. a 400) is NOT retried — it re-raises immediately
        so the bug surfaces, with ONE exception: the gpt-5.x "function tools with
        reasoning_effort" 400, which is repaired in place by sending
        ``reasoning_effort="none"`` once (see
        :func:`_is_reasoning_effort_tool_conflict`). Ported as original code from the vercel/ai
        ``retry-with-exponential-backoff`` pattern (no vercel-ai import).
        """
        attempt = 0
        while True:
            try:
                return await client.chat.completions.create(**request_kwargs)
            except Exception as exc:  # noqa: BLE001 — classify then re-raise/retry
                # One-shot repair (not a transport retry, so it costs no budget):
                # a reasoning model that refuses function tools unless reasoning
                # is off. Retried at most once — the key is set on the way in.
                if _is_reasoning_effort_tool_conflict(exc) and "reasoning_effort" not in (
                    request_kwargs
                ):
                    request_kwargs["reasoning_effort"] = "none"
                    continue
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
        repairs: list[LLMUsage | None],
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
        * At most :data:`_MAX_REPAIRS_PER_ROUND` repairs run per round (the
          ``repairs`` list is the round's ledger: one usage entry per repair).
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
                repairs=repairs,
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
                repairs=repairs,
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
        repairs: list[LLMUsage | None],
    ) -> dict[str, Any] | None:
        """Run ONE repair round; return valid args dict or ``None`` on failure.

        Reuses :func:`services.llm.oneshot.complete` (rides the per-request BYOK
        creds) to ask the SAME model to re-emit ONLY a valid JSON arguments
        object for ``tool_name`` given the schema + the validation error + its
        own raw args. The reply is parsed, schema-re-validated, and returned —
        ``None`` if it still cannot be parsed or still fails validation (the
        caller then surfaces an error turn). No network on the test path: the
        ``oneshot`` call is mocked. Past the round's repair cap it returns
        ``None`` without a call; each call is timed and its usage appended to
        ``repairs`` so it reaches the round's ``done``.
        """
        if not schema or len(repairs) >= _MAX_REPAIRS_PER_ROUND:
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
            reply, repair_usage = await oneshot.complete_with_usage(
                self._provider_id,
                model,
                api_key,
                [{"role": "user", "content": prompt}],
                timeout=_REPAIR_TIMEOUT_S,
            )
            repairs.append(repair_usage)
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
        # A schema echo validates for any tool with no required keys; it is not args.
        if parsed == schema or (set(parsed) & _SCHEMA_KEYWORDS) - set(
            schema.get("properties") or {}
        ):
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
        # OpenAI takes a ``web_search_options`` param (search-preview models only);
        # OpenRouter (WS5) takes its own ``{"type": "openrouter:web_search"}``
        # tools entry to ride the upstream model's native search. xAI and
        # DeepSeek have no native search here (xAI retired Live Search's
        # ``search_parameters``, R15-LEAD-008), so they are left untouched
        # (graceful no-op; the runtime keeps the local search tool).
        native_search = False
        if web_search:
            if self._provider_id == "openrouter":
                tools.append(openrouter_web_search_tool())
                native_search = True
            elif self._provider_id == "openai":
                # Chat-completions takes ``web_search_options`` — NOT a tools
                # entry. A ``{"type": "web_search"}`` tool 400s ("Supported
                # values are: 'function' and 'custom'"), and the param itself is
                # only accepted on the *-search-preview models, so anything else
                # rides the local search tool instead.
                if openai_native_search_supported(model):
                    request_kwargs["web_search_options"] = openai_web_search_options()
                    native_search = True
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
            repairs: list[LLMUsage | None] = []
            finish_reason: str | None = None
            # The native searches this round ran are counted from the raw usage
            # and the citations (R15-AGENT-049).
            raw_usage: Any = None
            cited = False
            # Function-call streaming sends the id/name once and the arguments
            # JSON in fragments across many chunks, keyed by the tool_call
            # index. Accumulate per index, then emit ONE tool_use event per
            # call with the parsed arguments dict when the round finishes.
            tool_buffers: dict[int, dict[str, str]] = {}
            # Accumulate assistant text for the content-leak rescue (Step 2):
            # a round that finishes with no native tool buffers may still carry
            # a leaked ``{"name", "arguments"}`` block in the text. On the gated
            # providers the text from a leaked call's marker on is held until
            # the rescue decides (rc1-drive-onboarding-stranger:1).
            hold = LeakHold(
                known_tool_ids if self._provider_id in _CONTENT_LEAK_PROVIDERS else set()
            )
            # Accumulate DeepSeek-reasoner ``reasoning_content`` (Step 4): the
            # reasoner streams its chain-of-thought in a SEPARATE delta field;
            # surface it as a thinking event so the runtime can echo it on the
            # reconstructed tool-use turn for a well-formed multi-round reasoner.
            emitted_tool_events = False
            # Chain-of-thought never reaches the answer (R15-LEAD-018): a
            # separate reasoning field, <think> spans and a reasoning echo in
            # content all come out as thinking events.
            splitter = ReasoningSplitter()
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
                        split = splitter.reasoning(reasoning) if reasoning else []
                        if getattr(delta, "annotations", None):
                            cited = True
                        content = getattr(delta, "content", None)
                        if content:
                            split += splitter.content(content)
                        for event in split:
                            if isinstance(event, LLMDeltaEvent):
                                shown = hold.feed(event.text)
                                if shown:
                                    yield LLMDeltaEvent(text=shown)
                                continue
                            yield event
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
                            events, failures, model=model, api_key=api_key, repairs=repairs
                        ):
                            emitted_tool_events = True
                            yield event
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    raw_usage = chunk_usage
                    usage = LLMUsage(
                        input_tokens=getattr(chunk_usage, "prompt_tokens", 0) or 0,
                        output_tokens=getattr(chunk_usage, "completion_tokens", 0) or 0,
                    )
            for event in splitter.flush():
                if isinstance(event, LLMDeltaEvent):
                    shown = hold.feed(event.text)
                    if shown:
                        yield LLMDeltaEvent(text=shown)
                    continue
                yield event
            # Stream ended with buffers still pending (no explicit
            # ``tool_calls`` finish_reason from this provider) — flush them so
            # the call is never dropped.
            if tool_buffers:
                events, failures = _drain_tool_buffers(tool_buffers)
                for event in await self._resolve_tool_events(
                    events, failures, model=model, api_key=api_key, repairs=repairs
                ):
                    emitted_tool_events = True
                    yield event
            # Content-leak rescue (Step 2): if the round produced NO tool calls
            # at all and did NOT finish via ``tool_calls``, but the accumulated
            # text carries a leaked ``{"name", "arguments"}`` block matching a
            # known tool, recover it. GATED to providers whose models do this
            # (DeepSeek / OpenRouter / Ollama) so a chatty-but-correct
            # OpenAI/Anthropic answer never mis-fires a tool the user did not
            # intend. A rescued call's held text is dropped; otherwise the held
            # text is shown now, so none is lost.
            rescued = None
            if (
                not emitted_tool_events
                and finish_reason != "tool_calls"
                and self._provider_id in _CONTENT_LEAK_PROVIDERS
                and known_tool_ids
            ):
                rescued = rescue_leaked_tool_call(hold.text, known_tool_ids)
            if rescued is not None:
                for event in await self._resolve_tool_events(
                    [rescued], [], model=model, api_key=api_key, repairs=repairs
                ):
                    emitted_tool_events = True
                    yield event
            elif hold.held():
                yield LLMDeltaEvent(text=hold.held())
            # A stream that ended with no finish_reason and no tool call never
            # finished (a cut socket, a 200 non-SSE body, empty choices): do not
            # fabricate a clean ``done`` for it — the consumer reports the
            # missing terminator (R15-AGENT-026).
            if finish_reason is None and not emitted_tool_events:
                return
            metered = [u for u in repairs if u is not None]
            if metered:
                base = usage or LLMUsage()
                usage = LLMUsage(
                    input_tokens=base.input_tokens + sum(u.input_tokens for u in metered),
                    output_tokens=base.output_tokens + sum(u.output_tokens for u in metered),
                )
            if native_search:
                searches = openai_shaped_search_count(self._provider_id, raw_usage, cited)
                usage = (usage or LLMUsage()).model_copy(update={"web_search_requests": searches})
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
        """Probe an authenticated endpoint with ``api_key``.

        ``/v1/models`` for OpenAI, DeepSeek and xAI. OpenRouter serves
        ``/models`` without auth (any string passes), so it probes ``/key``,
        which answers 401 on a bad key. xAI answers a bad key with 400
        "Incorrect API key", which is a bad key too, not a transport error.
        """
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            if self._provider_id == "openrouter":
                await client.get("/key", cast_to=dict[str, Any])
            else:
                await client.models.list()
            return True
        except openai.AuthenticationError:
            return False
        except openai.PermissionDeniedError:
            return False
        except openai.BadRequestError as exc:
            if says_invalid_key(str(exc)):
                return False
            raise
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
