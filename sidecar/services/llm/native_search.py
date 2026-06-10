"""Native server-side web search — provider tool injection + citation normalizer.

Five of the BYOK providers expose a *native* server-side web-search capability
billed to the user's own key (Pass B research, ``docs/redesign/PASS_B_RESEARCH.md``
§C.1; FR-081): Anthropic ``web_search``, OpenAI ``web_search``, Gemini
``google_search`` grounding, Groq Compound (search runs server-side, no explicit
tool), and xAI Live Search (``search_parameters`` in the request body, not a tool).

This module is the single source for two concerns:

1. **Tool injection** — small pure helpers each adapter calls to add its provider's
   native search affordance to the outgoing request, gated by an opt-in ``web_search``
   kwarg. When the active model does not support native search the helper is simply
   never called (the adapter no-ops), so the agent runtime can fall back to a BYOK
   search plugin (FR-082) without the adapter raising.
2. **Citation normalization** — each provider returns a different citation shape;
   :func:`normalize_anthropic` / :func:`normalize_openai` / :func:`normalize_gemini` /
   :func:`normalize_xai` flatten them to the common ``{url, title, excerpt}`` record
   so the research layer renders one citation UI regardless of backend.

No live API calls happen here; the helpers shape request payloads and parse
already-fetched response payloads only.
"""

from __future__ import annotations

from typing import Any

# The common citation record. Pass B's plugin contract (PASS_B_RESEARCH §C.4)
# settles on ``{url, title, excerpt}``; reuse ``services.search.base.Citation``
# when that module exists so the two layers can never drift, else fall back to a
# local dataclass with the same field names.
try:  # pragma: no cover - exercised only once the search package lands
    from services.search.base import Citation  # type: ignore[attr-defined]
except Exception:  # ImportError today; broaden so a half-built module can't crash import
    from dataclasses import dataclass

    @dataclass(slots=True)
    class Citation:  # type: ignore[no-redef]
        """A normalized web-search citation: source url, title, and a short excerpt."""

        url: str
        title: str
        excerpt: str


#: Providers that CAN serve native server-side web search billed to the user's
#: own key. Five expose it at the PROVIDER level (every routable model supports
#: it). ``openrouter`` is added in WS5 but is a special case: it is a broker, so
#: native search is a PER-MODEL property — the agent runtime gates OpenRouter on
#: the resolved model's :attr:`LLMModelOption.web_search` flag, not on mere
#: membership here. Membership only means "this provider has a native-search
#: rung at all"; the runtime gate is ``agent_runtime._native_search_enabled``.
SUPPORTS_NATIVE_SEARCH: set[str] = {"anthropic", "openai", "gemini", "groq", "xai", "openrouter"}

#: The five providers whose native search is a PROVIDER-level guarantee (any model
#: routes the provider's own search). OpenRouter is deliberately excluded — it is
#: per-model. The runtime uses this to keep the existing five working unchanged
#: while gating OpenRouter on the resolved model's capability.
PROVIDER_LEVEL_NATIVE_SEARCH: set[str] = {"anthropic", "openai", "gemini", "groq", "xai"}

#: Anthropic's server-side web-search tool type (dated tool version).
ANTHROPIC_WEB_SEARCH_TYPE = "web_search_20250305"
#: Default per-request search cap (Anthropic ``max_uses``); other providers cap
#: at the agent-runtime loop level since their APIs expose no per-request knob.
DEFAULT_WEB_SEARCH_MAX_USES = 5


# ---------------------------------------------------------------------------
# Tool injection helpers (request-builder side)
# ---------------------------------------------------------------------------


def anthropic_web_search_tool(max_uses: int = DEFAULT_WEB_SEARCH_MAX_USES) -> dict[str, Any]:
    """The Anthropic Messages ``tools`` entry enabling server-side web search.

    ``max_uses`` caps the searches per request (Anthropic is the only provider
    with a native per-request cap; the runtime enforces a loop counter for the
    rest). See PASS_B_RESEARCH §C.1.
    """
    return {
        "type": ANTHROPIC_WEB_SEARCH_TYPE,
        "name": "web_search",
        "max_uses": int(max_uses),
    }


