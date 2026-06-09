"""Tests for the search-tiers router — the guided SearXNG flow surface (R7 Component 2).

The router is a thin wire over :mod:`services.searxng_manager`; these tests
pin the wiring (routes exist, delegate to the process-global manager, return
the state-machine snapshot verbatim) with the docker subprocess + health seams
monkeypatched at module level — no docker, no network, ever.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import create_app
from services import searxng_manager
from services.searxng_manager import (
    CONTAINER_NAME,
    STATE_DOCKER_PRESENT_NOT_SETUP,
    STATE_ERROR,
    STATE_NOT_INSTALLED_DOCKER,
    STATE_PULLING,
    STATE_READY,
    STATE_STARTING,
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


@pytest.mark.asyncio
async def test_setup_failure_is_observable_through_the_status_poll(monkeypatch) -> None:
    """The wire contract: after a failed background setup, GET /status says error(reason).

    Regression: refresh() used to re-derive unconditionally once the setup task
    was done, so the very first poll after a failed pull returned
    docker_present_not_setup with reason=None — POST /setup never awaits setup()
    directly, so NO endpoint could ever return state=error. The poll IS the only
    surface the UI has ("pulling → starting → ready/error"); error must survive
    on it until a retry or teardown clears it.
    """
    responses = {
        "version": (0, _VERSION_OK, ""),
        "inspect": (1, "", f"Error: No such object: {CONTAINER_NAME}"),
        "pull": (1, "", "Error response from daemon: pull access denied"),
    }
    monkeypatch.setattr(searxng_manager, "_run_docker", _fake_docker(responses))

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://sidecar") as client:
        kicked = (await client.post("/search/searxng/setup")).json()
        assert kicked["state"] == STATE_PULLING

        # Poll exactly like the UI does until the guided flow settles.
        body: dict[str, object] = kicked
        for _ in range(500):
            response = await client.get("/search/searxng/status")
            assert response.status_code == 200
            body = response.json()
            if body["state"] not in (STATE_PULLING, STATE_STARTING):
                break
            await asyncio.sleep(0.01)

        assert body["state"] == STATE_ERROR
        assert "pull access denied" in str(body["reason"])

        # Sticky across polls — no silent re-derivation back to not_setup.
        again = (await client.get("/search/searxng/status")).json()
        assert again["state"] == STATE_ERROR
        assert "pull access denied" in str(again["reason"])

        # A retry clears the error through the same wire surface.
        retried = (await client.post("/search/searxng/setup")).json()
        assert retried["state"] == STATE_PULLING
        assert retried["reason"] is None

    # Settle the retry's background task so nothing leaks past the test.
    task = searxng_manager.manager._task
    if task is not None:
        await task


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
