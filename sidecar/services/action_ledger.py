"""In-memory ack ledger for dispatched host actions (R10, E3.3).

The autonomy=auto loop used to synthesize "applied … past tense" tool results
BEFORE the frontend ran ``applyHostAction`` — whose D33 shrink guard can keep
the OLD brief — so the agent truthfully reported a publish that never landed.
The fix is a read-back: the frontend POSTs ``/agents/actions/ack`` after it
applies (or declines) each host action, keyed by the streamed ``tool_call_id``;
the runtime checks this ledger at end-of-stream and emits an honest divergence
notice when a publish was never confirmed or the panel kept the previous brief.

Process-memory only (the ack is a per-stream read-back, not durable state);
entries expire after :data:`TTL_SECONDS` so an abandoned stream never leaks.
No secrets ever ride this ledger.
"""

from __future__ import annotations

import time
from typing import Any

#: How long an ack stays readable. A stream's end-of-stream check happens
#: seconds after the apply; 10 minutes covers even a very long multi-round
#: turn with margin.
TTL_SECONDS = 600.0

#: The statuses the frontend may report for one applied host action.
KNOWN_STATUSES = ("applied", "kept_previous", "failed")

# tool_call_id -> (expires_at_monotonic, entry)
_LEDGER: dict[str, tuple[float, dict[str, Any]]] = {}


def _prune(now: float) -> None:
    expired = [cid for cid, (expires, _) in _LEDGER.items() if expires <= now]
    for cid in expired:
        _LEDGER.pop(cid, None)


def record(tool_call_id: str, status: str, brief_meta: dict[str, Any] | None = None) -> None:
    """Record the frontend's ack for one host-action ``tool_call_id``.

    ``status`` is one of :data:`KNOWN_STATUSES`; an unknown spelling is stored
    verbatim (the reader treats anything that is not ``applied`` as a
    divergence to surface — honest by default).
    """
    now = time.monotonic()
    _prune(now)
    _LEDGER[tool_call_id] = (
        now + TTL_SECONDS,
        {
            "status": status,
            "brief": dict(brief_meta) if brief_meta else None,
            "recorded_at": time.time(),
        },
    )


def get(tool_call_id: str) -> dict[str, Any] | None:
    """Return the recorded ack entry for ``tool_call_id``, or ``None``."""
    now = time.monotonic()
    _prune(now)
    found = _LEDGER.get(tool_call_id)
    return found[1] if found else None


def reset_for_tests() -> None:
    """Drop every entry (test isolation)."""
    _LEDGER.clear()


__all__ = ["KNOWN_STATUSES", "TTL_SECONDS", "get", "record", "reset_for_tests"]
