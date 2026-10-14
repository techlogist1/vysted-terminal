"""Wire models for ``/local-models`` (R16 contract, camelCase on the wire).

Field names are camelCase on purpose: the attribute IS the wire key, so there
is no alias layer to drift. Mirrored by hand in ``types/data.ts``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Tier = Literal["under-8gb", "8gb", "16gb", "32gb"]
Fit = Literal["good", "tight", "too-big"]
DownloadPhase = Literal[
    "queued", "downloading", "verifying", "done", "paused", "failed", "cancelled"
]


class GpuInfo(BaseModel):
    name: str
    vramBytes: int | None = None
    unifiedMemory: bool = False


class HardwareInfo(BaseModel):
    os: str
    arch: str
    totalRamBytes: int
    availableRamBytes: int
    gpu: GpuInfo | None = None
    freeDiskBytes: int
    modelsDir: str


class Licence(BaseModel):
    id: str
    name: str
    url: str


class CatalogModel(BaseModel):
    id: str
    name: str
    family: str
    params: str
    quant: str
    sizeBytes: int
    diskNeededBytes: int
    minRamBytes: int
    licence: Licence
    purpose: str
    url: str
    sha256: str
    fits: Fit


class CatalogResponse(BaseModel):
    models: list[CatalogModel]
    recommendedId: str | None = None
    tier: Tier
    reason: str


class InstalledModel(BaseModel):
    id: str
    name: str
    path: str
    sizeBytes: int
    verified: bool
    active: bool


class OllamaStatus(BaseModel):
    running: bool
    models: list[str] = Field(default_factory=list)


class InstalledResponse(BaseModel):
    models: list[InstalledModel]
    ollama: OllamaStatus


class DownloadState(BaseModel):
    id: str
    state: DownloadPhase
    receivedBytes: int = 0
    totalBytes: int = 0
    bytesPerSec: float | None = None
    error: str | None = None
    retryable: bool = False


class DownloadsResponse(BaseModel):
    downloads: list[DownloadState]


class EngineConfigRequest(BaseModel):
    port: int | None = Field(default=None, ge=1, le=65535)
    modelId: str | None = None


class EngineConfigResponse(BaseModel):
    baseUrl: str | None = None
    modelId: str | None = None
