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


_MARKER = re.compile(r'\{\s*"name"\s*:\s*"([A-Za-z_]\w*)"|\b([A-Za-z_]\w*)\(')


def leak_start(text: str, offered: set[str]) -> int | None:
    """Where a leaked call to an offered tool begins in ``text``, or ``None``.

    The first ``{"name": "<offered>"`` or ``<offered>(`` marker, taken back to
    the start of its line, or to a code-fence line just before it. The adapters
    hold streamed text from here, so a rescued call and the result the model
    typed after it never reach the user or the history
    (rc1-drive-onboarding-stranger:1).
    """
    for match in _MARKER.finditer(text):
        if (match.group(1) or match.group(2)) not in offered:
            continue
        start = text.rfind("\n", 0, match.start()) + 1
        if start:
            prev = text.rfind("\n", 0, start - 1) + 1
            if text[prev : start - 1].lstrip().startswith("```"):
                start = prev
        return start
    return None


#: A marker cut off at the end of the text: ``{`` plus a prefix of
#: ``"name": "<ident>``, or a trailing identifier (``<ident>(`` to come).
_PARTIAL_JSON = re.compile(r'\{\s*(?:"(?:n(?:a(?:m(?:e(?:"\s*(?::\s*(?:"(\w*))?)?)?)?)?)?)?)?\Z')
_PARTIAL_CALL = re.compile(r"\b([A-Za-z_]\w*)\Z")


def _partial_start(text: str, pos: int, offered: set[str]) -> int | None:
    """Where a marker that may still become a leaked call to an offered tool
    starts at the end of ``text`` (searched from ``pos``), or ``None``."""
    for pattern in (_PARTIAL_JSON, _PARTIAL_CALL):
        match = pattern.search(text, pos)
        if match and any(name.startswith(match.group(1) or "") for name in offered):
            return match.start()
    return None


class LeakHold:
    """Streams text up to a leaked-call marker, then holds the rest.

    :meth:`feed` returns the chunks to show now. A chunk where a marker may be
    starting (``{"na``, ``price``) is held whole until the marker completes or
    stops matching an offered name, then replayed as it came (R15-LEAD-031).
    At end of stream the adapter drops :meth:`held` when the rescue fires and
    shows it otherwise, so no text is ever lost. An empty ``offered`` never holds.
    """

    def __init__(self, offered: set[str]) -> None:
        self.offered = offered
        self.text = ""
        self._shown = 0
        self._hold: int | None = None
        self._pending: list[str] = []  # chunks held while a partial marker may complete

    def feed(self, chunk: str) -> list[str]:
        self.text += chunk
        if self._hold is None and self.offered:
            # ponytail: rescans the whole text per chunk (quadratic in chunks);
            # scan from the last line start if a long answer ever shows it.
            start = leak_start(self.text, self.offered)
            if start is not None:
                self._hold = max(start, self._shown)
        if self._hold is not None:
            shown = self.text[self._shown : self._hold]
            self._shown = self._hold
            self._pending = []
            return [shown] if shown else []
        self._pending.append(chunk)
        cut = _partial_start(self.text, self._shown, self.offered) if self.offered else None
        out: list[str] = []
        while self._pending and (cut is None or self._shown + len(self._pending[0]) <= cut):
            out.append(self._pending.pop(0))
            self._shown += len(out[-1])
        return [c for c in out if c]

    def held(self) -> str:
        return self.text[self._shown :]


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


__all__ = ["LeakHold", "balanced_json_objects", "leak_start", "rescue_leaked_tool_call"]
