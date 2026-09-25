"""Google Gemini provider adapter.

Wraps ``google.genai.Client(...).aio.models.generate_content_stream(...)``
(unified ``google-genai`` SDK; the legacy ``google-generativeai`` package is
deprecated). The streaming API yields ``GenerateContentResponse`` objects
whose ``candidates[0].content.parts`` carry the text deltas.

Gemini's role enum is ``"user"`` / ``"model"``, distinct from the OpenAI
``"user"`` / ``"assistant"`` shape; the adapter translates at the boundary.
System instructions go on the top-level ``system_instruction`` field rather
than into the messages list.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import errors as genai_errors

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

from .base import LLMProvider, LLMStreamEvent
from .native_search import gemini_google_search_tool


def _split_system_and_contents(
    messages: list[LLMMessage],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Split out system messages and translate the rest to ``contents`` shape."""
    system_chunks: list[str] = []
    contents: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            system_chunks.append(message.content)
            continue
        if message.role == "tool":
            # A tool result is a ``functionResponse`` part on a "user" content.
            # Gemini keys the response by the tool *name*, not the call id (its
            # function-calling protocol pairs request/response by name + order).
            response_part = {
                "function_response": {
                    "name": message.metadata.get("name", "") if message.metadata else "",
                    "response": {"result": message.content},
                }
            }
            # Parallel calls: every response of one call turn rides ONE content,
            # or the API 400s on a response/call part-count mismatch.
            previous = contents[-1] if contents else None
            if (
                previous
                and previous["role"] == "user"
                and "function_response" in previous["parts"][-1]
            ):
                previous["parts"].append(response_part)
            else:
                contents.append({"role": "user", "parts": [response_part]})
            continue
        if message.role == "assistant" and message.metadata and message.metadata.get("tool_calls"):
            # Reconstruct the assistant tool-call turn as a "model" content with
            # ``functionCall`` parts so the following ``functionResponse`` parts
            # associate by name (runtime carries the calls in metadata).
            parts: list[dict[str, Any]] = []
            if message.content:
                parts.append({"text": message.content})
            for tc in message.metadata["tool_calls"]:
                part: dict[str, Any] = {
                    "function_call": {
                        "name": tc.get("name", ""),
                        "args": tc.get("input", {}) or {},
                    }
                }
                # Gemini 3 requires each call's thought signature back on the
                # same part (R15-AGENT-006); one part per call, never merged.
                signature = (tc.get("provider_meta") or {}).get("thought_signature")
                if signature:
                    part["thought_signature"] = base64.b64decode(signature)
                parts.append(part)
            contents.append({"role": "model", "parts": parts})
            continue
        # Gemini uses "model" for assistant turns and "user" for everything
        # else.
        role = "model" if message.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": message.content}]})
    system = "\n\n".join(system_chunks) if system_chunks else None
    return system, contents


