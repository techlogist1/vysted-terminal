"""Shared error types and the LLM-error humanizer.

``ProviderError`` is raised by data-provider services on upstream failure;
``humanize`` converts raw provider exceptions (or raw HTTP status codes from
the LLM adapters) into plain-language :class:`HumanError` structs the chat
UI can render without exposing JSON blobs or tracebacks to the user.

Design constraints
~~~~~~~~~~~~~~~~~~
- Dependency-free: only the Python standard library and
  :mod:`dataclasses`. No openai / anthropic / groq imports at module level
  — exception classes are matched by string type name so this module stays
  importable in every context.
- Provider display names come from the canonical map here; adapters pass
  their ``provider_id`` and need not re-spell the label.
- The ``code`` field is a stable machine tag the frontend can branch on.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

ProviderErrorKind = Literal["rate_limited", "not_found", "network"]

_log = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Raised when a data provider cannot satisfy a request.

    ``kind`` optionally classifies the failure so callers can react to a
    throttle differently than to genuine absence (R11 / D53):

      - ``"rate_limited"`` — the upstream throttled the request (HTTP 429 /
        ``YFRateLimitError``). Callers should back off / consult the circuit
        breaker and report the skip as ``rate_limited``, never ``no_data``.
      - ``"not_found"`` — the upstream answered and has no such instrument or
        series.
      - ``"network"`` — the upstream could not be reached (connection refused,
        DNS failure, timeout).
      - ``None`` — unclassified (the pre-R11 behaviour, handled as before).
    """

    def __init__(self, message: str, *, kind: ProviderErrorKind | None = None) -> None:
        super().__init__(message)
        self.kind = kind


#: The one ProviderError -> HTTP mapping (D-B8-10, D-B9-1): per kind the status,
#: the ``code``, the sentence the panel shows and the next step. Raw upstream text
#: goes to the sidecar log only. An unclassified error with no ``__cause__`` keeps
#: the provider layer's own authored message (e.g. "FRED needs a free API key");
#: one that wraps a cause gets :data:`_UNEXPECTED_SENTENCE`.
_PROVIDER_ERROR_HTTP: dict[str | None, tuple[int, str, str | None, str]] = {
    "rate_limited": (
        429,
        "rate_limited",
        "The data provider is throttled right now — try again shortly.",
        "Wait a minute, then retry.",
    ),
    "not_found": (
        404,
        "not_found",
        "The data provider has no data for this symbol or series — check the symbol.",
        "Check the symbol or series id.",
    ),
    "network": (
        503,
        "network",
        "Could not reach the data provider — check your internet connection.",
        "Retry once you are back online.",
    ),
    None: (502, "provider_error", None, "Retry, or try again later."),
}


_UNEXPECTED_SENTENCE = "The data provider returned an unexpected response."

#: Transport failures across requests, httpx, curl_cffi and the builtins,
#: matched by class name anywhere in the MRO (this module imports no HTTP stack).
_NETWORK_ERROR_NAMES = frozenset(
    {
        "ConnectionError",
        "ConnectError",
        "ProxyError",
        "Timeout",
        "TimeoutError",
        "TimeoutException",
        "DNSError",
    }
)


def _kind_from_cause(exc: BaseException) -> ProviderErrorKind | None:
    """Classify an unclassified ProviderError from what it wraps: an HTTP 404 is
    ``not_found``, a 429 ``rate_limited``, a connection/timeout error ``network``."""
    seen: list[BaseException] = []
    node = exc.__cause__
    while node is not None and all(node is not s for s in seen):
        seen.append(node)
        response = getattr(node, "response", None)
        status = getattr(response, "status_code", None) or getattr(node, "status_code", None)
        if status == 404:
            return "not_found"
        if status == 429:
            return "rate_limited"
        if any(cls.__name__ in _NETWORK_ERROR_NAMES for cls in type(node).__mro__):
            return "network"
        node = node.__cause__ or node.__context__
    return None


