"""Crypto router — ccxt-backed REST quotes/history plus a live WebSocket stream.

The REST ``/crypto/ticker`` + ``/crypto/history`` endpoints wrap their single
blocking ccxt call (``fetch_ticker`` / ``fetch_ohlcv``) in ``asyncio.to_thread``
so a slow exchange round-trip never blocks the uvicorn event loop and starves
other routes. Mirrors the quotes-fan-out pattern in ``routers/quotes.py`` and
the ``services/bar_loader.py`` thread-offload precedent.

The ``/crypto/stream`` WebSocket pushes a JSON-serialised :class:`Quote` on every
ticker update from the chosen exchange. ccxt.pro's exchange instance is always
closed on disconnect via the streaming generator's ``finally`` block.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from models.market import OHLCVSeries, Quote
from services import ccxt_provider
from services.errors import ProviderError

router = APIRouter(prefix="/crypto", tags=["crypto"])


@router.get("/exchanges")
def list_exchanges() -> dict[str, list[str]]:
    """Return the crypto exchanges this build supports."""
    return {"exchanges": list(ccxt_provider.SUPPORTED_EXCHANGES)}


@router.get("/ticker")
async def crypto_ticker(exchange: str, symbol: str) -> Quote:
    """Return the latest REST ticker for ``symbol`` on ``exchange``.

    The blocking ccxt ``fetch_ticker`` runs on a worker thread. A
    ``ProviderError`` (e.g. unsupported exchange) propagates to the app-level
    handler and surfaces as a clean 502 — unchanged behaviour.
    """
    return await asyncio.to_thread(ccxt_provider.get_ticker, exchange, symbol)


@router.get("/history")
async def crypto_history(exchange: str, symbol: str, timeframe: str = "1d") -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` on ``exchange``."""
    return await asyncio.to_thread(ccxt_provider.get_ohlcv, exchange, symbol, timeframe)


@router.websocket("/stream")
async def crypto_stream(websocket: WebSocket, exchange: str, symbol: str) -> None:
    """Stream live ticker quotes for ``symbol`` on ``exchange`` until disconnect."""
    await websocket.accept()
    stream = ccxt_provider.watch_ticker(exchange, symbol)
    try:
        async for quote in stream:
            await websocket.send_json(quote.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    except ProviderError as exc:
        await websocket.close(code=1011, reason=str(exc)[:120])
    finally:
        await stream.aclose()