class GeminiProvider(LLMProvider):
    """Google Gemini adapter via the unified ``google-genai`` SDK."""

    def _client(self, api_key: str | None) -> genai.Client:
        return genai.Client(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        # Pop tool_ids/web_search before anything reaches the SDK —
        # generate_content_stream rejects unknown kwargs, so these must never be
        # forwarded.
        tool_ids = kwargs.pop("tool_ids", None)
        web_search = bool(kwargs.pop("web_search", False))
        # Anthropic-only cap; pop so it never leaks into the SDK config.
        kwargs.pop("web_search_max_uses", None)
        system, contents = _split_system_and_contents(messages)
        config: dict[str, Any] = {}
        if system is not None:
            config["system_instruction"] = system
        config.update(kwargs.pop("config", {}) or {})
        tools: list[dict[str, Any]] = []
        if tool_ids:
            from services.agent_tools.schemas import gemini_tools

            tools.extend(gemini_tools(tool_ids))
        # Native server-side web search (FR-081): enable the ``google_search``
        # grounding tool, opt-in via ``web_search``. Alongside function tools it
        # is Gemini 3 only; ``native_search_available`` gates the flag per model,
        # so an agent round on an older model never sets it.
        if web_search:
            tools.append(gemini_google_search_tool())
        if tools:
            config["tools"] = tools
        client = self._client(api_key)
        try:
            stream = await client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config or None,
                **kwargs,
            )
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            # Each grounded search query is one billed search (R15-AGENT-049).
            search_queries: set[str] = set()
            # Function calls have no stable id in Gemini's protocol; synthesise a
            # stable one per call from the name + ordinal within the stream.
            tool_call_index = 0
            async for response in stream:
                # Text deltas — Gemini packs them into candidates[i].content.parts.
                candidates = getattr(response, "candidates", None) or []
                for candidate in candidates:
                    # Grounding can ride a content-less final chunk.
                    grounding = getattr(candidate, "grounding_metadata", None)
                    search_queries.update(getattr(grounding, "web_search_queries", None) or [])
                    # Read before the content check: a MAX_TOKENS/SAFETY stop can
                    # arrive on a candidate with no content at all.
                    reason = getattr(candidate, "finish_reason", None)
                    if reason:
                        finish_reason = str(reason)
                    content = getattr(candidate, "content", None)
                    if content is None:
                        continue
                    parts = getattr(content, "parts", None) or []
                    for part in parts:
                        text = getattr(part, "text", None)
                        if text:
                            yield LLMDeltaEvent(text=text)
                        fc = getattr(part, "function_call", None)
                        if fc is not None:
                            name = getattr(fc, "name", "") or ""
                            # Base64 so it survives a Delegate checkpoint's JSON dump.
                            signature = getattr(part, "thought_signature", None)
                            yield LLMToolUseEvent(
                                tool_call_id=getattr(fc, "id", None) or f"{name}_{tool_call_index}",
                                name=name,
                                input=dict(getattr(fc, "args", None) or {}),
                                provider_meta=(
                                    {"thought_signature": base64.b64encode(signature).decode()}
                                    if signature
                                    else None
                                ),
                            )
                            tool_call_index += 1
                # Usage arrives on every chunk; the final value wins.
                meta = getattr(response, "usage_metadata", None)
                if meta is not None:
                    # Gemini bills thinking and the tool-use prompt too
                    # (R15-CODE-AGENT-004); each count may be None.
                    usage = LLMUsage(
                        input_tokens=(getattr(meta, "prompt_token_count", 0) or 0)
                        + (getattr(meta, "tool_use_prompt_token_count", 0) or 0),
                        output_tokens=(getattr(meta, "candidates_token_count", 0) or 0)
                        + (getattr(meta, "thoughts_token_count", 0) or 0),
                    )
            if web_search:
                usage = (usage or LLMUsage()).model_copy(
                    update={"web_search_requests": len(search_queries)}
                )
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except genai_errors.APIError as exc:  # pragma: no cover — network path
            _h = humanize("gemini", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )
        except Exception as exc:  # pragma: no cover — defensive
            _h = humanize("gemini", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )

    async def validate_key(self, api_key: str | None = None) -> bool:
        """Probe ``models.list`` — the cheapest authenticated call."""
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            # ``models.list`` returns a pager; resolving it triggers a network
            # round-trip. The SDK does not surface a synchronous "1 page" knob,
            # so we iterate at most one entry.
            async for _ in await client.aio.models.list():
                break
            return True
        except genai_errors.ClientError as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if status in {401, 403}:
                return False
            # Gemini answers a bad key with 400 INVALID_ARGUMENT / API_KEY_INVALID.
            if status == 400 and says_invalid_key(str(exc)):
                return False
            raise

    async def list_models(self, api_key: str | None = None) -> list[LLMModelOption]:
        """Live catalog via ``models.list``, kept to ``generateContent`` models."""
        if not api_key:
            return []
        try:
            client = self._client(api_key)
            options: list[LLMModelOption] = []
            async for model in await client.aio.models.list():
                actions = getattr(model, "supported_actions", None) or []
                if "generateContent" not in actions:
                    continue
                name = getattr(model, "name", "") or ""
                model_id = name.split("/")[-1] if name else ""
                if not model_id:
                    continue
                options.append(
                    LLMModelOption(
                        id=model_id,
                        label=str(getattr(model, "display_name", None) or model_id),
                        context_length=getattr(model, "input_token_limit", None),
                    )
                )
            return options
        except genai_errors.ClientError as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if status in {401, 403}:
                return []
            raise
