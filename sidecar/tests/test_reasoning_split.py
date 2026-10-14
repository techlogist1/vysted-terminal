"""R15-LEAD-018: chain-of-thought is routed out of the visible answer."""

from __future__ import annotations

from services.llm.reasoning_split import ReasoningSplitter


def _run(splitter: ReasoningSplitter, pieces: list[tuple[str, str]]) -> tuple[str, str]:
    events = []
    for field, text in pieces:
        events += splitter.reasoning(text) if field == "reasoning" else splitter.content(text)
    events += splitter.flush()
    answer = "".join(e.text for e in events if e.kind == "delta")
    thinking = "".join(e.text for e in events if e.kind == "thinking")
    return answer, thinking


def test_think_span_split_across_chunks_becomes_thinking() -> None:
    answer, thinking = _run(
        ReasoningSplitter(),
        [("content", "<thi"), ("content", "nk>check the P/E</th"), ("content", "ink>P/E is 30.")],
    )
    assert (answer, thinking) == ("P/E is 30.", "check the P/E")


def test_content_echo_of_streamed_reasoning_is_dropped() -> None:
    answer, thinking = _run(
        ReasoningSplitter(),
        [
            ("reasoning", "The user asks"),
            ("reasoning", " about P/E."),
            ("content", "The user asks"),
        ],
    )
    assert (answer, thinking) == ("", "The user asks about P/E.")


def test_an_answer_that_starts_like_the_reasoning_is_kept_whole() -> None:
    answer, _ = _run(
        ReasoningSplitter(),
        [("reasoning", "The user asks about P/E."), ("content", "The"), ("content", " P/E is 30.")],
    )
    assert answer == "The P/E is 30."


def test_a_lone_angle_bracket_in_the_answer_is_released() -> None:
    answer, thinking = _run(
        ReasoningSplitter(), [("content", "P/E <"), ("content", " 20"), ("content", " <")]
    )
    assert (answer, thinking) == ("P/E < 20 <", "")
