"""Bundled India fundamentals seed pack — loader (R11, D52).

The pack (``services/screener_universes/india_fundamentals_seed.json.gz``) is
a build-time snapshot of the full india-all fundamentals vocabulary, generated
by ``services/screener_universes/regenerate_fundamentals_seed.py`` from a warm
fundamentals store. Shape::

    {
      "_generated": "<ISO date>",
      "_source": "<provenance line>",
      "rows": [
        {"symbol": "RELIANCE.NS", "name": …, "currency": "INR",
         "sector": …, "industry": …, "sector_source": …,
         "seed_as_of": <epoch seconds>,  # per-row: the source row's stamp
         "market_cap": …, "pe_ratio": …, "roe": …, …},
        …
      ]
    }

The loader is best-effort: a missing/corrupt pack degrades to an empty list
(the app runs exactly as pre-D52 — cold tiers, honest partials). Values from
the pack NEVER masquerade as live: :func:`fundamentals_store.seed_fundamentals`
stamps ``seed_updated_at`` only, and the screener labels the serving basis.
"""

from __future__ import annotations

import gzip
import json
import logging
from functools import lru_cache
from importlib import resources
from typing import Any

logger = logging.getLogger(__name__)

_PACK_FILENAME = "india_fundamentals_seed.json.gz"


@lru_cache(maxsize=1)
def _load_pack() -> dict[str, Any]:
    try:
        blob = resources.files("services.screener_universes").joinpath(_PACK_FILENAME).read_bytes()
        return json.loads(gzip.decompress(blob))
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError) as exc:
        logger.info("fundamentals seed: no bundled pack (%s) — cold tiers only", exc)
        return {}
    except (OSError, ValueError) as exc:
        logger.warning("fundamentals seed: bundled pack unreadable: %s", exc)
        return {}


def load_seed_rows() -> list[dict[str, Any]]:
    """The pack's rows (empty when no pack ships)."""
    rows = _load_pack().get("rows")
    return list(rows) if isinstance(rows, list) else []


def pack_info() -> dict[str, Any]:
    """The pack's provenance header ({} when no pack ships)."""
    pack = _load_pack()
    return {k: v for k, v in pack.items() if k.startswith("_")}


def reset_for_tests() -> None:
    _load_pack.cache_clear()


__all__ = ["load_seed_rows", "pack_info", "reset_for_tests"]
