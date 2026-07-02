"""Shared upstream-health tracker — the Yahoo-family circuit breaker (R11, D53).

One process-wide health record per upstream FAMILY (not per endpoint): the v7
batch endpoint, the per-symbol yfinance quote/``.info`` scrape, and
``yfinance.Search`` all ride the same Yahoo IP reputation, so a hard throttle
on one is a hard throttle on all of them. Tracking them as one family lets a
429 storm observed by the sweep short-circuit the enrichment phase and the
deep crawler IMMEDIATELY instead of each path independently rediscovering the
block and burning its own budget.

Semantics
~~~~~~~~~

- :func:`record_rate_limited` — one throttle observation. ``weight`` lets a
  batch caller report "most of a sweep came back 429" as more than one event.
  Crossing ``_OPEN_THRESHOLD`` consecutive observations OPENS the circuit for
  a cooldown that grows geometrically with each consecutive re-open (base 60 s
  → cap 900 s, ±20 % jitter) — mirroring the warm-loop backoff discipline in
  ``services.screener``.
- :func:`record_success` — one healthy round-trip; fully resets the family
  (closes the circuit, clears the streak and the re-open count).
- :func:`is_open` — True while the family is inside an open cooldown window.
  Callers about to spend budget on the family should skip the fetch and serve
  their stale/seed basis instead (D52), reporting the skip as
  ``rate_limited``.
- :func:`status` — the observable state (for logs, /health surfaces, tests).

The tracker is advisory, never authoritative: a caller MAY probe through an
open circuit (that is how the half-open recovery happens — the first call
after the cooldown lapses flows normally and its outcome re-opens or resets).
Thread-safe (the sweep runs on the event loop; tests and threadpool routes
may touch it concurrently).
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

#: The one family every Yahoo-backed path shares (v7 batch, yfinance quote /
#: ``.info`` / Search). Exchange-direct lanes (nse_direct, bse) keep their own
#: per-path breakers inside their modules — different upstreams, different
#: block semantics.
YAHOO = "yahoo"

#: Consecutive throttle observations that OPEN the circuit.
_OPEN_THRESHOLD = 3
#: First-open cooldown.
_COOLDOWN_BASE_SECONDS = 60.0
#: Geometric growth per consecutive re-open, capped.
_COOLDOWN_FACTOR = 2.0
_COOLDOWN_CAP_SECONDS = 900.0
#: ± jitter fraction on every cooldown (de-synchronises loops).
_COOLDOWN_JITTER_FRACTION = 0.2


@dataclass
class _FamilyState:
    consecutive_throttles: float = 0.0
    open_until: float = 0.0  # monotonic deadline; 0 = closed
    consecutive_opens: int = 0
    last_throttle_at: float | None = None
    last_success_at: float | None = None
    opens_total: int = 0
    throttles_total: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


_families: dict[str, _FamilyState] = {}
_registry_lock = threading.Lock()


def _state(family: str) -> _FamilyState:
    with _registry_lock:
        state = _families.get(family)
        if state is None:
            state = _FamilyState()
            _families[family] = state
        return state


def _cooldown_seconds(consecutive_opens: int) -> float:
    """Jittered cooldown for the ``n``-th consecutive open (1-indexed)."""
    target = min(
        _COOLDOWN_CAP_SECONDS,
        _COOLDOWN_BASE_SECONDS * (_COOLDOWN_FACTOR ** max(0, consecutive_opens - 1)),
    )
    jitter = target * _COOLDOWN_JITTER_FRACTION
    return max(1.0, target + random.uniform(-jitter, jitter))


def record_rate_limited(family: str = YAHOO, *, weight: float = 1.0) -> None:
    """Record ``weight`` throttle observations for ``family``.

    Crossing the threshold opens (or re-opens) the circuit; while already
    open, further observations extend nothing (the cooldown stands — the
    caller should not have been fetching anyway)."""
    state = _state(family)
    now = time.monotonic()
    with state.lock:
        state.last_throttle_at = now
        state.throttles_total += weight
        if now < state.open_until:
            return
        state.consecutive_throttles += weight
        if state.consecutive_throttles >= _OPEN_THRESHOLD:
            state.consecutive_opens += 1
            state.opens_total += 1
            cooldown = _cooldown_seconds(state.consecutive_opens)
            state.open_until = now + cooldown
            state.consecutive_throttles = 0.0
            logger.warning(
                "provider health: %s circuit OPEN for %.0fs (consecutive opens=%d) — "
                "callers serve stale/seed basis until it half-opens",
                family,
                cooldown,
                state.consecutive_opens,
            )


def record_success(family: str = YAHOO) -> None:
    """Record a healthy round-trip — closes the circuit and resets streaks."""
    state = _state(family)
    now = time.monotonic()
    with state.lock:
        was_open = now < state.open_until
        state.consecutive_throttles = 0.0
        state.consecutive_opens = 0
        state.open_until = 0.0
        state.last_success_at = now
        if was_open:
            logger.info("provider health: %s circuit CLOSED (healthy round-trip)", family)


def is_open(family: str = YAHOO) -> bool:
    """True while ``family`` is inside an open cooldown window."""
    state = _state(family)
    with state.lock:
        return time.monotonic() < state.open_until


def cooldown_remaining(family: str = YAHOO) -> float:
    """Seconds until the circuit half-opens (0 when closed)."""
    state = _state(family)
    with state.lock:
        return max(0.0, state.open_until - time.monotonic())


def status(family: str = YAHOO) -> dict[str, float | int | bool]:
    """Observable health snapshot for logs / surfaces / tests."""
    state = _state(family)
    now = time.monotonic()
    with state.lock:
        return {
            "open": now < state.open_until,
            "cooldown_remaining": max(0.0, state.open_until - now),
            "consecutive_throttles": state.consecutive_throttles,
            "consecutive_opens": state.consecutive_opens,
            "opens_total": state.opens_total,
            "throttles_total": state.throttles_total,
        }


def reset_for_tests() -> None:
    """Drop every family's state (test isolation)."""
    with _registry_lock:
        _families.clear()


__all__ = [
    "YAHOO",
    "cooldown_remaining",
    "is_open",
    "record_rate_limited",
    "record_success",
    "reset_for_tests",
    "status",
]
