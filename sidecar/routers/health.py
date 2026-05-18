"""Health router — the liveness probe the Tauri core polls on app launch."""

from __future__ import annotations

from fastapi import APIRouter, Request

from services.provider_registry import active_providers

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Liveness probe consumed by the Tauri core and by clients.

    The version string is read from the FastAPI app instance (set in
    ``app.py::create_app`` from the canonical version-bump location) so a
    release-time edit to ``FastAPI(version=...)`` propagates here without
    a second hardcoded source of truth. Phase 8 hot-patch (was hardcoded
    ``"0.2.1"`` and silently drifted 5 releases — finding
    UC1-health-version-stale).
    """
    return {
        "status": "ok",
        "service": "vysted-sidecar",
        "version": request.app.version,
        "providers": active_providers(),
    }
