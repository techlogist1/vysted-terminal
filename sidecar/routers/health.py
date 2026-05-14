"""Health router — the liveness probe the Tauri core polls on app launch."""

from __future__ import annotations

from fastapi import APIRouter

from services.provider_registry import active_providers

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness probe consumed by the Tauri core and by clients."""
    return {
        "status": "ok",
        "service": "vysted-sidecar",
        "version": "0.2.0",
        "providers": active_providers(),
    }
