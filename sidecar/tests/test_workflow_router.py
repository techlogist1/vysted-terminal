"""Tests for the ``/workflow`` router's wire behaviour (run stream + request contract)."""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient


def _spec(edges: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "id": "wf-router",
        "name": "Router test",
        "nodes": [{"id": "a", "type": "flow.sleep", "position": {"x": 0, "y": 0}}],
        "edges": edges,
    }


def _frames(body: str) -> list[dict[str, Any]]:
    return [json.loads(chunk[len("data: ") :]) for chunk in body.split("\n\n") if chunk.strip()]


def test_dangling_edge_yields_one_run_error_frame(client: TestClient) -> None:
    dangling = {
        "id": "e1",
        "sourceNode": "a",
        "sourcePort": "value",
        "targetNode": "ghost",
        "targetPort": "value",
    }
    response = client.post("/workflow/run", json={"spec": _spec([dangling])})

    assert response.status_code == 200
    frames = _frames(response.text)
    errors = [f for f in frames if f["kind"] == "run-error"]
    assert len(errors) == 1
    assert "edge e1 references unknown target node 'ghost'" in errors[0]["message"]
    # The run is opened so the client can key the error to a run id.
    assert [f["kind"] for f in frames] == ["run-start", "run-error"]
    assert frames[0]["runId"] == errors[0]["runId"]
