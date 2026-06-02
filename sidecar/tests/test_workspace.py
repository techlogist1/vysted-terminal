"""Tests for the /workspace save/list/load/delete endpoints.

``VYSTED_DATA_DIR`` is monkeypatched to a per-test ``tmp_path`` so the workspace
files land in a temporary directory and never touch the developer's real data
dir. ``config.get_data_dir`` reads the env var on every call, so no module
reload is needed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _temp_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Point the sidecar's data dir at a temporary directory for every test."""
    monkeypatch.setenv("VYSTED_DATA_DIR", str(tmp_path))


def _sample_workspace(name: str = "research") -> dict:
    """A workspace body shaped like what the frontend serialises."""
    return {
        "name": name,
        "layout": {"grid": {"root": {}}, "panels": {"chart": {}}},
        "enabledModules": {"chart": True, "watchlist": False, "platform": True},
    }


def test_list_is_empty_initially(client: TestClient) -> None:
    assert client.get("/workspace").json() == []


def test_save_then_list_returns_the_name(client: TestClient) -> None:
    response = client.post(
        "/workspace", json={"name": "research", "workspace": _sample_workspace()}
    )
    assert response.status_code == 200
    assert client.get("/workspace").json() == ["research"]


def test_round_trip_preserves_the_body(client: TestClient) -> None:
    workspace = _sample_workspace()
    client.post("/workspace", json={"name": "research", "workspace": workspace})
    loaded = client.get("/workspace/research").json()
    assert loaded == workspace


def test_save_overwrites_an_existing_workspace(client: TestClient) -> None:
    client.post("/workspace", json={"name": "research", "workspace": _sample_workspace()})
    updated = _sample_workspace()
    updated["enabledModules"]["watchlist"] = True
    client.post("/workspace", json={"name": "research", "workspace": updated})
    assert client.get("/workspace/research").json() == updated
    assert client.get("/workspace").json() == ["research"]


def test_list_is_sorted(client: TestClient) -> None:
    for name in ("zeta", "alpha", "mu"):
        client.post("/workspace", json={"name": name, "workspace": _sample_workspace(name)})
    assert client.get("/workspace").json() == ["alpha", "mu", "zeta"]


def test_load_missing_workspace_is_404(client: TestClient) -> None:
    assert client.get("/workspace/does-not-exist").status_code == 404


def test_delete_removes_the_workspace(client: TestClient) -> None:
    client.post("/workspace", json={"name": "research", "workspace": _sample_workspace()})
    assert client.delete("/workspace/research").status_code == 204
    assert client.get("/workspace").json() == []
    assert client.get("/workspace/research").status_code == 404


def test_delete_missing_workspace_is_404(client: TestClient) -> None:
    assert client.delete("/workspace/does-not-exist").status_code == 404


def test_unsafe_name_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/workspace",
        json={"name": "../escape", "workspace": _sample_workspace()},
    )
    assert response.status_code == 400


def test_corrupt_file_degrades_to_404_not_500(client: TestClient) -> None:
    """A torn/corrupt autosave (e.g. an old pre-atomic-write race) must not 500.

    The frontend's restore path falls back to the default layout on a 404, so a
    damaged blob degrades gracefully instead of dead-ending the boot.
    """
    from config import get_workspaces_dir
    from services.workspace_store import WORKSPACE_SUFFIX

    # Write a file that is valid JSON followed by garbage — exactly the shape the
    # observed concurrent-write race produced ("Extra data: ...").
    path = get_workspaces_dir() / f"__autosave__{WORKSPACE_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"name": "x"}\n  "stray": "tail"\n}', encoding="utf-8")

    response = client.get("/workspace/__autosave__")
    assert response.status_code == 404  # not 500


def test_save_is_atomic_under_concurrency(client: TestClient) -> None:
    """Concurrent saves of the same name must never leave a torn (invalid-JSON)
    file — each writer writes a temp then atomically renames, so the result is
    always one writer's complete body."""
    import json
    import threading

    from config import get_workspaces_dir
    from services import workspace_store
    from services.workspace_store import WORKSPACE_SUFFIX

    bodies = [{"name": "race", "n": i, "pad": "x" * (500 * (i + 1))} for i in range(12)]

    def _save(body: dict) -> None:
        for _ in range(8):
            workspace_store.save_workspace("race", body)

    threads = [threading.Thread(target=_save, args=(b,)) for b in bodies]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The file must be parseable (no torn write) and equal to one of the bodies.
    path = get_workspaces_dir() / f"race{WORKSPACE_SUFFIX}"
    loaded = json.loads(path.read_text(encoding="utf-8"))  # must not raise
    assert loaded in bodies
    # No stray temp files leaked.
    leftover = list(get_workspaces_dir().glob("*.tmp"))
    assert leftover == []
