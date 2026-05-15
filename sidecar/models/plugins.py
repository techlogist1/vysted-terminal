"""Plugin Pydantic models.

Mirrors the ``PluginPersistedConfig`` interface in ``types/plugin-runtime.ts``
1:1 — change the TS interface and this model in the same commit (see CLAUDE.md
Gotchas: ``types/data.ts`` mirrors ``sidecar/models/`` by hand).

The sidecar persists this opaque blob; capability negotiation and lifecycle
supervision live in the host runtime, not here. ``settings`` is a free-form
dict the host hands the plugin via ``PluginConfig.settings`` at
``initialize()`` time — the sidecar never inspects it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PluginConfigPayload(BaseModel):
    """Per-plugin persisted config — mirrors ``PluginPersistedConfig`` in TS."""

    plugin_id: str
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)
    granted_secret_ids: list[str] = Field(default_factory=list)


class PluginConfigUpdate(BaseModel):
    """PUT/POST body for updating a plugin's config (id comes from the URL)."""

    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)
    granted_secret_ids: list[str] = Field(default_factory=list)