def openai_web_search_tool() -> dict[str, Any]:
    """The OpenAI ``tools`` entry enabling server-side web search.

    The chat-completions / Responses ``tools`` array takes a bare
    ``{"type": "web_search"}`` entry; the model decides when to call it and the
    SDK returns ``url_citation`` annotations. OpenAI exposes no per-request cap,
    so the agent runtime enforces a loop-level search counter (PASS_B_RESEARCH §C.1).
    """
    return {"type": "web_search"}


def openrouter_web_search_tool() -> dict[str, Any]:
    """The OpenRouter ``tools`` entry enabling its native web search (WS5).

    OpenRouter rides the OpenAI-shaped adapter but takes its own tool type —
    ``{"type": "openrouter:web_search"}`` — to enable the upstream model's native
    server-side search (or, on a model OpenRouter prices a plugin for, its billed
    ``web`` plugin). Citations come back as OpenAI-style ``url_citation``
    annotations, so :func:`normalize_openai` parses them unchanged. Injected under
    the SAME ``web_search`` kwarg the other providers use; the runtime only sets
    that kwarg for OpenRouter when the resolved model is native-search capable.
    """
    return {"type": "openrouter:web_search"}


def xai_search_parameters() -> dict[str, Any]:
    """xAI Live Search ``search_parameters`` block for the request body.

    xAI rides the OpenAI adapter via a ``base_url`` override but does NOT use a
    ``tools`` entry for search — it takes a top-level ``search_parameters``
    object instead, and returns a ``citations[]`` array. ``mode="auto"`` lets
    Grok decide whether a query needs live data. (PASS_B_RESEARCH §C.1.)
    """
    return {"mode": "auto", "return_citations": True}


def gemini_google_search_tool() -> dict[str, Any]:
    """The Gemini ``config.tools`` entry enabling ``google_search`` grounding.

    Gemini's grounding tool is a bare ``{"google_search": {}}`` entry in the
    generation config's ``tools`` list; grounded responses carry
    ``grounding_metadata`` with ``groundingChunks``. (PASS_B_RESEARCH §C.1.)

    Note: Gemini's ToS requires rendering the returned Search-Suggestions UI;
    that is a frontend concern, surfaced via the grounding metadata.
    """
    return {"google_search": {}}


def provider_supports_native_search(provider_id: str) -> bool:
    """Return ``True`` when ``provider_id`` has a native server-side web search."""
    return provider_id in SUPPORTS_NATIVE_SEARCH


# ---------------------------------------------------------------------------
# R9 Track A interface — detection + invocation channel (Team B's cross-verify)
# ---------------------------------------------------------------------------


def native_search_available(provider_id: str, model_web_search: str | None = None) -> bool:
    """Decide whether THIS (provider, resolved-model) pair serves native search.

    THE one detection truth (the agent runtime's injection gate and Team B's
    tier_a cross-verify both read it, so the two surfaces can never disagree):

    * the five PROVIDER-level providers (anthropic/openai/gemini/groq/xai)
      always qualify — every routable model rides the provider's own search;
    * ``openrouter`` is a broker, so native search is a per-MODEL property:
      ``model_web_search`` is the resolved model's ``web_search`` capability
      flag (threaded from the frontend's public catalog) — only ``"native"``
      qualifies (``"plugin"`` is OpenRouter's billed web plugin, never
      auto-enabled; ``"none"``/unknown keeps the local search tool);
    * everything else has no native-search rung at all.
    """
    if provider_id in PROVIDER_LEVEL_NATIVE_SEARCH:
        return True
    if provider_id == "openrouter":
        return (model_web_search or "").strip().lower() == "native"
    return False


#: Per-call wall-clock cap for the invocation channel below — one grounded
#: completion, bounded so a stalled stream can never hang a cross-verify round.
NATIVE_SEARCH_ONESHOT_TIMEOUT_SECS = 90.0


