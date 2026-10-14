"""Where the bundled llama-server is listening (process memory only).

The frontend relays the Rust engine's port via ``PUT /local-models/engine``;
provider ``local`` reads :func:`base_url`. The URL is only ever built from the
port, never taken from a request.
"""

from __future__ import annotations

_port: int | None = None
_model_id: str | None = None


def set_engine(port: int | None, model_id: str | None) -> None:
    global _port, _model_id
    _port = port
    _model_id = model_id if port is not None else None


def base_url() -> str | None:
    return f"http://127.0.0.1:{_port}/v1" if _port is not None else None


def active_model_id() -> str | None:
    return _model_id
