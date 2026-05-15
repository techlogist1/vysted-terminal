"""Tests for the /plugins router and the SQLite plugins config store.

The ``temp_data_dir`` fixture redirects ``VYSTED_DATA_DIR`` at a ``tmp_path``;
``plugins_store`` resolves the database path per call so the env var fully
isolates each test's database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.plugins import PluginConfigPayload
from services import plugins_store


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Redirect the sidecar data directory to an isolated temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def _sample_payload(plugin_id: str = "example-plugin") -> PluginConfigPayload:
    return PluginConfigPayload(
        plugin_id=plugin_id,
        enabled=True,
        settings={"theme": "dark", "limit": 25},
        granted_secret_ids=["openbb-fmp-key"],
    )


# --------------------------------------------------------------------------
# plugins_store service — CRUD against a temp database
# --------------------------------------------------------------------------


def test_ensure_schema_is_idempotent(temp_data_dir: object) -> None:
    plugins_store._ensure_schema()
    plugins_store._ensure_schema()
    assert plugins_store.list_configs() == []


def test_upsert_and_list_config(temp_data_dir: object) -> None:
    stored = plugins_store.upsert_config(_sample_payload())
    assert stored.plugin_id == "example-plugin"
    assert stored.enabled is True
    assert stored.settings == {"theme": "dark", "limit": 25}
    assert stored.granted_secret_ids == ["openbb-fmp-key"]

    configs = plugins_store.list_configs()
    assert len(configs) == 1
    assert configs[0].plugin_id == "example-plugin"


def test_get_config_roundtrip(temp_data_dir: object) -> None:
    plugins_store.upsert_config(_sample_payload("openbb-odp"))
    fetched = plugins_store.get_config("openbb-odp")
    assert fetched is not None
    assert fetched.plugin_id == "openbb-odp"
    assert fetched.enabled is True


def test_get_missing_config_returns_none(temp_data_dir: object) -> None:
    assert plugins_store.get_config("does-not-exist") is None


def test_upsert_replaces_existing(temp_data_dir: object) -> None:
    plugins_store.upsert_config(_sample_payload())
    updated = plugins_store.upsert_config(
        PluginConfigPayload(
            plugin_id="example-plugin",
            enabled=False,
            settings={"theme": "light"},
            granted_secret_ids=[],
        )
    )
    assert updated.enabled is False
    assert updated.settings == {"theme": "light"}
    assert updated.granted_secret_ids == []
    # Still a single row — upsert, not insert.
    assert len(plugins_store.list_configs()) == 1


def test_delete_config(temp_data_dir: object) -> None:
    plugins_store.upsert_config(_sample_payload())
    assert plugins_store.delete_config("example-plugin") is True
    assert plugins_store.list_configs() == []


def test_delete_missing_config_returns_false(temp_data_dir: object) -> None:
    assert plugins_store.delete_config("does-not-exist") is False


# --------------------------------------------------------------------------
# /plugins router — CRUD over HTTP
# --------------------------------------------------------------------------


def test_list_plugin_configs_empty(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/plugins")
    assert response.status_code == 200
    assert response.json() == []


def test_save_plugin_config_endpoint(client: TestClient, temp_data_dir: object) -> None:
    response = client.post(
        "/plugins/example-plugin/config",
        json={
            "enabled": True,
            "settings": {"theme": "dark"},
            "granted_secret_ids": ["secret-a"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plugin_id"] == "example-plugin"
    assert body["enabled"] is True
    assert body["settings"] == {"theme": "dark"}
    assert body["granted_secret_ids"] == ["secret-a"]


def test_save_then_get_endpoint(client: TestClient, temp_data_dir: object) -> None:
    client.post(
        "/plugins/openbb-odp/config",
        json={
            "enabled": False,
            "settings": {"providers": ["yfinance", "fmp"]},
            "granted_secret_ids": [],
        },
    )
    response = client.get("/plugins/openbb-odp/config")
    assert response.status_code == 200
    body = response.json()
    assert body["plugin_id"] == "openbb-odp"
    assert body["enabled"] is False
    assert body["settings"] == {"providers": ["yfinance", "fmp"]}


def test_get_unknown_plugin_returns_404(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/plugins/does-not-exist/config")
    assert response.status_code == 404


def test_save_replaces_existing_endpoint(client: TestClient, temp_data_dir: object) -> None:
    client.post(
        "/plugins/example/config",
        json={"enabled": True, "settings": {"a": 1}, "granted_secret_ids": []},
    )
    client.post(
        "/plugins/example/config",
        json={"enabled": False, "settings": {"b": 2}, "granted_secret_ids": ["sec"]},
    )
    body = client.get("/plugins/example/config").json()
    assert body["enabled"] is False
    assert body["settings"] == {"b": 2}
    assert body["granted_secret_ids"] == ["sec"]
    assert len(client.get("/plugins").json()) == 1


def test_delete_plugin_config_endpoint(client: TestClient, temp_data_dir: object) -> None:
    client.post(
        "/plugins/example/config",
        json={"enabled": True, "settings": {}, "granted_secret_ids": []},
    )
    response = client.delete("/plugins/example/config")
    assert response.status_code == 204
    assert client.get("/plugins").json() == []


def test_delete_unknown_plugin_returns_404(client: TestClient, temp_data_dir: object) -> None:
    assert client.delete("/plugins/does-not-exist/config").status_code == 404


def test_settings_blob_roundtrips_complex_types(client: TestClient, temp_data_dir: object) -> None:
    """Opaque settings blob preserves nested arrays/objects/numbers/booleans."""
    payload = {
        "enabled": True,
        "settings": {
            "nested": {"deep": {"value": 42, "flag": True}},
            "list": [1, "two", {"three": 3}],
            "null_value": None,
        },
        "granted_secret_ids": ["a", "b", "c"],
    }
    client.post("/plugins/complex/config", json=payload)
    body = client.get("/plugins/complex/config").json()
    assert body["settings"] == payload["settings"]
    assert body["granted_secret_ids"] == ["a", "b", "c"]
