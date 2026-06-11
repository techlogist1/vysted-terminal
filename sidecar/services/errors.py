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

import re
from dataclasses import dataclass


class ProviderError(RuntimeError):
    """Raised when a data provider cannot satisfy a request."""


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


def _extract_status_from_str(text: str) -> int | None:
    """Try to read an HTTP status from an OpenAI-SDK-style error string."""
    m = _ERROR_CODE_RE.search(text)
    if m:
        return int(m.group(1))
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

    The ``detail`` argument (or ``str(exc)`` when absent) becomes the raw
    text the UI hides behind a "Show details" toggle.
    """
    label = _provider_label(provider_id)
    raw = detail or (str(exc) if exc is not None else None)

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
    # Exception class / message heuristics (no HTTP status available)
    # -----------------------------------------------------------------------

    if exc is not None:
        cls_name = type(exc).__name__.lower()
        exc_str = str(exc).lower()

        # Timeout / connection errors
        if any(
            kw in cls_name or kw in exc_str
            for kw in (
                "timeout",
                "timedout",
                "connection",
                "connect",
                "connectionerror",
                "connecttimeout",
                "connecterror",
            )
        ):
            return HumanError(
                message=f"Could not reach {label} — check your network.",
                action="Check your internet connection and try again.",
                detail=raw,
                code="network",
            )

        # SSL errors
        if any(kw in cls_name or kw in exc_str for kw in ("ssl", "certificate", "sslerror")):
            return HumanError(
                message=f"A TLS/SSL error occurred connecting to {label}.",
                action="Check your network or try a different connection.",
                detail=raw,
                code="network",
            )

        # JSON / parse errors.
        # For json.JSONDecodeError (and jsonparse): class name match alone is
        # sufficient — the stdlib exception message ("Expecting value: line 1
        # column 1 (char 0)") contains none of "json/parse/decode", so the
        # AND condition would silently fall through to "unknown".
        # For the broad ValueError: keep the AND to stay precise.
        _json_class = any(kw in cls_name for kw in ("jsondecode", "jsonparse"))
        _value_error_json = cls_name == "valueerror" and any(
            kw in exc_str for kw in ("json", "parse", "decode")
        )
        if _json_class or _value_error_json:
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