async def native_search_oneshot(
    provider_id: str,
    model: str,
    api_key: str | None,
    prompt: str,
    *,
    model_web_search: str | None = None,
    max_searches: int = 3,
    timeout: float = NATIVE_SEARCH_ONESHOT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Run ONE native-search-grounded completion — the callable channel for
    Team B's tier_a cross-verify (R9 Track A interface).

    Drives the provider adapter's ``stream_chat`` with the ``web_search`` opt-in
    kwarg (each adapter injects its own native affordance; see the helpers
    above) and joins the streamed text. Returns::

        {"ok": True,  "text": <grounded completion>, "citations": [...]}
        {"ok": False, "reason": <"unavailable"|"empty"|"error">, "text": "",
         "citations": []}

    ``citations`` is best-effort ``{url, title, excerpt}`` records: the adapters
    currently surface native-search grounding inline in the TEXT (no structured
    citation events ride the stream), so the list is usually empty — callers
    must treat the text as the verification payload and the citations as a
    bonus, never a requirement. Never raises; never logs the key.
    ``model_web_search`` is the resolved model's capability flag (OpenRouter is
    per-model); an unavailable pair returns an honest ``ok: False`` rather than
    a silent ungrounded run.
    """
    if not native_search_available(provider_id, model_web_search):
        return {"ok": False, "reason": "unavailable", "text": "", "citations": []}

    import asyncio

    from models.llm import LLMMessage
    from services.llm import get_provider

    parts: list[str] = []

    async def _drive() -> None:
        adapter = get_provider(provider_id)  # type: ignore[arg-type]
        stream = adapter.stream_chat(
            messages=[LLMMessage(role="user", content=prompt)],
            model=model,
            api_key=api_key,
            web_search=True,
            web_search_max_uses=int(max_searches),
        )
        async for event in stream:
            kind = getattr(event, "kind", None)
            if kind == "delta":
                parts.append(getattr(event, "text", "") or "")
            elif kind in ("done", "error"):
                break
            # tool_use / thinking events are ignored — one grounded text call.

    try:
        await asyncio.wait_for(_drive(), timeout if timeout and timeout > 0 else None)
    except TimeoutError:
        pass  # keep the partial text — the caller tolerates a degraded pass
    except Exception:  # noqa: BLE001 - cross-verify tolerates an empty completion
        if not parts:
            return {"ok": False, "reason": "error", "text": "", "citations": []}

    text = "".join(parts).strip()
    if not text:
        return {"ok": False, "reason": "empty", "text": "", "citations": []}
    return {"ok": True, "text": text, "citations": []}


# ---------------------------------------------------------------------------
# Citation normalizers (response side)
# ---------------------------------------------------------------------------


def _citation(url: Any, title: Any, excerpt: Any) -> dict[str, str] | None:
    """Build a ``{url, title, excerpt}`` record, dropping entries without a url."""
    if not url or not isinstance(url, str):
        return None
    return {
        "url": url,
        "title": str(title) if title else "",
        "excerpt": str(excerpt) if excerpt else "",
    }


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or an attribute-style object (SDK model or dict)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_anthropic(blocks: Any) -> list[dict[str, str]]:
    """Normalize Anthropic ``web_search`` citations to ``{url, title, excerpt}``.

    Anthropic threads citations through ``web_search_result`` content blocks and
    ``text`` blocks whose ``citations`` carry ``url`` + ``title`` + ``cited_text``.
    Accepts either: a list of content blocks, or a list of citation objects.
    Defensive — any block missing a url is skipped.
    """
    out: list[dict[str, str]] = []
    if not blocks:
        return out
    if not isinstance(blocks, (list, tuple)):
        blocks = [blocks]
    for block in blocks:
        # A text block may carry a nested ``citations`` list.
        nested = _get(block, "citations")
        candidates = nested if isinstance(nested, (list, tuple)) else [block]
        for cand in candidates:
            url = _get(cand, "url")
            title = _get(cand, "title")
            excerpt = _get(cand, "cited_text")
            rec = _citation(url, title, excerpt)
            if rec is not None:
                out.append(rec)
    return out


def normalize_openai(annotations: Any) -> list[dict[str, str]]:
    """Normalize OpenAI ``url_citation`` annotations to ``{url, title, excerpt}``.

    The Responses/chat web-search tool returns ``annotations`` of
    ``type == "url_citation"`` each carrying ``url`` + ``title``; an excerpt is
    not always present (the message text around the span is the excerpt), so it
    degrades to "". Accepts the annotations list directly or a wrapper carrying
    ``annotations``. Defensive against missing fields.
    """
    out: list[dict[str, str]] = []
    if not annotations:
        return out
    if isinstance(annotations, dict) and "annotations" in annotations:
        annotations = annotations["annotations"]
    if not isinstance(annotations, (list, tuple)):
        annotations = [annotations]
    for ann in annotations:
        ann_type = _get(ann, "type")
        if ann_type is not None and ann_type != "url_citation":
            continue
        # The citation fields may be flat or nested under ``url_citation``.
        inner = _get(ann, "url_citation")
        src = inner if inner is not None else ann
        url = _get(src, "url")
        title = _get(src, "title")
        excerpt = _get(src, "snippet") or _get(src, "text")
        rec = _citation(url, title, excerpt)
        if rec is not None:
            out.append(rec)
    return out


def normalize_gemini(grounding_metadata: Any) -> list[dict[str, str]]:
    """Normalize Gemini ``grounding_metadata`` to ``{url, title, excerpt}``.

    Gemini grounding returns ``groundingChunks`` (camelCase over the wire;
    ``grounding_chunks`` on the SDK model) each with a ``web`` object carrying
    ``uri`` + ``title``. Excerpts live in ``groundingSupports[].segment.text``
    but are not chunk-keyed reliably, so the excerpt degrades to "".
    Defensive against missing fields and either casing.
    """
    out: list[dict[str, str]] = []
    if not grounding_metadata:
        return out
    chunks = _get(grounding_metadata, "grounding_chunks")
    if chunks is None:
        chunks = _get(grounding_metadata, "groundingChunks")
    if not isinstance(chunks, (list, tuple)):
        return out
    for chunk in chunks:
        web = _get(chunk, "web")
        if web is None:
            continue
        url = _get(web, "uri") or _get(web, "url")
        title = _get(web, "title")
        rec = _citation(url, title, "")
        if rec is not None:
            out.append(rec)
    return out


def normalize_xai(citations: Any) -> list[dict[str, str]]:
    """Normalize xAI Live Search citations to ``{url, title, excerpt}``.

    xAI returns a bare ``citations`` array — historically plain url strings, but
    newer responses may use objects with ``url`` + ``title``. Handle both: a
    string becomes a url-only citation; an object reads ``url``/``title``/
    ``snippet``. Defensive against missing fields.
    """
    out: list[dict[str, str]] = []
    if not citations:
        return out
    if isinstance(citations, dict) and "citations" in citations:
        citations = citations["citations"]
    if not isinstance(citations, (list, tuple)):
        citations = [citations]
    for cit in citations:
        if isinstance(cit, str):
            rec = _citation(cit, "", "")
        else:
            url = _get(cit, "url")
            title = _get(cit, "title")
            excerpt = _get(cit, "snippet") or _get(cit, "text")
            rec = _citation(url, title, excerpt)
        if rec is not None:
            out.append(rec)
    return out


__all__ = [
    "ANTHROPIC_WEB_SEARCH_TYPE",
    "DEFAULT_WEB_SEARCH_MAX_USES",
    "NATIVE_SEARCH_ONESHOT_TIMEOUT_SECS",
    "PROVIDER_LEVEL_NATIVE_SEARCH",
    "SUPPORTS_NATIVE_SEARCH",
    "Citation",
    "anthropic_web_search_tool",
    "gemini_google_search_tool",
    "native_search_available",
    "native_search_oneshot",
    "normalize_anthropic",
    "normalize_gemini",
    "normalize_openai",
    "normalize_xai",
    "openai_web_search_tool",
    "openrouter_web_search_tool",
    "provider_supports_native_search",
    "xai_search_parameters",
]
