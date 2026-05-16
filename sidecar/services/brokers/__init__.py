"""Broker adapter package — v0.5.0 Phase 5.

Adapters live one-per-file under ``services/brokers/``. Each inherits
:class:`services.broker_base.BrokerAdapter` and is registered with the
broker registry (``registry.py``, owned by Teammate I) at sidecar startup.

This ``__init__`` module re-exports the adapter classes so callers can
``from services.brokers import AlpacaAdapter`` regardless of file
layout. Coordination note: Teammate I owns the canonical version of
this file plus the India broker re-exports + the registry; this file
will be hand-merged at integration time.
"""

from __future__ import annotations

from services.brokers.alpaca import AlpacaAdapter
from services.brokers.ib import IBAdapter
from services.brokers.oanda import OandaAdapter

__all__ = ["AlpacaAdapter", "IBAdapter", "OandaAdapter"]
