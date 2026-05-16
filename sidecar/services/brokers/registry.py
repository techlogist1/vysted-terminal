"""Broker adapter registry — lookup by :data:`BrokerId`, lifecycle.

The registry is the single source of truth for which adapter instance
serves a given broker id. The :mod:`routers.brokers` router resolves
incoming requests through :func:`get` so that the unit + integration tests
can substitute fake adapters via :func:`register` without monkeypatching
multiple modules.

Lifecycle:

  - At sidecar startup, :func:`bootstrap_default_adapters` instantiates the
    three India broker adapters (Dhan, Angel One, Kite) and registers them.
    Other teammates' adapters (Alpaca, IB, OANDA, ccxt-*) are wired through
    their own ``bootstrap_*`` entrypoints — Teammate I owns India only.
  - Adapters can be replaced (re-registering the same ``BrokerId`` overwrites
    the prior entry, which also drops its kill-switch subscription via
    :meth:`BrokerAdapter._unsubscribe`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from models.broker import BrokerId

if TYPE_CHECKING:
    from services.broker_base import BrokerAdapter

logger = logging.getLogger(__name__)

_adapters: dict[str, BrokerAdapter] = {}


def register(adapter: BrokerAdapter) -> None:
    """Register or replace a broker adapter.

    Replacing an existing adapter unsubscribes the old one from the
    kill-switch bus first — the unsubscribe is a closure captured in
    ``BrokerAdapter.__init__``, so calling it cleans up the bus entry.
    """
    broker_id = adapter.BROKER_ID
    existing = _adapters.get(broker_id)
    if existing is not None:
        try:
            existing._unsubscribe()  # noqa: SLF001 - intentional cleanup of internal handle
        except Exception:  # noqa: BLE001
            logger.warning("brokers.registry: unsubscribe of %s raised", broker_id)
    _adapters[broker_id] = adapter
    logger.info("brokers.registry: registered %s (total=%d)", broker_id, len(_adapters))


def unregister(broker_id: BrokerId | str) -> None:
    """Remove an adapter and clean up its kill-switch subscription."""
    adapter = _adapters.pop(str(broker_id), None)
    if adapter is None:
        return
    try:
        adapter._unsubscribe()  # noqa: SLF001
    except Exception:  # noqa: BLE001
        logger.warning("brokers.registry: unsubscribe of %s raised", broker_id)


def get(broker_id: BrokerId | str) -> BrokerAdapter:
    """Return the registered adapter for ``broker_id`` or raise ``KeyError``."""
    try:
        return _adapters[str(broker_id)]
    except KeyError as exc:
        raise KeyError(f"no broker adapter registered for id={broker_id!r}") from exc


def has(broker_id: BrokerId | str) -> bool:
    """Return whether an adapter is currently registered for ``broker_id``."""
    return str(broker_id) in _adapters


def all_adapters() -> dict[str, BrokerAdapter]:
    """Return a shallow copy of the registry (for the broker-list route)."""
    return dict(_adapters)


def reset_for_tests() -> None:
    """Drop every registered adapter — used by the test fixtures.

    Each adapter's kill-switch subscription is cleaned up in the process,
    matching :func:`unregister`. The module-singleton design means tests
    explicitly reset between cases.
    """
    for adapter in list(_adapters.values()):
        try:
            adapter._unsubscribe()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            pass
    _adapters.clear()


def bootstrap_default_adapters() -> None:
    """Instantiate + register the three India broker adapters.

    Called from :func:`main.main` at sidecar startup. Idempotent — if an
    adapter already exists in the registry (e.g. because tests bootstrapped
    early) the existing instance is preserved.
    """
    # Local imports keep the module-level import graph cycle-free.
    from services.brokers.angelone import AngelOneAdapter
    from services.brokers.dhan import DhanAdapter
    from services.brokers.kite import KiteAdapter

    for cls in (DhanAdapter, AngelOneAdapter, KiteAdapter):
        if has(cls.BROKER_ID):
            continue
        register(cls())
