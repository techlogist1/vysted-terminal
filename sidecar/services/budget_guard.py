"""BudgetGuard — the hard spend ceiling for a Delegate run (US9 / FR-026 / SC-008).

An autonomous BACKGROUND agent task is unsafe to ship without a spend ceiling:
a runaway loop could burn the user's BYOK budget unattended. The guard holds a
set of OPTIONAL ceilings — tokens, estimated USD spend, wall-clock seconds, and
tool-call steps — accumulates cost across the run as each round completes, and
reports the FIRST breached ceiling so the run executor can abort. SC-008: a
breach aborts the run 100% of the time, with a stated reason.

The guard governs SPEND only. It has NO order/placement authority — a Delegate
run uses the same agent loop whose ``propose_order`` only ever proposes (§6.5).
There is no path here to place, submit, or auto-approve anything.

Cost model
----------
- **tokens** — the running sum of ``input_tokens + output_tokens`` from each
  round's :class:`~models.llm.LLMUsage`. Cache-read/creation tokens are folded
  into the input side at their normal rate (best-effort; providers differ).
- **spend_usd** — an ESTIMATE: ``tokens × ($/token)`` from a per-provider/model
  :data:`PRICE_TABLE` of blended $/1M-token rates. It is NOT a billed figure —
  the sidecar holds no provider invoice. Unknown models fall back to a sane
  default rate so an estimate is always available rather than silently zero.
- **wall_seconds** — ``time.monotonic()`` delta from construction.
- **steps** — incremented once per round (one provider turn that fired tools).
"""

from __future__ import annotations

import time

from models.llm import LLMUsage
from services import model_registry

# ---------------------------------------------------------------------------
# Price table — blended $/1M tokens, best-effort ESTIMATE.
#
# Keyed ``(provider, model_substring)``: the model id is matched by the longest
# substring key that is contained in the requested model, so version-suffixed
# ids ("claude-opus-4-8-20251234", "gpt-4.1-mini-2025") resolve without an exact
# enumeration. Rates blend input+output into one figure (a Delegate run's mix is
# read-heavy tool calls + short completions) — exact per-direction billing lives
# with the provider, not here. Local providers (Ollama) are zero-cost. Rates are
# a snapshot and WILL drift; treat ``spend_usd`` as guidance, not an invoice.
#
# Single-sourced from ``config/model_registry.json`` (``prices.by_provider`` /
# ``prices.default_rate_per_million``) — edit the JSON, not this file. These
# numbers meter the Delegate spend ceiling (§6.5-adjacent / SC-008); the
# matching and abort logic below stays unchanged.
# ---------------------------------------------------------------------------

#: $/1M tokens, blended. Order within a provider does not matter — the matcher
#: prefers the longest matching key. Loaded from the registry at import.
PRICE_TABLE: dict[tuple[str, str], float] = model_registry.price_table()

#: Fallback blended rate for a provider/model not in :data:`PRICE_TABLE`.
#: Picked to be neither alarmingly high nor a free pass — an estimate, by design.
DEFAULT_RATE_PER_M: float = model_registry.default_rate_per_million()


def price_per_million(provider: str, model: str) -> float:
    """Return the blended $/1M-token rate for ``(provider, model)`` (best-effort).

    Matches the longest :data:`PRICE_TABLE` key for the provider whose model
    substring is contained in ``model`` (case-insensitive). Falls back to
    :data:`DEFAULT_RATE_PER_M` when the provider/model pair is unknown — the
    estimate is never silently zero for a metered provider.
    """
    model_lc = (model or "").lower()
    provider_lc = (provider or "").lower()
    best_key: str | None = None
    best_rate = DEFAULT_RATE_PER_M
    for (prov, sub), rate in PRICE_TABLE.items():
        if prov != provider_lc:
            continue
        if sub == "" or sub in model_lc:
            if best_key is None or len(sub) > len(best_key):
                best_key = sub
                best_rate = rate
    return best_rate


