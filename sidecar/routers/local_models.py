"""``/local-models`` — the on-computer model manager (R16 contract).

Hardware + catalog fit, verified resumable downloads, installed models
(including Ollama's), and the running engine's port for provider ``local``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from models.local_models import (
    CatalogResponse,
    DownloadsResponse,
    DownloadState,
    EngineConfigRequest,
    EngineConfigResponse,
    HardwareInfo,
    InstalledResponse,
)
from services import hardware_fit
from services.local_models import catalog, engine, hardware, store

router = APIRouter(prefix="/local-models", tags=["local-models"])


def _not_found(model_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Unknown model: {model_id}")


@router.get("/hardware")
def get_hardware() -> HardwareInfo:  # sync: vm_stat / nvidia-smi run in the threadpool
    return hardware.hardware(store.get_store().dir)


@router.get("/catalog")
async def get_catalog() -> CatalogResponse:
    total = hardware_fit.detect_device().ram_bytes
    return catalog.catalog_for(total, hardware.tier_for(total))


@router.get("/installed")
async def get_installed() -> InstalledResponse:
    ollama, ollama_models = await store.ollama_status()
    return InstalledResponse(models=store.get_store().installed() + ollama_models, ollama=ollama)


@router.post("/{model_id}/download", response_model=DownloadState)
async def start_download(model_id: str) -> DownloadState | JSONResponse:
    try:
        return store.get_store().start(model_id)
    except KeyError as exc:
        raise _not_found(model_id) from exc
    except store.DiskSpaceError as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "neededBytes": exc.needed, "freeBytes": exc.free},
        )


@router.post("/{model_id}/cancel")
async def cancel_download(model_id: str, discard: bool = False) -> DownloadState:
    try:
        return await store.get_store().cancel(model_id, discard=discard)
    except KeyError as exc:
        raise _not_found(model_id) from exc


@router.get("/downloads")
async def list_downloads() -> DownloadsResponse:
    return DownloadsResponse(downloads=store.get_store().downloads())


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: str) -> Response:
    if model_id.startswith("ollama:"):
        raise HTTPException(status_code=409, detail="Remove Ollama models from Ollama itself.")
    try:
        await store.get_store().delete(model_id)
    except store.ActiveModelError as exc:
        raise HTTPException(
            status_code=409, detail="This model is running. Stop it before removing it."
        ) from exc
    except KeyError as exc:
        raise _not_found(model_id) from exc
    return Response(status_code=204)


@router.put("/engine")
async def put_engine(body: EngineConfigRequest) -> EngineConfigResponse:
    n_ctx = await engine.fetch_n_ctx(body.port) if body.port is not None else None
    engine.set_engine(body.port, body.modelId, n_ctx)
    return EngineConfigResponse(baseUrl=engine.base_url(), modelId=engine.active_model_id())
