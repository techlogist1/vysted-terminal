"""LIVE validation of the native-citation normalizer against a real provider.

The 5 citation normalizers (``services.llm.native_search``) are unit-tested against
fake payloads but were never validated against a real provider response. This test
closes that gap for the OpenAI-shaped path (which OpenRouter's ``:online`` web plugin
emits): one cheap, non-streaming call, feed the live ``annotations`` to
``normalize_openai``, assert it yields real ``{url,title,excerpt}`` sources.

It is SKIPPED unless ``OPENROUTER_LIVE_KEY`` is set in the environment — it never
reads the OS keychain (the sidecar can't) and never logs the key. To run it, the
operator exports the key for the run; the project's standing rule is to keep BYOK
secrets out of the shell, so this stays an explicit, opt-in manual/CI step rather
than something the autonomous run executes by extracting the key.

    OPENROUTER_LIVE_KEY=… python -m pytest tests/test_native_search_live.py -q

Cost ceiling: ``max_tokens=200`` + ``max_results=2`` on the cheapest ``:online``
model — a single call, well under a cent.
"""

from __future__ import annotations

import os

import httpx
import pytest

from services.llm.native_search import normalize_openai

_KEY = os.getenv("OPENROUTER_LIVE_KEY")

#: Cheapest tool+web-capable ``:online`` models, tried in order until one returns
#: annotations (model availability drifts; the first that cites wins).
_MODELS = (
    "google/gemini-2.5-flash-lite:online",
    "openai/gpt-4o-mini:online",
    "perplexity/sonar",
)


@pytest.mark.skipif(not _KEY, reason="set OPENROUTER_LIVE_KEY to run the live citation check")
def test_openrouter_online_annotations_normalize() -> None:
    headers = {
        "Authorization": f"Bearer {_KEY}",
        "HTTP-Referer": "https://vysted.app",
        "X-Title": "Vysted Terminal",
    }
    last_error: str | None = None
    for model in _MODELS:
        body = {
            "model": model,
            "max_tokens": 200,
            "plugins": [{"id": "web", "max_results": 2}],
            "messages": [
                {"role": "user", "content": "What is Apple's most recent 10-K filing date? Cite."}
            ],
        }
        try:
            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=45,
            )
        except httpx.HTTPError as exc:
            last_error = f"{model}: transport {exc}"
            continue
        if resp.status_code != 200:
            last_error = f"{model}: HTTP {resp.status_code}"
            continue
        message = resp.json()["choices"][0]["message"]
        annotations = message.get("annotations")
        # The key must never leak into a captured payload/repr.
        assert _KEY not in repr(resp.json())
        if not annotations:
            last_error = f"{model}: no annotations"
            continue
        sources = normalize_openai(annotations)
        assert sources, f"{model}: normalize_openai produced no sources from {annotations!r}"
        assert all(s["url"].startswith("http") for s in sources)
        return  # validated

    pytest.fail(f"no :online model returned normalizable citations ({last_error})")
