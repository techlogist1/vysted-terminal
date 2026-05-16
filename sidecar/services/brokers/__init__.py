"""India + global broker adapter package — v0.5.0 Phase 5.

Each module in this package contributes one
:class:`services.broker_base.BrokerAdapter` subclass for a specific broker.
The registry in :mod:`services.brokers.registry` exposes the adapters by
:data:`models.broker.BrokerId`; the FastAPI router in :mod:`routers.brokers`
lets the frontend drive connect / mode / read-only / account / propose /
confirm / cancel through HTTP.

Teammates / scope at v0.5.0 release:

- **Teammate I** — India brokers (Dhan, Angel One, Kite Connect with the
  SEBI/NSE static-IP UX path) + the canonical registry + the brokers
  router.
- **Teammate G** — Global brokers (Alpaca via alpaca-py, Interactive
  Brokers via ib_async, OANDA via oandapyV20).
- **Teammate X** — Crypto execution (ccxt unified, one adapter
  parametrised by exchange id — ccxt-bybit / -binance / -kraken /
  -coinbase). Imported lazily by ``ccxt_exec`` after X's branch merges.

The :class:`BrokerAdapter` ABC lives in the foundation
(``services/broker_base.py``) and is NOT touched in this package.
"""

from __future__ import annotations

from services.brokers.alpaca import AlpacaAdapter
from services.brokers.angelone import AngelOneAdapter
from services.brokers.ccxt_exec import CcxtExecutionAdapter
from services.brokers.dhan import DhanAdapter
from services.brokers.ib import IBAdapter
from services.brokers.kite import KiteAdapter
from services.brokers.oanda import OandaAdapter

__all__ = [
    "AlpacaAdapter",
    "AngelOneAdapter",
    "CcxtExecutionAdapter",
    "DhanAdapter",
    "IBAdapter",
    "KiteAdapter",
    "OandaAdapter",
]