def estimate_spend_usd(provider: str, model: str, tokens: int) -> float:
    """Estimate USD spend for ``tokens`` against the ``(provider, model)`` rate."""
    return (max(tokens, 0) / 1_000_000.0) * price_per_million(provider, model)


class BudgetGuard:
    """Accumulates run cost and reports the first breached ceiling.

    Construct once per run with the desired (all-optional) ceilings; call
    :meth:`record` after each round with that round's usage + model, then check
    :meth:`breach` — a non-``None`` reason means the run MUST abort (SC-008).
    """

    def __init__(
        self,
        *,
        max_tokens: int | None = None,
        max_spend_usd: float | None = None,
        max_wall_seconds: float | None = None,
        max_steps: int | None = None,
        _now: float | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_spend_usd = max_spend_usd
        self.max_wall_seconds = max_wall_seconds
        self.max_steps = max_steps

        self._tokens = 0
        self._spend_usd = 0.0
        self._steps = 0
        self._start = _now if _now is not None else time.monotonic()

    # -- accumulation -------------------------------------------------------

    def record(self, usage: LLMUsage | None, model: str, provider: str = "") -> None:
        """Fold one round's usage into the running cost, and tick the step count.

        Called once per provider round. ``usage`` may be ``None`` (a provider
        that reported no usage on its terminator) — the step still counts so the
        step ceiling stays meaningful even for usage-blind providers. The USD
        estimate uses the round's own token delta against the round's model, so a
        run that switches models mid-stream is priced per round.
        """
        self._steps += 1
        if usage is None:
            return
        round_tokens = max(usage.input_tokens, 0) + max(usage.output_tokens, 0)
        # Cache-read/creation tokens are billed (at a discount upstream) but we
        # fold them in at the blended rate — an over-estimate is the safe side
        # for a HARD ceiling.
        round_tokens += max(usage.cache_read_input_tokens or 0, 0)
        round_tokens += max(usage.cache_creation_input_tokens or 0, 0)
        self._tokens += round_tokens
        self._spend_usd += estimate_spend_usd(provider, model, round_tokens)

    # -- inspection ---------------------------------------------------------

    def wall_seconds(self, _now: float | None = None) -> float:
        """Elapsed wall-clock seconds since construction (monotonic)."""
        now = _now if _now is not None else time.monotonic()
        return max(now - self._start, 0.0)

    def breach(self, _now: float | None = None) -> str | None:
        """Return the FIRST breached ceiling's reason, or ``None`` if under.

        Checked in a stable order (tokens → spend → wall-clock → steps) so the
        reason is deterministic for a given accumulated state. A ``None`` ceiling
        is never breached. The returned string is the human-readable abort reason
        persisted as the run's ``detail`` (SC-008 demands a STATED reason).
        """
        if self.max_tokens is not None and self._tokens >= self.max_tokens:
            return f"token ceiling {self.max_tokens} reached ({self._tokens} used)"
        if self.max_spend_usd is not None and self._spend_usd >= self.max_spend_usd:
            return (
                f"spend ceiling ${self.max_spend_usd:.4f} reached "
                f"(${self._spend_usd:.4f} estimated)"
            )
        wall = self.wall_seconds(_now)
        if self.max_wall_seconds is not None and wall >= self.max_wall_seconds:
            return f"wall-clock ceiling {self.max_wall_seconds:g}s reached ({wall:.1f}s elapsed)"
        if self.max_steps is not None and self._steps >= self.max_steps:
            return f"step ceiling {self.max_steps} reached ({self._steps} taken)"
        return None

    def cost(self) -> dict[str, float | int]:
        """Return the accumulated cost as ``{tokens, spend_usd, steps}``."""
        return {
            "tokens": self._tokens,
            "spend_usd": round(self._spend_usd, 6),
            "steps": self._steps,
        }
