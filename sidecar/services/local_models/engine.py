"""Where the bundled llama-server is listening (process memory only).

The frontend relays the Rust engine's port via ``PUT /local-models/engine``;
provider ``local`` reads :func:`base_url`. The URL is only ever built from the
port, never taken from a request. The engine's real context size is read from
its ``/props`` when the port is set, so the runtime budgets against the
``-c`` the engine actually runs with.
"""

from __future__ import annotations

import httpx

#: The Rust core's ``DEFAULT_CTX`` (src-tauri/src/local_engine.rs): assumed when
#: ``/props`` cannot be read.
DEFAULT_N_CTX = 16384
_PROPS_TIMEOUT_S = 2.0

_port: int | None = None
_model_id: str | None = None
_n_ctx: int | None = None


def set_engine(port: int | None, model_id: str | None, n_ctx: int | None = None) -> None:
    global _port, _model_id, _n_ctx
    _port = port
    _model_id = model_id if port is not None else None
    _n_ctx = n_ctx if port is not None else None


async def fetch_n_ctx(port: int, transport: httpx.AsyncBaseTransport | None = None) -> int | None:
    """llama-server's ``default_generation_settings.n_ctx``, or ``None`` when the
    engine does not answer (yet) or answers in another shape."""
    try:
        async with httpx.AsyncClient(transport=transport, timeout=_PROPS_TIMEOUT_S) as client:
            response = await client.get(f"http://127.0.0.1:{port}/props")
            response.raise_for_status()
            n_ctx = response.json()["default_generation_settings"]["n_ctx"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
    return n_ctx if isinstance(n_ctx, int) and n_ctx > 0 else None


def base_url() -> str | None:
    return f"http://127.0.0.1:{_port}/v1" if _port is not None else None


def active_model_id() -> str | None:
    return _model_id


def n_ctx() -> int:
    """The running engine's context size in real tokens."""
    return _n_ctx or DEFAULT_N_CTX
