"""BudgetGuard tests — price table + each ceiling breaches + cost (SC-008).

The guard is the hard spend ceiling for a Delegate run. These tests prove the
price-table resolution, that EACH ceiling triggers in isolation, that an under-
budget guard never breaches, and that the running cost is reported faithfully.
"""

from __future__ import annotations

from models.llm import LLMUsage
from services.budget_guard import (
    DEFAULT_RATE_PER_M,
    BudgetGuard,
    estimate_spend_usd,
    price_per_million,
)


def _usage(inp: int, out: int) -> LLMUsage:
    return LLMUsage(input_tokens=inp, output_tokens=out)


# ---------------------------------------------------------------------------
# Price table
# ---------------------------------------------------------------------------


def test_price_table_resolves_known_models() -> None:
    """Known provider/model pairs resolve to their blended rate, longest match."""
    # Longest-substring match wins: "claude-opus" over the "claude" catch-all.
    assert price_per_million("anthropic", "claude-opus-4-8-20251234") == 30.0
    assert price_per_million("anthropic", "claude-sonnet-4-6") == 9.0
    assert price_per_million("anthropic", "claude-haiku-4-5") == 2.0
    assert price_per_million("openai", "gpt-4.1-mini-2025") == 1.0
    assert price_per_million("openai", "gpt-4.1") == 6.0
    assert price_per_million("gemini", "gemini-2.5-pro") == 5.0


def test_price_table_provider_catch_all() -> None:
    """A provider with a wildcard ('' substring) prices any of its models."""
    # Groq has a '' catch-all; an unrecognised groq model still resolves to it.
    assert price_per_million("groq", "some-future-llama-variant") == 0.6
    # Ollama is local → zero metered cost.
    assert price_per_million("ollama", "qwen2.5:7b") == 0.0


def test_price_table_unknown_falls_back_to_default() -> None:
    """An unknown provider/model uses the documented default rate (never silent 0)."""
    assert price_per_million("mystery", "model-x") == DEFAULT_RATE_PER_M
    # Known provider, unknown model with NO matching substring and no catch-all
    # → falls back to the default (anthropic has no '' wildcard).
    assert price_per_million("anthropic", "totally-unknown") == DEFAULT_RATE_PER_M
    # xAI has only a 'grok' key, no catch-all → a model without that substring
    # defaults.
    assert price_per_million("xai", "mystery-model") == DEFAULT_RATE_PER_M


def test_estimate_spend_is_tokens_times_rate() -> None:
    """1M tokens at $30/1M == $30; linear below that."""
    assert estimate_spend_usd("anthropic", "claude-opus", 1_000_000) == 30.0
    assert estimate_spend_usd("anthropic", "claude-opus", 500_000) == 15.0
    assert estimate_spend_usd("ollama", "qwen", 1_000_000) == 0.0


# ---------------------------------------------------------------------------
# Cost accumulation
# ---------------------------------------------------------------------------


def test_cost_accumulates_tokens_spend_and_steps() -> None:
    guard = BudgetGuard()
    guard.record(_usage(1000, 500), "claude-opus", "anthropic")  # 1500 tok
    guard.record(_usage(2000, 500), "claude-opus", "anthropic")  # 2500 tok
    cost = guard.cost()
    assert cost["tokens"] == 4000
    assert cost["steps"] == 2
    # 4000 tokens at $30/1M = $0.12
    assert abs(cost["spend_usd"] - 0.12) < 1e-9


def test_record_counts_step_even_without_usage() -> None:
    """A usage-blind provider's round still ticks the step count."""
    guard = BudgetGuard(max_steps=2)
    guard.record(None, "claude-opus", "anthropic")
    assert guard.breach() is None
    guard.record(None, "claude-opus", "anthropic")
    assert guard.breach() is not None
    assert guard.cost()["tokens"] == 0
    assert guard.cost()["steps"] == 2


def test_cache_tokens_fold_into_total() -> None:
    """Cache-read/creation tokens are counted toward the hard ceiling."""
    guard = BudgetGuard()
    guard.record(
        LLMUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=200,
            cache_creation_input_tokens=300,
        ),
        "claude-opus",
        "anthropic",
    )
    assert guard.cost()["tokens"] == 650


# ---------------------------------------------------------------------------
# Breach — each ceiling triggers in isolation
# ---------------------------------------------------------------------------


def test_no_ceilings_never_breaches() -> None:
    guard = BudgetGuard()
    guard.record(_usage(10_000_000, 10_000_000), "claude-opus", "anthropic")
    assert guard.breach() is None


def test_token_ceiling_breaches() -> None:
    guard = BudgetGuard(max_tokens=1000)
    guard.record(_usage(400, 200), "claude-opus", "anthropic")  # 600 < 1000
    assert guard.breach() is None
    guard.record(_usage(400, 200), "claude-opus", "anthropic")  # 1200 >= 1000
    reason = guard.breach()
    assert reason is not None
    assert "token ceiling 1000" in reason


def test_spend_ceiling_breaches() -> None:
    # $30/1M → 1M tokens = $30. Cap at $1 → breaches well before 1M tokens.
    guard = BudgetGuard(max_spend_usd=1.0)
    guard.record(_usage(20_000, 0), "claude-opus", "anthropic")  # $0.60 < $1
    assert guard.breach() is None
    guard.record(_usage(20_000, 0), "claude-opus", "anthropic")  # $1.20 >= $1
    reason = guard.breach()
    assert reason is not None
    assert "spend ceiling" in reason


def test_wall_clock_ceiling_breaches() -> None:
    # Construct with a fixed start and probe breach() at a synthetic 'now'.
    guard = BudgetGuard(max_wall_seconds=10.0, _now=1000.0)
    assert guard.breach(_now=1005.0) is None  # 5s elapsed
    reason = guard.breach(_now=1011.0)  # 11s elapsed
    assert reason is not None
    assert "wall-clock ceiling 10s" in reason


def test_step_ceiling_breaches() -> None:
    guard = BudgetGuard(max_steps=2)
    guard.record(_usage(1, 1), "claude-opus", "anthropic")
    assert guard.breach() is None
    guard.record(_usage(1, 1), "claude-opus", "anthropic")
    reason = guard.breach()
    assert reason is not None
    assert "step ceiling 2" in reason


def test_breach_order_is_deterministic_tokens_first() -> None:
    """When multiple ceilings are breached, tokens is reported first."""
    guard = BudgetGuard(max_tokens=100, max_spend_usd=0.0001, max_steps=1)
    guard.record(_usage(1000, 0), "claude-opus", "anthropic")
    reason = guard.breach()
    assert reason is not None
    assert reason.startswith("token ceiling")
