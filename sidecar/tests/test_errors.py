"""Tests for services.errors — the LLM-error humanizer.

All assertions are against the stable HumanError contract fields: message,
action, detail, code. No live network calls are made.
"""

from __future__ import annotations

import pytest

from services.errors import (
    HumanError,
    ProviderError,
    error_frame,
    humanize,
    provider_error_response,
)

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


# ---------------------------------------------------------------------------
# R15-AGENT-027: body-aware classification over captured provider bodies
# ---------------------------------------------------------------------------


def _openai_err(cls: type, status: int, body: object) -> Exception:
    """An openai SDK status error shaped exactly as the SDK raises it."""
    import httpx

    request = httpx.Request("POST", "https://api.example/v1/chat/completions")
    response = httpx.Response(status, request=request)
    return cls(f"Error code: {status} - {body}", response=response, body=body)


def _captured_errors() -> list[tuple[str, str, Exception, str]]:
    import httpx
    import ollama
    import openai
    from google.genai import errors as genai_errors

    # OpenRouter free-model 429 (research-briefs r0-429-gemma-free), with a
    # stand-in user id.
    shared_pool = {
        "error": {
            "message": "Provider returned error",
            "code": 429,
            "metadata": {
                "raw": "google/gemma-4-31b-it:free is temporarily rate-limited upstream. "
                "Please retry shortly, or add your own key to accumulate your rate limits",
                "provider_name": "Google AI Studio",
                "limit_source": "upstream_provider_shared_pool",
            },
        },
        "user_id": "user_2FAKEFIXTUREID",
    }
    return [
        (
            "openai credit 429",
            "openai",
            _openai_err(
                openai.RateLimitError,
                429,
                {
                    "error": {
                        "message": "You exceeded your current quota, please check your plan "
                        "and billing details.",
                        "type": "insufficient_quota",
                        "code": "insufficient_quota",
                    }
                },
            ),
            "insufficient_credit",
        ),
        (
            "openai credit balance exhausted 429",
            "openai",
            _FakeExc("credit balance exhausted", 429),
            "insufficient_credit",
        ),
        (
            "openrouter shared-pool 429",
            "openrouter",
            _openai_err(openai.RateLimitError, 429, shared_pool),
            "free_pool_busy",
        ),
        (
            "gemini 400 invalid key",
            "gemini",
            genai_errors.ClientError(
                400,
                {
                    "error": {
                        "code": 400,
                        "message": "API key not valid. Please pass a valid API key.",
                        "status": "INVALID_ARGUMENT",
                        "details": [{"reason": "API_KEY_INVALID"}],
                    }
                },
            ),
            "auth",
        ),
        (
            "xai 400 invalid key",
            "xai",
            _openai_err(
                openai.BadRequestError,
                400,
                {"code": "invalid-argument", "error": "Incorrect API key provided: xa***ey."},
            ),
            "auth",
        ),
        (
            "openrouter 400 invalid model id",
            "openrouter",
            _openai_err(
                openai.BadRequestError,
                400,
                {
                    "error": {
                        "message": "zzz-nonsense/not-a-model-9000:free is not a valid model ID",
                        "code": 400,
                    },
                    "user_id": "user_2FAKEFIXTUREID",
                },
            ),
            "model_not_found",
        ),
        (
            "openai 400 context length",
            "openai",
            _FakeExc(
                "This model's maximum context length is 128000 tokens. However, your "
                "messages resulted in 131072 tokens.",
                400,
            ),
            "context_overflow",
        ),
        ("groq 413", "groq", _FakeExc("Request too large for model", 413), "context_overflow"),
        (
            "ollama not running",
            "ollama",
            httpx.ConnectError("All connection attempts failed"),
            "ollama_not_running",
        ),
        (
            "ollama model not pulled",
            "ollama",
            ollama.ResponseError('model "qwen3:8b" not found, try pulling it first', 404),
            "model_not_pulled",
        ),
    ]


@pytest.mark.parametrize(
    ("provider", "exc", "code"),
    [pytest.param(p, e, c, id=name) for name, p, e, c in _captured_errors()],
)
def test_captured_provider_bodies_get_the_right_next_step(
    provider: str, exc: Exception, code: str
) -> None:
    h = humanize(provider, exc)
    assert h.code == code
    assert h.message and h.action


def test_ollama_not_pulled_names_the_pull_command() -> None:
    import ollama

    h = humanize("ollama", ollama.ResponseError('model "qwen3:8b" not found, try pulling', 404))
    assert "qwen3:8b" in h.message
    assert h.action is not None and "ollama pull qwen3:8b" in h.action


