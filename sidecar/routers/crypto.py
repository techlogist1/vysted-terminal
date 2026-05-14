"""Crypto router — ccxt-backed REST quotes/history plus a live WebSocket stream.

The ``/crypto/stream`` WebSocket pushes a JSON-serialised :class:`Quote` on every
ticker update from the chosen exchange. ccxt.pro's exchange instance is always
closed on disconnect via the streaming generator's ``finally`` block.
"""

from __future__ import annotations

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
def crypto_ticker(exchange: str, symbol: str) -> Quote:
    """Return the latest REST ticker for ``symbol`` on ``exchange``."""
    return ccxt_provider.get_ticker(exchange, symbol)


@router.get("/history")
def crypto_history(exchange: str, symbol: str, timeframe: str = "1d") -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` on ``exchange``."""
    return ccxt_provider.get_ohlcv(exchange, symbol, timeframe)


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