def provider_error_response(exc: ProviderError) -> tuple[int, dict[str, str]]:
    """``(status, body)`` for a data-route :class:`ProviderError` (C5).

    ``body`` is ``{"detail": <sentence>, "code": <kind>, "action": <next step>}``;
    ``detail`` stays a string so the frontend's ``SidecarError`` reads it as
    before. Library text never reaches ``detail`` (D-B9-1)."""
    kind = exc.kind or _kind_from_cause(exc)
    status, code, sentence, action = _PROVIDER_ERROR_HTTP[kind]
    if sentence is None:
        if exc.__cause__ is None:
            sentence = str(exc)
        else:
            sentence = _UNEXPECTED_SENTENCE
            _log.warning("unexpected provider response: %s", exc)
    return status, {"detail": sentence, "code": code, "action": action}


# ---------------------------------------------------------------------------
# Provider display names
# ---------------------------------------------------------------------------

_PROVIDER_LABELS: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "groq": "Groq",
    "ollama": "Ollama",
    "deepseek": "DeepSeek",
    "xai": "xAI",
    "openrouter": "OpenRouter",
}


def _provider_label(provider_id: str | None) -> str:
    """Return a human display name for a provider id."""
    if not provider_id:
        return "the AI provider"
    return _PROVIDER_LABELS.get(provider_id, provider_id)


# ---------------------------------------------------------------------------
# HumanError contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HumanError:
    """Plain-language error struct for the chat error frame.

    ``message`` is shown immediately; ``action`` is a one-line suggestion;
    ``detail`` is the raw provider text hidden behind a "Show details" toggle
    in the UI; ``code`` is a stable machine tag for frontend branching.
    """

    message: str  # plain language, one sentence
    action: str | None  # the next step ("Top up or switch provider in Settings")
    detail: str | None  # the raw provider text — UI shows behind a toggle
    code: str | None  # machine tag: "provider_402", "network", "auth", ...


# ---------------------------------------------------------------------------
# Status-to-message map
# ---------------------------------------------------------------------------

# Regex that matches the OpenAI-SDK-style "Error code: NNN - {…}" format so
# we can extract a numeric status from raw exception strings when no SDK
# attribute is available.
_ERROR_CODE_RE = re.compile(r"Error code:\s*(\d{3})", re.IGNORECASE)


#: Lower-case body substrings that mean "this API key is bad" on providers that
#: answer a bad key with 400 instead of 401 (Gemini ``API_KEY_INVALID`` / "API
#: key not valid", xAI "Incorrect API key provided").
_INVALID_KEY_MARKERS = (
    "api_key_invalid",
    "api key not valid",
    "incorrect api key",
    "invalid api key",
)


def says_invalid_key(text: str) -> bool:
    """True when a provider error body says the API key itself is bad."""
    low = text.lower()
    return any(marker in low for marker in _INVALID_KEY_MARKERS)


def _extract_status_from_str(text: str) -> int | None:
    """Try to read an HTTP status from an OpenAI-SDK-style error string."""
    m = _ERROR_CODE_RE.search(text)
    if m:
        return int(m.group(1))
    return None


#: Body-aware rules, checked in order BEFORE the status-only fallbacks: the same
#: status means different things (a no-credit 429 is not a wait-a-minute 429, a
#: 400 can be a bad key, a bad model id or an overflowing prompt). Each row is
#: (provider or None for any, statuses or None for any/no status, lower-case
#: body markers (any one; empty = always), code, message, action). ``{label}``
#: is the provider name; ``{model}`` is the model named in an Ollama body.
_BODY_RULES: tuple[
    tuple[str | None, frozenset[int] | None, tuple[str, ...], str, str, str], ...
] = (
    (
        "openrouter",
        frozenset({429}),
        ("upstream_provider_shared_pool", ":free"),
        "free_pool_busy",
        "{label}'s free-model pool is busy right now.",
        "Try again shortly, or pick a paid model in Settings.",
    ),
    (
        None,
        frozenset({400}),
        _INVALID_KEY_MARKERS,
        "auth",
        "The {label} API key was rejected — check it in Settings.",
        "Re-enter the API key in Settings.",
    ),
    (
        None,
        frozenset({400, 429}),
        ("credit", "quota", "billing"),
        "insufficient_credit",
        "Your {label} account is out of credit or quota.",
        "Add credit or check your plan, or switch provider in Settings.",
    ),
    (
        None,
        frozenset({400}),
        ("not a valid model", "invalid model", "model not found", "model_not_found"),
        "model_not_found",
        "The requested model is not available on {label} — pick another model.",
        "Choose a different model in Settings.",
    ),
    (
        None,
        frozenset({413}),
        (),
        "context_overflow",
        "The conversation is too long for this {label} model.",
        "Start a new chat or pick a model with a larger context window.",
    ),
    (
        None,
        frozenset({400}),
        ("context length", "context_length", "maximum context", "context window", "too long"),
        "context_overflow",
        "The conversation is too long for this {label} model.",
        "Start a new chat or pick a model with a larger context window.",
    ),
    (
        "ollama",
        None,
        ("all connection attempts failed", "connection refused", "failed to connect"),
        "ollama_not_running",
        "Ollama is not running.",
        "Start Ollama (open the app or run `ollama serve`), then try again.",
    ),
    (
        "ollama",
        frozenset({404}),
        ("pull", "not found"),
        "model_not_pulled",
        "The model {model} is not downloaded in Ollama.",
        "Run `ollama pull {model}`, or pick an installed model in Settings.",
    ),
)