def test_user_id_is_scrubbed_from_detail() -> None:
    import openai

    exc = _openai_err(
        openai.BadRequestError,
        400,
        {"error": {"message": "x is not a valid model ID"}, "user_id": "user_2FAKEFIXTUREID"},
    )
    h = humanize("openrouter", exc)
    assert h.detail is not None
    assert "user_2FAKEFIXTUREID" not in h.detail
    assert "not a valid model ID" in h.detail


def test_anthropic_prompt_too_long_is_context_overflow() -> None:
    # Held out: the table was not written against an Anthropic body.
    import anthropic
    import httpx

    body = {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "prompt is too long: 215000 tokens > 200000 maximum",
        },
    }
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    exc = anthropic.BadRequestError(
        f"Error code: 400 - {body}", response=httpx.Response(400, request=request), body=body
    )
    assert humanize("anthropic", exc).code == "context_overflow"


def test_anthropic_low_credit_400_is_insufficient_credit() -> None:
    # Held out: Anthropic reports an empty balance as a 400, not a 402/429.
    h = humanize(
        "anthropic",
        _FakeExc(
            "Your credit balance is too low to access the Anthropic API. Please go to "
            "Plans & Billing to upgrade or purchase credits.",
            400,
        ),
    )
    assert h.code == "insufficient_credit"


def test_plain_rate_limit_429_still_says_wait() -> None:
    h = humanize("openai", _FakeExc("Rate limit reached for requests per min (RPM)", 429))
    assert h.code == "rate_limit"


# ---------------------------------------------------------------------------
# R15-AGENT-030: internal crashes are not blamed on the provider or network
# ---------------------------------------------------------------------------


def test_router_guard_frame_is_internal_not_network() -> None:
    frame = error_frame(RuntimeError("runs_store: database connection is closed"))
    assert frame["code"] == "internal"
    assert "network" not in frame["message"].lower()
    assert frame["detail"] == "RuntimeError: runs_store: database connection is closed"


def test_humanize_still_classifies_a_real_connect_error_by_class() -> None:
    import httpx

    assert humanize("openai", httpx.ConnectError("x")).code == "network"


def test_humanize_ignores_network_words_in_a_non_network_message() -> None:
    """The class case the fix was not written against: a ValueError whose text
    mentions a connection pool timeout is not a network failure."""
    assert humanize("openai", ValueError("connection pool timeout")).code != "network"


# ---------------------------------------------------------------------------
# provider_error_response — R15-DATA-061: a cause-less ProviderError is not
# authored just because it has no __cause__; only .authored() reaches the user.
# ---------------------------------------------------------------------------


def test_unauthored_cause_less_error_hides_raw_upstream_text() -> None:
    """A plain ``ProviderError(str(exc))`` with no cause — e.g. an MCP tool's
    raw error content wrapped with no ``from`` — used to read as "authored"
    just because __cause__ was None, and leaked verbatim."""
    exc = ProviderError("World Bank upstream: APIError: JSON decoding error (https://a...)")
    status, body = provider_error_response(exc)
    assert status == 502
    assert "APIError" not in body["detail"]
    assert body["detail"] == "The data provider returned an unexpected response."


def test_authored_cause_less_error_keeps_its_sentence() -> None:
    exc = ProviderError.authored("FRED needs a free API key for macro data.")
    status, body = provider_error_response(exc)
    assert status == 502
    assert body["detail"] == "FRED needs a free API key for macro data."


def test_authored_not_found_keeps_its_sentence() -> None:
    """An authored error paired with a classified kind still shows its own
    text, not the kind's generic sentence."""
    exc = ProviderError.authored("No such watchlist symbol.", kind="not_found")
    status, body = provider_error_response(exc)
    assert status == 404
    assert body["detail"] == "No such watchlist symbol."


def test_unauthored_classified_kind_also_hides_raw_text() -> None:
    """Class pin, not written against: an unauthored cause-less error carrying
    a classified kind (the openbb-mcp 422 shape — raw tool-error content, no
    ``from``) still gets the kind's generic sentence, never the raw body."""
    exc = ProviderError(
        "openbb-mcp tool 'equity.price.quote' reported error: 422 Unprocessable", kind="not_found"
    )
    status, body = provider_error_response(exc)
    assert status == 404
    assert "Unprocessable" not in body["detail"]
    assert (
        body["detail"]
        == "The data provider has no data for this symbol or series — check the symbol."
    )
