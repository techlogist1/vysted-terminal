"""Broker adapter registry — lookup by :data:`BrokerId`, lifecycle.

The registry is the single source of truth for which adapter instance
serves a given broker id. The :mod:`routers.brokers` router resolves
incoming requests through :func:`get` so that the unit + integration tests
can substitute fake adapters via :func:`register` without monkeypatching
multiple modules.

Lifecycle (FR-051 — no broker registers at boot):

  - The sidecar registers **no** broker adapter at startup. A broker is
    registered lazily via :func:`ensure_registered` when its marketplace
    plugin connects (``POST /brokers/{id}/connect``). :data:`KNOWN_ADAPTER_FACTORIES`
    maps every supported :data:`BrokerId` to a zero-arg factory that
    constructs its adapter with the real constructor signature.
  - Adapters can be replaced (re-registering the same ``BrokerId`` overwrites
    the prior entry, which also drops its kill-switch subscription via
    :meth:`BrokerAdapter._unsubscribe`).
  - :func:`bootstrap_default_adapters` is retained for explicit/test use, but
    is NO LONGER called at boot — the agent-native redesign registers brokers
    on the marketplace/connect path instead of eagerly at startup.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from models.broker import BrokerId

if TYPE_CHECKING:
    from services.broker_base import BrokerAdapter

logger = logging.getLogger(__name__)

_adapters: dict[str, BrokerAdapter] = {}


def _make_adapter_factories() -> dict[BrokerId, Callable[[], BrokerAdapter]]:
    """Build the id→factory map.

    Local imports keep the module-level import graph cycle-free (the adapter
    modules import :mod:`services.broker_base`, which imports the kill-switch
    bus that imports models that reference this registry's ``BrokerId``).

    Each ccxt exchange is a distinct :data:`BrokerId` (``ccxt-bybit`` etc.); the
    one :class:`CcxtExecutionAdapter` is parametrised by the bare ccxt exchange
    id, so each factory passes the matching exchange.
    """
    from services.brokers.alpaca import AlpacaAdapter
    from services.brokers.angelone import AngelOneAdapter
    from services.brokers.ccxt_exec import CcxtExecutionAdapter
    from services.brokers.dhan import DhanAdapter
    from services.brokers.ib import IBAdapter
    from services.brokers.kite import KiteAdapter
    from services.brokers.oanda import OandaAdapter

    return {
        "dhan": DhanAdapter,
        "angelone": AngelOneAdapter,
        "kite": KiteAdapter,
        "alpaca": AlpacaAdapter,
        "ib": IBAdapter,
        "oanda": OandaAdapter,
        "ccxt-bybit": lambda: CcxtExecutionAdapter("bybit"),
        "ccxt-binance": lambda: CcxtExecutionAdapter("binance"),
        "ccxt-kraken": lambda: CcxtExecutionAdapter("kraken"),
        "ccxt-coinbase": lambda: CcxtExecutionAdapter("coinbase"),
    }


#: BrokerId → zero-arg factory constructing the adapter with its real
#: constructor signature. Built lazily on first use of
#: :func:`ensure_registered` to keep module-import cycle-free; the
#: ``ccxt-*`` ids parametrise the single :class:`CcxtExecutionAdapter`.
KNOWN_ADAPTER_FACTORIES: dict[BrokerId, Callable[[], BrokerAdapter]] = {}


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


def ensure_registered(broker_id: BrokerId) -> BrokerAdapter:
    """Return the registered adapter for ``broker_id``, lazily creating it.

    FR-051: brokers are NOT registered at boot. The connect path calls this
    to register an adapter on first use. If an adapter is already registered
    the existing instance is returned untouched (so an in-flight session /
    kill-switch subscription is preserved). An unknown id raises ``KeyError``.
    """
    existing = _adapters.get(str(broker_id))
    if existing is not None:
        return existing

    if not KNOWN_ADAPTER_FACTORIES:
        KNOWN_ADAPTER_FACTORIES.update(_make_adapter_factories())
    try:
        factory = KNOWN_ADAPTER_FACTORIES[broker_id]
    except KeyError as exc:
        raise KeyError(f"no broker adapter factory for id={broker_id!r}") from exc

    adapter = factory()
    register(adapter)
    return adapter


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

    Retained for explicit/test use but NO LONGER called at sidecar startup
    (FR-051 — brokers register lazily via :func:`ensure_registered` on the
    marketplace/connect path). Idempotent — if an adapter already exists in
    the registry the existing instance is preserved.
    """
    # Local imports keep the module-level import graph cycle-free.
    from services.brokers.angelone import AngelOneAdapter
    from services.brokers.dhan import DhanAdapter
    from services.brokers.kite import KiteAdapter

    for cls in (DhanAdapter, AngelOneAdapter, KiteAdapter):
        if has(cls.BROKER_ID):
            continue
        register(cls())
