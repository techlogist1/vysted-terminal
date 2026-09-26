"""Tests for the /workspace save/list/load/delete endpoints.

``VYSTED_DATA_DIR`` is monkeypatched to a per-test ``tmp_path`` so the workspace
files land in a temporary directory and never touch the developer's real data
dir. ``config.get_data_dir`` reads the env var on every call, so no module
reload is needed.
"""

from __future__ import annotations

from urllib.parse import quote

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


def test_save_keeps_the_previous_body_as_bak(client: TestClient) -> None:
    """R15-LIFECYCLE-002: an overwrite keeps one ``.bak`` of the previous body,
    and the backup never shows up as a workspace in the listing."""
    import json

    from config import get_workspaces_dir
    from services.workspace_store import WORKSPACE_SUFFIX

    first = _sample_workspace()
    first["portfolios"] = [{"id": "p1", "positions": [{"symbol": "AAPL", "quantity": 10}]}]
    client.post("/workspace", json={"name": "research", "workspace": first})
    bak = get_workspaces_dir() / f"research{WORKSPACE_SUFFIX}.bak"
    assert not bak.exists()

    second = _sample_workspace()
    client.post("/workspace", json={"name": "research", "workspace": second})
    assert json.loads(bak.read_text(encoding="utf-8")) == first
    assert client.get("/workspace/research").json() == second
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


@pytest.mark.parametrize(
    "name",
    ["Research: M&M", "Research: RELIANCE.NS", "My Layout (2)", "मेरा लेआउट"],
)
def test_any_name_round_trips(client: TestClient, name: str) -> None:
    """R15-CODE-FRONTEND-004: the frontend's research-space names ("Research:
    TICKER") and any other name save, load, list and delete — the store
    percent-encodes the filename instead of rejecting the name."""
    url = f"/workspace/{quote(name, safe='')}"
    workspace = _sample_workspace(name)
    assert client.post("/workspace", json={"name": name, "workspace": workspace}).status_code == 200
    assert client.get(url).json() == workspace
    assert client.get("/workspace").json() == [name]
    assert client.delete(url).status_code == 204
    assert client.get("/workspace").json() == []


def test_a_traversal_name_stays_inside_the_workspaces_directory(client: TestClient) -> None:
    from config import get_workspaces_dir

    name = "../escape"
    workspace = _sample_workspace(name)
    assert client.post("/workspace", json={"name": name, "workspace": workspace}).status_code == 200
    workspaces_dir = get_workspaces_dir()
    assert [path.parent for path in workspaces_dir.parent.rglob("*.vysted-workspace")] == [
        workspaces_dir
    ]
    assert client.get("/workspace").json() == [name]
    assert client.get(f"/workspace/{quote(name, safe='')}").json() == workspace


def test_an_empty_name_is_rejected_with_the_reason(client: TestClient) -> None:
    response = client.post("/workspace", json={"name": "   ", "workspace": {}})
    assert response.status_code == 400
    assert response.json()["detail"] == "A workspace name is required."


def test_a_32_char_devanagari_name_saves(client: TestClient) -> None:
    """R15-UI-082: percent-encoding every non-ASCII byte inflated a Devanagari
    name to ~9 encoded bytes per character, so a 32-character name (86 raw
    UTF-8 bytes) tripped the 200-byte encoded-stem cap as "too long" even
    though it is nowhere near the filesystem's 255-byte filename limit. Only
    unsafe/control characters are percent-encoded now, so this saves."""
    name = " ".join(["मेरा लेआउट"] * 3)  # 32 characters, 86 UTF-8 bytes
    workspace = _sample_workspace(name)
    response = client.post("/workspace", json={"name": name, "workspace": workspace})
    assert response.status_code == 200
    assert client.get("/workspace").json() == [name]


def test_a_name_whose_encoded_bytes_exceed_the_cap_is_still_rejected(
    client: TestClient,
) -> None:
    """The byte cap still fires — now measured in encoded UTF-8 bytes, not
    code points, so a long run of characters that DO need encoding (here,
    literal dots — always escaped to keep dot-segments out of the stem) is
    still caught before it would produce an unusable filename."""
    name = "." * 90  # each '.' encodes to the 3-byte "%2E" -> 270 bytes
    response = client.post("/workspace", json={"name": name, "workspace": _sample_workspace(name)})
    assert response.status_code == 400
    assert "too long" in response.json()["detail"]


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


def test_corrupt_workspace_is_quarantined_and_served_from_bak(client: TestClient) -> None:
    """R15-DATA-090: a corrupt file is kept as ``.corrupt-*``, the last good
    ``.bak`` is served and restored, and the next save leaves ``.bak`` parseable."""
    import json

    from config import get_workspaces_dir
    from services.workspace_store import WORKSPACE_SUFFIX

    good = _sample_workspace("research")
    client.post("/workspace", json={"name": "research", "workspace": good})
    client.post("/workspace", json={"name": "research", "workspace": {**good, "v": 2}})
    path = get_workspaces_dir() / f"research{WORKSPACE_SUFFIX}"
    path.write_text('{"trunc', encoding="utf-8")

    response = client.get("/workspace/research")
    assert response.status_code == 200
    assert response.json() == good
    quarantined = list(get_workspaces_dir().glob(f"research{WORKSPACE_SUFFIX}.corrupt-*"))
    assert [p.read_text(encoding="utf-8") for p in quarantined] == ['{"trunc']

    path.write_text("[]", encoding="utf-8")  # valid JSON, not an object: corrupt too
    client.post("/workspace", json={"name": "research", "workspace": {**good, "v": 3}})
    bak = get_workspaces_dir() / f"research{WORKSPACE_SUFFIX}.bak"
    assert json.loads(bak.read_text(encoding="utf-8")) == good
    assert client.get("/workspace").json() == ["research"]


def test_non_object_workspace_without_backup_is_404_not_500(client: TestClient) -> None:
    from config import get_workspaces_dir
    from services.workspace_store import WORKSPACE_SUFFIX

    path = get_workspaces_dir() / f"notes{WORKSPACE_SUFFIX}"
    path.write_text("[1, 2]", encoding="utf-8")

    assert client.get("/workspace/notes").status_code == 404
    assert client.get("/workspace").json() == []


def test_a_disk_failure_on_save_is_a_detailed_507(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-CODE-FRONTEND-019: an OSError is not a bare 500 without CORS headers."""
    from services import workspace_store

    def _read_only(*_args: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(workspace_store, "save_workspace", _read_only)
    response = client.post("/workspace", json={"name": "x", "workspace": _sample_workspace()})

    assert response.status_code == 507
    assert response.json()["detail"] == "Could not write the workspace: Permission denied"
