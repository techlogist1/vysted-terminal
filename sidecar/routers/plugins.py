"""Plugins router — per-plugin config CRUD backed by local SQLite.

Owned by Teammate B (Phase 2, plugin runtime). Browser storage is NOT used for
plugin config — the sidecar-owned-persistence pattern from Phase 1
(``portfolio_db``, ``workspace_store``) extends here. The TypeScript
``PluginRuntime`` calls these endpoints to load and persist each plugin's
``PluginPersistedConfig`` (defined in ``types/plugin-runtime.ts``).

This file is mounted by ``app.create_app`` — only edit this file, not
``app.py`` (apart from the one-line tuple addition).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from models.plugins import PluginConfigPayload, PluginConfigUpdate
from services import plugins_store

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
def list_plugin_configs() -> list[PluginConfigPayload]:
    """Return every persisted plugin config."""
    return plugins_store.list_configs()


@router.get("/{plugin_id}/config")
def get_plugin_config(plugin_id: str) -> PluginConfigPayload:
    """Return one plugin's stored config; 404 if it has never been saved."""
    config = plugins_store.get_config(plugin_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"plugin {plugin_id!r} has no stored config")
    return config


@router.post("/{plugin_id}/config")
def save_plugin_config(plugin_id: str, payload: PluginConfigUpdate) -> PluginConfigPayload:
    """Insert or replace a plugin's stored config; returns the persisted record."""
    full = PluginConfigPayload(
        plugin_id=plugin_id,
        enabled=payload.enabled,
        settings=payload.settings,
        granted_secret_ids=payload.granted_secret_ids,
    )
    return plugins_store.upsert_config(full)


@router.delete("/{plugin_id}/config", status_code=status.HTTP_204_NO_CONTENT)
def delete_plugin_config(plugin_id: str) -> Response:
    """Delete a plugin's stored config; 404 if it has never been saved."""
    if not plugins_store.delete_config(plugin_id):
        raise HTTPException(status_code=404, detail=f"plugin {plugin_id!r} has no stored config")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
