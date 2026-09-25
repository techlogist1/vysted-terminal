"""Rescue a tool call a model leaked as plain text.

Some models answer a tool-capable turn by writing the call as JSON in the
assistant text (``{"name": "write_note", "parameters": {...}}``), or as call
syntax (``price_data(symbol="ZOMATO.NS")``), instead of
using the provider's native tool-call channel: DeepSeek's documented
text-fall-through, many OpenRouter-routed models, and local Ollama models such
as llama3.1:8b. Adapter-agnostic: each adapter calls :func:`rescue_leaked_tool_call`
at end of stream when no native tool call arrived. Only a name OFFERED this
round is rescued, so prose that merely mentions some other JSON never fires a
call. Ported as original code from the round-trip pattern litellm uses to coax
a function call out of a text-only response (no litellm import).
"""

from __future__ import annotations

import ast
import json
import re
import uuid
from typing import Any

from models.llm import LLMToolUseEvent

from .base import invalid_tool_args


def balanced_json_objects(text: str) -> list[str]:
    """Return every brace-balanced top-level ``{...}`` substring of ``text``.

    A leaked call is often embedded in prose, may carry a NESTED arguments
    object, and may be followed by other JSON. A non-greedy regex truncates at
    the first inner brace and a greedy one over-captures across a trailing
    object, so a brace-depth scan extracts each top-level object whole and
    ``json.loads`` is the real validator. Strings (with escapes) are tracked so
    a brace inside a quoted value never miscounts depth.
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


def _leaked_args(obj: dict[str, Any]) -> dict[str, Any]:
    """The call's arguments: OpenAI-style ``arguments`` or llama-style ``parameters``.

    Either may be an inline object or a JSON string. Absent means a no-argument
    call; anything unusable is stamped with the invalid-args sentinel.
    """
    raw = obj.get("arguments", obj.get("parameters"))
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return {}
    args = raw
    if isinstance(raw, str):
        try:
            args = json.loads(raw)
        except json.JSONDecodeError:
            return invalid_tool_args("arguments were not valid JSON", raw)
    if not isinstance(args, dict):
        return invalid_tool_args("arguments were not a JSON object", json.dumps(args))
    return args


def _call_syntax(text: str, offered: set[str]) -> tuple[str, dict[str, Any]] | None:
    """The first ``offered_name(k=<literal>, ...)`` call written into ``text``.

    llama3.1:8b also leaks a call as Python call syntax
    (``price_data(symbol="ZOMATO.NS")``). Each candidate is parsed with ``ast``
    and every argument must be a keyword with a literal value, so a bare-name
    mention such as ``research(X)``, a positional argument, or an expression
    never fires a call.
    """
    for match in re.finditer(r"\b([A-Za-z_]\w*)\(", text):
        name = match.group(1)
        if name not in offered:
            continue
        start = match.start(1)
        close = match.end()
        while (close := text.find(")", close)) != -1:
            try:
                call = ast.parse(text[start : close + 1], mode="eval").body
            except (SyntaxError, ValueError):
                close += 1
                continue
            keywords = call.keywords if isinstance(call, ast.Call) and not call.args else []
            if keywords and all(kw.arg for kw in keywords):
                try:
                    return name, {str(kw.arg): ast.literal_eval(kw.value) for kw in keywords}
                except (ValueError, TypeError):
                    pass
            break
    return None


def rescue_leaked_tool_call(text: str, offered: set[str]) -> LLMToolUseEvent | None:
    """Recover a tool call written into ``text``, or ``None`` if there is none.

    ``offered`` is the set of tool names sent this round. A candidate whose
    ``name`` is not in it stays text. JSON candidates are tried first, then
    keyword-literal call syntax (:func:`_call_syntax`). The rescued call gets a
    fresh unique id, because leaked text carries none the runtime could trust.
    """
    if not text or not offered:
        return None
    candidates: list[str] = []
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped).strip()
    candidates.append(stripped)
    candidates.extend(balanced_json_objects(text))
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("name")
        if not isinstance(name, str) or name not in offered:
            continue
        return LLMToolUseEvent(
            tool_call_id=f"leaked_{uuid.uuid4().hex}",
            name=name,
            input=_leaked_args(obj),
        )
    called = _call_syntax(text, offered)
    if called is not None:
        return LLMToolUseEvent(
            tool_call_id=f"leaked_{uuid.uuid4().hex}", name=called[0], input=called[1]
        )
    return None


__all__ = ["balanced_json_objects", "rescue_leaked_tool_call"]
