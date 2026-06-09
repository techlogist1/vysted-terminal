"""Per-engine circuit breakers for the keyless T1 search tier (R7 Component 1).

Each scrape engine (DuckDuckGo / Brave / Mojeek) gets ONE process-global
:class:`CircuitBreaker` so a blocking/rate-limiting engine is benched for a
cooldown instead of being hammered — and, critically, so the provider-chain
rotation in :mod:`services.search.keyless` can SKIP a benched engine without
spending a network round-trip on it.

State machine (the classic three states):

  * ``closed`` — healthy; requests flow. ``fail_threshold`` consecutive
    failures trip it to ``open``.
  * ``open`` — benched; :meth:`allow` is False until ``cooldown_secs`` has
    elapsed. The remaining bench time is exposed via
    :meth:`cooldown_remaining` so the UI can say "DuckDuckGo cooling down
    (24s)" — an honest per-engine status, never a fake global outage.
  * ``half_open`` — the cooldown elapsed; exactly ONE probe request is let
    through. Probe success → ``closed`` (counters reset); probe failure →
    ``open`` again for a fresh cooldown.

The breaker is synchronous on purpose: every transition happens inline on the
single event loop thread, so no lock is needed. ``clock`` is injectable purely
for deterministic tests (production uses :func:`time.monotonic`).

Pattern adapted from odysseus (MIT) github.com/pewdiepie-archdaemon/odysseus.
"""

from __future__ import annotations

import time
from collections.abc import Callable

#: Breaker states (string-valued so ``tier_status()`` serializes them as-is).
STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"

#: Consecutive failures that trip a CLOSED breaker to OPEN.
DEFAULT_FAIL_THRESHOLD = 2

#: Seconds an OPEN breaker benches its engine before allowing a probe.
DEFAULT_COOLDOWN_SECS = 45.0


class CircuitBreaker:
    """A three-state circuit breaker with a single-probe half-open phase."""

    def __init__(
        self,
        *,
        fail_threshold: int = DEFAULT_FAIL_THRESHOLD,
        cooldown_secs: float = DEFAULT_COOLDOWN_SECS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.fail_threshold = max(1, int(fail_threshold))
        self.cooldown_secs = float(cooldown_secs)
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probe_inflight = False

    @property
    def state(self) -> str:
        """The current state, lazily promoting OPEN → HALF_OPEN on cooldown expiry."""
        if self._opened_at is None:
            return STATE_CLOSED
        if self._clock() - self._opened_at >= self.cooldown_secs:
            return STATE_HALF_OPEN
        return STATE_OPEN

    def cooldown_remaining(self) -> float:
        """Seconds until an OPEN breaker reaches HALF_OPEN (``0.0`` otherwise)."""
        if self._opened_at is None:
            return 0.0
        remaining = self.cooldown_secs - (self._clock() - self._opened_at)
        return max(remaining, 0.0)

    def allow(self) -> bool:
        """May a request go through right now?

        CLOSED → always. OPEN → never (the engine is benched). HALF_OPEN →
        exactly one probe: the first ``allow()`` after the cooldown returns
        True and marks the probe in-flight; further calls return False until
        :meth:`record_success` / :meth:`record_failure` resolves the probe.
        """
        state = self.state
        if state == STATE_CLOSED:
            return True
        if state == STATE_OPEN:
            return False
        # HALF_OPEN — one probe only.
        if self._probe_inflight:
            return False
        self._probe_inflight = True
        return True

    def record_success(self) -> None:
        """A request succeeded — close the breaker and reset all counters."""
        self._failures = 0
        self._opened_at = None
        self._probe_inflight = False

    def record_failure(self) -> None:
        """A request failed — count it; trip to OPEN at the threshold.

        A HALF_OPEN probe failure re-opens immediately for a fresh cooldown
        (no need to re-accumulate ``fail_threshold`` misses against a host
        that just proved it is still blocking).
        """
        if self._probe_inflight or self._opened_at is not None:
            # Failed probe (or a stale failure while benched) → fresh cooldown.
            self._opened_at = self._clock()
            self._probe_inflight = False
            self._failures = self.fail_threshold
            return
        self._failures += 1
        if self._failures >= self.fail_threshold:
            self._opened_at = self._clock()


#: Process-global breaker per engine id, shared by every backend instance so a
#: tripped engine stays benched across requests (the whole point).
_BREAKERS: dict[str, CircuitBreaker] = {}


def breaker_for(engine_id: str) -> CircuitBreaker:
    """Return the process-global breaker for ``engine_id``, creating it lazily."""
    breaker = _BREAKERS.get(engine_id)
    if breaker is None:
        breaker = CircuitBreaker()
        _BREAKERS[engine_id] = breaker
    return breaker


def breaker_status(engine_id: str) -> dict[str, object]:
    """One engine's honest status row for the ``tier_status()`` surface."""
    breaker = breaker_for(engine_id)
    return {
        "id": engine_id,
        "state": breaker.state,
        "cooldown_remaining_s": round(breaker.cooldown_remaining(), 1),
    }


def reset_breakers() -> None:
    """Drop every process-global breaker (test isolation only)."""
    _BREAKERS.clear()


__all__ = [
    "DEFAULT_COOLDOWN_SECS",
    "DEFAULT_FAIL_THRESHOLD",
    "STATE_CLOSED",
    "STATE_HALF_OPEN",
    "STATE_OPEN",
    "CircuitBreaker",
    "breaker_for",
    "breaker_status",
    "reset_breakers",
]
