"""OpenBB ODP provider — import-guarded, deferred to Phase 2.

Phase 1 ships yfinance + ccxt as the working data providers. The OpenBB
Platform (`openbb`) is a large dependency tree that cannot be vetted against the
PyInstaller ``--onefile`` macOS build locally, so it is **not** in
``requirements.txt`` this phase. The blueprint already schedules the "OpenBB ODP
wrap plugin" for Phase 2 as a data-only plugin — building it there, on the
plugin contract, is cleaner than baking it into the core sidecar now and
re-extracting it later.

This module is the seam: it imports OpenBB if it happens to be installed and
exposes :func:`is_available` so :mod:`services.provider_registry` can prefer it
when present. With OpenBB absent (the Phase 1 norm) every accessor raises
:class:`ProviderError`, and the registry falls back to yfinance.
"""

from __future__ import annotations

from services.errors import ProviderError

try:  # pragma: no cover - exercised only when OpenBB is installed
    from openbb import obb as _obb

    OPENBB_AVAILABLE = True
except Exception:  # noqa: BLE001 - any import failure means OpenBB is unavailable
    _obb = None
    OPENBB_AVAILABLE = False

PROVIDER = "openbb"


def is_available() -> bool:
    """Return whether the OpenBB Platform is importable in this build."""
    return OPENBB_AVAILABLE


def _require() -> None:
    if not OPENBB_AVAILABLE:
        raise ProviderError(
            "OpenBB ODP is not bundled in Phase 1 — deferred to the Phase 2 "
            "OpenBB ODP wrap plugin. See docs/SIDECAR_API.md."
        )
