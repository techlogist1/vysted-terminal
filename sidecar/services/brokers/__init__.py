"""India + global broker adapter package.

Each module in this package contributes one :class:`~services.broker_base.BrokerAdapter`
subclass for a specific broker. The registry in :mod:`services.brokers.registry`
exposes the adapters by :data:`models.broker.BrokerId`; the FastAPI router in
:mod:`routers.brokers` lets the frontend drive connect / mode / read-only /
account / propose / confirm / cancel through HTTP.

Teammate I owns the three India brokers (Dhan, Angel One, Kite Connect).
Teammates G + X own the rest. The :class:`BrokerAdapter` ABC lives in the
foundation (``services/broker_base.py``) and is NOT touched here.
"""

from __future__ import annotations

from services.brokers.dhan import DhanAdapter

__all__ = ["DhanAdapter"]
