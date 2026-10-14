"""Keep a model's chain-of-thought out of the visible answer (R15-LEAD-018).

Reasoning reaches the content channel two ways, and both are routed here:

* ``<think>…</think>`` spans in the content stream (Ollama qwen3/deepseek-r1
  on templates that do not split thinking out). A tag can be cut across
  chunks, so a possible partial tag is held until the next piece decides it.
* An echo of the reasoning the provider already streamed in its own field.
  OpenRouter's free nemotron lane, when the output budget runs out mid-thought,
  sends the whole reasoning again as one ``content`` chunk before the
  ``length`` finish (fixture ``tests/fixtures/llm/nemotron_cot.jsonl``).
  Content that is still a prefix of the round's reasoning, before any real
  answer text, is held; if it diverges it is released as the answer, and if
  the round ends while it is still an echo it is dropped (it already went out
  as thinking).
"""

from __future__ import annotations

from models.llm import LLMDeltaEvent, LLMThinkingEvent

from .base import LLMStreamEvent

_OPEN = "<think>"
_CLOSE = "</think>"


def _partial_tag_len(text: str, tag: str) -> int:
    """Length of the longest proper prefix of ``tag`` that ``text`` ends with."""
    for size in range(min(len(tag) - 1, len(text)), 0, -1):
        if text.endswith(tag[:size]):
            return size
    return 0


class ReasoningSplitter:
    """Per-round stream filter: reasoning out as thinking, the answer as deltas."""

    def __init__(self) -> None:
        self._reasoning = ""
        self._echo = ""
        self._tag_tail = ""
        self._in_think = False
        self._answered = False

    def reasoning(self, text: str) -> list[LLMStreamEvent]:
        """Reasoning from the provider's own field (``reasoning``/``reasoning_content``)."""
        self._reasoning += text
        return [LLMThinkingEvent(text=text)]

    def content(self, text: str) -> list[LLMStreamEvent]:
        """One content chunk -> the thinking and answer events it resolves to."""
        out: list[LLMStreamEvent] = []
        buf, self._tag_tail = self._tag_tail + text, ""
        while buf:
            tag = _CLOSE if self._in_think else _OPEN
            at = buf.find(tag)
            if at == -1:
                keep = _partial_tag_len(buf, tag)
                out += self._emit(buf[: len(buf) - keep])
                self._tag_tail = buf[len(buf) - keep :]
                break
            out += self._emit(buf[:at])
            buf = buf[at + len(tag) :]
            self._in_think = not self._in_think
        return out

    def flush(self) -> list[LLMStreamEvent]:
        """End of the round: release a held partial tag; drop a pure echo."""
        tail, self._tag_tail = self._tag_tail, ""
        return self._emit(tail)

    def _emit(self, text: str) -> list[LLMStreamEvent]:
        if not text:
            return []
        if self._in_think:
            return [LLMThinkingEvent(text=text)]
        if not self._answered and self._reasoning:
            candidate = self._echo + text
            if self._reasoning.lstrip().startswith(candidate.lstrip()):
                self._echo = candidate
                return []
            self._echo, text = "", candidate
        self._answered = True
        return [LLMDeltaEvent(text=text)]
