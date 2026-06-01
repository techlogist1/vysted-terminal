"""Single source of truth for LLM providers, models, and pricing.

Loads ``sidecar/config/model_registry.json`` once at import and exposes typed
accessors. Everything that used to hardcode a provider list, a per-provider
default model, a price table, or the custom-agent provider allow-list now
DERIVES from this file (a one-line data edit, not a code change):

- ``services.llm.PROVIDER_INFO`` (``GET /llm/providers`` payload),
- ``services.agent_runtime._resolve_model`` per-provider defaults,
- ``services.budget_guard`` price table + default rate (SC-008 spend ceiling),
- ``models.custom_agent.KNOWN_PROVIDER_IDS`` allow-list.

The file is non-package data loaded by path, so it MUST be added to the
PyInstaller ``--onefile`` build (``--add-data`` → ``config/``) or it vanishes
in the frozen binary — see ``scripts/ensure-sidecar.mjs`` and the CLAUDE.md
gotcha. We resolve the path for both dev and a frozen freeze.

Load is eager and fails LOUD: a missing or malformed registry raises at import
so a packaging regression surfaces at startup, never as a silent empty list.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    """Resolve the registry JSON path for dev and a PyInstaller ``--onefile`` freeze.

    Under PyInstaller the data dir is added via ``--add-data "<src>:config"``,
    so it lands at ``<_MEIPASS>/config/model_registry.json``. In dev the file
    lives at ``sidecar/config/model_registry.json`` (two parents up from this
    module under ``services/``).
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base / "config" / "model_registry.json"
    return Path(__file__).resolve().parent.parent / "config" / "model_registry.json"


def _load() -> dict[str, Any]:
    path = _registry_path()
    if not path.is_file():
        raise RuntimeError(
            f"model registry not found at {path!s}; the config/ data dir is likely "
            "missing from the PyInstaller --add-data list (see scripts/ensure-sidecar.mjs)"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed-file guard
        raise RuntimeError(f"model registry at {path!s} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"model registry at {path!s} must be a JSON object")

    providers = raw.get("providers")
    if not isinstance(providers, list) or not providers:
        raise RuntimeError(f"model registry at {path!s} has no 'providers' list")
    for row in providers:
        if not isinstance(row, dict) or "id" not in row:
            raise RuntimeError(f"model registry at {path!s} has a malformed provider row: {row!r}")

    prices = raw.get("prices")
    if not isinstance(prices, dict):
        raise RuntimeError(f"model registry at {path!s} has no 'prices' object")
    return raw


_REGISTRY: dict[str, Any] = _load()

#: Provider rows in file order (each a dict with id/label/requires_key and
#: optional default_base_url/default_model/known_models).
_PROVIDER_ROWS: list[dict[str, Any]] = list(_REGISTRY["providers"])
_PROVIDER_IDS: tuple[str, ...] = tuple(str(row["id"]) for row in _PROVIDER_ROWS)
_PROVIDERS_BY_ID: dict[str, dict[str, Any]] = {str(row["id"]): row for row in _PROVIDER_ROWS}

_PRICES: dict[str, Any] = _REGISTRY["prices"]
_DEFAULT_RATE_PER_M: float = float(_PRICES.get("default_rate_per_million", 5.0))

#: Flatten ``prices.by_provider[provider][substring]`` into the same
#: ``(provider, substring) -> rate`` shape ``budget_guard`` matches against,
#: preserving the ``""`` empty-substring provider-wide fallback keys.
_PRICE_TABLE: dict[tuple[str, str], float] = {}
for _prov, _models in (_PRICES.get("by_provider") or {}).items():
    if not isinstance(_models, dict):
        raise RuntimeError(f"model registry price block for {_prov!r} is not an object")
    for _sub, _rate in _models.items():
        _PRICE_TABLE[(str(_prov), str(_sub))] = float(_rate)


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def provider_rows() -> list[dict[str, Any]]:
    """Return the provider rows in file order (shallow copies, safe to read)."""
    return [dict(row) for row in _PROVIDER_ROWS]


def provider_ids() -> tuple[str, ...]:
    """Return the provider ids in file order."""
    return _PROVIDER_IDS


def default_model_for(provider: str) -> str:
    """Return the registry default model id for ``provider`` (``""`` if unknown)."""
    row = _PROVIDERS_BY_ID.get(provider)
    if row is None:
        return ""
    return str(row.get("default_model", ""))


def known_models_for(provider: str) -> list[str]:
    """Return the selectable model ids for ``provider`` (empty list if unknown)."""
    row = _PROVIDERS_BY_ID.get(provider)
    if row is None:
        return []
    return [str(m) for m in row.get("known_models", [])]


def price_table() -> dict[tuple[str, str], float]:
    """Return the flattened ``(provider, model_substring) -> $/1M`` price table."""
    return dict(_PRICE_TABLE)


def default_rate_per_million() -> float:
    """Return the fallback blended $/1M-token rate for unknown provider/model pairs."""
    return _DEFAULT_RATE_PER_M


__all__ = [
    "default_model_for",
    "default_rate_per_million",
    "known_models_for",
    "price_table",
    "provider_ids",
    "provider_rows",
]
