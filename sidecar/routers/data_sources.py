"""Data sources router — ``GET /data-sources`` (C19).

Exposes ``provider_registry.declarations()`` — the SAME declaration table the
resolver dispatches against and ``/health`` derives from — so the frontend
marketplace can derive each provider's served model-keys + preference rank
from one source of truth instead of hand-maintained catalog metadata that
drifts from it (R15-CODE-PLATFORM-072 / R15-DATA-077).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from services import provider_registry

router = APIRouter(tags=["data-sources"])


class ProviderDeclarationOut(BaseModel):
    """One provider's served model-keys + scope, as reported to the frontend."""

    id: str
    keys: list[str]
    rank: int
    available: bool
    asset_classes: list[str]
    region: list[str]


class DataSourcesResponse(BaseModel):
    providers: list[ProviderDeclarationOut]


@router.get("/data-sources", response_model=DataSourcesResponse)
def get_data_sources() -> DataSourcesResponse:
    """Return every declared provider's served model-keys, rank, and scope."""
    return DataSourcesResponse(
        providers=[ProviderDeclarationOut(**d) for d in provider_registry.declarations()]
    )
