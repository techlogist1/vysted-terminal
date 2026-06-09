"""Tests for the search-tiers router — the guided SearXNG flow surface (R7 Component 2).

The router is a thin wire over :mod:`services.searxng_manager`; these tests
pin the wiring (routes exist, delegate to the process-global manager, return
the state-machine snapshot verbatim) with the docker subprocess + health seams
monkeypatched at module level — no docker, no network, ever.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import create_app
from services import searxng_manager
from services.searxng_manager import (
    CONTAINER_NAME,
    STATE_DOCKER_PRESENT_NOT_SETUP,
    STATE_NOT_INSTALLED_DOCKER,
    STATE_PULLING,
    STATE_READY,
)

_VERSION_OK = json.dumps(
    {
        "Client": {"Version": "27.4.0"},
        "Server": {"Version": "27.4.0", "Platform": {"Name": "OrbStack"}},
    }
)


@pytest.fixture(autouse=True)
def _fresh_manager(monkeypatch, tmp_path):
    """Isolate the process-global manager + data dir for every router test."""
    monkeypatch.setenv("VYSTED_DATA_DIR", str(tmp_path))
    searxng_manager.reset_for_tests()
    yield
    searxng_manager.reset_for_tests()


def _fake_docker(responses: dict[str, tuple[int, str, str]]):
    """A module-level ``_run_docker`` replacement keyed by subcommand."""

    calls: list[tuple[str, ...]] = []

    async def runner(*args: str, timeout: float | None = None) -> tuple[int, str, str]:
        calls.append(args)
        return responses.get(args[0], (1, "", f"no fake response for docker {args[0]}"))

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def test_status_route_reports_not_installed_docker(monkeypatch) -> None:
    monkeypatch.setattr(
        searxng_manager,
        "_run_docker",
        _fake_docker({"version": (127, "", "docker CLI not found")}),
    )
    client = TestClient(create_app())

    response = client.get("/search/searxng/status")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == STATE_NOT_INSTALLED_DOCKER
    assert body["docker"]["cli_present"] is False
    assert body["container_name"] == CONTAINER_NAME


def test_status_route_reports_ready_with_url(monkeypatch) -> None:
    monkeypatch.setattr(
        searxng_manager,
        "_run_docker",
        _fake_docker(
            {
                "version": (0, _VERSION_OK, ""),
                "inspect": (0, "running\n", ""),
                "port": (0, "127.0.0.1:8888\n", ""),
            }
        ),
    )

    async def healthy(_url: str) -> bool:
        return True

    monkeypatch.setattr(searxng_manager, "_probe_health", healthy)
    client = TestClient(create_app())

    body = client.get("/search/searxng/status").json()

    assert body["state"] == STATE_READY
    assert body["url"] == "http://127.0.0.1:8888"
    assert body["docker"]["runtime"] == "OrbStack"
    # The READY manager now routes the SearXNG backend's autodetect.
    assert searxng_manager.manager.ready_base_url() == "http://127.0.0.1:8888"


def test_setup_route_kicks_off_the_guided_setup(monkeypatch) -> None:
    """POST /setup delegates to begin_setup and returns its immediate snapshot."""
    calls: list[str] = []

    def fake_begin_setup() -> dict[str, object]:
        calls.append("begin_setup")
        return {"state": STATE_PULLING, "detail": "starting guided setup — checking docker"}

    monkeypatch.setattr(searxng_manager.manager, "begin_setup", fake_begin_setup)
    client = TestClient(create_app())

    response = client.post("/search/searxng/setup")

    assert response.status_code == 200
    assert response.json()["state"] == STATE_PULLING
    assert calls == ["begin_setup"]


def test_teardown_route_stops_and_removes_the_container(monkeypatch) -> None:
    runner = _fake_docker(
        {
            "version": (0, _VERSION_OK, ""),
            "inspect": (1, "", f"Error: No such object: {CONTAINER_NAME}"),
            "stop": (0, f"{CONTAINER_NAME}\n", ""),
            "rm": (0, f"{CONTAINER_NAME}\n", ""),
        }
    )
    monkeypatch.setattr(searxng_manager, "_run_docker", runner)
    client = TestClient(create_app())

    response = client.post("/search/searxng/teardown")

    assert response.status_code == 200
    assert response.json()["state"] == STATE_DOCKER_PRESENT_NOT_SETUP
    subcommands = [call[0] for call in runner.calls]
    assert "stop" in subcommands and "rm" in subcommands