_OLLAMA_MODEL_RE = re.compile(r"""model ["']([^"']+)["']""")

#: OpenRouter echoes the account's ``user_id`` in error bodies; keep it out of
#: the detail the UI shows (and users paste into bug reports).
_USER_ID_RE = re.compile(r"""(["']user_id["']\s*:\s*)(["'])[^"']*\2""")


def _match_body_rule(
    provider_id: str | None, status: int | None, raw: str, label: str
) -> HumanError | None:
    """The first :data:`_BODY_RULES` row matching provider, status and body."""
    low = raw.lower()
    for provider, statuses, markers, code, message, action in _BODY_RULES:
        if provider is not None and provider != provider_id:
            continue
        if statuses is not None and status not in statuses:
            continue
        if markers and not any(marker in low for marker in markers):
            continue
        model_match = _OLLAMA_MODEL_RE.search(raw)
        model = model_match.group(1) if model_match else "<model>"
        return HumanError(
            message=message.format(label=label, model=model),
            action=action.format(label=label, model=model),
            detail=raw,
            code=code,
        )
    return None


def humanize(
    provider_id: str | None,
    exc: Exception | None = None,
    *,
    status: int | None = None,
    detail: str | None = None,
) -> HumanError:
    """Convert a provider exception or HTTP status into a :class:`HumanError`.

    Lookup priority:
    1. Explicit ``status`` argument.
    2. ``.status_code`` / ``.status`` / ``.code`` attributes on ``exc``.
    3. Pattern-match ``str(exc)`` for the OpenAI "Error code: NNN" shape.
    4. Class name heuristics (timeout, connection, SSL, JSON).

    The body-aware :data:`_BODY_RULES` are checked before the status-only
    classification. The ``detail`` argument (or ``str(exc)`` when absent),
    with any ``user_id`` scrubbed, becomes the raw text the UI hides behind a
    "Show details" toggle.
    """
    label = _provider_label(provider_id)
    raw = detail or (str(exc) if exc is not None else None)
    if raw:
        raw = _USER_ID_RE.sub(r"\1\2<redacted>\2", raw)

    # Resolve the HTTP status if not explicitly provided.
    if status is None and exc is not None:
        for attr in ("status_code", "status", "code"):
            val = getattr(exc, attr, None)
            if isinstance(val, int) and 100 <= val < 600:
                status = val
                break
        # httpx.HTTPStatusError carries the status on response.status_code, not
        # directly on the exception — check that path so these errors classify
        # correctly instead of falling through to "unknown".
        if status is None:
            response = getattr(exc, "response", None)
            if response is not None:
                val = getattr(response, "status_code", None)
                if isinstance(val, int) and 100 <= val < 600:
                    status = val
        if status is None and raw:
            status = _extract_status_from_str(raw)

    if raw:
        matched = _match_body_rule(provider_id, status, raw, label)
        if matched is not None:
            return matched

    # -----------------------------------------------------------------------
    # HTTP status classification
    # -----------------------------------------------------------------------

    if status == 402:
        if provider_id == "deepseek":
            return HumanError(
                message=("Your DeepSeek balance is empty — top up or switch provider in Settings."),
                action=(
                    "Top up at platform.deepseek.com or pick a different provider in Settings."
                ),
                detail=raw,
                code="provider_402",
            )
        return HumanError(
            message=f"Your {label} account has no credit.",
            action="Add credit or switch provider in Settings.",
            detail=raw,
            code="provider_402",
        )

    if status in {401, 403}:
        return HumanError(
            message=f"The {label} API key was rejected — check it in Settings.",
            action="Re-enter the API key in Settings.",
            detail=raw,
            code="auth",
        )

    if status == 404:
        # 404 on LLM paths almost always means the model id is wrong.
        return HumanError(
            message=f"The requested model is not available on {label} — pick another model.",
            action="Choose a different model in Settings.",
            detail=raw,
            code="model_not_found",
        )

    if status == 429:
        return HumanError(
            message=f"{label} is rate-limiting your account — try again in a minute.",
            action="Wait a moment, then try again.",
            detail=raw,
            code="rate_limit",
        )

    if status is not None and status >= 500:
        return HumanError(
            message=f"{label} returned a server error — it may be a temporary outage.",
            action="Try again in a few minutes.",
            detail=raw,
            code="provider_5xx",
        )

    # -----------------------------------------------------------------------
    # Exception class heuristics (no HTTP status available). Class names only:
    # a message that merely mentions "connection" or "parse" is not evidence
    # the provider failed (R15-AGENT-030).
    # -----------------------------------------------------------------------

    if exc is not None:
        cls_name = type(exc).__name__.lower()

        # Timeout / connection errors
        if any(kw in cls_name for kw in ("timeout", "timedout", "connect")):
            return HumanError(
                message=f"Could not reach {label} — check your network.",
                action="Check your internet connection and try again.",
                detail=raw,
                code="network",
            )

        # SSL errors
        if any(kw in cls_name for kw in ("ssl", "certificate")):
            return HumanError(
                message=f"A TLS/SSL error occurred connecting to {label}.",
                action="Check your network or try a different connection.",
                detail=raw,
                code="network",
            )

        # JSON / parse errors (json.JSONDecodeError and the like).
        if any(kw in cls_name for kw in ("jsondecode", "jsonparse")):
            return HumanError(
                message=f"{label} returned an unreadable response.",
                action="Try again; if the problem persists, check the provider's status page.",
                detail=raw,
                code="parse_error",
            )

        # Authentication errors from SDK classes
        if any(kw in cls_name for kw in ("authentication", "auth", "unauthorized", "forbidden")):
            return HumanError(
                message=f"The {label} API key was rejected — check it in Settings.",
                action="Re-enter the API key in Settings.",
                detail=raw,
                code="auth",
            )

        # Rate-limit errors from SDK classes
        if any(kw in cls_name for kw in ("ratelimit", "toomanyrequests")):
            return HumanError(
                message=f"{label} is rate-limiting your account — try again in a minute.",
                action="Wait a moment, then try again.",
                detail=raw,
                code="rate_limit",
            )

        # Payment / credit errors from SDK classes
        if any(kw in cls_name for kw in ("payment", "credit", "billing", "quota")):
            if provider_id == "deepseek":
                return HumanError(
                    message=(
                        "Your DeepSeek balance is empty — top up or switch provider in Settings."
                    ),
                    action=(
                        "Top up at platform.deepseek.com or pick a different provider in Settings."
                    ),
                    detail=raw,
                    code="provider_402",
                )
            return HumanError(
                message=f"Your {label} account has no credit.",
                action="Add credit or switch provider in Settings.",
                detail=raw,
                code="provider_402",
            )

    # -----------------------------------------------------------------------
    # Generic fallback
    # -----------------------------------------------------------------------

    return HumanError(
        message=f"Something went wrong with {label}.",
        action="Try again or switch provider in Settings.",
        detail=raw,
        code="unknown",
    )


def error_frame(exc: BaseException) -> dict[str, Any]:
    """The SSE ``{kind:"error", message, action, detail, code:"internal"}`` frame
    both SSE routers' last-resort guards emit.

    The adapters humanize their own provider failures into error events, so an
    exception reaching a router guard is the terminal's own fault (runtime,
    tool, store) — never blamed on the provider or the user's network
    (R15-AGENT-030). The raw ``type: message`` rides ``detail`` behind the UI's
    "Show details" toggle.
    """
    return {
        "kind": "error",
        "message": "The terminal hit an internal error.",
        "action": "Try again; if it keeps happening, restart Vysted.",
        "detail": f"{type(exc).__name__}: {exc}",
        "code": "internal",
    }
