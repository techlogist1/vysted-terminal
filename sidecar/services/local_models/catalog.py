"""The curated on-computer model catalog (``catalog.json``, package data)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from models.local_models import CatalogModel, CatalogResponse

# Path(__file__).parent resolves inside the --onefile bundle too:
# scripts/sidecar-specs.mjs --add-data's this package dir.
_CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"

_TIER_LABEL = {
    "under-8gb": "less than 8 GB",
    "8gb": "8 GB",
    "16gb": "16 GB",
    "32gb": "32 GB or more",
}


@cache
def raw_catalog() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def entries() -> list[dict[str, Any]]:
    return list(raw_catalog()["models"])


def entry(model_id: str) -> dict[str, Any] | None:
    return next((m for m in entries() if m["id"] == model_id), None)


def fits(min_ram: int, total_ram: int) -> str:
    if min_ram <= total_ram * 0.75:
        return "good"
    if min_ram <= total_ram:
        return "tight"
    return "too-big"


def catalog_for(total_ram: int, tier: str) -> CatalogResponse:
    models = [
        CatalogModel(
            **{k: v for k, v in m.items() if k in CatalogModel.model_fields and k != "fits"},
            fits=fits(m["minRamBytes"], total_ram),
        )
        for m in entries()
    ]
    recommended = raw_catalog()["recommendedByTier"].get(tier)
    pick = next((m for m in models if m.id == recommended), None)
    if pick is None or pick.fits == "too-big":
        good = [m for m in models if m.fits == "good"]
        pick = max(good, key=lambda m: m.sizeBytes) if good else None
    if pick is None:
        reason = (
            f"This computer has {_TIER_LABEL[tier]} of memory, which is not enough to run "
            "any of these models well. You can still use an online provider."
        )
    else:
        reason = (
            f"This computer has {_TIER_LABEL[tier]} of memory, so {pick.name} is the best "
            "balance of quality and speed."
        )
    return CatalogResponse(
        models=models,
        recommendedId=pick.id if pick else None,
        tier=tier,
        reason=reason,
    )
