"""Tests for services.errors — the LLM-error humanizer.

All assertions are against the stable HumanError contract fields: message,
action, detail, code. No live network calls are made.
"""

from __future__ import annotations

import pytest

from services.errors import HumanError, ProviderError, humanize

# ---------------------------------------------------------------------------
# ProviderError smoke test
# ---------------------------------------------------------------------------


def test_provider_error_is_runtime_error() -> None:
    exc = ProviderError("upstream failed")
    assert isinstance(exc, RuntimeError)
    assert "upstream failed" in str(exc)


# ---------------------------------------------------------------------------
# HTTP status-based classification
# ---------------------------------------------------------------------------


class _FakeExc(Exception):
    """Minimal exception with a status_code attribute."""

    def __init__(self, msg: str, status_code: int) -> None:
        super().__init__(msg)
        self.status_code = status_code


def test_402_deepseek_balance() -> None:
    h = humanize("deepseek", _FakeExc("payment required", 402))
    assert h.code == "provider_402"
    assert "DeepSeek" in h.message
    assert "balance" in h.message.lower()
    assert h.action is not None
    assert "top up" in h.action.lower() or "Settings" in h.action


def test_402_generic_provider() -> None:
    h = humanize("openai", _FakeExc("payment required", 402))
    assert h.code == "provider_402"
    assert "OpenAI" in h.message
    assert "credit" in h.message.lower()


def test_401_auth_rejected() -> None:
    h = humanize("anthropic", _FakeExc("unauthorized", 401))
    assert h.code == "auth"
    assert "Anthropic" in h.message
    assert "key" in h.message.lower()


def test_403_auth_rejected() -> None:
    h = humanize("groq", _FakeExc("forbidden", 403))
    assert h.code == "auth"
    assert "Groq" in h.message


def test_404_model_not_found() -> None:
    h = humanize("openai", _FakeExc("not found", 404))
    assert h.code == "model_not_found"
    assert "model" in h.message.lower() or "not available" in h.message.lower()


def test_429_rate_limit() -> None:
    h = humanize("gemini", _FakeExc("too many requests", 429))
    assert h.code == "rate_limit"
    assert "rate" in h.message.lower() or "limiting" in h.message.lower()


def test_500_server_error() -> None:
    h = humanize("openai", _FakeExc("internal server error", 500))
    assert h.code == "provider_5xx"
    assert "server error" in h.message.lower() or "outage" in h.message.lower()


def test_503_server_error() -> None:
    h = humanize("anthropic", _FakeExc("service unavailable", 503))
    assert h.code == "provider_5xx"


# ---------------------------------------------------------------------------
# Explicit status argument (no exception)
# ---------------------------------------------------------------------------


def test_explicit_status_no_exc() -> None:
    h = humanize("openai", status=402)
    assert h.code == "provider_402"


def test_explicit_status_with_detail() -> None:
    h = humanize("groq", status=401, detail="raw provider JSON blob")
    assert h.code == "auth"
    assert h.detail == "raw provider JSON blob"


# ---------------------------------------------------------------------------
# "Error code: NNN" string extraction
# ---------------------------------------------------------------------------


def test_error_code_string_extraction_402() -> None:
    exc = Exception('Error code: 402 - {"error": "Insufficient balance"}')
    h = humanize("deepseek", exc)
    assert h.code == "provider_402"
    assert "DeepSeek" in h.message


def test_error_code_string_extraction_401() -> None:
    exc = Exception("Error code: 401 - Invalid API key")
    h = humanize("openai", exc)
    assert h.code == "auth"


def test_error_code_string_extraction_429() -> None:
    exc = Exception("Error code: 429 - Rate limit exceeded")
    h = humanize("openai", exc)
    assert h.code == "rate_limit"


# ---------------------------------------------------------------------------
# Exception class heuristics
# ---------------------------------------------------------------------------


def test_timeout_class_heuristic() -> None:
    class TimeoutError(Exception):
        pass

    h = humanize("openai", TimeoutError("timed out"))
    assert h.code == "network"
    assert "reach" in h.message.lower() or "network" in h.message.lower()


def test_connection_error_heuristic() -> None:
    class ConnectionError(Exception):
        pass

    h = humanize("anthropic", ConnectionError("connection refused"))
    assert h.code == "network"


def test_ssl_error_heuristic() -> None:
    class SSLError(Exception):
        pass

    h = humanize("gemini", SSLError("ssl certificate verify failed"))
    assert h.code == "network"


def test_json_decode_error_heuristic() -> None:
    import json

    try:
        json.loads("not-json")
    except json.JSONDecodeError as exc:
        h = humanize("openai", exc)
        # json.JSONDecodeError: class name is "jsondecode" (lowercase) — the
        # class-name-only branch fires without requiring the message to contain
        # "json/parse/decode" (the stdlib message is "Expecting value: line 1
        # column 1 (char 0)" which does NOT contain those keywords).
        assert h.code == "parse_error"


# ---------------------------------------------------------------------------
# httpx.HTTPStatusError — status on response.status_code (not exc attribute)
# ---------------------------------------------------------------------------


def test_httpx_response_status_code() -> None:
    """Exceptions where the HTTP status lives on exc.response.status_code (e.g.
    httpx.HTTPStatusError) must still classify correctly."""

    class _FakeResponse:
        status_code: int = 401

    class _FakeHTTPStatusError(Exception):
        response = _FakeResponse()

    h = humanize("openai", _FakeHTTPStatusError("401 unauthorized"))
    assert h.code == "auth"
    assert "OpenAI" in h.message


def test_httpx_response_status_code_402() -> None:
    class _FakeResponse:
        status_code: int = 402

    class _FakeHTTPStatusError(Exception):
        response = _FakeResponse()

    h = humanize("deepseek", _FakeHTTPStatusError("payment required"))
    assert h.code == "provider_402"
    assert "DeepSeek" in h.message


# ---------------------------------------------------------------------------
# detail passthrough
# ---------------------------------------------------------------------------


def test_detail_passthrough_from_exception() -> None:
    exc = _FakeExc("raw provider message", 402)
    h = humanize("openai", exc)
    # When detail is not provided, str(exc) becomes the detail.
    assert h.detail == str(exc)


def test_detail_explicit_overrides_exc_str() -> None:
    exc = _FakeExc("ignored", 402)
    h = humanize("openai", exc, detail="my custom detail")
    assert h.detail == "my custom detail"


# ---------------------------------------------------------------------------
# None provider fallback label
# ---------------------------------------------------------------------------


def test_none_provider_label() -> None:
    h = humanize(None, status=401)
    assert h.code == "auth"
    assert "provider" in h.message.lower()


# ---------------------------------------------------------------------------
# Unknown provider falls back gracefully
# ---------------------------------------------------------------------------


def test_unknown_provider_generic_fallback() -> None:
    h = humanize("my-custom-llm", status=None)
    assert h.code == "unknown"
    assert "my-custom-llm" in h.message


# ---------------------------------------------------------------------------
# HumanError is frozen (immutable)
# ---------------------------------------------------------------------------


def test_human_error_frozen() -> None:
    h = HumanError(message="x", action=None, detail=None, code="auth")
    with pytest.raises((AttributeError, TypeError)):
        h.message = "y"  # type: ignore[misc]
